"""Tests for the research layer. No network; the answer model is faked."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from research import analysis
from research.answer import INSUFFICIENT_MESSAGE, answer_question, validate_points
from research.opportunities import build, evidence_strength
from research.retrieval import fts_query, search, tag_targets, term_coverage
from research.store import BULK_REVIEWER, build_database, is_public, normalise, read_rows

SETTINGS = {"retrieve_limit": 40, "max_evidence": 12, "max_record_words": 90, "min_records": 3, "min_term_coverage": 0.6, "small_sample": 10}


def golden(record_id: str, text: str, **tags) -> dict:
    row = {"record_id": record_id, "source": "play_store", "app_id": "com.a", "source_url": f"https://x/{record_id}",
           "collected_at": "2026-10-26T00:00:00Z", "published_at": "2025-03-01", "text": text, "evidence_quote": text[:20],
           "quote_status": "exact", "review_status": "approved", "reviewer": BULK_REVIEWER, "reviewer_notes": "secret note",
           "confidence": 0.8, "is_hypothesis": False, "tagged_by": "m"}
    row.update({f: "unclear" for f in ("behavior", "lapse_type", "trigger", "expectation", "in_app_pain", "unmet_need", "tenure", "emotion")})
    row.update(tags)
    return row


@pytest.fixture()
def db(tmp_path):
    rows = [
        golden("a", "My SIP autopay mandate failed twice", behavior="pause_sip", trigger="mandate_or_payment", in_app_pain="mandate_autopay", unmet_need="easy_mandate_control"),
        golden("b", "Autopay failed again, UPI mandate never arrived", trigger="mandate_or_payment", in_app_pain="mandate_autopay", unmet_need="easy_mandate_control"),
        golden("c", "Mandate keeps failing and support does not reply", trigger="mandate_or_payment", unmet_need="easy_mandate_control"),
        golden("d", "Stopped my SIP after the market crash", behavior="stop_sip", trigger="market_or_returns"),
        golden("e", "Great app", review_status="rejected"),
        {**golden("f", "Comment on video"), "source": "youtube"},
    ]
    path = tmp_path / "research.db"
    build_database(rows, path)
    return path


def test_public_rows_exclude_internal_fields_and_ineligible_records(db) -> None:
    rows = read_rows(db)
    assert sorted(r["record_id"] for r in rows) == ["a", "b", "c", "d"]
    assert all("reviewer_notes" not in r and "reviewer" not in r for r in rows)
    assert all(r["individually_reviewed"] is False for r in rows)
    assert len(read_rows(db, public_only=False)) == 6


def test_is_public_requires_provenance() -> None:
    assert is_public(golden("x", "t"))
    assert not is_public({**golden("x", "t"), "collected_at": None})
    assert normalise({**golden("x", "t"), "reviewer": "Asha"})["individually_reviewed"] is True


def test_retrieval_uses_tags_and_words(db) -> None:
    assert ("trigger", "mandate_or_payment") in tag_targets("Why do AutoPay payments fail?")
    results = search(db, "Why do AutoPay payments fail?")
    assert {r["record_id"] for r in results[:3]} == {"a", "b", "c"}
    assert term_coverage(["autopay", "fail"], "the autopay failed") == 1.0
    assert fts_query(['x" OR 1']) == '"x" OR 1"*'


def test_insufficient_evidence_skips_the_model(db) -> None:
    called = []
    result = answer_question("What about crypto staking yields?", db, lambda m: called.append(m), SETTINGS, total_public=4)
    assert result["status"] == "insufficient" and result["message"] == INSUFFICIENT_MESSAGE
    assert called == []


def test_answer_keeps_only_cited_points(db) -> None:
    reply = {"sufficient": True, "summary": "Mandates fail.", "gaps": "No dates.",
             "points": [{"text": "Mandates fail", "basis": "stated", "records": ["R1", "R2"]},
                        {"text": "Uncited claim", "basis": "stated", "records": []},
                        {"text": "Bad ref", "basis": "inferred", "records": ["R99"]}]}
    fake = lambda messages: SimpleNamespace(content=json.dumps(reply), usage={"total_tokens": 900})
    result = answer_question("Why do AutoPay payments fail?", db, fake, SETTINGS, total_public=4)
    assert result["status"] == "answered"
    assert [p["text"] for p in result["points"]] == ["Mandates fail"]
    assert result["coverage"]["records"] >= 3 and result["tokens"] == 900
    assert any("bulk-approved" in note for note in result["limitations"])


def test_model_saying_insufficient_is_respected(db) -> None:
    fake = lambda m: SimpleNamespace(content=json.dumps({"sufficient": False, "points": [], "gaps": "off topic"}), usage={"total_tokens": 700})
    result = answer_question("Why do AutoPay payments fail?", db, fake, SETTINGS, 4)
    assert result["status"] == "insufficient" and result["tokens"] == 700  # quota use is still recorded


def test_model_error_is_reported_with_evidence(db) -> None:
    def boom(m):
        raise RuntimeError("rate limited")
    result = answer_question("Why do AutoPay payments fail?", db, boom, SETTINGS, 4)
    assert result["status"] == "error" and result["evidence"]


def test_validate_points_normalises_basis() -> None:
    points = validate_points({"points": [{"text": "t", "basis": "INFERRED", "records": ["R2", "R2", "r1"]}]}, 2)
    assert points == [{"text": "t", "basis": "inferred", "records": [2]}]


def test_opportunities_need_minimum_evidence(db) -> None:
    rows = read_rows(db)
    defs = {"min_records": 3, "opportunities": [
        {"id": "m", "title": "Mandates", "problem": "p", "business_metric": "b", "intervention": "i", "experiment": "e",
         "match": {"unmet_need": ["easy_mandate_control"]}},
        {"id": "x", "title": "Market", "problem": "p", "business_metric": "b", "intervention": "i", "experiment": "e",
         "match": {"trigger": ["market_or_returns"]}, "restrict_behavior": ["stop_sip"]},
    ]}
    result = build(rows, defs)
    assert [o["id"] for o in result["opportunities"]] == ["m"]
    assert result["opportunities"][0]["n"] == 3 and "unverified" in result["opportunities"][0]["strength"]
    assert [o["id"] for o in result["insufficient"]] == ["x"]
    assert evidence_strength(40, 2, 12, 40)[0] == "Strong"
    assert evidence_strength(40, 2, 12, 40)[1].endswith("; 40 of 40 human-reviewed")
    assert evidence_strength(40, 2, 12, 0)[1].endswith("; 40 of 40 not individually human-reviewed")


def test_analysis_counts_and_emerging_guard() -> None:
    rows = [{"behavior": "pause_sip", "year": 2025}, {"behavior": "unclear", "year": 2025}, {"behavior": "stop_sip", "year": None}]
    d = analysis.distribution(rows, "behavior")
    assert d["n"] == 3 and d["n_tagged"] == 2
    assert analysis.journey_stage(rows[0]) == "Lapsing"
    assert analysis.emerging(rows, "behavior", 2025)["themes"] == []  # windows too small
    assert len(analysis.filter_rows(rows, years=(2025, 2025), include_undated=False)) == 2
    many = [{"trigger": "support", "year": 2025}] * 25 + [{"trigger": "fees_or_charges", "year": 2020}] * 25
    e = analysis.emerging(many, "trigger", 2025)
    assert e["themes"][0]["value"] == "support" and e["themes"][0]["change_pts"] == 100.0
