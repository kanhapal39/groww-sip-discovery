"""Collection module — skeleton interfaces.

Responsibility: Accept records from approved collectors and preserve record
IDs, source URLs, timestamps, and provenance. Does not fetch or scrape any
data itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    """An immutable raw record collected from a permitted public source.

    Every record must carry provenance: a stable record ID, the source URL
    where it was found, and an ISO-8601 collection timestamp.
    """

    record_id: str
    source_url: str
    collected_at: str  # ISO-8601 timestamp
    text: str
    metadata: dict[str, Any]


def accept_record(record: RawRecord) -> RawRecord:
    """Accept a single raw record into the collection layer.

    Validates that the provenance fields are present and returns the record
    unchanged. It does not fetch, scrape, or modify any data.

    Args:
        record: A RawRecord with populated provenance fields.

    Returns:
        The same RawRecord instance.

    Raises:
        ValueError: If required provenance fields are missing or empty.
    """
    if not record.record_id:
        raise ValueError("record_id is required")
    if not record.source_url:
        raise ValueError("source_url is required")
    if not record.collected_at:
        raise ValueError("collected_at is required")
    return record


def collect_batch(records: list[RawRecord]) -> list[RawRecord]:
    """Accept a batch of raw records.

    Validates provenance on every record.

    Args:
        records: A list of RawRecord instances.

    Returns:
        The same list of records.

    Raises:
        ValueError: If any record is missing provenance fields.
    """
    return [accept_record(record) for record in records]
