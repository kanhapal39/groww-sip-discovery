"""Cleaning module — rule-based, no AI.

Responsibility: Merge every raw JSONL file, remove exact and near-duplicate
texts, drop short texts that carry no SIP keyword, and add ``year``,
``language`` and ``context`` fields. Every dropped item is kept with its
reason so nothing is lost silently.

Usage:
    python -m pipeline.clean

Outputs (gitignored): ``data/processed/clean.jsonl`` and
``data/processed/dropped.jsonl``. YouTube records keep their ``delete_after``
date in ``metadata``; copies here must be deleted by the same date.
"""

from __future__ import annotations

import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from rapidfuzz import fuzz, process

from collect.play_store import compile_keywords, matches_keywords

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Date field per source, used for ``year`` and to keep the earliest copy.
DATE_FIELDS = ("reviewed_at", "published_at", "created_at")
# Forum collectors must store the thread's opening question under this key.
FORUM_CONTEXT_FIELD = "thread_question"

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN = re.compile(r"[A-Za-z]")
_WORD = re.compile(r"[A-Za-z]+")
_NON_WORD = re.compile(r"[^\wऀ-ॿ]+")
_SPACE = re.compile(r"\s+")

# Romanized Hindi words that are rare in English. Ambiguous ones such as
# "me", "to", "main" and "par" are deliberately left out.
HINGLISH_MARKERS = frozenset(
    """
    hai hain h nahi nahin nhi na kya kyu kyun kyunki kyuki kyon aur bhi kar karo
    karna karne karte karta kiya kiye kr krna krne krke liye mera meri mere mujhe
    mujhko hum humko humara aap aapka apna apne apni tum ye yeh wo woh vo ko se ka
    ki ke mein mai hota hoti hote ho raha rahi rahe rha rhi rhe sab kuch bahut
    bohot bhut accha acha achha achchha paisa paise kaise kab lekin jab tab bata
    batao dikkat samajh thik theek bekar faltu wala wali wale diya dete deta
    milta milti mila gaya gayi hua hui chahiye sakte sakta jata jati jaata
    """.split()
)


@dataclass(frozen=True)
class CleanedRecord:
    """A cleaned record ready for downstream pipeline stages."""

    record_id: str
    source_url: str
    collected_at: str  # ISO-8601 timestamp
    text: str
    metadata: dict[str, Any]
    source: str = ""
    year: int | None = None
    language: str = "other"  # en / hi / hinglish / other
    context: str | None = None
    raw_file: str | None = None


def detect_language(text: str) -> str:
    """Classify text as en, hi, hinglish or other using script and word rules.

    - hi: at least 80% of letters are Devanagari.
    - hinglish: Devanagari mixed with Latin (20–80% Devanagari), or Latin
      script with romanized Hindi words (2 or more, or 1 in a text of 5
      words or fewer).
    - en: Latin script with no such markers.
    - other: no letters (emoji, numbers) or mostly another script.
    """
    devanagari = len(_DEVANAGARI.findall(text))
    latin = len(_LATIN.findall(text))
    other = sum(1 for ch in text if ch.isalpha() and not _LATIN.match(ch) and not _DEVANAGARI.match(ch))
    letters = devanagari + latin + other
    if letters == 0 or other / letters > 0.5:
        return "other"
    share = devanagari / letters
    if share >= 0.8:
        return "hi"
    if share >= 0.2:
        return "hinglish"
    words = [w.lower() for w in _WORD.findall(text)]
    hits = sum(1 for w in words if w in HINGLISH_MARKERS)
    if hits >= 2 or (hits == 1 and len(words) <= 5):
        return "hinglish"
    return "en"


def record_date(record: dict[str, Any]) -> str | None:
    metadata = record.get("metadata") or {}
    for field in DATE_FIELDS:
        if metadata.get(field):
            return str(metadata[field])
    return None


def record_year(record: dict[str, Any]) -> int | None:
    """Year the item was posted, from the source's own date field."""
    date = record_date(record)
    if date and date[:4].isdigit():
        return int(date[:4])
    return None


