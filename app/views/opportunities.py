"""Product Opportunities: ranked, evidence-backed, with supporting records."""

from __future__ import annotations

import streamlit as st

from app import data, ui

PAGE_SIZE = 10


def render() -> None:
    st.title("Product Opportunities")
    if not data.ready():
        ui.empty_dataset()
        return
    result = data.opportunities()
    st.markdown(
        "Each opportunity is a **written hypothesis** that is only shown when enough Golden Dataset records match its rules. "
        "Counts, shares, sources and quotes are **computed from the evidence**; the business metric, intervention and experiment "
        "are **qualitative judgements** that have not been tested."
    )
    with st.expander("How opportunities are ranked", expanded=False):
        st.markdown(f"`{result['formula']}`")
        st.markdown(f"An opportunity needs at least **{result['min_records']}** matching records to be listed. "
                    "Evidence strength: Strong = ≥30 records, ≥2 platforms, ≥10 exact quotes; Moderate = ≥10 records and ≥3 exact quotes; "
                    "otherwise Limited. \"(unverified)\" means some matching records were not individually reviewed by a human.")
    if not result["opportunities"]:
        ui.insufficient("no opportunity has enough matching records yet.")
    for rank, o in enumerate(result["opportunities"], 1):
        with st.container(border=True):
            head, score = st.columns([5, 1])
            head.markdown(f"### {rank}. {o['title']}")
            score.metric("Priority", o["priority"])
            c = st.columns(4)
            c[0].metric("Relevant records", o["n"])
            c[1].metric("Share of Golden Dataset", ui.pct(o["share"]), help=f"{o['n']} of {o['total']} records")
            c[2].metric("Report a lapse", ui.pct(o["lapse_share"]), help="Share of matching records tagged pause, reduce or stop")
            c[3].metric("Evidence strength", o["strength"].split(" (")[0], help=o["strength_reason"])
            st.markdown(f"**Problem (evidence-based):** {o['problem']}")
            st.markdown(f"**Sources:** " + ", ".join(f"{ui.SOURCE_LABELS.get(k, k)} {v}" for k, v in o["sources"].items())
                        + f" · {o['exact_quotes']} verbatim quotes · {o['strength_reason']}")
            seg = ", ".join(f"{ui.nice(k)} {v}" for k, v in (o["segment"] or {}).items()) or "unknown for all matching records"
            st.markdown(f"**Investor segment (tenure, where stated):** {seg}")
            st.markdown("**Qualitative judgements (not evidence):**")
            st.markdown(f"- Potential business metric: {o['business_metric']}\n- Proposed intervention: {o['intervention']}\n- Suggested experiment: {o['experiment']}")
            st.markdown("**Validation gaps:**\n" + "\n".join(f"- {g}" for g in o["validation_gaps"]))
            rules = "; ".join(f"{f} ∈ {{{', '.join(v)}}}" for f, v in (o["match"] or {}).items())
            if o.get("restrict_behavior"):
                rules += f"; and behaviour ∈ {{{', '.join(o['restrict_behavior'])}}}"
            st.caption(f"Matching rule: any of {rules}")
            with st.expander(f"Inspect the {o['n']} supporting records"):
                pages = max(1, -(-o["n"] // PAGE_SIZE))
                page = st.number_input("Page", 1, pages, 1, key=f"pg_{o['id']}") if pages > 1 else 1
                for i, r in enumerate(o["records"][(page - 1) * PAGE_SIZE: page * PAGE_SIZE], (page - 1) * PAGE_SIZE + 1):
                    ui.record_card(r, index=i, full_text=False, show_internal=data.is_admin())
    if result["insufficient"]:
        st.markdown("#### Not enough evidence yet")
        for o in result["insufficient"]:
            st.markdown(f"- {o['title']} — {o['n']} matching record(s); needs {result['min_records']}.")
