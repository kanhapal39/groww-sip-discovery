"""Tests for the Reddit (Apify) collector. No network; Apify is faked."""

from __future__ import annotations

import pytest

from collect.play_store import compile_keywords
from collect.reddit_apify import (
    BudgetExceeded,
    Ledger,
    event_prices,
    items_to_records,
    run_cost,
    scrub,
    search_urls,
    shortlist,
    worst_case_cost,
)

ACTOR = {"pricingInfos": [{"pricingModel": "PAY_PER_EVENT", "pricingPerEvent": {"actorChargeEvents": {
    "start": {"eventPriceUsd": 0.003},
    "post": {"eventTieredPricingUsd": {"FREE": {"tieredEventPriceUsd": 0.00115}, "BRONZE": {"tieredEventPriceUsd": 0.001}}},
    "comment": {"eventTieredPricingUsd": {"FREE": {"tieredEventPriceUsd": 0.000575}}},
}}}]}

POST = {"dataType": "post", "id": "abc", "title": "Stopped my SIP after job loss &amp; u/rahul_k said wait",
        "body": "I spoke to rahul_k and /u/OtherGuy. See https://www.reddit.com/user/rahul_k for more", "author": "rahul_k",
        "permalink": "/r/IndiaInvestments/comments/abc/stopped_my_sip/", "subreddit": "IndiaInvestments", "createdAt": "2023-05-01T10:00:00Z",
        "score": 12, "numComments": 3, "authorFlair": "Investor"}
COMMENT = {"dataType": "comment", "id": "c1", "postId": "abc", "body": "Don&#39;t stop, Rahul_K is wrong", "author": "helper99",
           "permalink": "/r/IndiaInvestments/comments/abc/stopped_my_sip/c1/", "subreddit": "IndiaInvestments", "createdAt": 1690000000, "depth": 0}


def test_event_prices_use_plan_tier() -> None:
    prices = event_prices(ACTOR, "FREE")
    assert prices == {"start": 0.003, "post": 0.00115, "comment": 0.000575}
    assert event_prices(ACTOR, "BRONZE")["post"] == 0.001


def test_worst_case_and_run_cost() -> None:
    prices = event_prices(ACTOR, "FREE")
    assert worst_case_cost(prices, 5, 25) == pytest.approx(0.003 + 5 * 0.00115 + 25 * 0.000575)
    assert run_cost(prices, {"start": 1, "post": 2, "unknown": 9}) == pytest.approx(0.003 + 0.0023)


