"""YouTube comments collector — capped, user-approved pilot.

Responsibility: Fetch public top-level comments for manually selected videos
through the official YouTube Data API v3 (``commentThreads.list``), convert
them into RawRecords with full provenance, and stay within a quota budget.

The user approved this pilot on 2026-10-26 (docs/source_access_plan.md §5a).
Comments fetched with an API key are Non-Authorized Data and may be stored for
no longer than 30 calendar days (Developer Policies §III.E.4.d), so every
record carries a ``delete_after`` date. Author names and channel IDs are never
stored. The API key is read from the environment or ``.env`` and is never
logged.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from collect.base import RawRecord, accept_record

SOURCE_NAME = "youtube"
API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_RESULTS_PER_PAGE = 100
# Quota cost per call, from https://developers.google.com/youtube/v3/determine_quota_cost
QUOTA_COST = {"commentThreads.list": 1, "videos.list": 1}
_RECORD_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "sip-discovery-engine/youtube")
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

Fetcher = Callable[[str, dict[str, Any]], dict[str, Any]]


class QuotaExceeded(RuntimeError):
    """Raised before a call that would exceed the configured quota budget."""


class YouTubeAPIError(RuntimeError):
    """An API error with the key removed from the message."""

    def __init__(self, status: int, reason: str, message: str) -> None:
        super().__init__(f"HTTP {status} {reason}: {message}")
        self.status = status
        self.reason = reason


class QuotaBudget:
    """Track quota units spent in one run and refuse to go over ``limit``."""

    def __init__(self, limit: int) -> None:
        if limit <= 0:
            raise ValueError("quota limit must be positive")
        self.limit = limit
        self.used = 0

    def spend(self, endpoint: str) -> None:
        cost = QUOTA_COST[endpoint]
        if self.used + cost > self.limit:
            raise QuotaExceeded(f"{endpoint} would use {self.used + cost} of {self.limit} units")
        self.used += cost


def parse_video_id(value: str) -> str:
    """Return the 11-character video ID from a YouTube URL or a bare ID."""
    value = value.strip()
    if _VIDEO_ID.match(value):
        return value
    parsed = urllib.parse.urlparse(value)
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    candidate = ""
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host in {"youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            candidate = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/shorts/", "/live/", "/embed/")):
            candidate = parsed.path.split("/")[2]
    if not _VIDEO_ID.match(candidate):
        raise ValueError(f"not a YouTube video URL or ID: {value!r}")
    return candidate


def load_api_key(env_var: str, env_path: Path) -> str:
    """Read the API key from the environment, falling back to a .env file."""
    key = os.environ.get(env_var, "").strip()
    if not key and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == env_var:
                key = value.strip().strip("'\"")
    if not key:
        raise RuntimeError(f"{env_var} is empty. Paste the key into .env and save the file.")
    return key


def comment_source_url(video_id: str, comment_id: str) -> str:
    """Link that opens the video with the comment highlighted."""
    return f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}"


def stable_record_id(comment_id: str) -> str:
    """Return a record ID that is identical across re-collections of a comment."""
    return str(uuid.uuid5(_RECORD_NAMESPACE, comment_id))


def delete_after(collected_at: str, retention_days: int) -> str:
    """Date by which the record must be deleted or refreshed."""
    return (datetime.fromisoformat(collected_at) + timedelta(days=retention_days)).date().isoformat()


def thread_to_record(
    thread: dict[str, Any], collected_at: str, retention_days: int, video_title: str | None
) -> RawRecord:
    """Convert one ``commentThread`` resource into a RawRecord.

    ``authorDisplayName``, ``authorChannelId``, ``authorProfileImageUrl`` and
    ``authorChannelUrl`` are deliberately dropped.
    """
    top = thread["snippet"]["topLevelComment"]
    snippet = top["snippet"]
    comment_id = top["id"]
    video_id = snippet.get("videoId") or thread["snippet"]["videoId"]
    return accept_record(
        RawRecord(
            record_id=stable_record_id(comment_id),
            source_url=comment_source_url(video_id, comment_id),
            collected_at=collected_at,
            text=snippet.get("textOriginal") or "",
            metadata={
                "source": SOURCE_NAME,
                "video_id": video_id,
                "video_title": video_title,
                "comment_id": comment_id,
                "like_count": snippet.get("likeCount"),
                "reply_count": thread["snippet"].get("totalReplyCount"),
                "published_at": snippet.get("publishedAt"),
                "updated_at": snippet.get("updatedAt"),
                "data_class": "youtube_api_non_authorized",
                "delete_after": delete_after(collected_at, retention_days),
            },
        )
    )


def make_fetcher(api_key: str, timeout: float = 30.0) -> Fetcher:
    """Return a function that GETs an API endpoint and returns parsed JSON.

    Errors are re-raised as YouTubeAPIError built from the response body only,
    so the request URL (which contains the key) never reaches logs.
    """

    def fetch(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        resource = endpoint.split(".")[0]
        query = urllib.parse.urlencode({**params, "key": api_key})
        try:
            with urllib.request.urlopen(f"{API_BASE}/{resource}?{query}", timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            try:
                error = json.load(exc).get("error", {})
            except ValueError:
                error = {}
            reason = (error.get("errors") or [{}])[0].get("reason", "unknown")
            raise YouTubeAPIError(exc.code, reason, error.get("message", exc.reason)) from None
        except urllib.error.URLError as exc:
            raise YouTubeAPIError(0, "network", str(exc.reason)) from None

    return fetch


def fetch_comments(
    video_ids: list[str],
    max_comments_total: int,
    budget: QuotaBudget,
    fetch: Fetcher,
    retention_days: int,
    order: str = "relevance",
) -> tuple[list[RawRecord], list[str]]:
    """Fetch up to ``max_comments_total`` top-level comments, split across videos.

    Videos that fail (comments disabled, not found, quota) are skipped and
    reported in the second element. Unused share from a skipped or short video
    is not reassigned, so the total never exceeds the cap.

    Returns:
        (records, skipped) where ``skipped`` holds "video_id: error" strings.
    """
    if not video_ids:
        return [], []
    skipped: list[str] = []
    titles: dict[str, str] = {}
    try:
        budget.spend("videos.list")
        info = fetch("videos.list", {"part": "snippet", "id": ",".join(video_ids)})
        titles = {item["id"]: item["snippet"]["title"] for item in info.get("items", [])}
    except (QuotaExceeded, YouTubeAPIError) as exc:
        skipped.append(f"videos.list: {exc}")

    per_video = max_comments_total // len(video_ids)
    records: list[RawRecord] = []
    for video_id in video_ids:
        if titles and video_id not in titles:
            skipped.append(f"{video_id}: video not found or private")
            continue
        collected_at = datetime.now(timezone.utc).isoformat()
        got = 0
        page_token = None
        try:
            while got < per_video:
                params = {
                    "part": "snippet",
                    "videoId": video_id,
                    "maxResults": min(MAX_RESULTS_PER_PAGE, per_video - got),
                    "order": order,
                    "textFormat": "plainText",
                }
                if page_token:
                    params["pageToken"] = page_token
                budget.spend("commentThreads.list")
                page = fetch("commentThreads.list", params)
                for thread in page.get("items", [])[: per_video - got]:
                    records.append(thread_to_record(thread, collected_at, retention_days, titles.get(video_id)))
                    got += 1
                page_token = page.get("nextPageToken")
                if not page_token:
                    break
        except QuotaExceeded as exc:
            skipped.append(f"{video_id}: quota budget reached ({exc})")
            break
        except YouTubeAPIError as exc:
            skipped.append(f"{video_id}: {exc}")
            continue
        if got == 0:
            skipped.append(f"{video_id}: no comments returned")
    return records, skipped
