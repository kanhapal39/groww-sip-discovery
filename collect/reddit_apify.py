"""Reddit collector via an Apify actor — capped, user-approved pilot.

Responsibility: Run a pay-per-event Reddit actor on Apify within a hard
budget, convert posts and comments into RawRecords with provenance, and remove
every username before anything is written to disk.

This scrapes Reddit's public web through a third party, not Reddit's official
API. Reddit is BLOCKED in docs/source_access_plan.md; the user chose to accept
that terms-of-service risk on 2026-10-26 (§6a).

Usage:
    python -m collect.reddit_apify price      # cost per 1,000 results (free)
    python -m collect.reddit_apify test       # max 30 items
    python -m collect.reddit_apify search     # step 1: posts only
    python -m collect.reddit_apify shortlist  # step 2: free, prints titles
    python -m collect.reddit_apify comments   # step 3: comments for the shortlist

Every run is refused if its worst-case cost would take total spend (kept in a
ledger) over the budget, and Apify is also told to stop charging at the
remaining budget (``maxTotalChargeUsd``).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml

from collect.base import RawRecord, accept_record
from collect.youtube import load_api_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_NAME = "reddit"
API_BASE = "https://api.apify.com/v2"
_RECORD_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "sip-discovery-engine/reddit")
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}

# Only these output fields are ever read; everything else (authors, flairs,
# avatars, awards) is dropped. Several names are tried because actors differ.
ID_KEYS = ("id", "name", "fullname", "postId", "commentId")
TITLE_KEYS = ("title",)
BODY_KEYS = ("body", "selfText", "selftext", "text", "content", "description")
POST_TITLE_KEYS = ("postTitle", "post_title", "linkTitle")
REMOVED_TEXTS = {"[deleted]", "[removed]"}
URL_KEYS = ("permalink", "url", "postUrl", "link")
SUBREDDIT_KEYS = ("subreddit", "subredditName", "community", "communityName")
CREATED_KEYS = ("createdAt", "created_utc", "createdUtc", "created", "date", "publishedAt")
SCORE_KEYS = ("score", "upvotes", "ups")
COMMENTS_KEYS = ("numComments", "num_comments", "commentsCount", "commentCount")
PARENT_POST_KEYS = ("postId", "post_id", "linkId", "link_id", "parentPostId")
DEPTH_KEYS = ("depth", "level")
KIND_KEYS = ("dataType", "type", "kind", "itemType")
AUTHOR_KEYS = ("author", "username", "authorName", "author_name", "user", "userName", "authorUsername")

_USER_MENTION = re.compile(r"(?<![\w/])/?u/[A-Za-z0-9_-]{3,20}", re.IGNORECASE)
_SUBREDDIT_IN_URL = re.compile(r"reddit\.com/r/([A-Za-z0-9_]+)/", re.IGNORECASE)
SCRAPED_KEYS = ("scrapedAt", "scraped_at")
# A created time this close to the scrape time is the actor's fallback, not the real date.
UNRELIABLE_DATE_SECONDS = 600
_USER_URL = re.compile(r"(reddit\.com/(?:u|user))/[A-Za-z0-9_-]{3,20}", re.IGNORECASE)


class BudgetExceeded(RuntimeError):
    """A run's worst-case cost would take total spend over the budget."""


# --- pricing and budget --------------------------------------------------------


def event_prices(actor: dict[str, Any], plan: str) -> dict[str, float]:
    """Current price per event in USD for the account's plan tier."""
    infos = actor.get("pricingInfos") or []
    if not infos:
        raise ValueError("actor has no pricing info")
    current = infos[-1]
    if current.get("pricingModel") != "PAY_PER_EVENT":
        raise ValueError(f"expected PAY_PER_EVENT pricing, got {current.get('pricingModel')}")
    prices: dict[str, float] = {}
    for name, event in ((current.get("pricingPerEvent") or {}).get("actorChargeEvents") or {}).items():
        tiers = event.get("eventTieredPricingUsd")
        if tiers:
            tier = tiers.get(plan) or tiers.get("FREE")
            price = tier.get("tieredEventPriceUsd") if tier else None
        else:
            price = event.get("eventPriceUsd")
        if price is not None:
            prices[name] = float(price)
    return prices


