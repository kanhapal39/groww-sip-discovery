"""AI relevance filter — labels each clean record yes / no / unsure.

Responsibility: Send clean records in batches to the configured LLM (Groq,
``openai/gpt-oss-20b``), store one result per record ID, rescue likely false
"no" labels with a keyword rule, and survive rate limits so a long run can be
stopped and resumed.

Usage:
    python -m pipeline.filter pilot            # 100 random items, stratified by app
    python -m pipeline.filter report           # pilot summary
    python -m pipeline.filter full [--auto-resume]

Outputs (gitignored): ``data/processed/filter_results.jsonl`` (one row per
record ID) and ``data/processed/filter_usage.jsonl`` (one row per request).
YouTube records are never sent (docs/source_access_plan.md §5a).
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml

from collect.youtube import load_api_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_VERSION = "filter-v1"
LABELS = ("yes", "no", "unsure")
MAX_TRANSIENT_RETRIES = 5
MAX_ITEM_ATTEMPTS = 2

SYSTEM_PROMPT = """You label short texts for research on why Indian investors start, continue, pause, reduce or stop SIPs (Systematic Investment Plans in mutual funds).

For each item set "relevant":
- "yes": an experience, reason, question, problem or feeling about starting, continuing, pausing, reducing or stopping a SIP; a new or first-time investor; SIP mandates or autopay; confusion about NAV or returns; mutual fund redemption or withdrawal.
- "no": only stocks, F&O, IPOs, demat or bank issues with no mutual fund angle; generic praise or complaints with nothing about SIPs or mutual funds; spam.
- "unsure": cannot tell.
Rules: a confused or first-time investor is never "no". When in doubt between "no" and "unsure", choose "unsure". "context" says where the text came from; label the text, not the context.

"reason": at most 10 words, describing only what the text says. Do not guess intent or add facts.

Illustrative examples (invented, not data):
{"id":1,"text":"Stopped my SIP after the market fell, scared of more losses"} -> {"id":1,"relevant":"yes","reason":"stopped SIP after market fall, fears more losses"}
{"id":2,"text":"F&O brokerage is too high, worst trading app"} -> {"id":2,"relevant":"no","reason":"complains about F&O brokerage charges"}
{"id":3,"text":"I am new here, which fund should I start with?"} -> {"id":3,"relevant":"yes","reason":"new investor asks which fund to start"}
{"id":4,"text":"Money deducted twice this month and support is not replying"} -> {"id":4,"relevant":"unsure","reason":"money deducted twice, support not replying"}

Return only JSON: {"results":[{"id":<id>,"relevant":"yes|no|unsure","reason":"..."}]} with exactly one entry per input id."""

# Safety net: a "no" is upgraded to "unsure" when the text names one of these
# AND is a question or written in the first person.
_RESCUE_TERMS = re.compile(
    r"(?<!\w)(?:sips?|mutual funds?|mf|lump ?sum|e-?mandates?|mandates?|auto[- ]?pay|navs?"
    r"|redemptions?|redeem(?:ed|ing)?|beginners?|newbies?"
    # Fund houses. Bank-owned AMCs (SBI, HDFC, ICICI, Axis, Kotak) are left out
    # because their names alone usually mean the bank.
    r"|nippon|mirae|parag parikh|ppfas|quant|motilal oswal|dsp|franklin templeton|franklin"
    r"|edelweiss|canara robeco|bandhan|invesco|sundaram|uti|aditya birla|absl|tata mutual"
    r"|navi mutual|whiteoak|baroda bnp|mahindra manulife|lic mf|hsbc mutual|amc)(?!\w)",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"\?|(?:^|[.!]\s*)(?:how|what|why|when|where|which|who|can|could|should|is|are|do|does|will|would)\b"
    r"|(?<!\w)(?:kya|kaise|kyu|kyun|kyon|kab|kaha|kahan)(?!\w)",
    re.IGNORECASE,
)
_FIRST_PERSON = re.compile(
    r"(?<!\w)(?:i|i'm|im|i've|ive|i'd|i'll|my|me|mine|myself|we|our|us"
    r"|mera|meri|mere|mujhe|maine|hum|humara|humne)(?!\w)",
    re.IGNORECASE,
)


def should_rescue(text: str) -> bool:
    return bool(_RESCUE_TERMS.search(text)) and bool(_QUESTION.search(text) or _FIRST_PERSON.search(text))


def truncate_words(text: str | None, limit: int) -> str:
    words = (text or "").split()
    return " ".join(words[:limit]) + (" …" if len(words) > limit else "")


def item_context(record: dict[str, Any]) -> str:
    """Stored context, or the review's provenance when there is none."""
    if record.get("context"):
        return record["context"]
    metadata = record.get("metadata") or {}
    if metadata.get("app_id"):
        return f"Google Play review of {metadata['app_id']}"
    if metadata.get("source") == "reddit":
        return f"Reddit {metadata.get('kind', 'post')} in r/{metadata.get('subreddit', '')}"
    return ""


