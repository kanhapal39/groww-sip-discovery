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


def test_errors_are_not_cached_but_answers_are(monkeypatch) -> None:
    from app import data

    data._answer_store().clear()
    results = iter([{"status": "error"}, {"status": "answered"}, {"status": "error"}])
    calls = []
    monkeypatch.setattr(data, "_generate", lambda q, v: calls.append(q) or next(results))
    assert data.answer("q", "v1")["status"] == "error"
    assert data.answer("q", "v1")["status"] == "answered"  # retried, not served from cache
    assert data.answer("q", "v1")["status"] == "answered"  # now cached
    assert calls == ["q", "q"]
    data._answer_store().clear()


def test_rate_limited_model_falls_back_to_the_next(monkeypatch) -> None:
    import pipeline.filter as pf
    import research.answer as ra
    from app import data

    tried = []

    class Client:
        def __init__(self, key, base, model, settings, timeout=0):
            self.model = model

        def complete(self, messages):
            tried.append(self.model)
            if self.model == "openai/gpt-oss-120b":
                raise pf.RateLimited(300, True, "tokens per day (TPD)")
            return "ok"

    def fake_answer(question, db, complete, settings, total_public):
        complete([])
        return {"status": "answered"}

    monkeypatch.setattr(pf, "GroqClient", Client)
    monkeypatch.setattr(ra, "answer_question", fake_answer)
    monkeypatch.setattr(data, "_secret", lambda name: "key")
    monkeypatch.setattr(data, "rows", lambda public_only=True: [])
    monkeypatch.setattr(data, "paths", lambda: {"db": None})
    result = data._generate("q", "v")
    assert tried == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    assert result["model"] == "openai/gpt-oss-20b"
