"""Investor Behaviour: behaviour, expectations and SIP discontinuation in one page."""

from __future__ import annotations

import streamlit as st

from app import data, ui
from research import analysis

DEFINITION_SHARE = "count of records by tag; unclear excluded from bars; shares are of n"


def filters(rows: list[dict]) -> list[dict]:
    sources = sorted({r.get("source") for r in rows})
    years = sorted({r["year"] for r in rows if r.get("year")})
    triggers = sorted({r.get("trigger") for r in rows if r.get("trigger") not in analysis.EMPTY_VALUES})
    c1, c2, c3 = st.columns([2, 3, 3])
    chosen_sources = c1.multiselect("Source", sources, default=sources, format_func=lambda s: ui.SOURCE_LABELS.get(s, s), key="bh_sources")
    year_range = None
    if len(years) >= 2:
        year_range = c2.slider("Publication year", years[0], years[-1], (years[0], years[-1]), key="bh_years")
    chosen_themes = c3.multiselect("Theme (trigger)", triggers, format_func=ui.nice, key="bh_themes", placeholder="All themes")
    include_undated = st.checkbox("Include records without a publication date", value=True, key="bh_undated")
    return analysis.filter_rows(rows, chosen_sources, year_range, include_undated, {"trigger": chosen_themes} if chosen_themes else None)


def excerpts(rows: list[dict], heading: str) -> None:
    st.markdown(f"**{heading}**")
    picked = analysis.representative(rows)
    if not picked:
        ui.insufficient("no record in this selection has a verbatim evidence quote.")
        return
    st.caption("Highest-confidence records with a verbatim quote, at most two per platform.")
    for r in picked:
        ui.record_card(r, full_text=False)


def section_behaviour(rows: list[dict]) -> None:
    left, right = st.columns(2)
    with left:
        d = analysis.distribution(rows, "behavior")
        ui.bar(d["counts"], d["n"], "Reported SIP behaviour", DEFINITION_SHARE, key="b_beh")
    with right:
        d = analysis.distribution(rows, analysis.journey_stage)
        ui.bar(d["counts"], d["n"], "Journey stage", analysis.JOURNEY_DEFINITION, key="b_stage")
    ui.heatmap(analysis.crosstab(rows, "behavior", "platform_detail"), len(rows), "Behaviour by source platform",
               "records per behaviour and platform; unclear excluded", "Platform", "Behaviour", key="b_heat")
    left, right = st.columns(2)
    with left:
        d = analysis.distribution(rows, "emotion")
        ui.bar(d["counts"], d["n"], "Emotion expressed", DEFINITION_SHARE + "; emotion is the model's reading of tone", key="b_emo")
    with right:
        d = analysis.distribution(rows, "outside_action")
        ui.bar(d["counts"], d["n"], "Actions outside the app", DEFINITION_SHARE, key="b_out")
    switched = [r for r in rows if r.get("lapse_type") == "platform_switch" or r.get("outside_action") == "switched_platform"]
    st.markdown(f"**Changing investment platforms:** {len(switched)} of {len(rows)} records report moving, or planning to move, to another app.")
    vol = [r for r in rows if r.get("trigger") == "market_or_returns"]
    st.markdown(f"**Reacting to market volatility:** {len(vol)} of {len(rows)} records name market falls or returns as the trigger.")
    t = analysis.by_year(rows)
    ui.line(t["counts"], t["n"], t["undated"], "Records by publication year",
            "records per publication year in the Golden Dataset sample; reflects what was collected and sampled, not discussion volume")
    excerpts(rows, "Representative evidence")


