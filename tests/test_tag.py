"""Tests for the tagging pipeline. No network; the LLM client is faked."""

from __future__ import annotations

import json
from typing import Any

import pytest

from pipeline.filter import Limits, RequestTooLarge, Response, ResultStore
from pipeline.tag import (
    build_messages,
    build_system_prompt,
    check_quote,
    code_maps,
    load_codebook,
    parse_reply,
    pilot_sample,
    run_tagger,
    unsupported_reason_terms,
)

CODEBOOK = load_codebook("codebook.yaml")
MAPS = code_maps(CODEBOOK)
SETTINGS = {"batch_size": 4, "max_text_words": 200, "max_context_words": 25, "max_reason_words": 12, "quote_min_score": 80}


def all_unclear(item: int, **overrides: Any) -> dict[str, Any]:
    entry = {code: "u" for code in MAPS}
    entry.update(lt="na", i=item, q="", rs="nothing stated", c=0.5, h=False)
    entry.update(overrides)
    return entry


def rec(record_id: str, text: str = "My SIP mandate failed again", app_id: str = "com.a") -> dict[str, Any]:
    return {
        "record_id": record_id, "source_url": f"https://play.google.com/x?reviewId={record_id}", "collected_at": "2026-10-26T00:00:00+00:00",
        "source": "play_store", "text": text, "year": 2025, "relevant": "yes", "prompt_context": f"Google Play review of {app_id}",
        "metadata": {"source": "play_store", "app_id": app_id},
    }


class FakeClient:
    model = "fake-120b"

    def __init__(self, max_items: int = 100, skip_once: set[int] | None = None, bad_always: bool = False, overrides: dict[str, Any] | None = None):
        self.max_items = max_items
        self.skip_once = set(skip_once or ())
        self.bad_always = bad_always
        self.overrides = overrides or {}
        self.batch_sizes: list[int] = []
        self.system_prompts: set[str] = set()

    def complete(self, messages: list[dict[str, str]]) -> Response:
        items = json.loads(messages[1]["content"])
        self.system_prompts.add(messages[0]["content"])
        self.batch_sizes.append(len(items))
        if len(items) > self.max_items:
            raise RequestTooLarge("HTTP 413: Request too large")
        out = []
        for item in items:
            if item["i"] in self.skip_once:
                self.skip_once.discard(item["i"])
                continue
            entry = all_unclear(item["i"], **{"bh": "pa", "lt": "iv", "tr": "mp", "q": "mandate failed", **self.overrides})
            if self.bad_always:
                entry["bh"] = "zz"
            out.append(entry)
        return Response(json.dumps({"r": out}), {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200}, Limits(), "stop")


def run(records, client, tmp_path):
    store = ResultStore(tmp_path / "tags.jsonl")
    summary = run_tagger(records, client, store, tmp_path / "usage.jsonl", SETTINGS, CODEBOOK, run="test", sleep=lambda _: None, log=lambda _: None)
    return summary, store


def test_codebook_codes_are_unique_and_every_field_has_unclear() -> None:
    for field in CODEBOOK["fields"]:
        assert "unclear" in {v["id"] for v in field["values"]}, field["id"]


def test_system_prompt_is_fixed_and_lists_every_field() -> None:
    prompt = build_system_prompt(CODEBOOK, 12)
    assert prompt == build_system_prompt(CODEBOOK, 12)
    for field in CODEBOOK["fields"]:
        assert f"{field['code']} ({field['id']})" in prompt
    assert all(f'"i":{n}' in prompt for n in (901, 902, 903, 904, 905))
    assert all(rule in prompt for rule in CODEBOOK["rules"])


def test_messages_are_compact_with_relevance_flag() -> None:
    messages = build_messages([rec("a")], "SYS", 200, 25)
    items = json.loads(messages[1]["content"])
    assert items == [{"i": 1, "rel": "y", "ctx": "Google Play review of com.a", "t": "My SIP mandate failed again"}]


def test_parse_reply_maps_codes_and_rejects_invalid_values() -> None:
    good = all_unclear(1, bh="sp", tr="mr", q="x", c=0.9)
    bad = all_unclear(2, bh="nope")
    parsed = parse_reply(json.dumps({"r": [good, bad]}), 2, MAPS, 12)
    assert set(parsed) == {1}
    assert parsed[1]["behavior"] == "stop_sip"
    assert parsed[1]["trigger"] == "market_or_returns"
    assert parsed[1]["income_stability"] == "unclear"
    assert parse_reply(json.dumps({"r": [all_unclear(1, c=1.5)]}), 1, MAPS, 12) == {}


@pytest.mark.parametrize(
    "quote, status, shown",
    [
        ("mandate failed", {"exact"}, "mandate failed"),
        ("Mandate  failed", {"repaired"}, "mandate failed"),
        ("my sip ... failed", {"repaired", "hidden"}, None),  # "..." is never shown as-is
        ("completely unrelated words here", {"hidden"}, None),
        ("", {"none"}, None),
    ],
)
def test_check_quote(quote: str, status: set[str], shown: str | None) -> None:
    text = "My SIP mandate failed again"
    result, got_status, _ = check_quote(quote, text, 80)
    assert got_status in status
    assert result is None or "..." not in result
    if shown is not None:
        assert shown in result  # repaired spans may widen to whole words
    if got_status == "repaired":
        assert result in text


