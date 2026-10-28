"""Regression tests for the AI Eval edge cases (docs/ai_eval_test_report.md).

Test names carry the edge-case number from the audit brief (EC1..EC30). No network:
the answer model is faked, and fixtures are small synthetic Golden Dataset rows.
Texts marked "observed" are quotes the AI Evaluation document cites from the real
Golden Dataset, with the tags those records carry there.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from research.analysis import dedupe
from research.answer import INSUFFICIENT_MESSAGE, answer_question, strong_matches, unsupported, validate_points
from research.opportunities import PRIORITY_FORMULA, build, load_definitions
from research.retrieval import query_terms, search, segment_targets, tag_targets, term_hits
from research.store import build_database, load_golden, read_rows
from tests.test_research import SETTINGS, golden

ROOT = Path(__file__).resolve().parent.parent
QUESTION_C = "What problems do first-time SIP investors experience when setting up their first SIP?"


def fake_model(reply: dict):
    calls = []

    def complete(messages):
        calls.append(messages)
        return SimpleNamespace(content=json.dumps(reply), usage={"total_tokens": 1})
    complete.calls = calls
    return complete


def make_db(tmp_path, rows) -> Path:
    path = tmp_path / "research.db"
    build_database(rows, path)
    return path


@pytest.fixture()
def case_c_db(tmp_path):
    """Records shaped like the weak matches the AI Eval doc reports for Case C."""
    return make_db(tmp_path, [
        # observed (Case C): tagged start_sip, describes no problem
        golden("c1", "one stop solution of your investment. You can start a SIP ,direct mutual fund", behavior="start_sip"),
        # observed (Case C): tagged new_under_1y although the text does not say so
        golden("c2", "I really wish I could start Sip in those international index funds.", behavior="start_sip", tenure="new_under_1y"),
        # generic words only ("experience", "time", "up" inside "upi"/"update")
        golden("c3", "Very bad experience, every time the upi update takes a long time", trigger="mandate_or_payment"),
        golden("c4", "Quick Order Retry: If your order fails, place a fresh one with ease in no time. Stay updated"),
        golden("c5", "Terrible experience setting up the app, it took time"),
    ])


# --- A. Relevance and classification ---------------------------------------------------------------

def test_ec1_generic_words_do_not_establish_relevance(case_c_db) -> None:
    assert query_terms(QUESTION_C) == []  # "experience", "time", "setting", "up" are not content words
    assert term_hits(["up"], "upi update") == 0  # short terms match whole words only
    assert term_hits(["starting"], "i started last week") == 1  # but "starting" still finds "started"
    result = answer_question(QUESTION_C, case_c_db, fake_model({}), SETTINGS, total_public=5)
    assert result["status"] == "insufficient"
    assert {r["record_id"] for r in result["evidence"]} <= {"c2"}


def test_ec1_one_shared_keyword_is_not_a_strong_match() -> None:
    ranked = [{"record_id": "x", "matched_tags": [], "term_coverage": 0.5, "term_hits": 1, "query_terms": 2, "tag_targets": 0}]
    assert strong_matches(ranked, 0.5) == []
    assert strong_matches([{**ranked[0], "term_coverage": 1.0, "term_hits": 2}], 0.5)


def test_ec2_payment_failure_is_held_out_of_flexible_sip(tmp_path) -> None:
    rows = read_rows(make_db(tmp_path, [
        # observed (Case 1 / Edge Case 2): AutoPay setup failure tagged as a flexible-SIP need
        golden("p1", "not able to set up auto pay", trigger="missing_feature", in_app_pain="mandate_autopay", unmet_need="flexible_sip"),
        golden("f1", "I want to pause my investment and suddenly app doesn't have sip pause options",
               in_app_pain="sip_management", unmet_need="flexible_sip"),
    ]))
    defs = load_definitions()
    flexible = next(o for o in build(rows, {**defs, "min_records": 1})["opportunities"] if o["id"] == "flexible_sip")
    assert [r["record_id"] for r in flexible["records"]] == ["f1"]
    assert [r["record_id"] for r in flexible["held_out"]] == ["p1"]
    assert flexible["n"] == 1 and any("held out" in g for g in flexible["validation_gaps"])
    mandate = next(o for o in build(rows, {**defs, "min_records": 1})["opportunities"] if o["id"] == "mandate_reliability")
    assert [r["record_id"] for r in mandate["records"]] == ["p1"]


def test_ec3_cancellation_is_reported_separately_from_pause_demand(tmp_path) -> None:
    rows = read_rows(make_db(tmp_path, [
        golden("k1", "cancelling SIPs is really hard on this app", in_app_pain="sip_management", unmet_need="flexible_sip"),  # observed
        golden("k2", "I want to pause my investment and suddenly app doesn't have sip pause options", unmet_need="flexible_sip"),  # observed
        golden("k3", "Cannot edit mutual fund sip amount and date", in_app_pain="sip_management"),  # observed (part)
    ]))
    flexible = next(o for o in build(rows, {**load_definitions(), "min_records": 1})["opportunities"] if o["id"] == "flexible_sip")
    counts = dict(flexible["breakdown"])
    assert counts == {"mentions pausing or skipping": 1, "mentions editing amount or date, or step-up": 1,
                      "mentions cancelling or stopping only": 1, "none of these": 0}
    assert any("cancellation friction" in g for g in flexible["validation_gaps"])


def test_ec5_ec7_ec21_segment_questions_use_only_segment_tagged_records(tmp_path) -> None:
    db = make_db(tmp_path, [
        golden("s1", "Started my first SIPs but one is already negative, I am a beginner", behavior="start_sip", tenure="new_under_1y"),
        golden("s2", "Started a SIP, setup problems with mandate", behavior="start_sip"),
        golden("s3", "Started SIP, the mandate setup failed", behavior="start_sip"),
        golden("s4", "Starting a SIP was confusing", behavior="start_sip"),
    ])
    assert segment_targets(QUESTION_C) == [("tenure", "new_under_1y")]
    assert segment_targets("What problems do investors face when starting a SIP?") == []
    result = answer_question(QUESTION_C, db, fake_model({}), SETTINGS, total_public=4)
    assert [r["record_id"] for r in result["evidence"]] == ["s1"]
    assert result["status"] == "insufficient"
    assert any("Segment (tenure=new_under_1y)" in n for n in result["limitations"])
    # Without a segment word, the same records are all evidence.
    general = answer_question("What problems do investors face when starting a SIP?", db, None, SETTINGS, 4)
    assert general["status"] == "no_model" and len(general["evidence"]) == 4


def test_ec3_cancellation_pain_is_not_flexible_sip_demand() -> None:
    import yaml
    from research.opportunities import matches
    flexible = {d["id"]: d for d in load_definitions()["opportunities"]}["flexible_sip"]
    assert not matches(golden("x1", "cancelling SIPs is really hard", in_app_pain="sip_cancellation"), flexible)
    assert matches(golden("x2", "no option to pause my SIP", in_app_pain="sip_management"), flexible)
    pains = next(f for f in yaml.safe_load((ROOT / "codebook.yaml").read_text())["fields"] if f["id"] == "in_app_pain")
    assert "sip_cancellation" in [v["id"] for v in pains["values"]]


def test_ec5_tenure_alone_is_not_evidence_for_beginner_guidance() -> None:
    beginner = {d["id"]: d for d in load_definitions()["opportunities"]}["beginner_guidance"]
    from research.opportunities import matches
    assert not matches(golden("n1", "Great app. My first SIP app!", tenure="new_under_1y"), beginner)
    assert matches(golden("n2", "Which fund should I choose?", unmet_need="fund_guidance"), beginner)


def test_ec6_implied_tags_are_counted_separately(tmp_path) -> None:
    rows = read_rows(make_db(tmp_path, [
        golden("i1", "SIP pause missing", unmet_need="flexible_sip", is_hypothesis=True),
        golden("i2", "SIP pause missing again", unmet_need="flexible_sip", is_hypothesis=False),
    ]))
    flexible = next(o for o in build(rows, {**load_definitions(), "min_records": 1})["opportunities"] if o["id"] == "flexible_sip")
    assert flexible["implied"] == 1


# --- B. Retrieval and evidence quality --------------------------------------------------------------

def test_ec8_duplicates_do_not_inflate_counts(tmp_path) -> None:
    rows = [golden("d1", "My SIP autopay mandate failed", trigger="mandate_or_payment"),
            golden("d2", "my sip AUTOPAY mandate failed!!", trigger="mandate_or_payment"),  # same text, new ID
            golden("d1", "re-promoted copy of d1", trigger="mandate_or_payment")]           # same ID
    unique, removed = dedupe(rows)
    assert [r["record_id"] for r in unique] == ["d1"] and removed == 2
    db = make_db(tmp_path, rows)
    assert len(read_rows(db)) == 2  # the index keeps the first row per ID
    result = build(read_rows(db), {"min_records": 1, "opportunities": [
        {"id": "m", "title": "t", "problem": "p", "business_metric": "b", "intervention": "i", "experiment": "e",
         "match": {"trigger": ["mandate_or_payment"]}}]})
    assert result["opportunities"][0]["n"] == 1 and result["duplicates_removed"] == 1 and result["total"] == 1


def test_ec9_percentages_have_defined_denominators(tmp_path) -> None:
    rows = read_rows(make_db(tmp_path, [
        golden("a", "mandate failed", behavior="stop_sip", trigger="mandate_or_payment"),
        golden("b", "mandate failed twice", behavior="continue_sip", trigger="mandate_or_payment"),
        golden("c", "great app"), golden("d", "nice returns"),
    ]))
    result = build(rows, {"min_records": 1, "opportunities": [
        {"id": "m", "title": "t", "problem": "p", "business_metric": "b", "intervention": "i", "experiment": "e",
         "match": {"trigger": ["mandate_or_payment"]}}]})
    o = result["opportunities"][0]
    assert (o["n"], o["total"], o["share"], o["lapse_share"]) == (2, 4, 0.5, 0.5)
    assert {"n", "share", "lapse_share", "scope"} <= set(result["definitions"])
    assert "do not estimate how many investors" in result["definitions"]["scope"]


def test_ec10_ec15_short_quotes_and_old_evidence_are_flagged(tmp_path) -> None:
    db = make_db(tmp_path, [
        golden("o1", "Autopay mandate failed", trigger="mandate_or_payment", published_at="2019-05-01", year=2019),
        golden("o2", "Autopay mandate failed again today", trigger="mandate_or_payment"),
        {**golden("o3", "Autopay mandate failed once more", trigger="mandate_or_payment"), "published_at": None},
    ])
    result = answer_question("Why do AutoPay payments fail?", db, None, {**SETTINGS, "recent_from_year": 2025}, 3)
    notes = " ".join(result["limitations"])
    assert "1 of 3 records were published before 2025" in notes
    assert "1 of 3 records have no reliable publication date" in notes
    assert "quote shorter than 5 words" in notes


def test_ec11_alternative_wording_maps_to_tags() -> None:
    assert ("behavior", "pause_sip") in tag_targets("stop one instalment temporarily")
    assert ("behavior", "stop_sip") in tag_targets("why do people temporarily discontinue investment?")
    assert ("behavior", "reduce_sip") in tag_targets("reduce monthly contribution")
    assert ("in_app_pain", "sip_management") in tag_targets("how do I change debit amount")
    assert ("behavior", "start_sip") not in tag_targets("New update is pathetic")  # "new" alone is not starting


def test_ec13_ec29_mixed_evidence_is_reported(tmp_path) -> None:
    db = make_db(tmp_path, [
        golden("m1", "Paused SIP because the mandate failed", behavior="pause_sip", trigger="mandate_or_payment"),
        golden("m2", "Paused my SIP, mandate issue", behavior="pause_sip", trigger="mandate_or_payment"),
        golden("m3", "Mandate failed but I continued my SIP", behavior="continue_sip", trigger="mandate_or_payment"),
        golden("m4", "Mandate failed, still continuing SIP", behavior="continue_sip", trigger="mandate_or_payment"),
    ])
    result = answer_question("Why do AutoPay payments fail?", db, None, SETTINGS, 4)
    assert any(n.startswith("Mixed evidence: behaviour tags in these records are") for n in result["limitations"])


def test_ec14_thread_context_alone_is_not_evidence(tmp_path) -> None:
    db = make_db(tmp_path, [{**golden("r1", "You may need a website for many websites."), "context": "How to start SIP mandate autopay"}])
    ranked = search(db, "mandate autopay starting")
    assert ranked and ranked[0]["term_hits"] == 0  # found for ranking, but no words of its own match
    assert strong_matches(ranked, 0.6) == []


def test_ec16_ec17_fabricated_quotes_and_numbers_are_removed() -> None:
    evidence = [{"text": "not able to set up auto pay"}, {"text": "I started sip and then cancel it with profit of 9 percent"}]
    payload = {"points": [
        {"text": 'Users say "auto pay never works on weekends"', "basis": "stated", "records": ["R1"]},   # invented quote
        {"text": 'One user "cancel it with profit of 9 percent"', "basis": "stated", "records": ["R2"]},  # real quote, real number
        {"text": "40% of investors cannot set up AutoPay", "basis": "stated", "records": ["R1"]},        # invented statistic
        {"text": "AutoPay setup fails", "basis": "stated", "records": ["R3"]},                           # citation out of range
    ]}
    removed: list = []
    kept = validate_points(payload, 2, evidence, removed)
    assert [p["records"] for p in kept] == [[2]]
    reasons = [r["reason"] for r in removed]
    assert reasons[0].startswith("quotes words not found") and reasons[1].startswith("gives a percentage")
    assert reasons[2] == "cites no record in the evidence"


# --- C. Insight generation and recommendations -------------------------------------------------------

def test_ec18_ec19_ec23_impact_claims_are_removed(tmp_path) -> None:
    db = make_db(tmp_path, [golden(k, f"Autopay mandate failed {k}", trigger="mandate_or_payment") for k in ("a", "b", "c")])
    reply = {"sufficient": True, "summary": "A pause option will improve 12-month SIP continuation.",
             "points": [{"text": "Mandates fail", "basis": "stated", "records": ["R1"]},
                        {"text": "Adding pre-debit checks would reduce SIP cancellations", "basis": "inferred", "records": ["R2"]}]}
    result = answer_question("Why do AutoPay payments fail?", db, fake_model(reply), SETTINGS, 3)
    assert result["status"] == "answered" and [p["text"] for p in result["points"]] == ["Mandates fail"]
    assert result["summary"] == ""
    assert [r["reason"] for r in result["removed"]] == [
        "predicts the effect of a product change, which the records cannot show",
        "summary predicts the effect of a product change, which the records cannot show"]
    assert unsupported("Investors report that mandates fail", ["mandates fail"]) is None


def test_ec20_priority_is_described_as_evidence_volume() -> None:
    assert "not business impact" in PRIORITY_FORMULA


def test_ec22_answers_state_sample_is_not_representative(tmp_path) -> None:
    db = make_db(tmp_path, [golden(k, f"Autopay mandate failed {k}", trigger="mandate_or_payment") for k in ("a", "b", "c")])
    notes = answer_question("Why do AutoPay payments fail?", db, None, SETTINGS, 3)["limitations"]
    assert any("not a representative sample of all investors" in n for n in notes)


# --- D. Safe failure and reliability ------------------------------------------------------------------

def test_ec21_investor_groups_need_a_basis_in_question_or_records(tmp_path) -> None:
    db = make_db(tmp_path, [golden(k, f"Autopay mandate failed {k}", trigger="mandate_or_payment") for k in ("a", "b", "c")])
    reply = {"sufficient": True, "summary": "New investors struggle with AutoPay.",
             "points": [{"text": "Salaried users see mandate failures", "basis": "inferred", "records": ["R1"]},
                        {"text": "Mandates fail", "basis": "stated", "records": ["R2"]}]}
    result = answer_question("Why do AutoPay payments fail?", db, fake_model(reply), SETTINGS, 3)
    assert [p["text"] for p in result["points"]] == ["Mandates fail"] and result["summary"] == ""
    assert [r["reason"].split("(")[0] for r in result["removed"]] == [
        "names an investor group ", "summary names an investor group "]
    # Allowed when the question asks about the group, or the cited record mentions it.
    assert unsupported("Beginners report mandate failures", ["mandate failed"], "Why do beginners stop SIPs?") is None
    assert unsupported("A first-time investor could not set up AutoPay", ["I am a first time investor, autopay failed"]) is None
    assert unsupported("The SIP failed the first time", ["mandate failed"]) is None


def test_ec22_frequency_words_are_flagged_not_removed(tmp_path) -> None:
    db = make_db(tmp_path, [golden(k, f"Autopay mandate failed {k}", trigger="mandate_or_payment") for k in ("a", "b", "c")])
    reply = {"sufficient": True, "summary": "Payments mainly fail at mandate setup.",
             "points": [{"text": "Mandates often fail", "basis": "stated", "records": ["R1"]}]}
    result = answer_question("Why do AutoPay payments fail?", db, fake_model(reply), SETTINGS, 3)
    assert result["summary"] and result["points"] and not result["removed"]
    assert result["limitations"][0].startswith("The answer uses words about how common something is (mainly, often)")
    plain = answer_question("Why do AutoPay payments fail?", db, fake_model({**reply, "summary": "Mandates fail.",
                                                                                   "points": [{"text": "Mandates fail", "records": ["R1"]}]}), SETTINGS, 3)
    assert not any("how common" in n for n in plain["limitations"])


def test_ec24_ec25_abstains_on_the_edge_case_doc_question(case_c_db) -> None:
    model = fake_model({"sufficient": True, "summary": "s", "points": [{"text": "t", "basis": "stated", "records": ["R1"]}]})
    result = answer_question("Why do first-time investors discontinue SIPs after 12 months?", case_c_db, model, SETTINGS, 5)
    assert result["status"] == "insufficient" and result["message"] == INSUFFICIENT_MESSAGE
    assert model.calls == []


def test_ec25_answer_with_every_point_removed_abstains(tmp_path) -> None:
    db = make_db(tmp_path, [golden(k, f"Autopay mandate failed {k}", trigger="mandate_or_payment") for k in ("a", "b", "c")])
    reply = {"sufficient": True, "summary": "s", "points": [{"text": '"invented words here"', "basis": "stated", "records": ["R1"]}]}
    result = answer_question("Why do AutoPay payments fail?", db, fake_model(reply), SETTINGS, 3)
    assert result["status"] == "insufficient" and len(result["removed"]) == 1


def test_ec26_unapproved_and_out_of_scope_records_are_never_evidence(tmp_path) -> None:
    db = make_db(tmp_path, [
        golden("ok1", "Autopay mandate failed", trigger="mandate_or_payment"),
        golden("rej", "Autopay mandate failed badly", trigger="mandate_or_payment", review_status="rejected"),
        golden("pen", "Autopay mandate failed again", trigger="mandate_or_payment", review_status="pending"),
        {**golden("yt", "Autopay mandate failed on video", trigger="mandate_or_payment"), "source": "youtube"},
        {**golden("np", "Autopay mandate failed no provenance", trigger="mandate_or_payment"), "source_url": None},
    ])
    result = answer_question("Why do AutoPay payments fail?", db, None, SETTINGS, 1)
    assert [r["record_id"] for r in result["evidence"]] == ["ok1"]


def test_ec27_retrieval_is_deterministic(tmp_path) -> None:
    db = make_db(tmp_path, [golden(f"k{i}", f"Autopay mandate failed {i}", trigger="mandate_or_payment") for i in range(8)])
    first = [r["record_id"] for r in search(db, "Why do AutoPay payments fail?")]
    assert first == [r["record_id"] for r in search(db, "Why do AutoPay payments fail?")]
    a = answer_question("Why do AutoPay payments fail?", db, fake_model({"sufficient": False}), SETTINGS, 8)
    b = answer_question("Why do AutoPay payments fail?", db, fake_model({"sufficient": True, "points": []}), SETTINGS, 8)
    assert [r["record_id"] for r in a["evidence"]] == [r["record_id"] for r in b["evidence"]]


def test_ec28_empty_missing_and_incomplete_datasets(tmp_path) -> None:
    assert search(tmp_path / "missing.db", "autopay") == []
    empty = make_db(tmp_path, [])
    assert answer_question("Why do AutoPay payments fail?", empty, None, SETTINGS, 0)["status"] == "insufficient"
    assert build([])["opportunities"] == [] and build([])["total"] == 0
    sparse = tmp_path / "sparse.db"
    build_database([{"record_id": "x", "source": "play_store", "source_url": "u", "collected_at": "t", "review_status": "approved"},
                    {"text": "no id", "source": "play_store", "review_status": "approved"}], sparse)
    assert [r["record_id"] for r in read_rows(sparse)] == ["x"]  # the row without an ID is not public
    assert search(sparse, "autopay") == [] and build(read_rows(sparse))["total"] == 1


def test_ec28_malformed_golden_file_fails_loudly(tmp_path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text('{"record_id": "a"}\n\n{not json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 3"):
        load_golden(path)
    path.write_text('["a list"]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="not a JSON object"):
        load_golden(path)


def test_ec30_model_errors_do_not_leak_secrets(tmp_path) -> None:
    db = make_db(tmp_path, [golden(k, f"Autopay mandate failed {k}", trigger="mandate_or_payment") for k in ("a", "b", "c")])

    def leaky(messages):
        raise RuntimeError("401 Unauthorized for key " + "gsk_" + "FAKE" * 6)  # built at runtime so the file scan below stays clean
    result = answer_question("Why do AutoPay payments fail?", db, leaky, SETTINGS, 3)
    assert result["status"] == "error" and "gsk_" not in json.dumps(result, default=str)


SECRET_PATTERNS = re.compile(r"gsk_[A-Za-z0-9]{20,}|apify_api_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{35}")


def test_ec30_no_credentials_in_tracked_files() -> None:
    try:
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git not available")
    assert ".env" not in files
    leaks = []
    for name in files:
        path = ROOT / name
        if path.suffix in {".png", ".jpg", ".xlsx", ".db"} or not path.is_file():
            continue
        if SECRET_PATTERNS.search(path.read_text(encoding="utf-8", errors="ignore")):
            leaks.append(name)
    assert leaks == []