def test_ledger_refuses_runs_that_could_exceed_budget(tmp_path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.add({"cost_usd": 3.0})
    assert ledger.check(0.4, 3.5) == pytest.approx(0.5)
    with pytest.raises(BudgetExceeded):
        ledger.check(0.6, 3.5)
    assert Ledger(tmp_path / "ledger.json").spent == 3.0  # persisted


def test_records_remove_every_username_and_decode_html() -> None:
    records = items_to_records([POST, COMMENT], "2026-10-26T00:00:00+00:00")
    post, comment = records
    flat = str([r.__dict__ for r in records]).lower()
    assert "rahul_k" not in flat and "otherguy" not in flat and "helper99" not in flat
    assert "authorflair" not in flat and "investor" not in flat
    assert post.metadata["title"] == "Stopped my SIP after job loss & u/[user] said wait"
    assert "reddit.com/user/[user]" in post.text
    assert comment.text == "Don't stop, [user] is wrong"
    assert post.source_url == "https://www.reddit.com/r/IndiaInvestments/comments/abc/stopped_my_sip/"
    assert comment.metadata["post_id"] == "t3_abc"
    assert comment.metadata["thread_question"].startswith("Stopped my SIP after job loss")
    assert comment.metadata["published_at"].startswith("2023-07-22")
    assert post.record_id != comment.record_id


def test_comments_get_context_from_posts_fetched_earlier() -> None:
    known = {"t3_abc": {"title": "Paused SIP", "body": "Lost job", "url": "https://x"}}
    (comment,) = items_to_records([COMMENT], "2026-10-26T00:00:00+00:00", known)
    assert comment.metadata["thread_question"] == "Paused SIP\n\nLost job"


def test_scrub_leaves_ordinary_words() -> None:
    assert scrub("my sip in mutual funds", {"sip"}) == "my [user] in mutual funds"  # known names are always removed
    assert scrub("u/ab is short", set()) == "u/ab is short"  # under 3 chars is not a Reddit username


def test_search_urls_and_shortlist() -> None:
    urls = search_urls(["IndiaInvestments", "mutualfunds"], ["stopped my SIP"])
    assert len(urls) == 2 and "restrict_sr=1" in urls[0] and "q=stopped+my+SIP" in urls[0]
    posts = [
        {"text": "Stopped my SIP\n\nmarket fell", "metadata": {"title": "Stopped my SIP"}},
        {"text": "Stopped trading F&O", "metadata": {"title": "Stopped trading F&O"}},
        {"text": "How to pick a SIP", "metadata": {"title": "How to pick a SIP"}},
    ]
    chosen = shortlist(posts, compile_keywords(["stopped", "stop"]), compile_keywords(["sip"]))
    assert [p["metadata"]["title"] for p in chosen] == ["Stopped my SIP"]


def test_post_body_from_selftext_and_deleted_comments_dropped() -> None:
    post = {**POST, "body": None, "selfText": "Market fell 20%"}
    deleted = {**COMMENT, "id": "c2", "body": "[deleted]", "author": "[deleted]"}
    orphan = {**COMMENT, "id": "c3", "postId": "zzz", "postTitle": "Should I stop SIP?"}
    records = items_to_records([post, deleted, orphan], "2026-10-26T00:00:00+00:00")
    assert [r.metadata["kind"] for r in records] == ["post", "comment"]
    assert records[0].text.endswith("Market fell 20%")
    assert records[1].metadata["thread_question"] == "Should I stop SIP?"


def test_final_cost_waits_for_charges_to_settle() -> None:
    from collect.reddit_apify import final_cost

    snapshots = [{"chargedEventCounts": {"post": 3}, "usageTotalUsd": 0.01}, {"chargedEventCounts": {"post": 5}, "usageTotalUsd": 0.02},
                 {"chargedEventCounts": {"post": 5}, "usageTotalUsd": 0.02}]

    class Client:
        def request(self, method, path, params=None, body=None):
            return snapshots.pop(0) if len(snapshots) > 1 else snapshots[0]

    run, cost = final_cost(Client(), "r1", {"post": 0.001}, sleep=lambda _: None)
    assert run["chargedEventCounts"] == {"post": 5}
    assert cost == pytest.approx(0.02)


def test_scrape_time_dates_are_unknown_and_subreddit_comes_from_url() -> None:
    post = {**POST, "createdAt": "2026-10-26T05:30:17Z", "scrapedAt": "2026-10-26T05:30:16Z"}
    comment = {**COMMENT, "subreddit": None, "scrapedAt": "2026-10-26T05:30:16Z"}
    p, c = items_to_records([post, comment], "2026-10-26T05:31:00+00:00")
    assert p.metadata["published_at"] is None and p.metadata["date_unknown"] is True
    assert c.metadata["date_unknown"] is False and c.metadata["published_at"].startswith("2023-07-22")
    assert c.metadata["subreddit"] == "IndiaInvestments"


def test_undated_posts_get_an_id_window_and_old_ones_are_dropped() -> None:
    from collect.reddit_apify import RawRecord, estimate_dates, meets_min_year

    def rec(rid: str, date: str | None) -> RawRecord:
        return RawRecord(rid, "https://x", "t", "x", {"kind": "post", "reddit_id": rid, "published_at": date, "date_unknown": date is None})

    records = [rec("t3_100", "2019-05-01"), rec("t3_200", "2020-12-01"), rec("t3_150", None), rec("t3_300", "2022-01-01"), rec("t3_250", None), rec("t3_400", None)]
    estimate_dates(records)
    by_id = {r.record_id: r.metadata for r in records}
    assert by_id["t3_150"]["date_estimate"] == {"after": "2019-05-01", "before": "2020-12-01", "method": "reddit_id_order"}
    assert by_id["t3_400"]["date_estimate"]["before"] is None
    assert not meets_min_year(by_id["t3_150"], 2021)  # whole window before 2021
    assert meets_min_year(by_id["t3_250"], 2021) and meets_min_year(by_id["t3_400"], 2021)
    assert by_id["t3_150"]["published_at"] is None  # estimate never replaces the real date
