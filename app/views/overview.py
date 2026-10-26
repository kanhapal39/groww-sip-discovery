"""Overview: ask a research question, then see what the evidence covers."""

from __future__ import annotations

import html

import streamlit as st

from app import data, ui
from research import analysis

SUGGESTED = (
    "Why do investors pause or stop their SIPs?",
    "Why do AutoPay payments fail?",
    "What do investors say about returns in the first year?",
    "How do investors react to a market crash?",
    "What problems do investors face when starting a SIP?",
)


def _ask(question: str) -> None:
    st.session_state["question"] = question
    st.session_state["submitted"] = question


def render() -> None:
    st.markdown(
        "<div class='hero'><h1>Understand Why Investors Start, Continue, and Stop Their SIPs</h1>"
        "<p>Explore real public discussions, discover investor behaviour, and identify evidence-backed product opportunities.</p></div>",
        unsafe_allow_html=True,
    )
    if not data.ready():
        ui.empty_dataset()
        return
    rows = data.rows()

    _, mid, _ = st.columns([1, 6, 1])
    with mid:
        with st.form("ask", clear_on_submit=False, border=True):
            question = st.text_input("Ask your question", key="question",
                                     placeholder="Ask anything about SIP investor behaviour, expectations, or pain points...")
            if st.form_submit_button("Ask the research assistant", type="primary", use_container_width=True) and question.strip():
                st.session_state["submitted"] = question.strip()
        st.markdown("<div class='muted' style='margin:0.6rem 0 0.3rem'>Suggested questions</div>", unsafe_allow_html=True)
        cols = st.columns(len(SUGGESTED))
        for col, q in zip(cols, SUGGESTED):
            col.button(q, key=f"suggest_{q}", on_click=_ask, args=(q,), use_container_width=True)

        submitted = st.session_state.get("submitted")
        if submitted:
            with st.spinner("Searching the Golden Dataset and drafting a grounded answer…"):
                result = data.answer(submitted, data.golden_version())
            render_answer(result)

    st.divider()
    render_summary(rows)


def render_answer(result: dict) -> None:
    st.subheader(result["question"])
    status = result["status"]
    if status == "insufficient":
        st.warning(f"**{result['message']}** {result.get('detail', '')}", icon=":material/search_off:")
        if result.get("gaps"):
            st.caption(f"What the matching records cannot tell us: {result['gaps']}")
    elif status in ("error", "no_model"):
        st.error(result["message"], icon=":material/error:")
    else:
        if result.get("summary"):
            st.markdown(result["summary"])
        for p in result["points"]:
            refs = ", ".join(f"R{i}" for i in p["records"])
            css = "basis-stated" if p["basis"] == "stated" else "basis-inferred"
            badge = "Stated in evidence" if p["basis"] == "stated" else "Possible explanation (inferred)"
            st.markdown(f"- <span class='{css}'>{html.escape(p['text'])}</span> <span class='tag'>{badge}</span> <span class='muted'>{refs}</span>",
                        unsafe_allow_html=True)
        if result.get("gaps"):
            st.caption(f"Gaps: {result['gaps']}")

    cov = result["coverage"]
    if cov["records"]:
        years = f"{cov['years'][0]}–{cov['years'][1]}" if cov["years"] else "dates unknown"
        sources = ", ".join(f"{ui.SOURCE_LABELS.get(k, k)} {v}" for k, v in cov["sources"].items())
        st.markdown(f"**Evidence coverage:** {cov['records']} records · {sources} · published {years}")
    with st.expander("Limitations", expanded=status == "answered"):
        for note in result["limitations"]:
            st.markdown(f"- {note}")
        meta = f"Dataset version {result.get('dataset_version')} · prompt {result.get('prompt_version')}"
        if result.get("model"):
            meta += f" · model {result['model']}"
        if result.get("tokens"):
            meta += f" · {result['tokens']:,} tokens"
        st.caption(meta)
    if result["evidence"]:
        st.markdown("**Source evidence**")
        for i, row in enumerate(result["evidence"], 1):
            ui.record_card(row, index=i, full_text=False)


def render_summary(rows: list[dict]) -> None:
    st.subheader("What the evidence covers")
    q = data.quality() or {}
    golden = q.get("golden", {})
    years = sorted({r["year"] for r in rows if r.get("year")})
    period_options = ["All time"] + [str(y) for y in reversed(years)]
    period = st.segmented_control("Period (by publication date)", period_options, default="All time", key="period")
    in_period = rows if period in (None, "All time") else [r for r in rows if str(r.get("year")) == period]

    c = st.columns(5 if data.is_admin() else 4)
    c[0].metric("Golden Dataset records", len(rows), help="Approved, public Golden Dataset records.")
    c[1].metric("Source platforms", len({r.get("source") for r in rows}),
                help=", ".join(ui.SOURCE_LABELS.get(s, s) for s in sorted({r.get("source") for r in rows})))
    c[2].metric(f"Published in {period or 'all time'}", len(in_period),
                help=f"{sum(1 for r in rows if not r.get('year'))} records have no publication date.")
    c[3].metric("Individually validated", golden.get("individually_reviewed", 0),
                help=f"{golden.get('bulk_approved', 0)} records were bulk-approved without row-by-row human review.")
    if data.is_admin():
        c[4].metric("Awaiting review", golden.get("review_statuses", {}).get("pending", 0), help="Pending rows in the review workbook.")
    if golden.get("bulk_approved"):
        st.caption(f"{golden['bulk_approved']} of {golden['records']} Golden Dataset records were bulk-approved by the project owner without row-by-row review; their tags are AI output.")

    left, right = st.columns(2)
    with left:
        d = analysis.distribution(in_period, "in_app_pain")
        ui.bar(d["counts"], d["n"], "Most frequently observed investor problems",
               "count of records by in-app pain tag; none/unclear excluded", top=6, key="ov_pain")
    with right:
        st.markdown("**Emerging discussion themes**")
        recent = data.config()["research"]["recent_from_year"]
        e = analysis.emerging(rows, "trigger", recent)
        if not e["themes"]:
            ui.insufficient(f"needs at least 20 dated records both before and from {recent} "
                            f"(have {e['earlier_n']} before, {e['recent_n']} from {recent}).")
        else:
            for t in e["themes"][:5]:
                st.markdown(f"- **{ui.nice(t['value'])}**: {ui.pct(t['share_recent'])} of records from {recent} "
                            f"({t['recent']} of {e['recent_n']}) vs {ui.pct(t['share_earlier'])} before ({t['earlier']} of {e['earlier_n']})")
        ui.chart_caption(e["recent_n"] + e["earlier_n"], f"trigger tags whose share rose in records published from {recent}, compared with earlier records; all periods")

    st.markdown("**Highest-priority evidence-backed opportunities**")
    opps = data.opportunities()["opportunities"][:3]
    if not opps:
        ui.insufficient("no opportunity has enough matching records yet.")
    cols = st.columns(max(len(opps), 1))
    for col, o in zip(cols, opps):
        with col.container(border=True):
            st.markdown(f"**{o['title']}**")
            st.markdown(f"{o['n']} records ({ui.pct(o['share'])} of the Golden Dataset) · {o['strength']}")
            st.caption(f"Sources: {', '.join(f'{ui.SOURCE_LABELS.get(k, k)} {v}' for k, v in o['sources'].items())}")
    pages = st.session_state.get("_pages", {})
    if "Product Opportunities" in pages:
        st.page_link(pages["Product Opportunities"], label="See all opportunities and their evidence", icon=":material/arrow_forward:")
