"""Tests for the AI relevance filter. No network; the LLM client is faked."""

from __future__ import annotations

import json
from typing import Any

import pytest

from pipeline.filter import (
    FatalError,
    Limits,
    RateLimited,
    Response,
    ResultStore,
    build_messages,
    full_order,
    parse_duration,
    parse_results,
    pilot_sample,
    run_filter,
    should_rescue,
    truncate_words,
)

SETTINGS = {"batch_size": 3, "max_text_words": 150, "max_context_words": 25, "max_reason_words": 10}


def rec(record_id: str, text: str = "some review text", app_id: str = "com.a", year: int = 2024, context: str | None = None) -> dict[str, Any]:
    return {"record_id": record_id, "source": "play_store", "text": text, "year": year, "context": context, "metadata": {"source": "play_store", "app_id": app_id}}


class FakeClient:
    """Answers with a fixed label per text; can raise queued errors first."""

    model = "fake-model"

    def __init__(self, label_for: dict[str, str] | None = None, errors: list[Exception] | None = None, drop_ids: set[int] | None = None, limits: Limits | None = None):
        self.label_for = label_for or {}
        self.errors = list(errors or [])
        self.drop_ids = drop_ids or set()
        self.limits = limits or Limits()
        self.calls = 0

    def complete(self, messages: list[dict[str, str]]) -> Response:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        items = json.loads(messages[1]["content"].split("\n", 1)[1])
        results = [
            {"id": item["id"], "relevant": self.label_for.get(item["text"], "yes"), "reason": "describes the text"}
            for item in items
            if item["id"] not in self.drop_ids
        ]
        return Response(json.dumps({"results": results}), {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}, self.limits)


def run(records, client, tmp_path, **kwargs):
    store = ResultStore(tmp_path / "results.jsonl")
    sleeps: list[float] = []
    summary = run_filter(records, client, store, tmp_path / "usage.jsonl", SETTINGS, run="test", sleep=sleeps.append, log=lambda _: None, **kwargs)
    return summary, store, sleeps


def test_truncate_words_and_messages_carry_context() -> None:
    assert truncate_words("a b c d", 2) == "a b …"
    assert truncate_words(None, 2) == ""
    messages = build_messages([rec("1", "word " * 200), rec("2", context="Why SIP returns fall")], 150, 25)
    items = json.loads(messages[1]["content"].split("\n", 1)[1])
    assert len(items[0]["text"].split()) == 151  # 150 words + ellipsis
    assert items[0]["context"] == "Google Play review of com.a"
    assert items[1]["context"] == "Why SIP returns fall"


def test_parse_results_validates_and_caps_reason() -> None:
    content = 'noise {"results": [{"id": 1, "relevant": "YES", "reason": "one two three four five six seven eight nine ten eleven"},' \
              ' {"id": 2, "relevant": "maybe", "reason": "x"}, {"id": 9, "relevant": "no", "reason": "x"}]} trailing'
    parsed = parse_results(content, batch_size=3, max_reason_words=10)
    assert parsed == {1: ("yes", "one two three four five six seven eight nine ten", True)}
    assert parse_results("not json", 3, 10) == {}


@pytest.mark.parametrize(
    "text, expected",
    [
        ("How do I stop my SIP?", True),
        ("I redeemed my mutual fund but money not received", True),
        ("Mera SIP kaise band kare", True),
        ("Best app for SIP", False),  # keyword but neither a question nor first person
        ("My IPO application failed", False),  # first person but no keyword
        ("Is Nippon small cap good for beginners?", True),
    ],
)
def test_should_rescue(text: str, expected: bool) -> None:
    assert should_rescue(text) is expected


def test_no_with_keyword_and_first_person_is_rescued(tmp_path) -> None:
    records = [rec("a", "My SIP mandate failed again"), rec("b", "Great app for stocks")]
    client = FakeClient(label_for={"My SIP mandate failed again": "no", "Great app for stocks": "no"})
    summary, store, _ = run(records, client, tmp_path)

    assert store.results["a"]["relevant"] == "unsure"
    assert store.results["a"]["model_label"] == "no"
    assert store.results["a"]["rescued_by_rule"] is True
    assert store.results["b"]["relevant"] == "no"
    assert summary.rescued == 1


def test_resume_skips_finished_ids(tmp_path) -> None:
    records = [rec(str(i)) for i in range(5)]
    run(records[:2], FakeClient(), tmp_path)
    client = FakeClient()
    summary, store, _ = run(records, client, tmp_path)

    assert summary.requested == 3
    assert client.calls == 1
    assert len(store.results) == 5
    assert len(ResultStore(tmp_path / "results.jsonl").results) == 5  # persisted


