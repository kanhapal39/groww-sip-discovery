"""Tagging module — tags relevant records against codebook.yaml with an LLM.

Responsibility: Send records the filter marked yes/unsure to the configured
model (Groq ``openai/gpt-oss-120b``) with a fixed codebook system prompt,
validate every value against the codebook, check that evidence quotes are
verbatim, and survive rate limits so a long run can be stopped and resumed.

Usage:
    python -m pipeline.tag pilot        # 50 yes/unsure items, stratified by app
    python -m pipeline.tag report       # pilot summary
    python -m pipeline.tag full [--auto-resume]

Outputs (gitignored): ``data/processed/tag_results.jsonl`` (one row per
record ID) and ``data/processed/tag_usage.jsonl`` (one row per request).
Only sources in ``pipeline.relevance.allowed_sources`` are tagged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml
from rapidfuzz import fuzz

from collect.youtube import load_api_key
from pipeline.filter import (
    FatalError,
    GroqClient,
    InvalidOutput,
    Limits,
    RequestTooLarge,
    ResultStore,
    RunSummary,
    append_usage,
    call_with_retries,
    group_key,
    sample_for_app,
    truncate_words,
    wait_for_capacity,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_VERSION = "tag-v4"
RELEVANCE_CODES = {"yes": "y", "unsure": "s"}  # anything else -> "x" (not filtered yet)
MAX_ITEM_ATTEMPTS = 2  # first try + one retry
# Terms a reason must not introduce when the text does not contain them.
REASON_TERMS = {
    "sip": re.compile(r"(?<!\w)sips?(?!\w)", re.IGNORECASE),
    "mandate": re.compile(r"(?<!\w)(?:e-?)?mandates?(?!\w)", re.IGNORECASE),
    "returns": re.compile(r"(?<!\w)returns?(?!\w)", re.IGNORECASE),
}


def load_codebook(codebook_path: str = "codebook.yaml") -> dict[str, Any]:
    """Load the codebook and check every field has unique value codes."""
    path = Path(codebook_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Codebook not found: {codebook_path}")
    with path.open(encoding="utf-8") as fh:
        codebook = yaml.safe_load(fh)
    for field in codebook.get("fields", []):
        codes = [v["code"] for v in field["values"]]
        if len(codes) != len(set(codes)):
            raise ValueError(f"duplicate value codes in field {field['id']}")
    return codebook


def code_maps(codebook: dict[str, Any]) -> dict[str, tuple[str, dict[str, str]]]:
    """{field code: (field id, {value code: value id})}."""
    return {f["code"]: (f["id"], {v["code"]: v["id"] for v in f["values"]}) for f in codebook["fields"]}


def build_system_prompt(codebook: dict[str, Any], max_reason_words: int) -> str:
    """Fixed system prompt: identical in every request for a given codebook."""
    lines = []
    for field in codebook["fields"]:
        values = "; ".join(f"{v['code']}={v['definition']}" for v in field["values"])
        lines.append(f"{field['code']} ({field['id']}) — {field['question']} {values}")
    order = ",".join(f'"{f["code"]}":..' for f in codebook["fields"])
    rules = "\n".join(f"- {rule}" for rule in codebook.get("rules", []))
    return f"""You tag Indian investor texts about SIPs (Systematic Investment Plans) and mutual funds for research.

For every item fill EVERY field below with exactly one code. Tag what the text states OR plainly implies. Use "u" only when the text gives nothing for that field.
Each item has: i (item number), rel (relevance flag from an earlier filter: y=yes, s=unsure, x=not filtered yet; information only, still fill every field), ctx (where the text came from; tag the text, not ctx), t (the text).

FIELDS (code (name) — question; value codes):
{chr(10).join(lines)}

RULES:
{rules}

Also return:
q = evidence quote: ONE continuous span copied exactly from t, character for character. Never join parts, never use "...", never fix spelling. Pick the span that best supports the behaviour/trigger/pain tags. "" if no span supports any tag.
rs = reason, at most {max_reason_words} words, describing only what the text says. Do not mention SIP, mandate or returns unless the text does.
c = confidence 0.0-1.0 for the tags as a whole.
h = true if any tag is plainly implied rather than stated; false if all are stated.

