"""Data Quality & Validation: how the dataset was produced and how reliable it is."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import data, ui

def render() -> None:
    st.title("Data Quality & Validation")
    q = data.quality()
    if not q:
        ui.empty_dataset()
        return
    st.caption(f"Metrics built {q['built_at'][:16].replace('T', ' ')} UTC from the pipeline's own files (`python -m research.build`).")

    clean, golden, tagging, flt = q["clean"], q["golden"], q["tagging"], q["filter"]
    dropped = clean["dropped"]
    duplicates = dropped.get("exact_duplicate", 0) + dropped.get("near_duplicate", 0) + dropped.get("recollected", 0)
    runs = q["collection_runs"]
    collection_failures = sum(1 for r in runs if r.get("status") not in (None, "SUCCEEDED"))
    validation_failures = tagging["failed"] + tagging["quote_status"].get("hidden", 0) + tagging["reason_flags"] + flt["errors"]
    missing_meta = sum(s.get("missing_provenance", 0) for s in q["raw"].values()) + golden["missing_provenance"]
    review = golden.get("review_statuses", {})

    st.subheader("Pipeline funnel")
    c = st.columns(4)
    c[0].metric("Raw records collected", f"{q['raw_total']:,}")
    c[1].metric("Cleaned records", f"{q['clean_total']:,}")
    c[2].metric("Duplicates detected", f"{duplicates:,}", help=f"exact {dropped.get('exact_duplicate', 0):,}, near {dropped.get('near_duplicate', 0):,}, re-collected {dropped.get('recollected', 0):,}")
    c[3].metric("Too short (excluded)", f"{dropped.get('short_text', 0):,}", help="Under 6 words with no SIP keyword")
    c = st.columns(4)
    c[0].metric("Irrelevant (excluded by filter)", f"{flt['labels'].get('no', 0):,}", help=f"of {flt['labelled']:,} records the AI filter has labelled so far")
    c[1].metric("Accepted into Golden Dataset", golden["records"], help=f"{golden['individually_reviewed']} individually reviewed, {golden['bulk_approved']} bulk-approved")
    c[2].metric("Awaiting review", review.get("pending", 0), help="Pending rows in the review workbook")
    c[3].metric("Rejected", review.get("rejected", 0) + review.get("needs_revision", 0), help="Rejected or needs revision")
    c = st.columns(4)
    c[0].metric("Validated evidence excerpts", golden["exact_quotes"], help="Golden records whose quote is an exact substring of the source text")
    c[1].metric("Missing source metadata", missing_meta, help="Raw or Golden records without record ID, source URL or collection time")
    c[2].metric("Collection failures (logged)", collection_failures, help=q["unlogged"])
    c[3].metric("Validation failures", validation_failures,
                help=f"tagging failed {tagging['failed']}, hidden quotes {tagging['quote_status'].get('hidden', 0)}, unsupported reasons {tagging['reason_flags']}, filter errors {flt['errors']}")
    if golden["bulk_approved"]:
        st.warning(f"{golden['bulk_approved']} of {golden['records']} Golden Dataset records were bulk-approved without row-by-row human review. "
                   "Their tags are AI output and should not be treated as verified ground truth.", icon=":material/rule:")

    st.subheader("Sources")
    table = []
    for s in q["sources"]:
        table.append({
            "Source": s["name"], "Status": s["status"], "Method": s.get("method", s.get("note", "")),
            "Raw": s.get("raw_records"), "Clean": s.get("clean_records"),
            "Published from": s.get("date_first"), "Published to": s.get("date_last"), "Undated": s.get("undated"),
            "Last collected": str(s.get("last_collected") or "")[:16].replace("T", " "),
            "AI-processed": ("Yes" if s.get("ai_processing") else "No") if s.get("integrated") else "",
        })
    st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
    st.caption("A source is listed as tested only when a raw file from a successful collection run exists.")

    src = [(k, v["records"], v["records"] / max(q["clean_total"], 1)) for k, v in clean["per_source"].items()]
    ui.bar(sorted(src, key=lambda x: -x[1]), q["clean_total"], "Clean records by source", "records after deduplication and the short-text rule", key="dq_src")
    gsrc = [(ui.SOURCE_LABELS.get(k, k), v, v / max(golden["records"], 1)) for k, v in golden["by_source"].items()]
    ui.bar(sorted(gsrc, key=lambda x: -x[1]), golden["records"], "Golden Dataset by source", "approved Golden Dataset records", key="dq_gsrc")

    st.subheader("How to read this dataset")
    ctx = q.get("context", {})
    ag = ctx.get("agreement")
    ag_text = (f"In a {ag['items']}-item check, {' and '.join(ag['models'])} agreed "
               + ", ".join(f"{v:.0f}% on {k.replace('_', ' ')}" for k, v in (ag.get("core") or {}).items())
               + ("." if ag.get("passed") else " (below the 70% bar on at least one field).")) if ag else "No inter-model check has been run."
    integrated = ", ".join(s["name"] for s in q["sources"] if s.get("operational"))
    missing = ", ".join(s["name"] for s in q["sources"] if not s.get("integrated"))
    threads = ctx.get("reddit_threads")
    st.markdown(f"""
