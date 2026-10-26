"""Shared UI components: styles, charts, record cards and states."""

from __future__ import annotations

import html
from typing import Any, Iterable

import altair as alt
import pandas as pd
import streamlit as st

# Single-series magnitude colour (reference palette slot 1, blue) and a
# one-hue sequential ramp for heatmaps. Text never uses series colours.
SERIES = "#2a78d6"
SEQUENTIAL = ["#dbe9f9", "#a9cbf2", "#6fa6e6", "#2a78d6", "#1b54a0"]

SOURCE_LABELS = {"play_store": "Google Play", "reddit": "Reddit", "youtube": "YouTube"}
APP_LABELS = {
    "com.nextbillion.groww": "Groww", "com.zerodha.kite3": "Zerodha Kite", "com.paytmmoney": "Paytm Money",
    "com.smartspends": "ET Money", "in.upstox.app": "Upstox",
}

CSS = """
<style>
.block-container {max-width: 1180px; padding-top: 1.6rem;}
h1, h2, h3 {letter-spacing: -0.01em;}
.hero {text-align: center; padding: 1.8rem 0 0.6rem;}
.hero h1 {font-size: 2.35rem; line-height: 1.2; margin-bottom: 0.4rem;}
.hero p {font-size: 1.08rem; opacity: 0.8; max-width: 720px; margin: 0 auto;}
.muted {opacity: 0.72; font-size: 0.9rem;}
.tag {display: inline-block; padding: 1px 8px; margin: 2px 4px 2px 0; border-radius: 999px;
      border: 1px solid rgba(128,128,128,0.35); font-size: 0.78rem;}
.quote {border-left: 3px solid rgba(42,120,214,0.65); padding: 0.2rem 0 0.2rem 0.8rem; margin: 0.4rem 0;}
.basis-stated {font-weight: 600;}
.basis-inferred {font-style: italic;}
div[data-testid="stForm"] {border-radius: 14px; padding: 1.2rem 1.4rem;}
div[data-testid="stForm"] input {font-size: 1.05rem; padding: 0.7rem 0.8rem;}
</style>
"""


def apply_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def nice(value: Any) -> str:
    if value is None:
        return "Unknown"
    return str(value).replace("_", " ").capitalize()


def platform_label(row: dict[str, Any]) -> str:
    detail = row.get("platform_detail") or ""
    if row.get("source") == "play_store":
        return f"Google Play · {APP_LABELS.get(detail, detail)}"
    if row.get("source") == "reddit":
        return f"Reddit · {detail}"
    return SOURCE_LABELS.get(row.get("source"), str(row.get("source")))


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def chart_caption(n: int, definition: str, extra: str = "") -> None:
    small = " · **small sample**" if n < 30 else ""
    st.caption(f"n = {n} records{small} · {definition}{(' · ' + extra) if extra else ''}")


