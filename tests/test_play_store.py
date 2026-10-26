"""Tests for the Play Store collector helpers. No network access."""

from __future__ import annotations

from datetime import datetime

import pytest

from collect.base import RawRecord, accept_record, collect_batch
from collect.play_store import (
    compile_keywords,
    matches_keywords,
    review_to_record,
    stable_record_id,
)

REVIEW = {
    "reviewId": "abc123",
    "userName": "Some Person",
    "userImage": "https://example.com/img.png",
    "content": "My SIP mandate failed twice this month",
    "score": 2,
    "at": datetime(2026, 10, 1, 12, 0, 0),
    "replyContent": "Sorry for the trouble",
}


def test_review_to_record_keeps_provenance_and_drops_personal_fields() -> None:
    record = review_to_record("com.example.app", REVIEW, "2026-10-26T00:00:00+00:00")

    assert record.record_id == stable_record_id("com.example.app", "abc123")
    assert record.source_url == (
        "https://play.google.com/store/apps/details?id=com.example.app&reviewId=abc123"
    )
    assert record.collected_at == "2026-10-26T00:00:00+00:00"
    assert record.text == REVIEW["content"]
    assert record.metadata["rating"] == 2
    assert record.metadata["reviewed_at"] == "2026-10-01T12:00:00"
    flat = str(record)
    assert "Some Person" not in flat
    assert "example.com/img" not in flat
    assert "Sorry for the trouble" not in flat


def test_stable_record_id_is_deterministic() -> None:
    assert stable_record_id("a", "1") == stable_record_id("a", "1")
    assert stable_record_id("a", "1") != stable_record_id("a", "2")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Stopped my SIP after the crash", True),
        ("sips are easy here", True),
        ("Great for Mutual Funds", True),
        ("autopay keeps failing", True),
        ("Gossip about the UI", False),  # "sip" inside another word
        ("Love the dark mode", False),
        ("navigation is confusing", False),  # "nav" inside another word
    ],
)
def test_keyword_filter_matches_whole_words(text: str, expected: bool) -> None:
    pattern = compile_keywords(["sip", "sips", "mutual fund", "mutual funds", "autopay", "nav"])
    assert matches_keywords(text, pattern) is expected


def test_compile_keywords_rejects_empty_list() -> None:
    with pytest.raises(ValueError):
        compile_keywords([])


def test_accept_record_requires_provenance() -> None:
    good = RawRecord("id", "https://x", "2026-10-26T00:00:00Z", "t", {})
    assert accept_record(good) is good
    assert collect_batch([good]) == [good]
    with pytest.raises(ValueError):
        accept_record(RawRecord("", "https://x", "2026", "t", {}))