def test_repaired_quote_keeps_whole_words() -> None:
    text = "Please add nominee deatils updation feature because it is missing"
    quote, status, _ = check_quote("needs nominee details updation feature", text, 80)
    assert status == "repaired"
    assert quote.split()[0] in text.split() and quote.split()[-1] in text.split()


def test_no_value_code_looks_like_a_boolean() -> None:
    for field in CODEBOOK["fields"]:
        for value in field["values"]:
            assert value["code"].lower() not in {"no", "yes", "true", "false", "on", "off"}, (field["id"], value["code"])


def test_unsupported_reason_terms() -> None:
    assert unsupported_reason_terms("stopped SIP due to returns", "I stopped investing, losses") == ["sip", "returns"]
    assert unsupported_reason_terms("mandate failed", "e-mandate failed twice") == []


def test_run_tagger_splits_too_large_requests(tmp_path) -> None:
    client = FakeClient(max_items=2)
    summary, store = run([rec(str(i)) for i in range(4)], client, tmp_path)

    assert client.batch_sizes == [4, 2, 2]
    assert summary.errors == 0 and len(store.results) == 4
    assert len(client.system_prompts) == 1


def test_run_tagger_retries_missing_items_once(tmp_path) -> None:
    client = FakeClient(skip_once={2})
    summary, store = run([rec("a"), rec("b"), rec("c")], client, tmp_path)

    assert store.results["b"]["status"] == "ok"
    assert client.batch_sizes == [3, 1]


def test_run_tagger_marks_failed_after_one_retry(tmp_path) -> None:
    summary, store = run([rec("a")], FakeClient(bad_always=True), tmp_path)

    assert store.results["a"]["status"] == "failed"
    assert summary.errors == 1


def test_rows_keep_provenance_and_quote_checks(tmp_path) -> None:
    client = FakeClient(overrides={"q": "mandate fail ed", "rs": "stopped SIP because returns fell"})
    _, store = run([rec("a", text="The mandate failed twice")], client, tmp_path)
    row = store.results["a"]

    assert row["source_url"] == "https://play.google.com/x?reviewId=a"
    assert row["behavior"] == "pause_sip" and row["lapse_type"] == "involuntary"
    assert row["quote_status"] == "repaired" and row["evidence_quote"] in "The mandate failed twice"
    assert row["reason_unsupported_terms"] == ["sip", "returns"]


def test_pilot_sample_round_robins_across_apps() -> None:
    records = [rec(f"a{i}", app_id="a") for i in range(30)] + [rec(f"b{i}", app_id="b") for i in range(3)]
    sample = pilot_sample(records, 10, seed=1)
    assert len(sample) == 10
    assert sum(r["metadata"]["app_id"] == "b" for r in sample) == 3


def test_shard_of_is_stable_and_splits_items() -> None:
    from pipeline.tag import shard_of

    ids = [f"id{i}" for i in range(200)]
    assert [shard_of(i, 2) for i in ids] == [shard_of(i, 2) for i in ids]
    zero = sum(shard_of(i, 2) == 0 for i in ids)
    assert 60 < zero < 140


def test_cohen_kappa() -> None:
    from pipeline.tag import cohen_kappa

    assert cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0
    assert cohen_kappa(["u", "u"], ["u", "u"]) is None  # one category only
    assert cohen_kappa([], []) is None


def test_agreement_counts_only_items_both_tagged() -> None:
    from pipeline.tag import agreement

    def row(behavior: str, status: str = "ok") -> dict:
        base = {f["id"]: "unclear" for f in CODEBOOK["fields"]}
        return {**base, "behavior": behavior, "status": status, "evidence_quote": "mandate failed"}

    a = {"1": row("stop_sip"), "2": row("pause_sip"), "3": row("stop_sip")}
    b = {"1": row("stop_sip"), "2": row("stop_sip"), "3": row("stop_sip", status="failed")}
    report = agreement(a, b, CODEBOOK)
    assert report["items_compared"] == 2
    assert report["fields"]["behavior"]["agree_pct"] == 50.0
    assert report["fields"]["tenure"]["both_unclear"] == 2
    assert report["quotes_overlapping"] == 2