def section_expectations(rows: list[dict]) -> None:
    d = analysis.distribution(rows, "expectation")
    unclear = d["n"] - d["n_tagged"]
    st.caption(f"{unclear} of {d['n']} records state no expectation; app reviews rarely say why someone invested.")
    left, right = st.columns(2)
    with left:
        ui.bar(d["counts"], d["n"], "Stated or implied expectations", DEFINITION_SHARE, key="e_exp")
    with right:
        c = analysis.distribution(rows, "checking")
        ui.bar(c["counts"], c["n"], "What investors check", DEFINITION_SHARE, key="e_chk")
    left, right = st.columns(2)
    with left:
        new = [r for r in rows if r.get("tenure") == "new_under_1y"]
        p = analysis.distribution(new, "in_app_pain")
        ui.bar(p["counts"], p["n"], "First-year investors: problems reported",
               "records with tenure = new/under 1 year, by in-app pain tag", key="e_first")
    with right:
        trust = [r for r in rows if r.get("emotion") == "distrust" or r.get("trigger") == "trust_or_fraud_fear"]
        st.markdown("**Trust in investment platforms**")
        st.markdown(f"{len(trust)} of {len(rows)} records express distrust or fear of fraud.")
        ui.chart_caption(len(rows), "records with emotion = distrust or trigger = trust_or_fraud_fear")
    st.markdown("**Expectations alongside reported experiences**")
    pairs = analysis.crosstab(rows, "expectation", "behavior")
    if not pairs:
        ui.insufficient("too few records state an expectation to compare with behaviour.")
    else:
        ui.heatmap(pairs, len(rows), "Expectation × reported behaviour",
                   "records carrying both tags; co-occurrence only — it does not show that an expectation was unmet", "Behaviour", "Expectation", key="e_gap")
    excerpts([r for r in rows if r.get("expectation") not in analysis.EMPTY_VALUES], "Evidence about expectations")


def section_discontinuation(rows: list[dict]) -> None:
    lapses = [r for r in rows if r.get("behavior") in analysis.LAPSE_BEHAVIORS]
    st.markdown(f"**{len(lapses)} of {len(rows)} records report pausing, reducing or stopping a SIP.**")
    if not lapses:
        ui.insufficient("no lapse records in this selection.")
        return
    left, right = st.columns(2)
    with left:
        d = analysis.distribution(lapses, "behavior")
        ui.bar(d["counts"], d["n"], "Type of discontinuation", "lapse records by behaviour tag", key="d_type")
    with right:
        d = analysis.distribution(lapses, "lapse_type")
        ui.bar(d["counts"], d["n"], "How the lapse happened", "lapse records by lapse_type; involuntary = instalment failed without the investor choosing it", key="d_how")
    d = analysis.distribution(lapses, "trigger")
    ui.bar(d["counts"], d["n"], "Reasons given for discontinuing", "lapse records by trigger tag; unclear excluded", key="d_why")

    st.markdown("**Stated reasons vs possible explanations**")
    stated = [r for r in lapses if r.get("is_hypothesis") is False]
    inferred = [r for r in lapses if r.get("is_hypothesis") is True]
    c1, c2 = st.columns(2)
    with c1:
        s = analysis.distribution(stated, "trigger")
        ui.bar(s["counts"], s["n"], "Explicitly stated", "lapse records where the model marked every tag as stated in the text", key="d_stated")
    with c2:
        i = analysis.distribution(inferred, "trigger")
        ui.bar(i["counts"], i["n"], "Inferred from the evidence", "lapse records where at least one tag is the model's inference", key="d_inferred")
    payment = [r for r in lapses if r.get("trigger") == "mandate_or_payment" or r.get("lapse_type") == "involuntary"]
    money = [r for r in lapses if r.get("trigger") == "money_need_or_income"]
    market = [r for r in lapses if r.get("trigger") == "market_or_returns"]
    service = [r for r in lapses if r.get("trigger") in ("support", "trust_or_fraud_fear", "app_bug_or_ux")]
    goal = [r for r in lapses if r.get("trigger") == "goal_or_life_event"]
    st.markdown(
        f"- Payment or mandate failures: **{len(payment)}**\n- Financial constraints: **{len(money)}**\n"
        f"- Market or returns concerns: **{len(market)}**\n- Trust, service or app problems: **{len(service)}**\n- Goals or life events: **{len(goal)}**"
    )
    ui.chart_caption(len(lapses), "lapse records per theme; a record can appear in more than one theme")
    excerpts(lapses, "Evidence from investors who paused, reduced or stopped")


def render() -> None:
    st.title("Investor Behaviour")
    st.caption("Behaviour, expectations and SIP discontinuation in the Golden Dataset. The sample is balanced across behaviours for review, "
               "so counts show what the evidence contains, not how common each behaviour is among all investors.")
    if not data.ready():
        ui.empty_dataset()
        return
    rows = filters(data.rows())
    if not rows:
        ui.insufficient("no records match these filters.")
        return
    tab_a, tab_b, tab_c = st.tabs(["Investor Behaviour", "Investor Expectations", "SIP Discontinuation"])
    with tab_a:
        section_behaviour(rows)
    with tab_b:
        section_expectations(rows)
    with tab_c:
        section_discontinuation(rows)
