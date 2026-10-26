"""SIP Discovery Engine dashboard.

Run:
    streamlit run app/streamlit_app.py

Five pages in the header navigation. All figures come from the Golden Dataset
index and quality metrics built by ``python -m research.build``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PAGE_TITLES = ("Overview", "Investor Behaviour", "Product Opportunities", "Evidence Explorer", "Data Quality & Validation")


def build_pages() -> dict:
    import streamlit as st

    from app.views import behaviour, evidence, opportunities, overview, quality

    return {
        "Overview": st.Page(overview.render, title="Overview", url_path="overview", default=True),
        "Investor Behaviour": st.Page(behaviour.render, title="Investor Behaviour", url_path="investor-behaviour"),
        "Product Opportunities": st.Page(opportunities.render, title="Product Opportunities", url_path="product-opportunities"),
        "Evidence Explorer": st.Page(evidence.render, title="Evidence Explorer", url_path="evidence-explorer"),
        "Data Quality & Validation": st.Page(quality.render, title="Data Quality & Validation", url_path="data-quality"),
    }


def main() -> None:
    import streamlit as st

    from app import ui

    st.set_page_config(page_title="SIP Discovery Engine", page_icon=":material/insights:", layout="wide")
    ui.apply_styles()
    pages = build_pages()
    st.session_state["_pages"] = pages
    nav = st.navigation(list(pages.values()), position="top")
    nav.run()


if __name__ == "__main__":
    main()
