"""Run approved collectors.

Usage:
    python -m collect.run_all play_store

Only sources listed in ``collection.sources`` in config.yaml can run. Raw
records go to ``paths.raw``; keyword-filtered records go to
``paths.processed``. Both are JSONL and gitignored.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from collect.base import RawRecord

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path = PROJECT_ROOT / "config.yaml") -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def write_jsonl(records: list[RawRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def run_play_store(config: dict[str, Any]) -> int:
    from collect.play_store import compile_keywords, fetch_reviews, matches_keywords

    settings = config["collection"]["play_store"]
    pattern = compile_keywords(settings["keywords"])
    records, skipped = fetch_reviews(
        apps=settings["apps"],
        lang=settings["lang"],
        country=settings["country"],
        max_reviews_per_app=settings["max_reviews_per_app"],
        pause_seconds=settings["pause_seconds_between_apps"],
    )
    kept = [r for r in records if matches_keywords(r.text, pattern)]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = PROJECT_ROOT / config["paths"]["raw"] / f"play_store_{stamp}.jsonl"
    kept_path = PROJECT_ROOT / config["paths"]["processed"] / f"play_store_kept_{stamp}.jsonl"
    write_jsonl(records, raw_path)
    write_jsonl(kept, kept_path)

    for line in skipped:
        print(f"SKIPPED {line}")
    print(f"Pulled: {len(records)}")
    print(f"Kept after keyword filter: {len(kept)}")
    print(f"Raw:  {raw_path.relative_to(PROJECT_ROOT)}")
    print(f"Kept: {kept_path.relative_to(PROJECT_ROOT)}")
    return 0 if records else 1


def run_youtube(config: dict[str, Any]) -> int:
    from collect.play_store import compile_keywords, matches_keywords
    from collect.youtube import QuotaBudget, fetch_comments, load_api_key, make_fetcher, parse_video_id

    settings = config["collection"]["youtube"]
    pattern = compile_keywords(settings["keywords"])
    video_ids = [parse_video_id(v) for v in settings["videos"]]
    try:
        api_key = load_api_key(settings["api_key_env_var"], PROJECT_ROOT / ".env")
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    budget = QuotaBudget(settings["max_quota_units"])
    records, skipped = fetch_comments(
        video_ids=video_ids,
        max_comments_total=settings["max_comments_total"],
        budget=budget,
        fetch=make_fetcher(api_key),
        retention_days=settings["retention_days"],
        order=settings["order"],
    )
    kept = [r for r in records if matches_keywords(r.text, pattern)]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = PROJECT_ROOT / config["paths"]["raw"] / f"youtube_{stamp}.jsonl"
    kept_path = PROJECT_ROOT / config["paths"]["processed"] / f"youtube_kept_{stamp}.jsonl"
    write_jsonl(records, raw_path)
    write_jsonl(kept, kept_path)

    for line in skipped:
        print(f"SKIPPED {line}")
    print(f"Pulled: {len(records)}")
    print(f"Kept after keyword filter: {len(kept)}")
    print(f"Quota used: {budget.used} of {budget.limit} budgeted units")
    if records:
        print(f"Delete or refresh by: {records[0].metadata['delete_after']}")
    print(f"Raw:  {raw_path.relative_to(PROJECT_ROOT)}")
    print(f"Kept: {kept_path.relative_to(PROJECT_ROOT)}")
    return 0 if records else 1


RUNNERS = {"play_store": run_play_store, "youtube": run_youtube}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run approved collectors.")
    parser.add_argument("sources", nargs="+", choices=sorted(RUNNERS))
    args = parser.parse_args(argv)

    config = load_config()
    approved = set(config["collection"]["sources"] or [])
    status = 0
    for source in args.sources:
        if source not in approved:
            print(f"{source} is not approved in config.yaml collection.sources", file=sys.stderr)
            status = 1
            continue
        status |= RUNNERS[source](config)
    return status


if __name__ == "__main__":
    sys.exit(main())