def worst_case_cost(prices: dict[str, float], posts: int, comments: int) -> float:
    """Highest possible charge for one run: start fee + every post + every comment."""
    return prices.get("start", 0.0) + posts * prices.get("post", 0.0) + comments * prices.get("comment", 0.0)


def run_cost(prices: dict[str, float], charged: dict[str, int]) -> float:
    """Actual charge from a run's ``chargedEventCounts``."""
    return sum(prices.get(name, 0.0) * count for name, count in (charged or {}).items())


class Ledger:
    """Spend recorded per run, kept next to the raw data (gitignored)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.runs: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    @property
    def spent(self) -> float:
        return sum(r["cost_usd"] for r in self.runs)

    def check(self, worst_case: float, budget: float) -> float:
        """Return the remaining budget, or raise if the run could exceed it."""
        remaining = budget - self.spent
        if worst_case > remaining:
            raise BudgetExceeded(
                f"worst case ${worst_case:.4f} exceeds remaining budget ${remaining:.4f} (spent ${self.spent:.4f} of ${budget:.2f})"
            )
        return remaining

    def add(self, entry: dict[str, Any]) -> None:
        self.runs.append(entry)
        self._save()

    def add_correction(self) -> None:
        """Save after an existing entry was updated in place."""
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.runs, indent=2), encoding="utf-8")


# --- anonymization and records -----------------------------------------------


def first(item: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def decode(text: Any) -> str:
    """Decode HTML entities (twice, for double-escaped Reddit text)."""
    value = html.unescape(html.unescape(str(text or "")))
    return value.replace("​", "").strip()


def author_names(items: Iterable[dict[str, Any]]) -> set[str]:
    names = set()
    for item in items:
        for key in AUTHOR_KEYS:
            value = item.get(key)
            if isinstance(value, dict):
                value = value.get("name") or value.get("username")
            if isinstance(value, str) and len(value) >= 3 and value.lower() not in {"[deleted]", "automoderator"}:
                names.add(value)
    return names


def scrub(text: str, names: set[str]) -> str:
    """Remove u/ mentions, user-profile links and any known author name."""
    text = _USER_URL.sub(r"\1/[user]", text)
    text = _USER_MENTION.sub("u/[user]", text)
    for name in sorted(names, key=len, reverse=True):
        text = re.sub(rf"(?<![\w-]){re.escape(name)}(?![\w-])", "[user]", text, flags=re.IGNORECASE)
    return text


def item_kind(item: dict[str, Any]) -> str:
    kind = str(first(item, KIND_KEYS) or "").lower()
    if "comment" in kind or kind == "t1":
        return "comment"
    if "post" in kind or kind == "t3":
        return "post"
    return "post" if first(item, TITLE_KEYS) else "comment"


def to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except ValueError:
        return str(value)


def published_date(item: dict[str, Any]) -> tuple[str | None, bool]:
    """(ISO date or None, unreliable). Dates equal to the scrape time are treated as unknown."""
    created = to_iso(first(item, CREATED_KEYS))
    scraped = to_iso(first(item, SCRAPED_KEYS))
    if created and scraped:
        try:
            gap = abs((datetime.fromisoformat(created) - datetime.fromisoformat(scraped)).total_seconds())
        except ValueError:
            return created, False
        if gap < UNRELIABLE_DATE_SECONDS:
            return None, True
    return created, False


def id_number(reddit_fullname: str) -> int | None:
    """Reddit IDs are base-36 counters that grow over time (t3_abc -> int)."""
    try:
        return int(reddit_fullname.split("_", 1)[1], 36)
    except (IndexError, ValueError):
        return None


def estimate_dates(records: list[RawRecord]) -> None:
    """Give undated records a date window from the nearest dated IDs of the same kind.

    Sets ``date_estimate`` = {"after": date or None, "before": date or None,
    "method": "reddit_id_order"}. Posts and comments use separate ID counters.
    The real ``published_at`` stays None: this is an estimate, not an observation.
    """
    import bisect

    for kind in ("post", "comment"):
        anchors = sorted(
            (n, r.metadata["published_at"][:10]) for r in records
            if r.metadata["kind"] == kind and not r.metadata["date_unknown"] and (n := id_number(r.metadata["reddit_id"])) is not None
        )
        numbers = [a[0] for a in anchors]
        for r in records:
            if r.metadata["kind"] != kind or not r.metadata["date_unknown"]:
                continue
            n = id_number(r.metadata["reddit_id"])
            if n is None or not anchors:
                continue
            i = bisect.bisect_left(numbers, n)
            r.metadata["date_estimate"] = {
                "after": anchors[i - 1][1] if i > 0 else None,
                "before": anchors[i][1] if i < len(anchors) else None,
                "method": "reddit_id_order",
            }


def meets_min_year(metadata: dict[str, Any], min_year: int) -> bool:
    """Dated: year >= min_year. Undated: kept unless its whole estimated window is older."""
    if not metadata["date_unknown"]:
        return (metadata.get("published_at") or "0")[:4] >= str(min_year)
    before = (metadata.get("date_estimate") or {}).get("before")
    return not before or before[:4] >= str(min_year)


def absolute_url(value: Any) -> str:
    url = str(value or "")
    if url.startswith("/"):
        url = "https://www.reddit.com" + url
    return url


def reddit_id(item: dict[str, Any], kind: str) -> str:
    raw = str(first(item, ID_KEYS) or "")
    if not raw:
        return ""
    return raw if raw.startswith(("t1_", "t3_")) else f"{'t1' if kind == 'comment' else 't3'}_{raw}"


def thread_context(title: str, body: str, words: int = 60) -> str:
    """The post as context for its comments: title plus the start of the body."""
    body_words = body.split()
    snippet = " ".join(body_words[:words]) + (" …" if len(body_words) > words else "")
    return f"{title}\n\n{snippet}".strip()


def items_to_records(items: list[dict[str, Any]], collected_at: str, posts_by_id: dict[str, dict[str, Any]] | None = None) -> list[RawRecord]:
    """Anonymized RawRecords for posts and comments.

    ``posts_by_id`` maps post IDs (t3_…) to already-anonymized post records so
    comments fetched in a later run still get their thread context.
    """
    names = author_names(items)
    posts: dict[str, dict[str, Any]] = dict(posts_by_id or {})
    records: list[RawRecord] = []
    parsed = []
    for item in items:
        kind = item_kind(item)
        rid = reddit_id(item, kind)
        if not rid:
            continue
        title = scrub(decode(first(item, TITLE_KEYS)), names) if kind == "post" else ""
        body = scrub(decode(first(item, BODY_KEYS)), names)
        url = scrub(absolute_url(first(item, URL_KEYS)), names)
        parsed.append((item, kind, rid, title, body, url))
        if kind == "post":
            posts[rid] = {"title": title, "body": body, "url": url}

    for item, kind, rid, title, body, url in parsed:
        subreddit = str(first(item, SUBREDDIT_KEYS) or "").removeprefix("r/")
        if not subreddit and (match := _SUBREDDIT_IN_URL.search(url)):
            subreddit = match.group(1)
        published, unreliable = published_date(item)
        metadata: dict[str, Any] = {
            "source": SOURCE_NAME,
            "kind": kind,
            "reddit_id": rid,
            "subreddit": subreddit,
            "published_at": published,
            "date_unknown": unreliable or published is None,
            "score": first(item, SCORE_KEYS),
        }
        if kind == "post":
            metadata.update(title=title, num_comments=first(item, COMMENTS_KEYS))
            text = f"{title}\n\n{body}".strip()
        else:
            post_id = str(first(item, PARENT_POST_KEYS) or "")
            post_id = post_id if post_id.startswith("t3_") or not post_id else f"t3_{post_id}"
            post = posts.get(post_id)
            metadata.update(post_id=post_id or None, depth=first(item, DEPTH_KEYS))
            if post:
                metadata["thread_question"] = thread_context(post["title"], post["body"])
                metadata["post_url"] = post["url"]
            elif first(item, POST_TITLE_KEYS):
                metadata["thread_question"] = scrub(decode(first(item, POST_TITLE_KEYS)), names)
            text = body
            if text in REMOVED_TEXTS:
                continue
        if not url:
            continue
        records.append(accept_record(RawRecord(
            record_id=str(uuid.uuid5(_RECORD_NAMESPACE, rid)),
            source_url=url,
            collected_at=collected_at,
            text=text,
            metadata=metadata,
        )))
    return records


# --- Apify client ------------------------------------------------------------------


class ApifyClient:
    """Minimal Apify API client. The token is sent in a header and never logged."""

    def __init__(self, token: str, timeout: float = 120.0) -> None:
        self._token = token
        self.timeout = timeout

    def request(self, method: str, path: str, params: dict[str, Any] | None = None, body: Any = None) -> Any:
        url = f"{API_BASE}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self._token}", "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as exc:
            try:
                message = json.load(exc).get("error", {}).get("message", exc.reason)
            except ValueError:
                message = exc.reason
            raise RuntimeError(f"Apify HTTP {exc.code}: {message}") from None
        return payload.get("data", payload) if isinstance(payload, dict) else payload

    def plan(self) -> str:
        return ((self.request("GET", "/users/me").get("plan") or {}).get("id")) or "FREE"

    def actor(self, actor_id: str) -> dict[str, Any]:
        return self.request("GET", f"/acts/{actor_id}")

    def run(self, actor_id: str, run_input: dict[str, Any], max_charge_usd: float, max_items: int, memory_mb: int, timeout_secs: int,
            sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = print) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Start a run with hard caps, wait for it to finish, return (run, items)."""
        run = self.request("POST", f"/acts/{actor_id}/runs", params={
            "maxTotalChargeUsd": f"{max_charge_usd:.4f}", "maxItems": max_items, "memory": memory_mb, "timeout": timeout_secs,
        }, body=run_input)
        log(f"  run {run['id']} started")
        while run.get("status") not in TERMINAL_STATUSES:
            sleep(5)
            try:  # waitForFinish must stay well under the socket timeout
                run = self.request("GET", f"/actor-runs/{run['id']}", params={"waitForFinish": 30})
            except (TimeoutError, OSError) as exc:
                log(f"  polling error ({type(exc).__name__}); retrying")
        log(f"  run {run['id']} {run['status']}")
        items = self.request("GET", f"/datasets/{run['defaultDatasetId']}/items", params={"clean": "true", "format": "json"})
        return run, items if isinstance(items, list) else []