Worked examples (invented, not data):
{{"i":901,"t":"My SIP failed twice because the autopay mandate didn't work and support never replied. Moving to another app."}}
-> {{"i":901,"bh":"pa","lt":"iv","tr":"mp","ex":"u","ck":"ts","cf":"u","pn":"ma","em":"fr","oa":"su","te":"u","is":"u","ag":"u","ms":"u","if":"u","un":"mc","q":"the autopay mandate didn't work","rs":"instalments failed due to autopay mandate, support silent, switching apps","c":0.85,"h":false}}
{{"i":902,"t":"Started 2000 rs monthly from salary 3 years back for my daughter's education. I check returns every month."}}
-> {{"i":902,"bh":"co","lt":"na","tr":"u","ex":"sg","ck":"rn","cf":"m","pn":"no","em":"ne","oa":"u","te":"l","is":"ss","ag":"u","ms":"sl","if":"u","un":"u","q":"for my daughter's education","rs":"invests monthly from salary for daughter's education, checks monthly","c":0.8,"h":true}}
{{"i":903,"t":"I am a beginner, which fund should I choose? Totally confused"}}
-> {{"i":903,"bh":"st","lt":"na","tr":"u","ex":"u","ck":"u","cf":"u","pn":"fs","em":"cn","oa":"u","te":"n","is":"u","ag":"u","ms":"u","if":"u","un":"fg","q":"which fund should I choose?","rs":"beginner confused about which fund to choose","c":0.7,"h":true}}
{{"i":904,"t":"Not able to pause my SIP, there is no option in the app"}}
-> {{"i":904,"bh":"co","lt":"na","tr":"mf","ex":"u","ck":"u","cf":"u","pn":"sm","em":"fr","oa":"u","te":"u","is":"u","ag":"u","ms":"u","if":"u","un":"fx","q":"Not able to pause my SIP","rs":"cannot pause SIP, no option in app","c":0.8,"h":true}}
{{"i":905,"t":"There is no redemption option against the MF, not user friendly"}}
-> {{"i":905,"bh":"u","lt":"na","tr":"mf","ex":"u","ck":"u","cf":"u","pn":"rw","em":"fr","oa":"u","te":"u","is":"u","ag":"u","ms":"u","if":"u","un":"fr","q":"There is no redemption option against the MF","rs":"no redemption option for mutual funds","c":0.8,"h":false}}

