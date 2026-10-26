"""Data quality and validation metrics, computed from the pipeline's own files.

``build_quality`` reads raw, processed, review and Golden Dataset files and
returns plain numbers. Nothing is estimated: a metric the pipeline does not
record is reported as ``None`` with a note.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Connectors that exist in code. A source counts as operational only if a raw
# file from a successful run exists.
CONNECTORS = {
    "play_store": {"name": "Google Play reviews", "module": "collect/play_store.py", "method": "Unofficial google-play-scraper library (user accepted ToS risk)", "ai_processing": True},
    "youtube": {"name": "YouTube comments", "module": "collect/youtube.py", "method": "Official YouTube Data API v3", "ai_processing": False},
    "reddit": {"name": "Reddit posts and comments", "module": "collect/reddit_apify.py", "method": "Apify actor automation-lab/reddit-scraper (third-party scraping; user accepted ToS risk)", "ai_processing": True},
}
NOT_INTEGRATED = {
    "app_store": "Apple App Store reviews — no connector; official API only for apps we own.",
    "tradingqna": "TradingQ&A forum — no connector; no verified permitted API.",
}
RAW_PREFIX = {"play_store": "play_store_", "youtube": "youtube_", "reddit": "reddit_"}


def _jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def _source_of(row: dict[str, Any]) -> str:
    return row.get("source") or (row.get("metadata") or {}).get("source") or "unknown"


def _date(row: dict[str, Any]) -> str | None:
    m = row.get("metadata") or {}
    return m.get("reviewed_at") or m.get("published_at")


def raw_stats(raw_dir: Path) -> dict[str, Any]:
    per_source: dict[str, dict[str, Any]] = defaultdict(lambda: {"records": 0, "files": 0, "last_collected": None, "missing_provenance": 0})
    for path in sorted(raw_dir.glob("*.jsonl")):
        for row in _jsonl(path):
            s = per_source[_source_of(row)]
            s["records"] += 1
            if not (row.get("record_id") and row.get("source_url") and row.get("collected_at")):
                s["missing_provenance"] += 1
            if row.get("collected_at") and (s["last_collected"] is None or row["collected_at"] > s["last_collected"]):
                s["last_collected"] = row["collected_at"]
        source = next((k for k, p in RAW_PREFIX.items() if path.name.startswith(p)), None)
        if source:
            per_source[source]["files"] += 1
    return dict(per_source)


def clean_stats(processed: Path) -> dict[str, Any]:
    per_source: dict[str, dict[str, Any]] = defaultdict(lambda: {"records": 0, "first": None, "last": None, "undated": 0})
    languages: Counter[str] = Counter()
    for row in _jsonl(processed / "clean.jsonl"):
        s = per_source[_source_of(row)]
        s["records"] += 1
        languages[row.get("language") or "unknown"] += 1
        d = _date(row)
        if not d:
            s["undated"] += 1
            continue
        d = str(d)[:10]
        s["first"] = d if s["first"] is None or d < s["first"] else s["first"]
        s["last"] = d if s["last"] is None or d > s["last"] else s["last"]
    dropped = Counter(r.get("drop_reason") for r in _jsonl(processed / "dropped.jsonl"))
    return {"per_source": dict(per_source), "languages": dict(languages), "dropped": dict(dropped)}


def filter_stats(processed: Path) -> dict[str, Any]:
    rows = list(_jsonl(processed / "filter_results.jsonl"))
    return {"labelled": len(rows), "labels": dict(Counter(str(r.get("relevant")) for r in rows)),
            "errors": sum(1 for r in rows if r.get("error")), "rescued": sum(bool(r.get("rescued_by_rule")) for r in rows),
            "by_source": dict(Counter(r.get("source") for r in rows))}


def tag_stats(processed: Path, results_files: list[str]) -> dict[str, Any]:
    rows = [r for f in results_files for r in _jsonl(processed / f)]
    ok = [r for r in rows if r.get("status") == "ok"]
    return {
        "tagged": len(rows), "ok": len(ok), "failed": len(rows) - len(ok),
        "by_model": dict(Counter(r.get("tagged_by") or r.get("model") for r in rows)),
        "quote_status": dict(Counter(r.get("quote_status") for r in ok)),
        "reason_flags": sum(1 for r in ok if r.get("reason_unsupported_terms")),
        "failures": [{"record_id": r["record_id"], "error": r.get("error"), "model": r.get("tagged_by") or r.get("model")} for r in rows if r.get("status") != "ok"][:200],
        "quote_problems": [{"record_id": r["record_id"], "status": r.get("quote_status"), "score": r.get("quote_score")}
                           for r in ok if r.get("quote_status") in ("hidden", "repaired")][:200],
    }


def golden_stats(golden_rows: list[dict[str, Any]], review_workbook: Path) -> dict[str, Any]:
    from research.store import BULK_REVIEWER

    statuses: Counter[str] = Counter()
    if review_workbook.exists():
        from openpyxl import load_workbook

        ws = load_workbook(review_workbook, read_only=True).active
        rows = ws.iter_rows(values_only=True)
        header = list(next(rows))
        col = header.index("review_status")
        statuses = Counter(str(v[col] or "pending").strip().lower() for v in rows)
    return {
        "records": len(golden_rows),
        "by_source": dict(Counter(r.get("source") for r in golden_rows)),
        "individually_reviewed": sum(1 for r in golden_rows if r.get("reviewer") and r.get("reviewer") != BULK_REVIEWER),
        "bulk_approved": sum(1 for r in golden_rows if r.get("reviewer") == BULK_REVIEWER),
        "missing_provenance": sum(1 for r in golden_rows if not (r.get("record_id") and r.get("source_url") and r.get("collected_at"))),
        "exact_quotes": sum(1 for r in golden_rows if r.get("quote_status") == "exact" and r.get("evidence_quote")),
        "review_workbook": review_workbook.name if review_workbook.exists() else None,
        "review_statuses": dict(statuses),
    }


def collection_runs(raw_dir: Path) -> list[dict[str, Any]]:
    """Logged runs. Only the Reddit connector keeps a run ledger today."""
    ledger = raw_dir / "reddit_apify_ledger.json"
    runs = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
    return [{"source": "reddit", "step": r.get("step"), "status": r.get("status"), "at": r.get("at"), "items": r.get("items"),
             "cost_usd": r.get("cost_usd")} for r in runs]


def source_status(raw: dict[str, Any], clean: dict[str, Any], runs: list[dict[str, Any]], allowed_ai: list[str]) -> list[dict[str, Any]]:
    out = []
    for key, info in CONNECTORS.items():
        r = raw.get(key, {})
        c = clean["per_source"].get(key, {})
        tested = r.get("records", 0) > 0
        failures = sum(1 for run in runs if run["source"] == key and run.get("status") not in (None, "SUCCEEDED"))
        out.append({
            "source": key, "name": info["name"], "module": info["module"], "method": info["method"],
            "integrated": True, "operational": tested,
            "status": "Tested — data collected" if tested else "Connector exists — not yet run successfully",
            "raw_records": r.get("records", 0), "clean_records": c.get("records", 0),
            "date_first": c.get("first"), "date_last": c.get("last"), "undated": c.get("undated", 0),
            "last_collected": r.get("last_collected"), "logged_failures": failures,
            "ai_processing": key in allowed_ai,
        })
    for key, note in NOT_INTEGRATED.items():
        out.append({"source": key, "name": note.split(" — ")[0], "integrated": False, "operational": False, "status": "Not integrated", "note": note})
    return out


def sampling_context(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Facts the dashboard's disclosures quote, read from config and pipeline outputs."""
    processed = root / config["paths"]["processed"]
    raw_dir = root / config["paths"]["raw"]
    shortlist = raw_dir / "reddit_shortlist.json"
    agreement = None
    reports = sorted(processed.glob("tag_agreement_report_*.json"))
    if reports:
        report = json.loads(reports[-1].read_text(encoding="utf-8"))
        agreement = {"file": reports[-1].name, "items": report.get("items_compared"), "models": report.get("models"),
                     "core": report.get("core_fields"), "passed": report.get("passed")}
    return {
        "play_max_per_app": config["collection"]["play_store"]["max_reviews_per_app"],
        "play_apps": len(config["collection"]["play_store"]["apps"]),
        "reddit_subreddits": len(config["collection"]["reddit"]["subreddits"]),
        "reddit_threads": len(json.loads(shortlist.read_text(encoding="utf-8"))) if shortlist.exists() else None,
        "youtube_retention_days": config["collection"]["youtube"]["retention_days"],
        "agreement": agreement,
        "small_sample": 30,
    }


def build_quality(root: Path, config: dict[str, Any], golden_rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw_dir = root / config["paths"]["raw"]
    processed = root / config["paths"]["processed"]
    raw = raw_stats(raw_dir)
    clean = clean_stats(processed)
    runs = collection_runs(raw_dir)
    results_files = [m["results_file"] for m in config["pipeline"]["tagging"]["models"]]
    allowed_ai = config["pipeline"]["relevance"]["allowed_sources"]
    return {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "raw": raw,
        "raw_total": sum(s["records"] for s in raw.values()),
        "clean": clean,
        "clean_total": sum(s["records"] for s in clean["per_source"].values()),
        "filter": filter_stats(processed),
        "tagging": tag_stats(processed, results_files),
        "golden": golden_stats(golden_rows, root / config["paths"]["review"] / "golden_sample_300.xlsx"),
        "collection_runs": runs,
        "sources": source_status(raw, clean, runs, allowed_ai),
        "unlogged": "Play Store and YouTube collectors print skipped apps/videos but do not persist a run log, so their collection failures are not counted.",
        "context": sampling_context(root, config),
    }