def test_priority_queue_orders_tiers_and_skips_filter_no(tmp_path) -> None:
    from collect.play_store import compile_keywords
    from pipeline.tag import priority_queue

    clean = [
        {"record_id": "yes_p", "source": "play_store", "text": "my SIP mandate failed", "metadata": {"app_id": "a"}},
        {"record_id": "unf_sip", "source": "play_store", "text": "stopped my sip", "metadata": {"app_id": "a"}},
        {"record_id": "unf_other", "source": "play_store", "text": "big loss in F&O", "metadata": {"app_id": "a"}},
        {"record_id": "no_p", "source": "play_store", "text": "loss on shares", "metadata": {"app_id": "a"}},
        {"record_id": "yes_plain", "source": "play_store", "text": "which fund for kids", "metadata": {"app_id": "a"}},
        {"record_id": "unf_plain", "source": "play_store", "text": "nice app", "metadata": {"app_id": "a"}},
        {"record_id": "yt", "source": "youtube", "text": "stopped my sip", "metadata": {}},
    ]
    (tmp_path / "clean.jsonl").write_text("\n".join(json.dumps(r) for r in clean), encoding="utf-8")
    flags = [{"record_id": "yes_p", "relevant": "yes"}, {"record_id": "no_p", "relevant": "no"}, {"record_id": "yes_plain", "relevant": "unsure"}]
    (tmp_path / "filter_results.jsonl").write_text("\n".join(json.dumps(f) for f in flags), encoding="utf-8")

    queue = priority_queue(tmp_path, ["play_store"], compile_keywords(["stopped", "failed", "loss"]), compile_keywords(["sip"]))
    assert [(r["record_id"], r["priority_tier"]) for r in queue] == [("yes_p", 0), ("unf_sip", 1), ("unf_other", 2), ("yes_plain", 3)]
    assert build_messages(queue[1:2], "S", 200, 25)[1]["content"].count('"rel":"x"') == 1


def test_invalid_json_reply_splits_the_batch(tmp_path) -> None:
    from pipeline.filter import InvalidOutput

    class FlakyClient(FakeClient):
        def complete(self, messages):
            if len(json.loads(messages[1]["content"])) > 2:
                self.batch_sizes.append(-1)
                raise InvalidOutput("HTTP 400: Failed to validate JSON")
            return super().complete(messages)

    client = FlakyClient()
    summary, store = run([rec(str(i)) for i in range(4)], client, tmp_path)
    assert summary.errors == 0 and len(store.results) == 4
    assert client.batch_sizes == [-1, 2, 2]


def test_model_settings_apply_per_model_overrides() -> None:
    from pipeline.tag import model_settings

    settings = {"batch_size": 20, "models": [{"model_id": "a", "results_file": "x"}, {"model_id": "b", "results_file": "y", "batch_size": 8}]}
    assert model_settings(settings, "a")["batch_size"] == 20
    assert model_settings(settings, "b")["batch_size"] == 8
    assert "results_file" not in model_settings(settings, "b")


def test_parse_reply_accepts_a_bare_list() -> None:
    parsed = parse_reply("[" + json.dumps(all_unclear(1, bh="sp")) + "]", 1, MAPS, 12)
    assert parsed[1]["behavior"] == "stop_sip"


def test_priority_queue_can_require_a_sip_keyword(tmp_path) -> None:
    from collect.play_store import compile_keywords
    from pipeline.tag import priority_queue

    clean = [
        {"record_id": "sip", "source": "play_store", "text": "stopped my sip", "metadata": {"app_id": "a"}},
        {"record_id": "stock", "source": "play_store", "text": "big loss in F&O", "metadata": {"app_id": "a"}},
    ]
    (tmp_path / "clean.jsonl").write_text("\n".join(json.dumps(r) for r in clean), encoding="utf-8")
    queue = priority_queue(tmp_path, ["play_store"], compile_keywords(["stopped", "loss"]), compile_keywords(["sip"]), require_sip_keyword=True)
    assert [r["record_id"] for r in queue] == ["sip"]


def test_reddit_records_go_first_and_never_twice(tmp_path) -> None:
    from collect.play_store import compile_keywords
    from pipeline.tag import priority_queue, shard_of

    clean = [
        {"record_id": "ps", "source": "play_store", "text": "stopped my sip", "metadata": {"app_id": "a"}},
        {"record_id": "rd", "source": "reddit", "text": "Should I pause my SIP?", "metadata": {"source": "reddit", "kind": "post", "subreddit": "mutualfunds"}},
        {"record_id": "rd_no", "source": "reddit", "text": "crypto", "metadata": {"source": "reddit", "kind": "post", "subreddit": "x"}},
    ]
    (tmp_path / "clean.jsonl").write_text("\n".join(json.dumps(r) for r in clean), encoding="utf-8")
    (tmp_path / "filter_results.jsonl").write_text(json.dumps({"record_id": "rd_no", "relevant": "no"}), encoding="utf-8")
    queue = priority_queue(tmp_path, ["play_store", "reddit"], compile_keywords(["stopped"]), compile_keywords(["sip"]), True)
    assert [r["record_id"] for r in queue] == ["rd", "ps"]
    assert queue[0]["prompt_context"] == "Reddit post in r/mutualfunds"
    shards = {r["record_id"]: shard_of(r["record_id"], 2) for r in queue}
    assert len(shards) == len(queue)  # each item belongs to exactly one shard


def test_per_source_pool_caps_each_source() -> None:
    from pipeline.tag import per_source_pool

    records = [rec(f"a{i}", app_id="a") for i in range(5)] + [rec(f"b{i}", app_id="b") for i in range(2)]
    pool = per_source_pool(records, 3)
    assert [r["record_id"] for r in pool] == ["a0", "a1", "a2", "b0", "b1"]