def bar(counts: list[tuple[Any, int, float]], n: int, title: str, definition: str, top: int = 10, key: str = "") -> None:
    """Horizontal bars of record counts, sorted, with hover and a table view."""
    st.markdown(f"**{title}**")
    if not counts:
        insufficient("No records in this selection carry this tag.")
        chart_caption(n, definition)
        return
    df = pd.DataFrame([{"Value": nice(v), "Records": c, "Share": s} for v, c, s in counts[:top]])
    chart = (
        alt.Chart(df)
        .mark_bar(color=SERIES, cornerRadiusEnd=4, height={"band": 0.7})
        .encode(
            x=alt.X("Records:Q", title="Records", axis=alt.Axis(tickMinStep=1, grid=True, gridOpacity=0.25)),
            y=alt.Y("Value:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            tooltip=[alt.Tooltip("Value:N"), alt.Tooltip("Records:Q"), alt.Tooltip("Share:Q", format=".0%", title="Share of n")],
        )
        .properties(height=max(120, 30 * len(df)))
    )
    labels = chart.mark_text(align="left", dx=4).encode(text="Records:Q", color=alt.value("#888"))
    st.altair_chart(chart + labels, use_container_width=True, theme="streamlit")
    chart_caption(n, definition, f"showing top {min(top, len(counts))} of {len(counts)} values" if len(counts) > top else "")
    with st.expander("Table view", expanded=False):
        st.dataframe(df.assign(Share=df["Share"].map(pct)), hide_index=True, use_container_width=True, key=f"tbl_{key}_{title}")


def heatmap(rows: list[tuple[str, str, int]], n: int, title: str, definition: str, x_title: str, y_title: str, key: str = "") -> None:
    st.markdown(f"**{title}**")
    if not rows:
        insufficient("Not enough tagged records for this comparison.")
        chart_caption(n, definition)
        return
    df = pd.DataFrame([{"Row": nice(a), "Column": b, "Records": c} for a, b, c in rows])
    base = alt.Chart(df).encode(
        x=alt.X("Column:N", title=x_title, axis=alt.Axis(labelAngle=-30, labelLimit=160)),
        y=alt.Y("Row:N", title=y_title, axis=alt.Axis(labelLimit=200)),
    )
    cells = base.mark_rect(cornerRadius=3, stroke="white", strokeWidth=2).encode(
        color=alt.Color("Records:Q", scale=alt.Scale(range=SEQUENTIAL), legend=alt.Legend(title="Records")),
        tooltip=["Row:N", "Column:N", "Records:Q"],
    )
    text = base.mark_text(fontSize=11).encode(text="Records:Q", color=alt.condition(alt.datum.Records > df["Records"].max() * 0.55, alt.value("white"), alt.value("#222")))
    st.altair_chart((cells + text).properties(height=max(160, 34 * df["Row"].nunique())), use_container_width=True, theme="streamlit")
    chart_caption(n, definition)
    with st.expander("Table view", expanded=False):
        st.dataframe(df.pivot_table(index="Row", columns="Column", values="Records", fill_value=0), use_container_width=True, key=f"hm_{key}_{title}")


def line(points: list[tuple[int, int]], n: int, undated: int, title: str, definition: str) -> None:
    st.markdown(f"**{title}**")
    if len(points) < 2:
        insufficient("Fewer than two years with records; a trend cannot be shown.")
        chart_caption(n, definition)
        return
    df = pd.DataFrame([{"Year": str(y), "Records": c} for y, c in points])
    base = alt.Chart(df).encode(x=alt.X("Year:O", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("Records:Q", axis=alt.Axis(tickMinStep=1, gridOpacity=0.25)))
    chart = base.mark_line(color=SERIES, strokeWidth=2) + base.mark_point(color=SERIES, size=70, filled=True).encode(tooltip=["Year:O", "Records:Q"])
    st.altair_chart(chart.properties(height=220), use_container_width=True, theme="streamlit")
    chart_caption(n, definition, f"{undated} undated records excluded" if undated else "")


def insufficient(message: str) -> None:
    st.info(f"Insufficient evidence — {message}", icon=":material/info:")


def empty_dataset() -> None:
    st.warning(
        "The Golden Dataset index has not been built yet. Run `python -m research.build` after promoting approved rows "
        "with `python -m pipeline.export golden`.",
        icon=":material/database:",
    )


def tags_html(row: dict[str, Any], fields: Iterable[str]) -> str:
    chips = []
    for f in fields:
        v = row.get(f)
        if v in (None, "", "unclear", "none", "no_lapse"):
            continue
        chips.append(f'<span class="tag">{html.escape(nice(f))}: {html.escape(nice(v))}</span>')
    return "".join(chips)


def record_card(row: dict[str, Any], show_internal: bool = False, index: int | None = None, full_text: bool = True) -> None:
    from research.store import TAG_FIELDS

    with st.container(border=True):
        date = str(row.get("published_at") or "date unknown")[:10]
        head = f"**R{index}** · " if index else ""
        st.markdown(f"{head}{platform_label(row)} · {date} · [Open source ↗]({row.get('source_url')})")
        if row.get("context"):
            st.markdown(f"<div class='muted'>In thread: {html.escape(' '.join(str(row['context']).split()[:30]))}</div>", unsafe_allow_html=True)
        if row.get("evidence_quote") and row.get("quote_status") in ("exact", "repaired"):
            status = "verbatim" if row["quote_status"] == "exact" else "matched to closest text"
            st.markdown(f"<div class='quote'>“{html.escape(row['evidence_quote'])}”<br><span class='muted'>Quote {status}</span></div>", unsafe_allow_html=True)
        text = row.get("text") or ""
        if full_text:
            with st.expander("Full text", expanded=not row.get("evidence_quote")):
                st.write(text)
        st.markdown(tags_html(row, TAG_FIELDS), unsafe_allow_html=True)
        meta = [f"Record `{row.get('record_id')}`", f"collected {str(row.get('collected_at'))[:10]}", f"tagged by {row.get('tagged_by')}",
                "implied tags" if row.get("is_hypothesis") else "stated tags",
                "individually reviewed" if row.get("individually_reviewed") else "bulk-approved, not individually reviewed"]
        st.markdown(f"<div class='muted'>{' · '.join(html.escape(m) if '`' not in m else m for m in meta)}</div>", unsafe_allow_html=True)
        if show_internal and row.get("reviewer_notes"):
            st.markdown(f"<div class='muted'>Reviewer ({html.escape(str(row.get('reviewer')))}): {html.escape(str(row['reviewer_notes']))}</div>", unsafe_allow_html=True)
