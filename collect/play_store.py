"""Google Play reviews collector — capped, user-approved pilot.

Responsibility: Fetch public reviews for configured investment apps using the
unofficial ``google-play-scraper`` library, convert them into RawRecords with
full provenance, and apply a keyword filter.

This is not an official Google API. The user accepted the terms-of-service
risk for a capped pilot on 2026-10-26 (docs/source_access_plan.md §1c).
Reviewer names, profile images and developer replies are never stored.
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from collect.base import RawRecord, accept_record

SOURCE_NAME = "play_store"
_RECORD_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "sip-discovery-engine/play_store")


def review_source_url(app_id: str, review_id: str) -> str:
    """Build a link to the review on the app's Play Store listing."""
    return (
        f"https://play.google.com/store/apps/details?id={app_id}"
        f"&reviewId={review_id}"
    )


def stable_record_id(app_id: str, review_id: str) -> str:
    """Return a record ID that is identical across re-collections of a review."""
    return str(uuid.uuid5(_RECORD_NAMESPACE, f"{app_id}:{review_id}"))


def review_to_record(app_id: str, review: dict[str, Any], collected_at: str) -> RawRecord:
    """Convert one google-play-scraper review dict into a RawRecord.

    Only the minimal fields are kept. ``userName``, ``userImage`` and
    ``replyContent`` are deliberately dropped.
    """
    review_id = review["reviewId"]
    reviewed_at = review.get("at")
    return accept_record(
        RawRecord(
            record_id=stable_record_id(app_id, review_id),
            source_url=review_source_url(app_id, review_id),
            collected_at=collected_at,
            text=review.get("content") or "",
            metadata={
                "source": SOURCE_NAME,
                "app_id": app_id,
                "review_id": review_id,
                "rating": review.get("score"),
                "reviewed_at": reviewed_at.isoformat() if isinstance(reviewed_at, datetime) else reviewed_at,
            },
        )
    )


def compile_keywords(keywords: list[str]) -> re.Pattern[str]:
    """Compile keywords into one case-insensitive whole-word pattern."""
    if not keywords:
        raise ValueError("at least one keyword is required")
    alternatives = sorted((re.escape(k.strip()) for k in keywords if k.strip()), key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(alternatives) + r")(?!\w)", re.IGNORECASE)


def matches_keywords(text: str, pattern: re.Pattern[str]) -> bool:
    """Return True if any keyword appears in ``text``."""
    return bool(pattern.search(text))


def fetch_reviews(
    apps: list[str],
    lang: str,
    country: str,
    max_reviews_per_app: int,
    pause_seconds: float,
) -> tuple[list[RawRecord], list[str]]:
    """Fetch up to ``max_reviews_per_app`` newest reviews for each app.

    Apps that cannot be fetched are skipped; their IDs and errors are returned
    in the second element so the caller can log them.

    Returns:
        (records, skipped) where ``skipped`` holds "app_id: error" strings.
    """
    from google_play_scraper import Sort, reviews

    records: list[RawRecord] = []
    skipped: list[str] = []
    for index, app_id in enumerate(apps):
        if index:
            time.sleep(pause_seconds)
        collected_at = datetime.now(timezone.utc).isoformat()
        try:
            batch, _ = reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=max_reviews_per_app,
            )
        except Exception as exc:  # library raises several unrelated types
            skipped.append(f"{app_id}: {type(exc).__name__}: {exc}")
            continue
        if not batch:
            skipped.append(f"{app_id}: no reviews returned")
            continue
        records.extend(review_to_record(app_id, r, collected_at) for r in batch[:max_reviews_per_app])
    return records, skipped
