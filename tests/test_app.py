"""Smoke tests: every dashboard page renders without an exception (no model calls)."""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

PAGES = ("app/views/overview.py", "app/views/behaviour.py", "app/views/opportunities.py", "app/views/evidence.py", "app/views/quality.py")


def run_page(page: str) -> AppTest:
    script = f"""
import sys
sys.path.insert(0, ".")
from app import ui
ui.apply_styles()
import importlib.util
spec = importlib.util.spec_from_file_location("page", "{page}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.render()
"""
    at = AppTest.from_string(script, default_timeout=60)
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page: str) -> None:
    at = run_page(page)
    assert not at.exception, at.exception


def test_overview_has_question_box_and_five_suggestions() -> None:
    at = run_page("app/views/overview.py")
    assert at.text_input[0].label == "Ask your question"
    suggestions = [b.label for b in at.button if b.label.endswith("?")]
    assert len(suggestions) == 5