def build_messages(batch: list[dict[str, Any]], max_text_words: int, max_context_words: int) -> list[dict[str, str]]:
    items = [
        {
            "id": i,
            "context": truncate_words(item_context(r), max_context_words),
            "text": truncate_words(r.get("text"), max_text_words),
        }
        for i, r in enumerate(batch, 1)
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Label these items:\n" + json.dumps(items, ensure_ascii=False)},
    ]


def parse_results(content: str, batch_size: int, max_reason_words: int) -> dict[int, tuple[str, str, bool]]:
    """Return {item id: (label, reason, reason_truncated)} for valid entries only."""
    match = re.search(r"\{.*\}", content or "", re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
    except ValueError:
        return {}
    parsed: dict[int, tuple[str, str, bool]] = {}
    for entry in payload.get("results", []) if isinstance(payload, dict) else []:
        try:
            item_id = int(entry["id"])
        except (KeyError, TypeError, ValueError):
            continue
        label = str(entry.get("relevant", "")).strip().lower()
        if not 1 <= item_id <= batch_size or label not in LABELS or item_id in parsed:
            continue
        words = str(entry.get("reason", "")).split()
        parsed[item_id] = (label, " ".join(words[:max_reason_words]), len(words) > max_reason_words)
    return parsed


def parse_duration(value: str | None) -> float | None:
    """Parse Groq durations such as "2m59.56s", "7.66s", "1h2m3s" or "120"."""
    if not value:
        return None
    value = value.strip()
    try:
        return float(value)
    except ValueError:
        pass
    parts = re.findall(r"([\d.]+)\s*(ms|h|m|s)", value)
    if not parts:
        return None
    scale = {"h": 3600, "m": 60, "s": 1, "ms": 0.001}
    return sum(float(n) * scale[u] for n, u in parts)


class RateLimited(Exception):
    def __init__(self, wait_seconds: float, daily: bool, message: str) -> None:
        super().__init__(message)
        self.wait_seconds = wait_seconds
        self.daily = daily


class TransientError(Exception):
    """Network problem or server error worth retrying."""


class FatalError(Exception):
    """Request rejected for a reason retrying will not fix."""


class RequestTooLarge(FatalError):
    """The request exceeds the model's per-request or per-minute token size."""


class InvalidOutput(FatalError):
    """The provider rejected the model's reply as invalid JSON (JSON mode)."""


@dataclass
class Limits:
    """Latest values from Groq's x-ratelimit-* headers."""

    limit_requests_day: int | None = None
    remaining_requests_day: int | None = None
    reset_requests_seconds: float | None = None
    limit_tokens_minute: int | None = None
    remaining_tokens_minute: int | None = None
    reset_tokens_seconds: float | None = None

    @classmethod
    def from_headers(cls, headers: Any) -> "Limits":
        def num(name: str) -> int | None:
            raw = headers.get(name)
            try:
                return int(float(raw)) if raw is not None else None
            except ValueError:
                return None

        return cls(
            limit_requests_day=num("x-ratelimit-limit-requests"),
            remaining_requests_day=num("x-ratelimit-remaining-requests"),
            reset_requests_seconds=parse_duration(headers.get("x-ratelimit-reset-requests")),
            limit_tokens_minute=num("x-ratelimit-limit-tokens"),
            remaining_tokens_minute=num("x-ratelimit-remaining-tokens"),
            reset_tokens_seconds=parse_duration(headers.get("x-ratelimit-reset-tokens")),
        )


@dataclass
class Response:
    content: str
    usage: dict[str, Any]
    limits: Limits
    finish_reason: str | None = None


class GroqClient:
    """Minimal OpenAI-compatible chat client. Errors never include the key."""

    def __init__(self, api_key: str, base_url: str, model: str, settings: dict[str, Any], timeout: float = 120.0) -> None:
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.settings = settings
        self.timeout = timeout

    def complete(self, messages: list[dict[str, str]]) -> Response:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.settings.get("temperature", 0.0),
            "response_format": {"type": "json_object"},
            "reasoning_effort": self.settings.get("reasoning_effort", "low"),
            "include_reasoning": False,
            "max_completion_tokens": self.settings.get("max_completion_tokens", 4000),
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": "sip-discovery-engine",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                payload = json.load(resp)
                limits = Limits.from_headers(resp.headers)
        except urllib.error.HTTPError as exc:
            message = _error_message(exc)
            if exc.code == 413 or re.search(r"request too large|context length|too many tokens", message, re.IGNORECASE):
                raise RequestTooLarge(f"HTTP {exc.code}: {message}") from None
            if exc.code == 400 and re.search(r"failed to validate json|json_validate_failed", message, re.IGNORECASE):
                raise InvalidOutput(f"HTTP {exc.code}: {message}") from None
            if exc.code == 429:
                wait = parse_duration(exc.headers.get("retry-after")) or _wait_from_message(message) or 60.0
                daily = bool(re.search(r"per day|\(TPD\)|\(RPD\)", message, re.IGNORECASE))
                raise RateLimited(wait, daily, message) from None
            if exc.code >= 500 or exc.code == 408:
                raise TransientError(f"HTTP {exc.code}: {message}") from None
            raise FatalError(f"HTTP {exc.code}: {message}") from None
        except (urllib.error.URLError, OSError) as exc:  # OSError covers socket.timeout on Python 3.9
            raise TransientError(f"network: {type(exc).__name__}: {exc}") from None
        choice = (payload.get("choices") or [{}])[0]
        return Response((choice.get("message") or {}).get("content") or "", payload.get("usage") or {}, limits, choice.get("finish_reason"))


def _error_message(exc: urllib.error.HTTPError) -> str:
    try:
        return str(json.load(exc).get("error", {}).get("message", exc.reason))
    except ValueError:
        return str(exc.reason)


def _wait_from_message(message: str) -> float | None:
    match = re.search(r"try again in ([\dhms.]+)", message)
    return parse_duration(match.group(1)) if match else None


class ResultStore:
    """Append-only JSONL keyed by record_id; the first result per ID wins."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.results: dict[str, dict[str, Any]] = {}
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        row = json.loads(line)
                        self.results.setdefault(row["record_id"], row)

    def __contains__(self, record_id: str) -> bool:
        return record_id in self.results

    def add(self, rows: Iterable[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            for row in rows:
                if row["record_id"] not in self.results:
                    self.results[row["record_id"]] = row
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_usage(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


@dataclass
class RunSummary:
    requested: int
    done_this_run: int = 0
    errors: int = 0
    rescued: int = 0
    tokens: int = 0
    requests: int = 0
    labels: Counter[str] = field(default_factory=Counter)
    stopped: str = "complete"

    def text(self, remaining: int) -> str:
        labels = ", ".join(f"{k} {self.labels[k]}" for k in LABELS)
        return (
            f"Stopped: {self.stopped}. Labelled this run: {self.done_this_run} of {self.requested} "
            f"({labels}; rescued by rule {self.rescued}; errors {self.errors}). "
            f"Requests {self.requests}, tokens {self.tokens:,}. Remaining: {remaining}."
        )


def wait_for_capacity(limits: Limits, est_tokens: int | None, auto_resume: bool, sleep: Callable[[float], None], log: Callable[[str], None]) -> str | None:
    """Sleep if the last headers say a limit is exhausted. Returns a stop reason or None."""
    if limits.remaining_requests_day == 0:
        wait = (limits.reset_requests_seconds or 3600) + 30
        if not auto_resume:
            return "daily request limit reached (run again later or use --auto-resume)"
        log(f"Daily request limit reached; waiting {wait / 60:.0f} min for reset")
        sleep(wait)
    if est_tokens and limits.remaining_tokens_minute is not None and limits.remaining_tokens_minute < est_tokens:
        sleep((limits.reset_tokens_seconds or 60) + 1)
    return None


def call_with_retries(
    client: Any,
    messages: list[dict[str, str]],
    usage_path: Path,
    run: str,
    auto_resume: bool,
    sleep: Callable[[float], None],
    log: Callable[[str], None],
) -> Response | str:
    """Call the model, waiting out rate limits and retrying transient errors.

    Returns the Response, or a stop reason string at the daily limit (without
    ``auto_resume``) or after repeated errors. FatalError propagates.
    """
    transient = 0
    while True:
        try:
            return client.complete(messages)
        except RateLimited as exc:
            append_usage(usage_path, {"at": datetime.now(timezone.utc).isoformat(), "run": run, "status": 429, "daily": exc.daily, "wait_seconds": exc.wait_seconds, "message": exc.args[0][:300]})
            if exc.daily and not auto_resume:
                return f"daily limit reached: {exc.args[0][:200]} (run again later or use --auto-resume)"
            log(f"Rate limited ({'daily' if exc.daily else 'per minute'}); waiting {exc.wait_seconds:.0f}s")
            sleep(exc.wait_seconds + (30 if exc.daily else 1))
        except TransientError as exc:
            transient += 1
            if transient > MAX_TRANSIENT_RETRIES:
                return f"repeated errors: {exc}"
            sleep(2**transient)


def make_row(record: dict[str, Any], label: str | None, reason: str, truncated: bool, model: str, run: str, error: str | None = None) -> dict[str, Any]:
    final, rescued = label, False
    if label == "no" and should_rescue(record.get("text") or ""):
        final, rescued = "unsure", True
    metadata = record.get("metadata") or {}
    return {
        "record_id": record["record_id"],
        "source": record.get("source") or metadata.get("source"),
        "app_id": metadata.get("app_id"),
        "year": record.get("year"),
        "relevant": final,
        "model_label": label,
        "reason": reason,
        "reason_truncated": truncated,
        "rescued_by_rule": rescued,
        "error": error,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "run": run,
        "labelled_at": datetime.now(timezone.utc).isoformat(),
    }


def run_filter(
    records: list[dict[str, Any]],
    client: GroqClient,
    store: ResultStore,
    usage_path: Path,
    settings: dict[str, Any],
    run: str,
    auto_resume: bool = False,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> RunSummary:
    """Label every record not already in ``store``, honouring rate limits."""
    pending = [r for r in records if r["record_id"] not in store]
    summary = RunSummary(requested=len(pending))
    batch_size = settings["batch_size"]
    attempts: Counter[str] = Counter()
    queue = list(pending)
    limits = Limits()
    est_tokens = None

    while queue:
        batch, queue = queue[:batch_size], queue[batch_size:]

        stop = wait_for_capacity(limits, est_tokens, auto_resume, sleep, log)
        if stop:
            summary.stopped = stop
            return summary
        messages = build_messages(batch, settings["max_text_words"], settings["max_context_words"])
        try:
            response = call_with_retries(client, messages, usage_path, run, auto_resume, sleep, log)
        except FatalError as exc:
            summary.stopped = f"request rejected: {exc}"
            return summary
        if isinstance(response, str):
            summary.stopped = response
            return summary

        limits = response.limits
        tokens = int(response.usage.get("total_tokens") or 0)
        est_tokens = max(est_tokens or 0, tokens)
        summary.requests += 1
        summary.tokens += tokens
        parsed = parse_results(response.content, len(batch), settings["max_reason_words"])
        append_usage(usage_path, {
            "at": datetime.now(timezone.utc).isoformat(), "run": run, "status": 200, "items": len(batch),
            "valid_items": len(parsed), "prompt_tokens": response.usage.get("prompt_tokens"),
            "completion_tokens": response.usage.get("completion_tokens"), "total_tokens": tokens,
            "remaining_requests_day": limits.remaining_requests_day, "remaining_tokens_minute": limits.remaining_tokens_minute,
        })

        rows = []
        for i, record in enumerate(batch, 1):
            if i in parsed:
                label, reason, truncated = parsed[i]
                rows.append(make_row(record, label, reason, truncated, client.model, run))
                continue
            attempts[record["record_id"]] += 1
            if attempts[record["record_id"]] < MAX_ITEM_ATTEMPTS:
                queue.append(record)
            else:
                rows.append(make_row(record, None, "", False, client.model, run, error="no valid label from model"))
        store.add(rows)
        for row in rows:
            summary.done_this_run += 1
            summary.labels[row["relevant"]] += row["relevant"] is not None
            summary.errors += row["error"] is not None
            summary.rescued += row["rescued_by_rule"]
        log(f"  {summary.done_this_run}/{summary.requested} labelled, {summary.tokens:,} tokens"
            + (f", {limits.remaining_requests_day} requests left today" if limits.remaining_requests_day is not None else ""))
    return summary


def eligible_records(clean_path: Path, allowed_sources: list[str]) -> list[dict[str, Any]]:
    with clean_path.open(encoding="utf-8") as fh:
        return [r for r in map(json.loads, fh) if r.get("source") in allowed_sources]


def group_key(record: dict[str, Any]) -> str:
    return (record.get("metadata") or {}).get("app_id") or record.get("source") or ""


def pilot_sample(records: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    """Random sample split as evenly as possible across apps/sources."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[group_key(record)].append(record)
    rng = random.Random(seed)
    keys = sorted(groups)
    sample: list[dict[str, Any]] = []
    for index, key in enumerate(keys):
        share = size // len(keys) + (1 if index < size % len(keys) else 0)
        sample.extend(rng.sample(groups[key], min(share, len(groups[key]))))
    return sample


def sample_for_app(records: list[dict[str, Any]], done: Any, app: str, size: int, seed: int) -> list[dict[str, Any]]:
    """Random ``size`` records from one app that are not already in ``done``."""
    pool = [r for r in records if group_key(r) == app and r["record_id"] not in done]
    return random.Random(seed).sample(pool, min(size, len(pool)))


def full_order(records: list[dict[str, Any]], first_year: int) -> list[dict[str, Any]]:
    """Records from ``first_year`` onward first, then older or undated ones."""
    recent = [r for r in records if (r.get("year") or 0) >= first_year]
    older = [r for r in records if (r.get("year") or 0) < first_year]
    return recent + older


def estimate_days(usage_path: Path, remaining: int, settings: dict[str, Any], requests_per_day: int | None) -> tuple[float, float, float] | None:
    """(tokens per item, days by token limit, days by request limit) from logged usage."""
    if not usage_path.exists():
        return None
    rows = [json.loads(l) for l in usage_path.open(encoding="utf-8") if l.strip()]
    ok = [r for r in rows if r.get("status") == 200]
    items = sum(r["items"] for r in ok)
    if not items:
        return None
    per_item = sum(r["total_tokens"] for r in ok) / items
    by_tokens = remaining * per_item / settings["daily_token_limit"]
    by_requests = remaining / settings["batch_size"] / requests_per_day if requests_per_day else 0.0
    return per_item, by_tokens, by_requests


def pilot_report(clean_path: Path, store: ResultStore, usage_path: Path, settings: dict[str, Any], seed: int, run: str = "pilot") -> None:
    texts = {}
    with clean_path.open(encoding="utf-8") as fh:
        for r in map(json.loads, fh):
            texts[r["record_id"]] = r
    pilot = [row for row in store.results.values() if row["run"] == run]
    print(f"Run {run}: {len(pilot)} items")
    by_source: dict[str, Counter[str]] = defaultdict(Counter)
    for row in pilot:
        by_source[row["app_id"] or row["source"]][str(row["relevant"])] += 1
    print(f"  {'source':<24} yes  no  unsure  error")
    for key in sorted(by_source):
        c = by_source[key]
        print(f"  {key:<24} {c['yes']:>3} {c['no']:>3} {c['unsure']:>7} {c['None']:>6}")
    total = Counter(str(r["relevant"]) for r in pilot)
    print(f"  {'TOTAL':<24} {total['yes']:>3} {total['no']:>3} {total['unsure']:>7} {total['None']:>6}")
    print(f"  rescued_by_rule: {sum(r['rescued_by_rule'] for r in pilot)}")

    rng = random.Random(seed)
    for label in ("yes", "no"):
        rows = [r for r in pilot if r["relevant"] == label]
        print(f"\n{min(10, len(rows))} random '{label}' items")
        for row in rng.sample(rows, min(10, len(rows))):
            text = " ".join((texts[row["record_id"]]["text"] or "").split())
            print(f"  [{row['app_id']}] {text[:220]!r}\n      -> {row['reason']}")

    usage = [json.loads(l) for l in usage_path.open(encoding="utf-8") if l.strip()] if usage_path.exists() else []
    ok = [u for u in usage if u.get("run") == run and u.get("status") == 200]
    print(f"\nTokens: {sum(u['total_tokens'] for u in ok):,} over {len(ok)} requests "
          f"(prompt {sum(u['prompt_tokens'] or 0 for u in ok):,}, completion {sum(u['completion_tokens'] or 0 for u in ok):,})")
    remaining = len([r for r in eligible_records(clean_path, settings["allowed_sources"]) if r["record_id"] not in store])
    rpd = next((u["remaining_requests_day"] for u in reversed(ok) if u.get("remaining_requests_day") is not None), None)
    estimate = estimate_days(usage_path, remaining, settings, settings.get("requests_per_day"))
    if estimate:
        per_item, by_tokens, by_requests = estimate
        print(f"Full run: {remaining:,} items left, ~{per_item:.0f} tokens per item -> ~{remaining * per_item:,.0f} tokens")
        print(f"  ~{by_tokens:.1f} days at {settings['daily_token_limit']:,} tokens/day"
              + (f"; ~{by_requests:.1f} days at {settings['requests_per_day']} requests/day" if by_requests else ""))
    if rpd is not None:
        print(f"  Requests left today (from headers): {rpd}")


def load_settings() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    return config, config["llm"], config["pipeline"]["relevance"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI relevance filter (yes / no / unsure).")
    parser.add_argument("mode", choices=["pilot", "sample", "full", "report"])
    parser.add_argument("--auto-resume", action="store_true", help="wait for limit resets instead of stopping")
    parser.add_argument("--app", help="sample mode: app ID to sample from, e.g. com.nextbillion.groww")
    parser.add_argument("--size", type=int, help="sample mode: number of items")
    args = parser.parse_args(argv)
    if args.mode == "sample" and not (args.app and args.size):
        parser.error("sample mode needs --app and --size")
    run = f"sample:{args.app}" if args.mode == "sample" else args.mode

    config, llm, settings = load_settings()
    processed = PROJECT_ROOT / config["paths"]["processed"]
    clean_path = processed / "clean.jsonl"
    store = ResultStore(processed / "filter_results.jsonl")
    usage_path = processed / "filter_usage.jsonl"
    seed = settings["sample_seed"]

    if args.mode == "report":
        pilot_report(clean_path, store, usage_path, settings, seed)
        return 0

    records = eligible_records(clean_path, settings["allowed_sources"])
    if args.mode == "pilot":
        targets = pilot_sample(records, settings["pilot_size"], seed)
    elif args.mode == "sample":
        targets = sample_for_app(records, store, args.app, args.size, seed)
    else:
        targets = full_order(records, settings["full_run_first_year"])
    client = GroqClient(load_api_key(llm["auth_env_var"], PROJECT_ROOT / ".env"), llm["base_url"], llm["model_id"], {**llm, **settings})
    summary = run_filter(targets, client, store, usage_path, settings, run=run, auto_resume=args.auto_resume)
    remaining = sum(1 for r in targets if r["record_id"] not in store)
    print(summary.text(remaining))
    if args.mode in ("pilot", "sample"):
        print()
        pilot_report(clean_path, store, usage_path, settings, seed, run=run)
    return 0 if summary.stopped == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