def record_context(record: dict[str, Any]) -> str | None:
    """Video title for YouTube comments; thread question for forum replies.

    Play Store reviews have no thread, so they get None. Nothing is inferred:
    if the collector did not store the context, the field stays None.
    """
    metadata = record.get("metadata") or {}
    if metadata.get("source") == "youtube":
        return metadata.get("video_title")
    return metadata.get(FORUM_CONTEXT_FIELD)


def normalize_exact(text: str) -> str:
    """Case- and whitespace-insensitive form used for exact duplicates."""
    return _SPACE.sub(" ", unicodedata.normalize("NFKC", text).casefold()).strip()


def normalize_fuzzy(text: str) -> str:
    """Exact form with punctuation and emoji removed, used for near-duplicates."""
    return _SPACE.sub(" ", _NON_WORD.sub(" ", normalize_exact(text))).strip()


def word_count(text: str) -> int:
    return len(text.split())


def clean_record(record: dict[str, Any]) -> CleanedRecord:
    """Add year, language and context to one raw record.

    Raises:
        ValueError: If a provenance field is missing or empty.
    """
    required = ("record_id", "source_url", "collected_at")
    for field in required:
        if field not in record or not record[field]:
            raise ValueError(f"Required field missing or empty: {field}")
    text = record.get("text") or ""
    metadata = record.get("metadata") or {}
    return CleanedRecord(
        record_id=record["record_id"],
        source_url=record["source_url"],
        collected_at=record["collected_at"],
        text=text,
        metadata=metadata,
        source=metadata.get("source", ""),
        year=record_year(record),
        language=detect_language(text),
        context=record_context(record),
        raw_file=record.get("raw_file"),
    )


def _dropped(record: dict[str, Any], reason: str, **detail: Any) -> dict[str, Any]:
    return {**record, "drop_reason": reason, "drop_detail": detail or None}


