"""Tests that all skeleton modules import successfully."""

from __future__ import annotations

import importlib

MODULES = [
    "collect",
    "collect.base",
    "pipeline",
    "pipeline.clean",
    "pipeline.relevance",
    "pipeline.tag",
    "pipeline.validate",
    "pipeline.export",
    "app",
    "app.streamlit_app",
    "research.store",
    "research.retrieval",
    "research.answer",
    "research.analysis",
    "research.opportunities",
    "research.quality",
]


def test_all_skeleton_modules_import() -> None:
    """Every skeleton module must import without error."""
    for module_name in MODULES:
        importlib.import_module(module_name)


def test_collect_base_has_expected_symbols() -> None:
    """collect.base exposes the expected classes and functions."""
    from collect.base import RawRecord, accept_record, collect_batch

    assert RawRecord is not None
    assert callable(accept_record)
    assert callable(collect_batch)


def test_pipeline_clean_has_expected_symbols() -> None:
    """pipeline.clean exposes the expected classes and functions."""
    from pipeline.clean import CleanedRecord, clean_record, clean_batch

    assert CleanedRecord is not None
    assert callable(clean_record)
    assert callable(clean_batch)


def test_pipeline_relevance_has_expected_symbols() -> None:
    """pipeline.relevance exposes the expected classes and functions."""
    from pipeline.relevance import (
        RelevanceLabel,
        RelevanceResult,
        classify_relevance,
        classify_batch,
    )

    assert RelevanceLabel is not None
    assert RelevanceResult is not None
    assert callable(classify_relevance)
    assert callable(classify_batch)


def test_pipeline_tag_has_expected_symbols() -> None:
    """pipeline.tag exposes the expected classes and functions."""
    from pipeline.tag import check_quote, load_codebook, run_tagger

    assert callable(load_codebook)
    assert callable(run_tagger)
    assert callable(check_quote)


def test_pipeline_validate_has_expected_symbols() -> None:
    """pipeline.validate exposes the expected classes and functions."""
    from pipeline.validate import ValidationResult, validate_record, validate_batch

    assert ValidationResult is not None
    assert callable(validate_record)
    assert callable(validate_batch)


def test_pipeline_export_has_expected_symbols() -> None:
    """pipeline.export exposes the expected classes and functions."""
    from pipeline.export import ExportFormat, ExportResult, export_records

    assert ExportFormat is not None
    assert ExportResult is not None
    assert callable(export_records)


def test_app_streamlit_app_has_expected_symbols() -> None:
    """app.streamlit_app exposes the expected functions."""
    from app.streamlit_app import PAGE_TITLES, build_pages, main

    assert callable(main) and callable(build_pages)
    assert PAGE_TITLES == ("Overview", "Investor Behaviour", "Product Opportunities", "Evidence Explorer", "Data Quality & Validation")
