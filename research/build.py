"""Rebuild the dashboard's data: Golden Dataset index and quality metrics.

Usage:
    python -m research.build

Reads data/manual/golden_dataset.jsonl (authoritative) and pipeline files;
writes the dashboard's only inputs to data/export/:
  golden_public.jsonl    approved, publishable rows without internal review fields
  quality_metrics.json   data quality figures
The dashboard builds its search index from these at startup. No API calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from research.quality import build_quality
from research.store import golden_version, is_public, load_golden, normalise, public_view

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def paths(config: dict) -> dict[str, Path]:
    export = PROJECT_ROOT / config["paths"]["export"]
    return {
        "golden": PROJECT_ROOT / config["golden_dataset"]["manual_path"] / "golden_dataset.jsonl",
        "public": export / "golden_public.jsonl",
        "quality": export / "quality_metrics.json",
    }


def main() -> int:
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    p = paths(config)
    rows = load_golden(p["golden"])
    # Internal review fields are dropped; approval and the reviewed flag are kept (not sensitive).
    public = [{**public_view(r), "review_status": "approved", "individually_reviewed": normalise(r)["individually_reviewed"]}
              for r in rows if is_public(r)]
    p["public"].parent.mkdir(parents=True, exist_ok=True)
    with p["public"].open("w", encoding="utf-8") as fh:
        for row in public:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    quality = build_quality(PROJECT_ROOT, config, rows)
    quality["golden_version"] = golden_version(p["public"])
    p["quality"].write_text(json.dumps(quality, indent=2, default=str), encoding="utf-8")
    print(f"Exported {len(public)} of {len(rows)} Golden Dataset rows (public fields only, version {quality['golden_version']}) "
          f"-> {p['public'].relative_to(PROJECT_ROOT)}")
    print(f"Quality metrics -> {p['quality'].relative_to(PROJECT_ROOT)} (raw {quality['raw_total']:,}, clean {quality['clean_total']:,})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
