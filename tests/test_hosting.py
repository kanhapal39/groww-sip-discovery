"""Checks on the Render Blueprint and Streamlit config (no network)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def service() -> dict:
    return yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))["services"][0]


def test_start_command_binds_render_port_and_runs_existing_app() -> None:
    command = service()["startCommand"]
    assert "--server.port $PORT" in command
    assert "--server.address 0.0.0.0" in command
    assert (ROOT / command.split()[2]).is_file()


def test_build_installs_dashboard_requirements_only() -> None:
    assert service()["buildCommand"] == "pip install -r requirements.txt"


def test_secrets_have_no_value_in_blueprint() -> None:
    env = {item["key"]: item for item in service()["envVars"]}
    for name in ("GROQ_API_KEY", "ADMIN_PASSWORD"):
        assert env[name]["sync"] is False
        assert "value" not in env[name]


def test_toolbar_hides_host_controls() -> None:
    assert 'toolbarMode = "minimal"' in (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