Return only compact JSON: {{"r":[{{"i":<item number>,{order},"q":"..","rs":"..","c":0.0,"h":false}}]}} with exactly one entry per input item."""


def build_messages(batch: list[dict[str, Any]], system_prompt: str, max_text_words: int, max_context_words: int) -> list[dict[str, str]]:
    items = [
        {
            "i": i,
            "rel": RELEVANCE_CODES.get(r.get("relevant"), "x"),
            "ctx": truncate_words(r.get("prompt_context"), max_context_words),
            "t": truncate_words(r.get("text"), max_text_words),
        }
        for i, r in enumerate(batch, 1)
    ]
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(items, ensure_ascii=False, separators=(",", ":"))},
    ]


def validate_item(entry: dict[str, Any], maps: dict[str, tuple[str, dict[str, str]]], max_reason_words: int) -> dict[str, Any] | None:
    """Map short codes to full names; None if any value is missing or invalid."""
    tags: dict[str, Any] = {}
    for field_code, (field_id, values) in maps.items():
        code = entry.get(field_code)
        if not isinstance(code, str) or code not in values:
            return None
        tags[field_id] = values[code]
    confidence = entry.get("c")
    hypothesis = entry.get("h")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        return None
    if not isinstance(hypothesis, bool) or not isinstance(entry.get("q", ""), str) or not isinstance(entry.get("rs", ""), str):
        return None
    words = entry.get("rs", "").split()
    tags.update(
        confidence=float(confidence),
        is_hypothesis=hypothesis,
        model_quote=entry.get("q", ""),
        reason=" ".join(words[:max_reason_words]),
        reason_truncated=len(words) > max_reason_words,
    )
    return tags


def _reply_entries(content: str) -> list[Any]:
    """Entries from {"r": [...]} or a bare [...] list (some models drop the wrapper)."""
    for pattern in (r"\{.*\}", r"\[.*\]"):
        match = re.search(pattern, content or "", re.DOTALL)
        if not match:
            continue
        try:
            payload = json.loads(match.group(0))
        except ValueError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("r"), list):
            return payload["r"]
        if isinstance(payload, list):
            return payload
    return []


def parse_reply(content: str, batch_size: int, maps: dict[str, tuple[str, dict[str, str]]], max_reason_words: int) -> dict[int, dict[str, Any]]:
    parsed: dict[int, dict[str, Any]] = {}
    for entry in _reply_entries(content):
        if not isinstance(entry, dict):
            continue
        try:
            item = int(entry.get("i"))
        except (TypeError, ValueError):
            continue
        if not 1 <= item <= batch_size or item in parsed:
            continue
        tags = validate_item(entry, maps, max_reason_words)
        if tags is not None:
            parsed[item] = tags
    return parsed


def check_quote(quote: str, text: str, min_score: float) -> tuple[str | None, str, float | None]:
    """Return (quote to show, status, score).

    status: "none" (no quote), "exact", "repaired" (replaced by the closest
    span of the text) or "hidden" (closest span scored under ``min_score``).
    """
    quote = quote.strip()
    if not quote:
        return None, "none", None
    if quote in text:
        return quote, "exact", 100.0
    same_length = len(text.lower()) == len(text)
    haystack, needle = (text.lower(), quote.lower()) if same_length else (text, quote)
    alignment = fuzz.partial_ratio_alignment(needle, haystack)
    if alignment is None or alignment.score < min_score:
        return None, "hidden", round(alignment.score, 1) if alignment else 0.0
    start, end = alignment.dest_start, alignment.dest_end
    while start > 0 and text[start - 1].isalnum():  # never cut a word in half
        start -= 1
    while end < len(text) and text[end].isalnum():
        end += 1
    return text[start:end].strip(), "repaired", round(alignment.score, 1)


def unsupported_reason_terms(reason: str, text: str) -> list[str]:
    """Terms the reason mentions that the text does not."""
    return [term for term, pattern in REASON_TERMS.items() if pattern.search(reason) and not pattern.search(text)]


def make_row(record: dict[str, Any], tags: dict[str, Any] | None, model: str, codebook_version: Any, run: str, min_score: float, error: str | None = None) -> dict[str, Any]:
    metadata = record.get("metadata") or {}
    row: dict[str, Any] = {
        "record_id": record["record_id"],
        "source_url": record["source_url"],
        "collected_at": record["collected_at"],
        "source": record.get("source"),
        "app_id": metadata.get("app_id"),
        "year": record.get("year"),
        "relevance": record.get("relevant") or "not_filtered",
        "priority": record.get("priority_tier"),
        "status": "failed" if tags is None else "ok",
        "error": error,
        "model": model,
        "tagged_by": model,
        "prompt_version": PROMPT_VERSION,
        "codebook_version": codebook_version,
        "run": run,
        "tagged_at": datetime.now(timezone.utc).isoformat(),
    }
    if tags is None:
        return row
    text = record.get("text") or ""
    quote, status, score = check_quote(tags["model_quote"], text, min_score)
    row.update(tags)
    row.update(
        evidence_quote=quote,
        quote_status=status,
        quote_score=score,
        reason_unsupported_terms=unsupported_reason_terms(tags["reason"], text),
    )
    return row


def run_tagger(
    records: list[dict[str, Any]],
    client: GroqClient,
    store: ResultStore,
    usage_path: Path,
    settings: dict[str, Any],
    codebook: dict[str, Any],
    run: str,
    auto_resume: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> RunSummary:
    """Tag every record not already in ``store``.

    Too-large requests (HTTP 413 or a reply cut off at the token limit) are
    split in half and retried. Items missing or invalid in a reply are retried
    once in a later request, then stored with status "failed".
    """
    maps = code_maps(codebook)
    system_prompt = build_system_prompt(codebook, settings["max_reason_words"])
    pending = [r for r in records if r["record_id"] not in store]
    summary = RunSummary(requested=len(pending))
    size = settings["batch_size"]
    queue: list[list[dict[str, Any]]] = [pending[i : i + size] for i in range(0, len(pending), size)]
    retry: list[dict[str, Any]] = []
    attempts: Counter[str] = Counter()
    limits = Limits()
    est_tokens = None

    while queue or retry:
        if not queue:
            queue = [retry[i : i + size] for i in range(0, len(retry), size)]
            retry = []
        batch = queue.pop(0)
        stop = wait_for_capacity(limits, est_tokens, auto_resume, sleep, log)
        if stop:
            summary.stopped = stop
            return summary
        messages = build_messages(batch, system_prompt, settings["max_text_words"], settings["max_context_words"])
        too_large = ""
        try:
            response = call_with_retries(client, messages, usage_path, run, auto_resume, sleep, log)
        except (RequestTooLarge, InvalidOutput) as exc:
            response, too_large = None, str(exc)
        except FatalError as exc:
            summary.stopped = f"request rejected: {exc}"
            return summary
        if isinstance(response, str):
            summary.stopped = response
            return summary

        if response is not None:
            if response.finish_reason == "length":
                too_large = "reply cut off at max_completion_tokens"
            limits = response.limits
            tokens = int(response.usage.get("total_tokens") or 0)
            est_tokens = max(est_tokens or 0, tokens)
            summary.requests += 1
            summary.tokens += tokens
            append_usage(usage_path, {
                "at": datetime.now(timezone.utc).isoformat(), "run": run, "status": 200, "items": len(batch),
                "finish_reason": response.finish_reason, "prompt_tokens": response.usage.get("prompt_tokens"),
                "completion_tokens": response.usage.get("completion_tokens"), "total_tokens": tokens,
                "remaining_requests_day": limits.remaining_requests_day, "remaining_tokens_minute": limits.remaining_tokens_minute,
            })

        if too_large:
            if len(batch) > 1:
                half = len(batch) // 2
                log(f"Request failed ({too_large[:80]}); splitting {len(batch)} -> {half} + {len(batch) - half}")
                queue[:0] = [batch[:half], batch[half:]]
                continue
            store.add([make_row(batch[0], None, client.model, codebook.get("version"), run, settings["quote_min_score"], error=f"too large: {too_large[:200]}")])
            summary.done_this_run += 1
            summary.errors += 1
            continue

        parsed = parse_reply(response.content, len(batch), maps, settings["max_reason_words"])
        rows = []
        for i, record in enumerate(batch, 1):
            if i in parsed:
                rows.append(make_row(record, parsed[i], client.model, codebook.get("version"), run, settings["quote_min_score"]))
                continue
            attempts[record["record_id"]] += 1
            if attempts[record["record_id"]] < MAX_ITEM_ATTEMPTS:
                retry.append(record)
            else:
                rows.append(make_row(record, None, client.model, codebook.get("version"), run, settings["quote_min_score"], error="missing or invalid in reply after retry"))
        store.add(rows)
        for row in rows:
            summary.done_this_run += 1
            summary.errors += row["status"] == "failed"
            summary.labels[row.get("behavior") or "failed"] += 1
        log(f"  {summary.done_this_run}/{summary.requested} tagged, {summary.tokens:,} tokens")
    return summary


def tagging_inputs(processed: Path, allowed_sources: list[str]) -> list[dict[str, Any]]:
    """Clean records the filter marked yes/unsure, with relevance and context attached."""
    from pipeline.filter import item_context

    flags = {}
    results_path = processed / "filter_results.jsonl"
    if results_path.exists():
        with results_path.open(encoding="utf-8") as fh:
            for row in map(json.loads, fh):
                if row.get("relevant") in ("yes", "unsure"):
                    flags[row["record_id"]] = row["relevant"]
    records = []
    with (processed / "clean.jsonl").open(encoding="utf-8") as fh:
        for record in map(json.loads, fh):
            if record["record_id"] in flags and record.get("source") in allowed_sources:
                records.append({**record, "relevant": flags[record["record_id"]], "prompt_context": item_context(record)})
    return records


def pilot_sample(records: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    """Random sample split as evenly as possible across apps; unused share is reassigned."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[group_key(record)].append(record)
    rng = random.Random(seed)
    for key in groups:
        rng.shuffle(groups[key])
    sample: list[dict[str, Any]] = []
    while len(sample) < size and any(groups.values()):
        for key in sorted(groups):
            if groups[key] and len(sample) < size:
                sample.append(groups[key].pop())
    return sample


