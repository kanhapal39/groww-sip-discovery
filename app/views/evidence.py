"""Evidence Explorer: search and filter approved Golden Dataset records."""

from __future__ import annotations

import streamlit as st

from app import data, ui
from research import analysis
from research.retrieval import search

PAGE_SIZE = 20


def _values(rows: list[dict], field) -> list:
    get = field if callable(field) else (lambda r: r.get(field))
    return sorted({v for v in map(get, rows) if v not in analysis.EMPTY_VALUES}, key=str)


def render() -> None:
    st.title("Evidence Explorer")
    st.caption("Approved Golden Dataset records eligible for publication. Internal review notes are not shown"
               + (" (administrator view: notes shown)." if data.is_admin() else "."))
    if not data.ready():
        ui.empty_dataset()
        return
    rows = data.rows()
    query = st.text_input("Search by keyword", placeholder="e.g. mandate failed, XIRR, pause, first SIP", key="ev_q")

    c = st.columns(4)
    sources = c[0].multiselect("Source", _values(rows, "source"), format_func=lambda s: ui.SOURCE_LABELS.get(s, s), key="ev_src")
    topic = c[1].multiselect("Topic (trigger)", _values(rows, "trigger"), format_func=ui.nice, key="ev_topic")
    behavior = c[2].multiselect("Investor behaviour", _values(rows, "behavior"), format_func=ui.nice, key="ev_beh")
    expectation = c[3].multiselect("Expectation", _values(rows, "expectation"), format_func=ui.nice, key="ev_exp")
    c = st.columns(4)
    pain = c[0].multiselect("Pain point", _values(rows, "in_app_pain"), format_func=ui.nice, key="ev_pain")
    stages = c[1].multiselect("Journey stage", _values(rows, analysis.journey_stage), key="ev_stage")
    years = sorted({r["year"] for r in rows if r.get("year")})
    year_range = c[2].slider("Publication year", years[0], years[-1], (years[0], years[-1]), key="ev_years") if len(years) >= 2 else None
    validation = c[3].selectbox("Validation status", ["All", "Individually reviewed", "Bulk-approved (not individually reviewed)"], key="ev_val")

    filtered = analysis.filter_rows(rows, sources or None, year_range, True,
                                    {"trigger": topic, "behavior": behavior, "expectation": expectation, "in_app_pain": pain})
    if stages:
        filtered = [r for r in filtered if analysis.journey_stage(r) in stages]
    if validation == "Individually reviewed":
        filtered = [r for r in filtered if r.get("individually_reviewed")]
    elif validation.startswith("Bulk"):
        filtered = [r for r in filtered if not r.get("individually_reviewed")]

    if query.strip():
        ranked = search(data.paths()["db"], query, limit=len(rows))
        keep = {r["record_id"] for r in filtered}
        order = [r for r in ranked if r["record_id"] in keep and (r.get("term_coverage", 0) > 0 or r["matched_tags"])]
        by_id = {r["record_id"]: r for r in filtered}
        filtered = [by_id[r["record_id"]] for r in order]
        sort_note = "ranked by match to your search"
    else:
        filtered = sorted(filtered, key=lambda r: str(r.get("published_at") or ""), reverse=True)
        sort_note = "newest first"

    total = len(filtered)
    if not total:
        ui.insufficient("no records match this search and these filters.")
        return
    pages = max(1, -(-total // PAGE_SIZE))
    left, right = st.columns([3, 1])
    left.markdown(f"**{total}** of {len(rows)} records · {sort_note}")
    page = right.number_input("Page", 1, pages, 1, key="ev_page") if pages > 1 else 1
    start = (page - 1) * PAGE_SIZE
    for i, r in enumerate(filtered[start:start + PAGE_SIZE], start + 1):
        ui.record_card(r, index=i, show_internal=data.is_admin())
    st.caption(f"Showing {start + 1}–{min(start + PAGE_SIZE, total)} of {total}.")
