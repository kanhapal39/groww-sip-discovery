"""Evidence-backed product opportunities.

Definitions live in ``research/opportunities.yaml`` (human-authored hypotheses).
This module counts the Golden Dataset records that match each one and ranks
them with a transparent formula. An opportunity with fewer than
``min_records`` matching records is not shown as an opportunity.

Duplicate records (same ID or same text) are counted once. Records matching an
opportunity's ``hold_out`` rule are not counted: they are listed separately as
needing review, because their tags point to a different problem.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from research.analysis import LAPSE_BEHAVIORS, dedupe

DEFINITIONS_PATH = Path(__file__).with_name("opportunities.yaml")
PRIORITY_FORMULA = (
    "priority = matching records × (1 + share of matching records that report a pause, reduction or stop) "
    "× (number of source platforms ÷ 2, capped at 1). It ranks the volume of evidence in this sample, "
    "not business impact or effect on SIP continuation."
)
# Shown next to the figures, so every percentage states its numerator and denominator.
METRIC_DEFINITIONS = {
    "n": "Matching records: unique public Golden Dataset records matching the rule, minus held-out records.",
    "share": "Share of Golden Dataset: matching records ÷ all unique public Golden Dataset records.",
    "lapse_share": "Report a lapse: matching records whose behaviour tag is pause, reduce or stop ÷ matching records.",
    "scope": "These are statistics about a reviewed sample of public posts and reviews, balanced across behaviours; "
             "they do not estimate how many investors are affected.",
}


def load_definitions(path: Path = DEFINITIONS_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def matches(row: dict[str, Any], definition: dict[str, Any]) -> bool:
    hit = any(row.get(field) in set(values) for field, values in (definition.get("match") or {}).items())
    restrict = definition.get("restrict_behavior")
    return hit and (not restrict or row.get("behavior") in set(restrict))


def held_out(row: dict[str, Any], definition: dict[str, Any]) -> bool:
    """True if the row's tags match the opportunity's ``hold_out`` rule (any field has any listed value)."""
    return any(row.get(field) in set(values) for field, values in (definition.get("hold_out") or {}).items())


def breakdown(rows: list[dict[str, Any]], groups: list[dict[str, str]] | None) -> list[tuple[str, int]] | None:
    """Count records by the first keyword group their text matches; the rest are "none of these".

    Keyword rules on the record text, not a verified classification; shown so readers can see what the
    evidence actually asks for.
    """
    if not groups:
        return None
    counts = Counter()
    for r in rows:
        text = (r.get("text") or "").lower()
        counts[next((g["label"] for g in groups if re.search(g["pattern"], text)), "none of these")] += 1
    return [(g["label"], counts[g["label"]]) for g in groups] + [("none of these", counts["none of these"])]


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
    rows, duplicates = dedupe(rows)
    total = len(rows)
    shown, insufficient = [], []
    for d in definitions["opportunities"]:
        candidates = [r for r in rows if matches(r, d)]
        matched = [r for r in candidates if not held_out(r, d)]
        n = len(matched)
        platforms = len({r.get("source") for r in matched})
        lapse_share = sum(r.get("behavior") in LAPSE_BEHAVIORS for r in matched) / n if n else 0.0
        exact = sum(r.get("quote_status") == "exact" and bool(r.get("evidence_quote")) for r in matched)
        reviewed = sum(bool(r.get("individually_reviewed")) for r in matched)
        strength, strength_reason = evidence_strength(n, platforms, exact, reviewed)
        segments = Counter(r.get("tenure") for r in matched if r.get("tenure") not in (None, "unclear"))
        item = {
            **{k: d[k] for k in ("id", "title", "problem", "business_metric", "intervention", "experiment")},
            "match": d.get("match"), "restrict_behavior": d.get("restrict_behavior"), "hold_out": d.get("hold_out"),
            "held_out": [r for r in candidates if held_out(r, d)],
            "breakdown": breakdown(matched, d.get("breakdown")),
            "implied": sum(bool(r.get("is_hypothesis")) for r in matched),
            "records": matched, "n": n, "share": n / total if total else 0.0, "total": total,
            "platforms": platforms, "sources": dict(Counter(r.get("source") for r in matched)),
            "lapse_share": lapse_share, "exact_quotes": exact, "reviewed": reviewed,
            "strength": strength, "strength_reason": strength_reason,
            "segment": dict(segments.most_common()) or None,
            "priority": round(n * (1 + lapse_share) * min(platforms / 2, 1.0), 1),
            "validation_gaps": validation_gaps(n, platforms, reviewed, segments),
        }
        if item["held_out"]:
            item["validation_gaps"].insert(0, f"{len(item['held_out'])} record(s) matched the rule but were held out for review "
                                              "because their tags point to a different problem.")
        if item["breakdown"]:
            item["validation_gaps"].insert(0, "Complaints about cancelling show cancellation friction, not demand for pausing "
                                              "or editing; see the keyword breakdown.")
        (shown if n >= definitions["min_records"] else insufficient).append(item)
    shown.sort(key=lambda o: (-o["priority"], o["id"]))
    return {"opportunities": shown, "insufficient": insufficient, "min_records": definitions["min_records"],
            "formula": PRIORITY_FORMULA, "definitions": METRIC_DEFINITIONS, "total": total, "duplicates_removed": duplicates}


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
