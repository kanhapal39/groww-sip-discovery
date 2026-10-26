"""Cached data access for the dashboard. All numbers come from these loaders."""

from __future__ import annotations

import hmac
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(show_spinner=False)
def config() -> dict[str, Any]:
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def paths() -> dict[str, Path]:
    """The app reads only data/export/; the search index is built in a temp folder."""
    export = PROJECT_ROOT / config()["paths"]["export"]
    return {"public": export / "golden_public.jsonl", "quality": export / "quality_metrics.json", "db": _index()}


@st.cache_resource(show_spinner=False)
def _index_for(public: str, version: str) -> Path:
    from research.store import build_database, load_golden

    db = Path(tempfile.gettempdir()) / f"sip_research_{version}.db"
    if not db.exists():
        build_database(load_golden(Path(public)), db)
    return db


def _index() -> Path:
    from research.store import golden_version

    public = PROJECT_ROOT / config()["paths"]["export"] / "golden_public.jsonl"
    return _index_for(str(public), golden_version(public)) if public.exists() else Path(tempfile.gettempdir()) / "sip_research_missing.db"


@st.cache_data(show_spinner=False)
def _rows(db: str, mtime: float, public_only: bool) -> list[dict[str, Any]]:
    from research.store import read_rows

    return read_rows(Path(db), public_only=public_only)


def rows(public_only: bool = True) -> list[dict[str, Any]]:
    db = paths()["db"]
    return _rows(str(db), db.stat().st_mtime if db.exists() else 0.0, public_only)


@st.cache_data(show_spinner=False)
def _quality(path: str, mtime: float) -> dict[str, Any] | None:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def quality() -> dict[str, Any] | None:
    p = paths()["quality"]
    return _quality(str(p), p.stat().st_mtime if p.exists() else 0.0)


def golden_version() -> str:
    q = quality()
    return q.get("golden_version", "unknown") if q else "unknown"


@st.cache_data(show_spinner=False)
def _opportunities(db_mtime: float) -> dict[str, Any]:
    from research.opportunities import build

    return build(rows())


def opportunities() -> dict[str, Any]:
    db = paths()["db"]
    return _opportunities(db.stat().st_mtime if db.exists() else 0.0)


def _secret(name: str) -> str | None:
    """st.secrets first (Streamlit Community Cloud), then the environment, then .env (local)."""
    try:
        value = st.secrets.get(name)
    except Exception:  # no secrets.toml configured
        value = None
    if value:
        return str(value)
    from collect.youtube import load_api_key

    try:
        return load_api_key(name, PROJECT_ROOT / ".env")
    except RuntimeError:
        return None


@st.cache_resource(show_spinner=False)
def _answer_store() -> dict[tuple[str, str], dict[str, Any]]:
    """Shared across sessions; holds only successful or final results, never errors."""
    return {}


def answer(question: str, version: str) -> dict[str, Any]:
    """Answer once per (question, dataset version). Errors are not cached, so a retry can succeed."""
    store = _answer_store()
    key = (question, version)
    if key in store:
        return store[key]
    result = _generate(question, version)
    if result["status"] != "error":
        if len(store) > 200:
            store.pop(next(iter(store)))
        store[key] = result
    return result


def _generate(question: str, version: str) -> dict[str, Any]:
    from pipeline.filter import GroqClient, RateLimited
    from research.answer import answer_question

    cfg = config()
    settings = cfg["research"]
    api_key = _secret(cfg["llm"]["auth_env_var"])
    models = [settings["answer_model"], *settings.get("answer_fallback_models", [])]
    used: dict[str, Any] = {}

    def complete(messages: list[dict[str, str]]) -> Any:
        """Try each model in turn; move on only when a model is rate-limited."""
        last: Exception | None = None
        for model in models:
            try:
                response = GroqClient(api_key, cfg["llm"]["base_url"], model, {**cfg["llm"], **settings}, timeout=90).complete(messages)
                used["model"] = model
                return response
            except RateLimited as exc:
                last = exc
                used.setdefault("waits", []).append(exc.wait_seconds)
        raise last or RuntimeError("no answer model configured")

    result = answer_question(question, paths()["db"], complete if api_key else None, settings, total_public=len(rows()))
    result["model"] = used.get("model")
    if result["status"] == "error" and used.get("waits"):
        minutes = max(1, round(min(used["waits"]) / 60))
        result["message"] = (f"The research assistant is busy: every answer model has reached its free usage limit. "
                             f"Try again in about {minutes} minute(s). Matching evidence is shown below.")
    result["dataset_version"] = version
    return result


def is_admin() -> bool:
    return bool(st.session_state.get("is_admin"))


def admin_login(password: str) -> bool:
    expected = _secret(config()["research"]["admin_password_env"])
    ok = bool(expected) and hmac.compare_digest(password.encode(), expected.encode())
    st.session_state["is_admin"] = ok
    return ok


def admin_configured() -> bool:
    return bool(_secret(config()["research"]["admin_password_env"]))


def ready() -> bool:
    p = paths()
    return p["public"].exists() and p["quality"].exists() and p["db"].exists()


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")
