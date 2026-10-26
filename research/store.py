"""Golden Dataset store: a SQLite index rebuilt from the authoritative JSONL.

``data/manual/golden_dataset.jsonl`` is the source of truth (written only by
``python -m pipeline.export golden`` from approved review rows). This module
loads it, decides which rows are eligible for public display, and builds a
SQLite database with an FTS5 full-text index for search and retrieval. The
database can be deleted and rebuilt at any time.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

TAG_FIELDS = (
    "behavior", "lapse_type", "trigger", "expectation", "checking", "check_frequency", "in_app_pain",
    "emotion", "outside_action", "tenure", "income_stability", "age_band", "money_source", "influencer", "unmet_need",
)
# Never shown to public viewers.
INTERNAL_FIELDS = ("reviewer", "reviewer_notes", "review_status", "stratum", "model_quote")
PUBLISHABLE_SOURCES = ("play_store", "reddit")
BULK_REVIEWER = "project owner (bulk)"

BOOL_COLUMNS = ("is_hypothesis", "individually_reviewed", "public")
NUMBER_COLUMNS = ("year", "confidence")

COLUMNS = (
    "record_id", "source", "platform_detail", "source_url", "collected_at", "published_at", "year", "kind", "language",
    "text", "context", "evidence_quote", "quote_status", "confidence", "is_hypothesis", "reason", "tagged_by",
    "prompt_version", "codebook_version", "review_status", "reviewer", "reviewer_notes", "individually_reviewed",
    "public", *TAG_FIELDS,
)


def load_golden(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def golden_version(path: Path) -> str:
    """Short content hash, so caches and answers can say which dataset they used."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.exists() else "empty"


def platform_detail(row: dict[str, Any]) -> str:
    """Play Store app ID, or r/<subreddit> for Reddit."""
    if row.get("app_id"):
        return str(row["app_id"])
    if row.get("subreddit"):
        return f"r/{row['subreddit']}"
    return str(row.get("source") or "unknown")


def is_public(row: dict[str, Any]) -> bool:
    """Approved, from a publishable source, with full provenance."""
    return (
        str(row.get("review_status") or "").lower() == "approved"
        and row.get("source") in PUBLISHABLE_SOURCES
        and bool(row.get("source_url"))
        and bool(row.get("collected_at"))
        and bool(row.get("record_id"))
    )


def normalise(row: dict[str, Any]) -> dict[str, Any]:
    published = row.get("published_at")
    year = row.get("year") or (int(str(published)[:4]) if published and str(published)[:4].isdigit() else None)
    out = {col: row.get(col) for col in COLUMNS}
    out.update(
        platform_detail=platform_detail(row),
        year=int(year) if year else None,
        individually_reviewed=(bool(row["individually_reviewed"]) if "individually_reviewed" in row
                               else bool(row.get("reviewer")) and row.get("reviewer") != BULK_REVIEWER),
        public=is_public(row),
        is_hypothesis=bool(row.get("is_hypothesis")) if row.get("is_hypothesis") is not None else None,
    )
    return out


def public_view(row: dict[str, Any]) -> dict[str, Any]:
    """The row without internal review fields."""
    return {k: v for k, v in row.items() if k not in INTERNAL_FIELDS}


def build_database(rows: Iterable[dict[str, Any]], db_path: Path) -> int:
    """(Re)create the SQLite index. Returns the number of rows stored."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    types = {c: "INTEGER" if c in BOOL_COLUMNS else "REAL" if c in NUMBER_COLUMNS else "TEXT" for c in COLUMNS}
    con.execute(f"CREATE TABLE golden ({', '.join(f'{c} {types[c]}' for c in COLUMNS)}, PRIMARY KEY (record_id))")
    # Tags are indexed as words ("pause sip mandate or payment") so plain-language queries match them.
    con.execute("CREATE VIRTUAL TABLE golden_fts USING fts5(record_id UNINDEXED, text, evidence_quote, reason, context, tags)")
    count = 0
    for row in map(normalise, rows):
        con.execute(f"INSERT OR REPLACE INTO golden VALUES ({', '.join('?' for _ in COLUMNS)})",
                    [None if row[c] is None else int(row[c]) if c in BOOL_COLUMNS else row[c] if c in NUMBER_COLUMNS else str(row[c])
                     for c in COLUMNS])
        tags = " ".join(str(row[f]).replace("_", " ") for f in TAG_FIELDS if row[f] and row[f] not in ("unclear", "none", "no_lapse"))
        con.execute("INSERT INTO golden_fts VALUES (?, ?, ?, ?, ?, ?)",
                    (row["record_id"], row["text"] or "", row["evidence_quote"] or "", row["reason"] or "", row["context"] or "", tags))
        count += 1
    con.commit()
    con.close()
    tmp.replace(db_path)
    return count


def read_rows(db_path: Path, public_only: bool = True) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = []
    for r in con.execute("SELECT * FROM golden"):
        row = dict(r)
        for c in BOOL_COLUMNS:
            row[c] = None if row[c] is None else bool(row[c])
        if row["year"] is not None:
            row["year"] = int(row["year"])
        rows.append(row)
    con.close()
    return [public_view(r) for r in rows if r["public"]] if public_only else rows
