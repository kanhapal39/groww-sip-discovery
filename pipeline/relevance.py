"""Relevance filtering module — skeleton interface.

Responsibility: Define the future interface for classifying records as relevant,
not relevant, or uncertain. Does not call an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class RelevanceLabel:
    """Relevance classification labels."""

    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class RelevanceResult:
    """Result of relevance classification for a single record."""

    record_id: str
    label: str  # One of RelevanceLabel values
    score: float  # 0.0 to 1.0 confidence
    reason: str  # Human-readable explanation (never fabricated)


def classify_relevance(record: dict[str, Any]) -> RelevanceResult:
    """Classify a single record as relevant, not relevant, or uncertain.

    Stub for the future relevance filtering implementation. Validates input and
    raises NotImplementedError — no LLM call or classification is performed.

    Args:
        record: A dictionary representing a cleaned record with at least
            record_id and text fields.

    Returns:
        A RelevanceResult instance.

    Raises:
        ValueError: If required fields are missing.
        NotImplementedError: Always, since relevance filtering is not yet
            implemented.
    """
    if not record.get("record_id"):
        raise ValueError("record_id is required")
    if not record.get("text"):
        raise ValueError("text is required")

    raise NotImplementedError(
        "Relevance filtering is not yet implemented. "
        "Stage 4 (cleaning and relevance filtering) must be authorized before "
        "the relevance classifier is built."
    )


def classify_batch(records: list[dict[str, Any]]) -> list[RelevanceResult]:
    """Classify a batch of records for relevance.

    Stub for future batch relevance classification. Raises NotImplementedError.

    Args:
        records: A list of cleaned record dictionaries.

    Returns:
        A list of RelevanceResult instances.

    Raises:
        NotImplementedError: Always, since relevance filtering is not yet
            implemented.
    """
    for record in records:
        classify_relevance(record)
    raise NotImplementedError(
        "Batch relevance filtering is not yet implemented. "
        "Stage 4 (cleaning and relevance filtering) must be authorized before "
        "the relevance classifier is built."
    )
