"""Tests for the YouTube collector. No network access; the API is faked."""

from __future__ import annotations

from typing import Any

import pytest

from collect.youtube import (
    QuotaBudget,
    QuotaExceeded,
    YouTubeAPIError,
    fetch_comments,
    load_api_key,
    parse_video_id,
    stable_record_id,
    thread_to_record,
)


def make_thread(comment_id: str, video_id: str = "oIAQsjJEwj8", text: str = "Paused my SIP") -> dict[str, Any]:
    return {
        "snippet": {
            "videoId": video_id,
            "totalReplyCount": 2,
            "topLevelComment": {
                "id": comment_id,
                "snippet": {
                    "videoId": video_id,
                    "textOriginal": text,
                    "authorDisplayName": "Some Person",
                    "authorChannelId": {"value": "UCsecretchannel"},
                    "authorProfileImageUrl": "https://example.com/img.png",
                    "likeCount": 5,
                    "publishedAt": "2026-10-01T12:00:00Z",
                    "updatedAt": "2026-10-01T12:00:00Z",
                },
            },
        }
    }


class FakeAPI:
    """Serve canned pages and record every call."""

    def __init__(self, threads: dict[str, list[dict[str, Any]]], errors: dict[str, YouTubeAPIError] | None = None):
        self.threads = threads
        self.errors = errors or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((endpoint, params))
        if endpoint == "videos.list":
            ids = params["id"].split(",")
            return {"items": [{"id": v, "snippet": {"title": f"Title {v}"}} for v in ids if v in self.threads]}
        video_id = params["videoId"]
        if video_id in self.errors:
            raise self.errors[video_id]
        start = int(params.get("pageToken", 0))
        items = self.threads[video_id][start : start + params["maxResults"]]
        page: dict[str, Any] = {"items": items}
        if start + len(items) < len(self.threads[video_id]):
            page["nextPageToken"] = str(start + len(items))
        return page


@pytest.mark.parametrize(
    "value",
    [
        "https://www.youtube.com/watch?v=oIAQsjJEwj8",
        "https://youtube.com/watch?v=oIAQsjJEwj8&t=30s",
        "https://youtu.be/oIAQsjJEwj8",
        "https://www.youtube.com/shorts/oIAQsjJEwj8",
        "oIAQsjJEwj8",
    ],
)
def test_parse_video_id_accepts_common_forms(value: str) -> None:
    assert parse_video_id(value) == "oIAQsjJEwj8"


def test_parse_video_id_rejects_other_urls() -> None:
    with pytest.raises(ValueError):
        parse_video_id("https://example.com/watch?v=oIAQsjJEwj8")


def test_thread_to_record_keeps_provenance_and_drops_author_fields() -> None:
    record = thread_to_record(make_thread("Ugx1"), "2026-10-26T00:00:00+00:00", 30, "Title")

    assert record.record_id == stable_record_id("Ugx1")
    assert record.source_url == "https://www.youtube.com/watch?v=oIAQsjJEwj8&lc=Ugx1"
    assert record.collected_at == "2026-10-26T00:00:00+00:00"
    assert record.text == "Paused my SIP"
    assert record.metadata["delete_after"] == "2026-11-25"
    flat = str(record)
    assert "Some Person" not in flat
    assert "UCsecretchannel" not in flat
    assert "example.com/img" not in flat


def test_fetch_comments_splits_cap_across_videos_and_paginates() -> None:
    api = FakeAPI({"aaaaaaaaaaa": [make_thread(f"a{i}") for i in range(300)], "bbbbbbbbbbb": [make_thread("b0")]})
    budget = QuotaBudget(100)

    records, skipped = fetch_comments(["aaaaaaaaaaa", "bbbbbbbbbbb"], 240, budget, api, 30)

    assert len([r for r in records if r.metadata["comment_id"].startswith("a")]) == 120
    assert len([r for r in records if r.metadata["comment_id"].startswith("b")]) == 1
    assert skipped == []
    # 1 videos.list + 2 pages for video a + 1 page for video b
    assert budget.used == 4 == len(api.calls)


def test_fetch_comments_skips_disabled_videos() -> None:
    error = YouTubeAPIError(403, "commentsDisabled", "Comments are disabled")
    api = FakeAPI({"aaaaaaaaaaa": [make_thread("a0")], "bbbbbbbbbbb": []}, errors={"bbbbbbbbbbb": error})

    records, skipped = fetch_comments(["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"], 30, QuotaBudget(100), api, 30)

    assert len(records) == 1
    assert any("bbbbbbbbbbb" in s and "commentsDisabled" in s for s in skipped)
    assert any("ccccccccccc" in s and "not found" in s for s in skipped)


def test_fetch_comments_stops_at_quota_budget() -> None:
    api = FakeAPI({"aaaaaaaaaaa": [make_thread(f"a{i}") for i in range(500)]})
    budget = QuotaBudget(3)

    records, skipped = fetch_comments(["aaaaaaaaaaa"], 500, budget, api, 30)

    assert budget.used == 3
    assert len(records) == 200
    assert any("quota budget reached" in s for s in skipped)


def test_quota_budget_refuses_overspend() -> None:
    budget = QuotaBudget(1)
    budget.spend("commentThreads.list")
    with pytest.raises(QuotaExceeded):
        budget.spend("commentThreads.list")


def test_load_api_key_reads_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comment\nYOUTUBE_API_KEY=abc123\nOTHER=x\n", encoding="utf-8")
    assert load_api_key("YOUTUBE_API_KEY", env) == "abc123"


def test_load_api_key_errors_when_blank(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("YOUTUBE_API_KEY=\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="empty"):
        load_api_key("YOUTUBE_API_KEY", env)
