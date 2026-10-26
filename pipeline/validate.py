"""Validation module — skeleton interface.

Responsibility: Define the future interface for validating record structure,
provenance, and tag fields against codebook constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a single record."""

    record_id: str
    is_valid: bool
    errors: list[str]  # Empty when is_valid is True
    warnings: list[str]  # Non-fatal issues (e.g., missing optional fields)


def validate_record(record: dict[str, Any]) -> ValidationResult:
    """Validate a single record's structure, provenance, and tag fields.

    Stub for the future validation implementation. Validates that required
    fields are present and raises NotImplementedError — no full validation is
    performed.

    Args:
        record: A dictionary representing a tagged record with provenance and
            tag fields.

    Returns:
        A ValidationResult instance.

    Raises:
        ValueError: If required fields are missing.
        NotImplementedError: Always, since validation is not yet implemented.
    """
    required = ("record_id", "source_url", "collected_at")
    for field in required:
        if field not in record or not record[field]:
            raise ValueError(f"Required field missing or empty: {field}")

    raise NotImplementedError(
        "Validation is not yet implemented. "
        "Stage 6 (validation and export) must be authorized before the "
        "validation logic is built."
    )


def validate_batch(records: list[dict[str, Any]]) -> list[ValidationResult]:
    """Validate a batch of records.

    Stub for future batch validation. Raises NotImplementedError.

    Args:
        records: A list of tagged record dictionaries.

    Returns:
        A list of ValidationResult instances.

    Raises:
        NotImplementedError: Always, since validation is not yet implemented.
    """
    for record in records:
        validate_record(record)
    raise NotImplementedError(
        "Batch validation is not yet implemented. "
        "Stage 6 (validation and export) must be authorized before the "
        "validation logic is built."
    )