# --- steps ---------------------------------------------------------------------------


def search_urls(subreddits: list[str], queries: list[str]) -> list[str]:
    """One Reddit search URL per subreddit × query, restricted to that subreddit."""
    return [
        f"https://www.reddit.com/r/{sub}/search/?" + urllib.parse.urlencode({"q": q, "restrict_sr": "1", "sort": "relevance", "t": "all"})
        for sub in subreddits for q in queries
    ]


def shortlist(posts: list[dict[str, Any]], title_terms: re.Pattern[str], sip_terms: re.Pattern[str]) -> list[dict[str, Any]]:
    """Posts whose title has a lapse/problem term AND whose title or body is about SIPs or mutual funds."""
    return [
        p for p in posts
        if title_terms.search(p["metadata"].get("title") or "") and sip_terms.search(p["text"] or "")
    ]


def read_manual_urls(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("http")]


def write_jsonl(records: Iterable[RawRecord | dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            row = record if isinstance(record, dict) else record.__dict__
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def load_records(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            rows.extend(json.loads(l) for l in fh if l.strip())
    return rows


def execute(client: ApifyClient, settings: dict[str, Any], ledger: Ledger, prices: dict[str, float], step: str,
            run_input: dict[str, Any], max_posts: int, max_comments: int) -> tuple[dict[str, Any], list[dict[str, Any]], float]:
    """Budget-check, run, and record the actual cost. Returns (run, items, cost)."""
    worst = worst_case_cost(prices, max_posts, max_comments)
    remaining = ledger.check(worst, settings["budget_usd"])
    print(f"{step}: worst case ${worst:.4f} (max {max_posts} posts, {max_comments} comments); remaining budget ${remaining:.4f}")
    run, items = client.run(settings["actor_id"], run_input, max_charge_usd=min(worst, remaining), max_items=max_posts + max_comments,
                            memory_mb=settings["memory_mbytes"], timeout_secs=settings["timeout_secs"])
    run, cost = final_cost(client, run["id"], prices)
    charged = run.get("chargedEventCounts") or {}
    ledger.add({
        "step": step, "run_id": run["id"], "status": run.get("status"), "at": datetime.now(timezone.utc).isoformat(),
        "items": len(items), "charged_events": charged, "cost_usd": round(cost, 6),
        "platform_usage_usd": run.get("usageTotalUsd"), "worst_case_usd": round(worst, 6),
    })
    return run, items, cost


def final_cost(client: ApifyClient, run_id: str, prices: dict[str, float], sleep: Callable[[float], None] = time.sleep) -> tuple[dict[str, Any], float]:
    """Re-read a finished run until its charges stop changing (they settle a few seconds late).

    Returns (run, cost) with cost = the larger of charged events × price and the run's usageTotalUsd.
    """
    run = client.request("GET", f"/actor-runs/{run_id}")
    for _ in range(6):
        sleep(5)
        again = client.request("GET", f"/actor-runs/{run_id}")
        if again.get("chargedEventCounts") == run.get("chargedEventCounts") and again.get("usageTotalUsd") == run.get("usageTotalUsd"):
            break
        run = again
    return run, max(run_cost(prices, run.get("chargedEventCounts") or {}), float(run.get("usageTotalUsd") or 0.0))


def main(argv: list[str] | None = None) -> int:
    from collect.play_store import compile_keywords

    parser = argparse.ArgumentParser(description="Reddit via Apify, within a hard budget.")
    parser.add_argument("step", choices=["price", "test", "search", "shortlist", "comments", "rebuild"])
    parser.add_argument("--run-id", help="rebuild: re-read a finished run's results (free) and rewrite its file")
    parser.add_argument("--as-step", choices=["test", "search", "comments"], help="rebuild: step of a run missing from the ledger (e.g. after a crash)")
    args = parser.parse_args(argv)
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    settings = config["collection"]["reddit"]
    raw_dir = PROJECT_ROOT / config["paths"]["raw"]
    ledger = Ledger(raw_dir / "reddit_apify_ledger.json")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    collected_at = datetime.now(timezone.utc).isoformat()
    sip_terms = compile_keywords(config["pipeline"]["cleaning"]["keywords"])

    if args.step == "shortlist":
        posts = [p for p in load_records(sorted(raw_dir.glob("reddit_posts_*.jsonl"))) if p["metadata"]["kind"] == "post"]
        chosen = shortlist(posts, compile_keywords(settings["shortlist_title_terms"]), sip_terms)
        (raw_dir / "reddit_shortlist.json").write_text(json.dumps([p["source_url"] for p in chosen], indent=2), encoding="utf-8")
        print(f"Shortlist: {len(chosen)} of {len(posts)} posts")
        for p in chosen:
            print(f"  [r/{p['metadata']['subreddit']}, {str(p['metadata']['published_at'])[:10]}] {p['metadata']['title']}")
        return 0

    token = next((t for t in (_try_key(v) for v in settings["token_env_vars"]) if t), None)
    if not token:
        print(f"None of {settings['token_env_vars']} is set in .env", file=sys.stderr)
        return 1
    client = ApifyClient(token)
    plan = client.plan()
    prices = event_prices(client.actor(settings["actor_id"]), plan)
    budget = settings["budget_usd"]
    print(f"Actor {settings['actor_id']} ({plan} plan): post ${prices.get('post', 0) * 1000:.2f}/1,000, "
          f"comment ${prices.get('comment', 0) * 1000:.2f}/1,000, start ${prices.get('start', 0):.4f}/run. "
          f"Spent ${ledger.spent:.4f} of ${budget:.2f}.")
    if args.step == "price":
        return 0

    try:
        if args.step == "rebuild":
            entry = next((r for r in ledger.runs if r["run_id"] == args.run_id), None)
            if not entry and not args.as_step:
                print(f"run {args.run_id} is not in the ledger; pass --as-step to record it", file=sys.stderr)
                return 1
            if not entry:
                entry = {"step": args.as_step, "run_id": args.run_id, "at": datetime.now(timezone.utc).isoformat(), "adopted_after_crash": True}
                ledger.add(entry)
            run, cost = final_cost(client, args.run_id, prices)
            entry.update(cost_usd=round(cost, 6), charged_events=run.get("chargedEventCounts"), platform_usage_usd=run.get("usageTotalUsd"),
                         status=run.get("status"))
            ledger.add_correction()
            items = client.request("GET", f"/datasets/{run['defaultDatasetId']}/items", params={"clean": "true", "format": "json"})
            prefix = {"test": "reddit_test", "search": "reddit_posts", "comments": "reddit_comments"}[entry["step"]]
            for old in raw_dir.glob(f"{prefix}_*.jsonl"):
                if entry.get("file") == old.name or entry["step"] == "test":
                    old.unlink()
            out = raw_dir / f"{prefix}_{stamp}.jsonl"
            entry["file"] = out.name
            ledger.add_correction()
        elif args.step == "test":
            t = settings["test"]
            run_input = {"searchQuery": t["query"], "searchSubreddit": t["subreddit"], "sort": "relevance", "timeFilter": "all",
                         "maxPostsPerSource": t["max_posts"], "includeComments": True, "maxCommentsPerPost": t["comments_per_post"],
                         "commentDepth": 1, "deduplicatePosts": True}
            run, items, cost = execute(client, settings, ledger, prices, "test", run_input, t["max_posts"], t["max_posts"] * t["comments_per_post"])
            out = raw_dir / f"reddit_test_{stamp}.jsonl"
        elif args.step == "search":
            s = settings["search"]
            urls = search_urls(settings["subreddits"], settings["queries"])
            run_input = {"urls": urls, "sort": "relevance", "timeFilter": "all", "maxPostsPerSource": s["max_posts_per_search"],
                         "includeComments": False, "deduplicatePosts": True}
            run, items, cost = execute(client, settings, ledger, prices, "search", run_input, len(urls) * s["max_posts_per_search"], 0)
            out = raw_dir / f"reddit_posts_{stamp}.jsonl"
        else:
            c = settings["comments"]
            short_path = raw_dir / "reddit_shortlist.json"
            shortlisted = json.loads(short_path.read_text(encoding="utf-8")) if short_path.exists() else []
            manual = read_manual_urls(PROJECT_ROOT / settings["manual_threads_file"])
            urls = list(dict.fromkeys(manual + shortlisted))
            per_thread = worst_case_cost({**prices, "start": 0.0}, 1, c["per_post"])
            room = budget - ledger.spent - prices.get("start", 0.0)
            fit = max(0, int(room // per_thread)) if per_thread else len(urls)
            if fit < len(urls):
                print(f"Budget fits {fit} of {len(urls)} threads; manual URLs first, the rest are skipped")
                urls = urls[:fit]
            if not urls:
                print("No thread URLs to fetch.")
                return 1
            run_input = {"urls": urls, "maxPostsPerSource": 1, "includeComments": True, "maxCommentsPerPost": c["per_post"],
                         "commentDepth": c["depth"], "deduplicatePosts": True}
            run, items, cost = execute(client, settings, ledger, prices, "comments", run_input, len(urls), len(urls) * c["per_post"])
            out = raw_dir / f"reddit_comments_{stamp}.jsonl"
    except BudgetExceeded as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3

    posts_by_id = {}
    for p in load_records(sorted(raw_dir.glob("reddit_posts_*.jsonl"))):
        if p["metadata"]["kind"] == "post":
            title = p["metadata"].get("title") or ""
            posts_by_id[p["metadata"]["reddit_id"]] = {"title": title, "body": p["text"][len(title):].strip(), "url": p["source_url"]}
    records = items_to_records(items, collected_at, posts_by_id)
    min_year = settings["min_year"]
    estimate_dates(records)
    kept = [r for r in records if meets_min_year(r.metadata, min_year)]
    write_jsonl(kept, out)
    if args.step != "rebuild" and ledger.runs:
        ledger.runs[-1]["file"] = out.name
        ledger.add_correction()
    kinds = {k: sum(r.metadata["kind"] == k for r in kept) for k in ("post", "comment")}
    unknown = sum(r.metadata["date_unknown"] for r in kept)
    print(f"Received {len(items)} items -> {len(records)} records -> {len(kept)} from {min_year}+ or undated "
          f"({kinds['post']} posts, {kinds['comment']} comments; {unknown} with unknown date)")
    print(f"Cost this run: ${cost:.4f} (charged events {run.get('chargedEventCounts')}); total spent ${ledger.spent:.4f} of ${budget:.2f}")
    print(f"Saved (usernames removed): {out.relative_to(PROJECT_ROOT)}")
    return 0


def _try_key(env_var: str) -> str | None:
    try:
        return load_api_key(env_var, PROJECT_ROOT / ".env")
    except RuntimeError:
        return None


if __name__ == "__main__":
    sys.exit(main())