def dedupe(records: list[dict[str, Any]], threshold: float, min_words_fuzzy: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Remove re-collected records, exact duplicates and near-duplicates.

    1. Same record_id in several raw files: keep the latest collection.
    2. Same text after case/whitespace normalization: keep the earliest post.
    3. Near-duplicates: rapidfuzz ``ratio`` >= ``threshold`` on punctuation-free
       text, compared only within blocks that share the first or last three
       words. Only texts with at least ``min_words_fuzzy`` words are compared,
       because short texts ("good app") match by coincidence, not copying.

    Returns:
        (kept, dropped) with ``drop_reason`` and ``drop_detail`` on dropped items.
    """
    dropped: list[dict[str, Any]] = []

    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        current = latest.get(record["record_id"])
        if current is None:
            latest[record["record_id"]] = record
        elif record["collected_at"] > current["collected_at"]:
            dropped.append(_dropped(current, "recollected", kept_record_id=record["record_id"], kept_raw_file=record.get("raw_file")))
            latest[record["record_id"]] = record
        else:
            dropped.append(_dropped(record, "recollected", kept_record_id=current["record_id"], kept_raw_file=current.get("raw_file")))

    # Earliest post first, so the original is the copy that survives.
    ordered = sorted(latest.values(), key=lambda r: (record_date(r) or "9999", r["record_id"]))

    seen_exact: dict[str, str] = {}
    blocks: dict[tuple[str, ...], list[tuple[str, str]]] = defaultdict(list)
    kept: list[dict[str, Any]] = []
    for record in ordered:
        text = record.get("text") or ""
        exact = normalize_exact(text)
        if exact in seen_exact:
            dropped.append(_dropped(record, "exact_duplicate", duplicate_of=seen_exact[exact]))
            continue
        seen_exact[exact] = record["record_id"]

        fuzzy = normalize_fuzzy(text)
        tokens = fuzzy.split()
        if len(tokens) >= min_words_fuzzy:
            keys = {("head", *tokens[:3]), ("tail", *tokens[-3:])}
            candidates = [c for key in keys for c in blocks[key]]
            match = process.extractOne(
                fuzzy, [c[0] for c in candidates], scorer=fuzz.ratio, score_cutoff=threshold
            ) if candidates else None
            if match:
                dropped.append(_dropped(record, "near_duplicate", duplicate_of=candidates[match[2]][1], similarity=round(match[1], 1)))
                continue
            for key in keys:
                blocks[key].append((fuzzy, record["record_id"]))
        kept.append(record)
    return kept, dropped


def length_filter(records: list[dict[str, Any]], min_words: int, keywords: re.Pattern[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Drop texts under ``min_words`` words unless they contain a SIP keyword."""
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for record in records:
        text = record.get("text") or ""
        words = word_count(text)
        if words < min_words and not matches_keywords(text, keywords):
            dropped.append(_dropped(record, "short_text", word_count=words, min_words=min_words))
        else:
            kept.append(record)
    return kept, dropped


def clean_batch(
    records: list[dict[str, Any]],
    keywords: re.Pattern[str],
    min_words: int = 6,
    near_duplicate_threshold: float = 95.0,
) -> tuple[list[CleanedRecord], list[dict[str, Any]], dict[str, Counter[str]]]:
    """Run dedupe, then the length filter, then add derived fields.

    Returns:
        (cleaned, dropped, funnel) where funnel maps stage -> per-source counts.
    """
    funnel: dict[str, Counter[str]] = {"raw": Counter(r.get("metadata", {}).get("source", "") for r in records)}
    deduped, dropped = dedupe(records, near_duplicate_threshold, min_words)
    funnel["after_dedupe"] = Counter(r.get("metadata", {}).get("source", "") for r in deduped)
    kept, short = length_filter(deduped, min_words, keywords)
    funnel["after_length_filter"] = Counter(r.get("metadata", {}).get("source", "") for r in kept)
    cleaned = [clean_record(r) for r in kept]
    dropped_enriched = [
        {**d, "year": record_year(d), "language": detect_language(d.get("text") or ""), "context": record_context(d)}
        for d in dropped + short
    ]
    return cleaned, dropped_enriched, funnel


def load_raw(raw_dir: Path) -> list[dict[str, Any]]:
    """Read every JSONL file in ``raw_dir``; each record notes its file."""
    records: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    records.append({**json.loads(line), "raw_file": path.name})
    return records


def write_jsonl(rows: Iterable[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def print_report(cleaned: list[CleanedRecord], dropped: list[dict[str, Any]], funnel: dict[str, Counter[str]], seed: int) -> None:
    sources = sorted(funnel["raw"])
    print("Funnel per source (raw -> after dedupe -> after length filter)")
    for source in sources + ["TOTAL"]:
        counts = [sum(funnel[s].values()) if source == "TOTAL" else funnel[s][source] for s in funnel]
        print(f"  {source:<12} " + " -> ".join(f"{c:,}" for c in counts))
    reasons = Counter(d["drop_reason"] for d in dropped)
    print("Dropped by reason: " + ", ".join(f"{k} {v:,}" for k, v in reasons.most_common()))

    print("Clean records by year")
    for year, n in sorted(Counter(r.year for r in cleaned).items(), key=lambda kv: (kv[0] is None, kv[0] or 0)):
        print(f"  {year}: {n:,}")
    print("Clean records by language")
    for lang, n in Counter(r.language for r in cleaned).most_common():
        print(f"  {lang}: {n:,}")

    short = [d for d in dropped if d["drop_reason"] == "short_text"]
    sample = random.Random(seed).sample(short, min(5, len(short)))
    print(f"5 random dropped short items (seed {seed})")
    for d in sample:
        rating = d.get("metadata", {}).get("rating")
        print(f"  [{d['metadata'].get('source')}{f', {rating}★' if rating else ''}] {d.get('text')!r}")


def main(argv: list[str] | None = None) -> int:
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    settings = config["pipeline"]["cleaning"]
    records = load_raw(PROJECT_ROOT / config["paths"]["raw"])
    if not records:
        print("No raw records found.", file=sys.stderr)
        return 1
    cleaned, dropped, funnel = clean_batch(
        records,
        keywords=compile_keywords(settings["keywords"]),
        min_words=settings["min_words"],
        near_duplicate_threshold=settings["near_duplicate_threshold"],
    )
    processed = PROJECT_ROOT / config["paths"]["processed"]
    write_jsonl((asdict(r) for r in cleaned), processed / "clean.jsonl")
    write_jsonl(dropped, processed / "dropped.jsonl")
    print_report(cleaned, dropped, funnel, seed=settings.get("sample_seed", 42))
    print(f"Clean:   {(processed / 'clean.jsonl').relative_to(PROJECT_ROOT)}")
    print(f"Dropped: {(processed / 'dropped.jsonl').relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