- **Integrated sources:** {integrated} have tested connectors. Not integrated: {missing}.
- **Collection restrictions:** Google Play is read with an unofficial library and Reddit through a third-party scraper (Apify); the project owner accepted both terms-of-service risks. YouTube comments use the official API, may be kept for at most {ctx.get('youtube_retention_days')} days, and are not sent to AI models or included in the Golden Dataset.
- **Sampling:** Play Store collection took the newest {ctx.get('play_max_per_app', 0):,} reviews for each of {ctx.get('play_apps')} apps, so older periods are covered unevenly. Reddit posts came from keyword searches in {ctx.get('reddit_subreddits')} subreddits{f" and comments from {threads} threads chosen by title" if threads else ""}, so they over-represent stop/pause/autopay discussions by design.
- **Selection bias:** public reviews and posts over-represent people with problems; nothing here measures how common a behaviour is among all investors.
- **Golden Dataset:** {golden['records']} rows sampled across source × behaviour for review. It is not a random sample, so its distributions are not prevalence estimates.
- **Classification:** tags come from LLMs against a draft codebook. {ag_text} Segment fields (income, age, money source, influencer) are almost always unclear in public posts; segments will be estimated from proxies and validated through interviews.
- **Small samples:** any chart computed on fewer than {ctx.get('small_sample', 30)} records is labelled "small sample".
""")

    st.subheader("Administrator")
    if not data.is_admin():
        if not data.admin_configured():
            st.caption("Administrator access is disabled: set ADMIN_PASSWORD in the server's .env.")
            return
        with st.form("admin"):
            pw = st.text_input("Administrator password", type="password")
            if st.form_submit_button("Sign in") and not data.admin_login(pw):
                st.error("Incorrect password.")
        if not data.is_admin():
            return
        st.rerun()
    st.success("Signed in as administrator.", icon=":material/admin_panel_settings:")
    if st.button("Sign out"):
        st.session_state["is_admin"] = False
        st.rerun()
    st.markdown("**Tagging failures**")
    st.dataframe(pd.DataFrame(tagging["failures"] or [{"record_id": "none"}]), hide_index=True, use_container_width=True)
    st.markdown("**Evidence quotes repaired or hidden by the quote check**")
    st.dataframe(pd.DataFrame(tagging["quote_problems"] or [{"record_id": "none"}]), hide_index=True, use_container_width=True)
    st.markdown("**Collection runs (Reddit ledger)**")
    st.dataframe(pd.DataFrame(runs or [{"source": "none"}]), hide_index=True, use_container_width=True)
    st.caption("Processing logs stay on the machine that runs the pipeline; they are not published with the dashboard.")
