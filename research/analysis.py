"""Descriptive analysis of Golden Dataset records.

Every function returns counts with the sample size they were computed on, so
the dashboard can always print "n = …" and a metric definition next to a chart.
Nothing here estimates prevalence in the investor population: the Golden
Dataset is a behaviour-balanced review sample, not a random sample.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Callable, Iterable

EMPTY_VALUES = frozenset({None, "", "unclear", "none", "no_lapse"})
LAPSE_BEHAVIORS = ("pause_sip", "reduce_sip", "stop_sip")

# Derived field: where in the SIP journey the record sits. Definition shown in the UI.
JOURNEY_STAGES = {
    "start_sip": "Starting",
    "continue_sip": "Continuing",
    "increase_sip": "Continuing",
    "pause_sip": "Lapsing",
    "reduce_sip": "Lapsing",
    "stop_sip": "Lapsing",
}
JOURNEY_DEFINITION = (
    "Journey stage is derived from the behaviour tag: Starting = start_sip; Continuing = continue_sip or increase_sip; "
    "Lapsing = pause_sip, reduce_sip or stop_sip. Records with other or unclear behaviour are excluded."
)


def label(value: Any) -> str:
    return str(value).replace("_", " ").capitalize() if value is not None else "Unknown"


def journey_stage(row: dict[str, Any]) -> str | None:
    return JOURNEY_STAGES.get(row.get("behavior"))


def distribution(rows: Iterable[dict[str, Any]], field: str | Callable[[dict[str, Any]], Any], drop_empty: bool = True) -> dict[str, Any]:
    """{"n": rows considered, "counts": [(value, count, share of n)]} sorted by count."""
    rows = list(rows)
    get = field if callable(field) else (lambda r: r.get(field))
    values = [get(r) for r in rows]
    counted = Counter(v for v in values if not (drop_empty and v in EMPTY_VALUES))
    n = len(rows)
    return {
        "n": n,
        "n_tagged": sum(counted.values()),
        "counts": [(v, c, c / n if n else 0.0) for v, c in counted.most_common()],
    }


def filter_rows(rows: Iterable[dict[str, Any]], sources: Iterable[str] | None = None, years: tuple[int, int] | None = None,
                include_undated: bool = True, field_values: dict[str, Iterable[str]] | None = None) -> list[dict[str, Any]]:
    sources = set(sources) if sources else None
    out = []
    for r in rows:
        if sources and r.get("source") not in sources:
            continue
        if years:
            y = r.get("year")
            if y is None and not include_undated:
                continue
            if y is not None and not years[0] <= y <= years[1]:
                continue
        if field_values and any(vals and r.get(f) not in set(vals) for f, vals in field_values.items()):
            continue
        out.append(r)
    return out


def crosstab(rows: Iterable[dict[str, Any]], row_field: str, col_field: str) -> list[tuple[str, str, int]]:
    counts = Counter((r.get(row_field), r.get(col_field)) for r in rows
                     if r.get(row_field) not in EMPTY_VALUES and r.get(col_field) not in EMPTY_VALUES)
    return [(a, b, c) for (a, b), c in counts.most_common()]


def by_year(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    years = Counter(r["year"] for r in rows if r.get("year"))
    return {"n": len(rows), "undated": sum(1 for r in rows if not r.get("year")), "counts": sorted(years.items())}


def emerging(rows: Iterable[dict[str, Any]], field: str, recent_from: int, min_window: int = 20, min_count: int = 3) -> dict[str, Any]:
    """Values whose share rose in records from ``recent_from`` onward vs earlier records.

    Returns no themes when either window has fewer than ``min_window`` records,
    so a change in a handful of records is never shown as a trend.
    """
    rows = [r for r in rows if r.get("year")]
    recent = [r for r in rows if r["year"] >= recent_from]
    earlier = [r for r in rows if r["year"] < recent_from]
    result = {"recent_n": len(recent), "earlier_n": len(earlier), "recent_from": recent_from, "themes": []}
    if len(recent) < min_window or len(earlier) < min_window:
        return result
    rc = Counter(r.get(field) for r in recent if r.get(field) not in EMPTY_VALUES)
    ec = Counter(r.get(field) for r in earlier if r.get(field) not in EMPTY_VALUES)
    for value, count in rc.items():
        if count < min_count:
            continue
        share_recent, share_earlier = count / len(recent), ec.get(value, 0) / len(earlier)
        if share_recent > share_earlier:
            result["themes"].append({"value": value, "recent": count, "earlier": ec.get(value, 0),
                                     "share_recent": share_recent, "share_earlier": share_earlier,
                                     "change_pts": 100 * (share_recent - share_earlier)})
    result["themes"].sort(key=lambda t: -t["change_pts"])
    return result


def stated_vs_inferred(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    """is_hypothesis = False means the model said every tag was stated in the text."""
    rows = list(rows)
    return {"stated": sum(r.get("is_hypothesis") is False for r in rows),
            "inferred": sum(r.get("is_hypothesis") is True for r in rows),
            "unknown": sum(r.get("is_hypothesis") is None for r in rows)}


def representative(rows: Iterable[dict[str, Any]], k: int = 5) -> list[dict[str, Any]]:
    """Up to k records with an exact quote, highest confidence first, at most 2 per platform."""
    picked: list[dict[str, Any]] = []
    per_platform: Counter[str] = Counter()
    for r in sorted(rows, key=lambda r: (-(r.get("confidence") or 0), r.get("record_id"))):
        if r.get("quote_status") != "exact" or not r.get("evidence_quote"):
            continue
        if per_platform[r.get("platform_detail")] >= 2:
            continue
        picked.append(r)
        per_platform[r.get("platform_detail")] += 1
        if len(picked) == k:
            break
    return picked


def recent_year_default() -> int:
    return date.today().year