def pilot_report(processed: Path, store: ResultStore, usage_path: Path, settings: dict[str, Any], codebook: dict[str, Any], expected_items: int | None, run: str = "pilot", app: str | None = None) -> None:
    """Summarise one run, or every tagged row of ``app`` when given (tokens are for ``run``)."""
    texts = {}
    with (processed / "clean.jsonl").open(encoding="utf-8") as fh:
        for r in map(json.loads, fh):
            texts[r["record_id"]] = r["text"]
    rows = [r for r in store.results.values() if (r["app_id"] == app if app else r["run"] == run)]
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"{app or 'Run ' + run}: {len(rows)} items, {len(ok)} tagged, {len(rows) - len(ok)} failed")
    print("By app: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r["app_id"] for r in rows).items())))

    print("\n8 tagged items")
    for r in random.Random(settings["sample_seed"]).sample(ok, min(8, len(ok))):
        text = " ".join(texts[r["record_id"]].split())
        print(f"- [{r['app_id']}, {r['relevance']}] {text[:200]!r}")
        print(f"    behavior={r['behavior']} lapse={r['lapse_type']} trigger={r['trigger']} pain={r['in_app_pain']} "
              f"emotion={r['emotion']} need={r['unmet_need']} conf={r['confidence']} implied={r['is_hypothesis']}")
        print(f"    quote ({r['quote_status']}): {r['evidence_quote']!r}  reason: {r['reason']}")
        print(f"    {r['source_url']}")

    for field in ("lapse_type", "trigger"):
        print(f"\n{field}: " + ", ".join(f"{k} {v}" for k, v in Counter(r[field] for r in ok).most_common()))
    print("\n% unclear per field")
    for field in codebook["fields"]:
        share = 100 * sum(r[field["id"]] == "unclear" for r in ok) / max(len(ok), 1)
        print(f"  {field['id']:<17} {share:5.1f}%")

    statuses = Counter(r["quote_status"] for r in ok)
    print("\nQuote check: " + ", ".join(f"{k} {statuses[k]}" for k in ("exact", "repaired", "hidden", "none")))
    for r in ok:
        if r["quote_status"] in ("repaired", "hidden"):
            print(f"  {r['quote_status']} ({r['quote_score']}): model {r['model_quote']!r} -> shown {r['evidence_quote']!r}")
    flagged = [r for r in ok if r["reason_unsupported_terms"]]
    print(f"Reasons mentioning SIP/mandate/returns not in the text: {len(flagged)}")
    for r in flagged:
        print(f"  {r['reason_unsupported_terms']}: {r['reason']!r} | text: {' '.join(texts[r['record_id']].split())[:120]!r}")

    usage = [json.loads(l) for l in usage_path.open(encoding="utf-8") if l.strip()] if usage_path.exists() else []
    calls = [u for u in usage if u.get("run") == run and u.get("status") == 200]
    tokens = sum(u["total_tokens"] for u in calls)
    items = sum(u["items"] for u in calls) or 1
    print(f"\nTokens (run {run}): {tokens:,} over {len(calls)} requests (prompt {sum(u['prompt_tokens'] or 0 for u in calls):,}, "
          f"completion {sum(u['completion_tokens'] or 0 for u in calls):,}); {tokens / items:.0f} tokens per item")
    if expected_items:
        days = expected_items * tokens / items / settings["daily_token_limit"]
        print(f"Full run: ~{expected_items:,} items expected -> ~{days:.1f} days at {settings['daily_token_limit']:,} tokens/day")


def expected_full_items(processed: Path, allowed_sources: list[str]) -> int | None:
    """Projected yes/unsure count: filter rate so far × eligible clean records."""
    results_path = processed / "filter_results.jsonl"
    if not results_path.exists():
        return None
    with results_path.open(encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    if not rows:
        return None
    rate = sum(r["relevant"] in ("yes", "unsure") for r in rows) / len(rows)
    with (processed / "clean.jsonl").open(encoding="utf-8") as fh:
        eligible = sum(1 for r in map(json.loads, fh) if r.get("source") in allowed_sources)
    return round(rate * eligible)


def model_files(processed: Path, settings: dict[str, Any], model_id: str) -> tuple[Path, Path]:
    """(results file, usage file) for one tagging model, from ``tagging.models``."""
    for entry in settings["models"]:
        if entry["model_id"] == model_id:
            return processed / entry["results_file"], processed / entry["usage_file"]
    raise ValueError(f"model {model_id} is not listed in pipeline.tagging.models")


def model_settings(settings: dict[str, Any], model_id: str) -> dict[str, Any]:
    """Tagging settings with the model's own overrides (batch_size, reasoning_effort, ...)."""
    entry = next((e for e in settings["models"] if e["model_id"] == model_id), {})
    return {**settings, **{k: v for k, v in entry.items() if k not in ("model_id", "results_file", "usage_file")}}


def all_tagged_ids(processed: Path, settings: dict[str, Any]) -> set[str]:
    """Record IDs already tagged by any configured model."""
    ids: set[str] = set()
    for entry in settings["models"]:
        ids.update(ResultStore(processed / entry["results_file"]).results)
    return ids


def shard_of(record_id: str, shards: int) -> int:
    """Stable shard number, so parallel taggers never take the same item."""
    return int(hashlib.md5(record_id.encode("utf-8")).hexdigest(), 16) % shards


def priority_queue(processed: Path, allowed_sources: list[str], priority: re.Pattern[str], sip_keywords: re.Pattern[str], require_sip_keyword: bool = False) -> list[dict[str, Any]]:
    """Every record to tag, in order.

    Priority items (text matches a priority term) come first, without waiting
    for the filter; items the filter labelled "no" are skipped. Reddit records
    come before everything (tier -1). Within the rest:
    tier 0 = filter yes/unsure, tier 1 = also mentions a SIP keyword, tier 2 =
    the rest (dropped when ``require_sip_keyword``). Then the remaining filter
    yes/unsure items (tier 3).
    """
    from pipeline.filter import item_context

    flags: dict[str, str] = {}
    results_path = processed / "filter_results.jsonl"
    if results_path.exists():
        with results_path.open(encoding="utf-8") as fh:
            for row in map(json.loads, fh):
                flags[row["record_id"]] = row["relevant"]
    tiers: dict[int, list[dict[str, Any]]] = defaultdict(list)
    with (processed / "clean.jsonl").open(encoding="utf-8") as fh:
        for record in map(json.loads, fh):
            if record.get("source") not in allowed_sources:
                continue
            flag = flags.get(record["record_id"])
            text = record.get("text") or ""
            if flag == "no":
                continue
            if record.get("source") == "reddit":  # collected from SIP searches; always first
                tier = -1
            elif priority.search(text):
                tier = 0 if flag in ("yes", "unsure") else 1 if sip_keywords.search(text) else 2
                if tier == 2 and require_sip_keyword:
                    continue
            elif flag in ("yes", "unsure"):
                tier = 3
            else:
                continue
            tiers[tier].append({**record, "relevant": flag, "priority_tier": tier, "prompt_context": item_context(record)})
    return [r for tier in sorted(tiers) for r in tiers[tier]]


def per_source_pool(records: list[dict[str, Any]], per_source: int) -> list[dict[str, Any]]:
    """Up to ``per_source`` records from each source (Reddit, each Play Store app), keeping queue order."""
    taken: Counter[str] = Counter()
    pool = []
    for record in records:
        key = group_key(record)
        if taken[key] < per_source:
            taken[key] += 1
            pool.append(record)
    return pool


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    """Cohen's kappa for two raters over the same items; None if undefined."""
    n = len(a)
    if not n:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def agreement(rows_a: dict[str, dict[str, Any]], rows_b: dict[str, dict[str, Any]], codebook: dict[str, Any]) -> dict[str, Any]:
    """Field-by-field agreement on items both models tagged successfully."""
    ids = sorted(i for i in rows_a if i in rows_b and rows_a[i]["status"] == "ok" and rows_b[i]["status"] == "ok")
    fields = {}
    for field in codebook["fields"]:
        a = [rows_a[i][field["id"]] for i in ids]
        b = [rows_b[i][field["id"]] for i in ids]
        both_unclear = sum(x == y == "unclear" for x, y in zip(a, b))
        fields[field["id"]] = {
            "agree_pct": round(100 * sum(x == y for x, y in zip(a, b)) / max(len(ids), 1), 1),
            "kappa": None if (k := cohen_kappa(a, b)) is None else round(k, 2),
            "both_unclear": both_unclear,
        }
    quotes_overlap = sum(
        1 for i in ids
        if rows_a[i]["evidence_quote"] and rows_b[i]["evidence_quote"]
        and fuzz.partial_ratio(rows_a[i]["evidence_quote"], rows_b[i]["evidence_quote"]) >= 80
    )
    return {"items_compared": len(ids), "fields": fields, "quotes_overlapping": quotes_overlap}


def run_agreement(processed: Path, settings: dict[str, Any], codebook: dict[str, Any], queue: list[dict[str, Any]], make_client: Callable[[str], GroqClient], auto_resume: bool) -> int:
    """Both models tag the same items; report agreement; keep the first model's rows."""
    ids_path = processed / "tag_agreement_items.json"
    if ids_path.exists():  # re-checks use the same items so results are comparable
        wanted = json.loads(ids_path.read_text(encoding="utf-8"))
        by_id = {r["record_id"]: r for r in queue}
        items = [by_id[i] for i in wanted if i in by_id]
        if len(items) < len(wanted):
            print(f"Note: {len(wanted) - len(items)} of the saved agreement items are no longer in the queue")
    else:
        sip_related = [r for r in queue if r["priority_tier"] in (0, 1)]
        items = pilot_sample(sip_related, settings["agreement_size"], settings["sample_seed"])
        random.Random(settings["sample_seed"]).shuffle(items)
        ids_path.write_text(json.dumps([r["record_id"] for r in items]), encoding="utf-8")
    stores = {}
    tokens = {}
    for entry in settings["models"]:
        model = entry["model_id"]
        slug = model.rsplit("/", 1)[-1]
        store = ResultStore(processed / f"tag_agreement_{slug}_{PROMPT_VERSION}.jsonl")
        usage = processed / f"tag_agreement_usage_{slug}_{PROMPT_VERSION}.jsonl"
        summary = run_tagger(items, make_client(model), store, usage, model_settings(settings, model), codebook, run="agreement", auto_resume=auto_resume)
        if summary.stopped != "complete":
            print(f"{model}: stopped early: {summary.stopped}")
            return 2
        stores[model] = {i: store.results[i] for i in (r["record_id"] for r in items) if i in store.results}
        calls = [json.loads(l) for l in usage.open(encoding="utf-8") if l.strip()] if usage.exists() else []
        tokens[model] = sum(c.get("total_tokens") or 0 for c in calls if c.get("status") == 200)

    (model_a, rows_a), (model_b, rows_b) = list(stores.items())[:2]
    report = agreement(rows_a, rows_b, codebook)
    report.update(models=[model_a, model_b], tokens=tokens, prompt_version=PROMPT_VERSION, codebook_version=codebook.get("version"),
                  failed={m: sum(r["status"] != "ok" for r in rows.values()) for m, rows in stores.items()},
                  quote_status={m: dict(Counter(r.get("quote_status") for r in rows.values() if r["status"] == "ok")) for m, rows in stores.items()},
                  at=datetime.now(timezone.utc).isoformat())
    core = {f: report["fields"][f]["agree_pct"] for f in settings["agreement_core_fields"]}
    report.update(core_fields=core, threshold_pct=settings["agreement_threshold_pct"],
                  passed=min(core.values()) >= settings["agreement_threshold_pct"])
    (processed / f"tag_agreement_report_{PROMPT_VERSION}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Inter-model check: {model_a} vs {model_b}, {report['items_compared']} items compared")
    print(f"  {'field':<17} agree%  kappa  both unclear")
    for name, f in report["fields"].items():
        kappa = "  n/a" if f["kappa"] is None else f"{f['kappa']:5.2f}"
        print(f"  {name:<17} {f['agree_pct']:6.1f}  {kappa}  {f['both_unclear']:>5}")
    print(f"  evidence quotes overlapping (>=80): {report['quotes_overlapping']} of {report['items_compared']}")
    print(f"  failed: {report['failed']}; quote status: {report['quote_status']}")
    print(f"  tokens: " + ", ".join(f"{m} {t:,} ({t / max(len(items), 1):.0f}/item)" for m, t in tokens.items()))

    verdict = "PASSED" if report["passed"] else "NOT passed"
    print(f"  core fields {core}: {verdict} (threshold {settings['agreement_threshold_pct']}% each)")
    if not report["passed"]:
        return 3
    # The first model's rows are valid results; keep them so the full run skips these items.
    main_store = ResultStore(model_files(processed, settings, model_a)[0])
    main_store.add(r for r in rows_a.values() if r["status"] == "ok")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tag relevant records against codebook.yaml.")
    parser.add_argument("mode", choices=["pilot", "sample", "agree", "pool", "full", "report"])
    parser.add_argument("--per-source", type=int, help="pool mode: untagged items to take per source (Reddit, each app)")
    parser.add_argument("--auto-resume", action="store_true", help="wait for limit resets instead of stopping")
    parser.add_argument("--app", help="sample mode: app ID to sample from, e.g. com.nextbillion.groww")
    parser.add_argument("--size", type=int, help="sample mode: number of items")
    parser.add_argument("--model", help="model ID from pipeline.tagging.models (default: the first)")
    parser.add_argument("--shard", default="0/1", help="full mode: take shard i of n, e.g. 1/2, so parallel taggers split the items")
    args = parser.parse_args(argv)
    if args.mode == "sample" and not (args.app and args.size):
        parser.error("sample mode needs --app and --size")
    shard, shards = (int(x) for x in args.shard.split("/"))
    run = f"sample:{args.app}" if args.mode == "sample" else args.mode

    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    llm, settings = config["llm"], config["pipeline"]["tagging"]
    allowed = config["pipeline"]["relevance"]["allowed_sources"]
    codebook = load_codebook(settings["codebook_path"])
    processed = PROJECT_ROOT / config["paths"]["processed"]
    model = args.model or settings["models"][0]["model_id"]
    results_path, usage_path = model_files(processed, settings, model)
    store = ResultStore(results_path)
    api_key = load_api_key(llm["auth_env_var"], PROJECT_ROOT / ".env") if args.mode != "report" else ""

    def make_client(model_id: str) -> GroqClient:
        return GroqClient(api_key, llm["base_url"], model_id, {**llm, **model_settings(settings, model_id)})

    if args.mode == "report":
        pilot_report(processed, store, usage_path, settings, codebook, expected_full_items(processed, allowed), app=args.app)
        return 0
    if args.mode in ("agree", "full", "pool"):
        from collect.play_store import compile_keywords

        queue = priority_queue(processed, allowed, compile_keywords(settings["priority_terms"]), compile_keywords(config["pipeline"]["cleaning"]["keywords"]),
                               require_sip_keyword=settings.get("priority_requires_sip_keyword", False))
        if args.mode == "agree":
            return run_agreement(processed, settings, codebook, queue, make_client, args.auto_resume)
        done = all_tagged_ids(processed, settings)
        targets = [r for r in queue if r["record_id"] not in done and shard_of(r["record_id"], shards) == shard]
        if args.mode == "pool":
            if not args.per_source:
                parser.error("pool mode needs --per-source")
            targets = per_source_pool(targets, args.per_source)
        print(f"{model}: shard {shard}/{shards}, {len(targets):,} items to tag "
              f"(tiers: " + ", ".join(f"{t} {n}" for t, n in sorted(Counter(r["priority_tier"] for r in targets).items())) + ")")
    else:
        records = tagging_inputs(processed, allowed)
        if args.mode == "pilot":
            targets = pilot_sample(records, settings["pilot_size"], settings["sample_seed"])
        else:
            targets = sample_for_app(records, store, args.app, args.size, settings["sample_seed"])
    summary = run_tagger(targets, make_client(model), store, usage_path, model_settings(settings, model), codebook, run=run, auto_resume=args.auto_resume)
    print(f"Stopped: {summary.stopped}. Tagged this run: {summary.done_this_run} of {summary.requested} "
          f"(failed {summary.errors}). Requests {summary.requests}, tokens {summary.tokens:,}.")
    if args.mode in ("pilot", "sample"):
        print()
        pilot_report(processed, store, usage_path, settings, codebook, expected_full_items(processed, allowed), run=run, app=args.app)
    return 0 if summary.stopped == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