def test_missing_items_are_retried_then_marked_error(tmp_path) -> None:
    client = FakeClient(drop_ids={2})
    summary, store, _ = run([rec("a"), rec("b"), rec("c")], client, tmp_path)

    # "b" is id 2 in the first batch, then id 1 on retry, so it succeeds.
    assert store.results["b"]["relevant"] == "yes"
    client = FakeClient(drop_ids={1})
    summary, store, _ = run([rec("x")], client, tmp_path)
    assert store.results["x"]["error"] == "no valid label from model"
    assert summary.errors == 1


def test_per_minute_rate_limit_waits_and_retries(tmp_path) -> None:
    client = FakeClient(errors=[RateLimited(7.0, daily=False, message="TPM")])
    summary, store, sleeps = run([rec("a")], client, tmp_path)

    assert summary.stopped == "complete"
    assert sleeps == [8.0]
    assert "a" in store


def test_daily_limit_stops_cleanly_without_auto_resume(tmp_path) -> None:
    client = FakeClient(errors=[RateLimited(3600, daily=True, message="Limit 200000 tokens per day (TPD)")])
    summary, store, sleeps = run([rec("a"), rec("b")], client, tmp_path)

    assert summary.stopped.startswith("daily limit reached")
    assert summary.done_this_run == 0 and sleeps == []
    assert summary.text(remaining=2).endswith("Remaining: 2.")


def test_daily_limit_waits_with_auto_resume(tmp_path) -> None:
    client = FakeClient(errors=[RateLimited(3600, daily=True, message="tokens per day (TPD)")])
    summary, store, sleeps = run([rec("a")], client, tmp_path, auto_resume=True)

    assert summary.stopped == "complete"
    assert sleeps == [3630]


def test_zero_remaining_requests_header_stops_before_next_batch(tmp_path) -> None:
    client = FakeClient(limits=Limits(remaining_requests_day=0, reset_requests_seconds=100))
    summary, _, _ = run([rec(str(i)) for i in range(6)], client, tmp_path)

    assert client.calls == 1
    assert summary.stopped.startswith("daily request limit")


def test_fatal_error_stops(tmp_path) -> None:
    summary, _, _ = run([rec("a")], FakeClient(errors=[FatalError("HTTP 401: Invalid API Key")]), tmp_path)
    assert summary.stopped.startswith("request rejected")


def test_parse_duration() -> None:
    assert parse_duration("2m59.56s") == pytest.approx(179.56)
    assert parse_duration("7.66s") == pytest.approx(7.66)
    assert parse_duration("1h2m3s") == 3723
    assert parse_duration("120") == 120
    assert parse_duration("250ms") == pytest.approx(0.25)
    assert parse_duration(None) is None


def test_sample_for_app_picks_only_that_app_and_skips_done() -> None:
    from pipeline.filter import sample_for_app

    records = [rec(f"g{i}", app_id="groww") for i in range(10)] + [rec(f"o{i}", app_id="other") for i in range(10)]
    sample = sample_for_app(records, {"g0", "g1"}, "groww", 5, seed=1)
    assert len(sample) == 5
    assert all(r["metadata"]["app_id"] == "groww" and r["record_id"] not in {"g0", "g1"} for r in sample)
    assert len(sample_for_app(records, set(), "groww", 50, seed=1)) == 10


def test_pilot_sample_is_stratified_and_full_order_puts_recent_first() -> None:
    records = [rec(f"{app}{i}", app_id=app) for app in ("a", "b", "c") for i in range(50)]
    sample = pilot_sample(records, 10, seed=1)
    counts = {app: sum(r["metadata"]["app_id"] == app for r in sample) for app in ("a", "b", "c")}
    assert sorted(counts.values()) == [3, 3, 4]

    ordered = full_order([rec("old", year=2019), rec("new", year=2024), rec("none", year=None)], 2021)
    assert [r["record_id"] for r in ordered] == ["new", "old", "none"]


def test_socket_timeout_becomes_transient_error(monkeypatch) -> None:
    import socket

    from pipeline.filter import GroqClient, TransientError

    def slow(*args, **kwargs):
        raise socket.timeout("The read operation timed out")

    monkeypatch.setattr("urllib.request.urlopen", slow)
    with pytest.raises(TransientError):
        GroqClient("k", "https://example.invalid", "m", {}).complete([{"role": "user", "content": "x"}])


def test_auto_resume_waits_out_network_outages(tmp_path) -> None:
    from pipeline.filter import OUTAGE_WAIT_SECONDS, TransientError

    errors = [TransientError("dns")] * 7
    summary, store, sleeps = run([rec("a")], FakeClient(errors=errors), tmp_path, auto_resume=True)
    assert summary.stopped == "complete" and "a" in store
    assert OUTAGE_WAIT_SECONDS in sleeps


def test_without_auto_resume_repeated_network_errors_stop(tmp_path) -> None:
    from pipeline.filter import TransientError

    summary, _, _ = run([rec("a")], FakeClient(errors=[TransientError("dns")] * 7), tmp_path)
    assert summary.stopped.startswith("repeated errors")
