"""Tests for the rule-based cleaning pipeline. No network, no AI."""

from __future__ import annotations

import json
from typing import Any

import pytest

from collect.play_store import compile_keywords
from pipeline.clean import (
    clean_batch,
    clean_record,
    dedupe,
    detect_language,
    length_filter,
    load_raw,
    record_context,
)

KEYWORDS = compile_keywords(["sip", "mutual fund"])


def rec(record_id: str, text: str, source: str = "play_store", date: str = "2026-01-01", collected_at: str = "2026-10-26T00:00:00+00:00", **meta: Any) -> dict[str, Any]:
    date_field = "published_at" if source == "youtube" else "reviewed_at"
    return {
        "record_id": record_id,
        "source_url": f"https://example.com/{record_id}",
        "collected_at": collected_at,
        "text": text,
        "metadata": {"source": source, date_field: date, **meta},
    }


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Great app for long term investing", "en"),
        ("SIP क्यों बंद हो रहे हैं", "hi"),  # Hindi with an English acronym
        ("Mera SIP बंद हो गया", "hinglish"),  # Devanagari mixed with Latin
        ("बहुत अच्छा ऐप है", "hi"),
        ("app bahut accha hai, sip easily start ho jata", "hinglish"),
        ("worst app h", "hinglish"),
        ("👍👍👍", "other"),
        ("மிகவும் நல்ல செயலி", "other"),
        ("I told me to wait", "en"),  # "me"/"to" are not Hinglish markers
    ],
)
def test_detect_language(text: str, expected: str) -> None:
    assert detect_language(text) == expected


def test_context_is_video_title_for_youtube_and_question_for_forum() -> None:
    assert record_context(rec("y", "x", source="youtube", video_title="Why SIP returns fall")) == "Why SIP returns fall"
    assert record_context(rec("f", "x", source="forum", thread_question="Should I stop my SIP?")) == "Should I stop my SIP?"
    assert record_context(rec("p", "x")) is None


def test_clean_record_adds_fields_and_requires_provenance() -> None:
    cleaned = clean_record(rec("a", "Stopped my SIP after the crash", date="2024-05-02T10:00:00"))
    assert (cleaned.year, cleaned.language, cleaned.source) == (2024, "en", "play_store")
    with pytest.raises(ValueError):
        clean_record({**rec("b", "x"), "source_url": ""})


def test_dedupe_keeps_latest_recollection_and_earliest_text_copy() -> None:
    records = [
        rec("r1", "old copy", collected_at="2026-10-26T01:00:00+00:00"),
        rec("r1", "new copy", collected_at="2026-10-26T02:00:00+00:00"),
        rec("late", "Best app for SIP investing in India", date="2026-05-01"),
        rec("early", "best app for sip investing in   india", date="2025-05-01"),
    ]
    kept, dropped = dedupe(records, threshold=95, min_words_fuzzy=6)

    assert {r["record_id"]: r["text"] for r in kept}["r1"] == "new copy"
    assert "early" in {r["record_id"] for r in kept}
    reasons = {(d["record_id"], d["drop_reason"]) for d in dropped}
    assert ("r1", "recollected") in reasons
    assert ("late", "exact_duplicate") in reasons


def test_dedupe_removes_near_duplicates_but_not_short_texts() -> None:
    records = [
        rec("a", "My SIP got cancelled without any reason, very bad support", date="2025-01-01"),
        rec("b", "My SIP got cancelled without any reason!! very bad supports", date="2025-02-01"),
        rec("c", "good app", date="2025-01-01"),
        rec("d", "god app", date="2025-02-01"),
    ]
    kept, dropped = dedupe(records, threshold=95, min_words_fuzzy=6)

    assert {r["record_id"] for r in kept} == {"a", "c", "d"}
    assert dropped[0]["drop_reason"] == "near_duplicate"
    assert dropped[0]["drop_detail"]["duplicate_of"] == "a"


def test_length_filter_keeps_short_texts_with_keywords() -> None:
    records = [rec("a", "Best for SIP"), rec("b", "nice app"), rec("c", "this one has exactly six words")]
    kept, dropped = length_filter(records, min_words=6, keywords=KEYWORDS)

    assert [r["record_id"] for r in kept] == ["a", "c"]
    assert dropped[0]["drop_reason"] == "short_text"


def test_clean_batch_funnel_counts_every_record() -> None:
    records = [rec("a", "Paused my SIP last month due to job loss"), rec("b", "Paused my SIP last month due to job loss"), rec("c", "ok"), rec("y", "SIP is great", source="youtube", video_title="T")]
    cleaned, dropped, funnel = clean_batch(records, KEYWORDS)

    assert funnel["raw"] == {"play_store": 3, "youtube": 1}
    assert funnel["after_dedupe"] == {"play_store": 2, "youtube": 1}
    assert funnel["after_length_filter"] == {"play_store": 1, "youtube": 1}
    assert len(cleaned) + len(dropped) == len(records)
    assert next(c for c in cleaned if c.source == "youtube").context == "T"


def test_load_raw_merges_files_and_records_origin(tmp_path) -> None:
    for name in ("a.jsonl", "b.jsonl"):
        (tmp_path / name).write_text(json.dumps(rec(name, "t")) + "\n\n", encoding="utf-8")
    rows = load_raw(tmp_path)
    assert [r["raw_file"] for r in rows] == ["a.jsonl", "b.jsonl"]
