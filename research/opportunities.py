"""Evidence-backed product opportunities.

Definitions live in ``research/opportunities.yaml`` (human-authored hypotheses).
This module counts the Golden Dataset records that match each one and ranks
them with a transparent formula. An opportunity with fewer than
``min_records`` matching records is not shown as an opportunity.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from research.analysis import LAPSE_BEHAVIORS

DEFINITIONS_PATH = Path(__file__).with_name("opportunities.yaml")
PRIORITY_FORMULA = (
    "priority = matching records × (1 + share of matching records that report a pause, reduction or stop) "
    "× (number of source platforms ÷ 2, capped at 1)"
)


def load_definitions(path: Path = DEFINITIONS_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def matches(row: dict[str, Any], definition: dict[str, Any]) -> bool:
    hit = any(row.get(field) in set(values) for field, values in (definition.get("match") or {}).items())
    restrict = definition.get("restrict_behavior")
    return hit and (not restrict or row.get("behavior") in set(restrict))


def evidence_strength(n: int, platforms: int, exact_quotes: int, reviewed: int) -> tuple[str, str]:
    """(label, reason). Rules are fixed and shown to users."""
    if n >= 30 and platforms >= 2 and exact_quotes >= 10:
        level = "Strong"
    elif n >= 10 and exact_quotes >= 3:
        level = "Moderate"
    else:
        level = "Limited"
    reason = f"{n} records, {platforms} source platform(s), {exact_quotes} exact quotes"
    if reviewed < n:
        level = f"{level} (unverified)"
        reason += f"; {n - reviewed} of {n} not individually human-reviewed"
    else:
        reason += f"; {reviewed} of {n} human-reviewed"
    return level, reason


def build(rows: list[dict[str, Any]], definitions: dict[str, Any] | None = None) -> dict[str, Any]:
    definitions = definitions or load_definitions()
    total = len(rows)
    shown, insufficient = [], []
    for d in definitions["opportunities"]:
        matched = [r for r in rows if matches(r, d)]
        n = len(matched)
        platforms = len({r.get("source") for r in matched})
        lapse_share = sum(r.get("behavior") in LAPSE_BEHAVIORS for r in matched) / n if n else 0.0
        exact = sum(r.get("quote_status") == "exact" and bool(r.get("evidence_quote")) for r in matched)
        reviewed = sum(bool(r.get("individually_reviewed")) for r in matched)
        strength, strength_reason = evidence_strength(n, platforms, exact, reviewed)
        segments = Counter(r.get("tenure") for r in matched if r.get("tenure") not in (None, "unclear"))
        item = {
            **{k: d[k] for k in ("id", "title", "problem", "business_metric", "intervention", "experiment")},
            "match": d.get("match"), "restrict_behavior": d.get("restrict_behavior"),
            "records": matched, "n": n, "share": n / total if total else 0.0, "total": total,
            "platforms": platforms, "sources": dict(Counter(r.get("source") for r in matched)),
            "lapse_share": lapse_share, "exact_quotes": exact, "reviewed": reviewed,
            "strength": strength, "strength_reason": strength_reason,
            "segment": dict(segments.most_common()) or None,
            "priority": round(n * (1 + lapse_share) * min(platforms / 2, 1.0), 1),
            "validation_gaps": validation_gaps(n, platforms, reviewed, segments),
        }
        (shown if n >= definitions["min_records"] else insufficient).append(item)
    shown.sort(key=lambda o: (-o["priority"], o["id"]))
    return {"opportunities": shown, "insufficient": insufficient, "min_records": definitions["min_records"],
            "formula": PRIORITY_FORMULA, "total": total}


def validation_gaps(n: int, platforms: int, reviewed: int, segments: Counter[str]) -> list[str]:
    gaps = []
    if reviewed < n:
        gaps.append("Tags not individually verified by a human reviewer.")
    if platforms < 2:
        gaps.append("Evidence comes from a single source platform.")
    if not segments:
        gaps.append("Investor segment (tenure) unknown for all matching records.")
    gaps.append("Frequency in public posts does not measure how many customers are affected; validate with product analytics.")
    gaps.append("Proposed intervention and experiment are qualitative judgements, not tested.")
    return gaps
