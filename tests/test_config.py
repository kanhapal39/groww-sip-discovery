"""Tests for configuration files (config.yaml and codebook.yaml)."""

from __future__ import annotations

import os
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_config_yaml_parses() -> None:
    """config.yaml must parse as valid YAML."""
    config = _load_yaml(os.path.join(PROJECT_ROOT, "config.yaml"))
    assert isinstance(config, dict)


def test_codebook_yaml_parses() -> None:
    """codebook.yaml must parse as valid YAML."""
    codebook = _load_yaml(os.path.join(PROJECT_ROOT, "codebook.yaml"))
    assert isinstance(codebook, dict)


def test_config_has_groq_provider() -> None:
    """The LLM provider must be set to Groq."""
    config = _load_yaml(os.path.join(PROJECT_ROOT, "config.yaml"))
    assert config.get("llm", {}).get("provider") == "groq"


def test_config_has_model_id() -> None:
    """config.yaml must specify a candidate model ID."""
    config = _load_yaml(os.path.join(PROJECT_ROOT, "config.yaml"))
    model_id = config.get("llm", {}).get("model_id")
    assert model_id is not None
    assert isinstance(model_id, str)
    assert "/" in model_id  # namespace/name format


def test_config_has_base_url() -> None:
    """config.yaml must specify the LLM API base URL."""
    config = _load_yaml(os.path.join(PROJECT_ROOT, "config.yaml"))
    base_url = config.get("llm", {}).get("base_url")
    assert base_url is not None
    assert isinstance(base_url, str)
    assert base_url.startswith("https://")


def test_config_uses_env_var_for_auth() -> None:
    """Authentication must reference an environment variable, not a key value."""
    config = _load_yaml(os.path.join(PROJECT_ROOT, "config.yaml"))
    auth_env_var = config.get("llm", {}).get("auth_env_var")
    assert auth_env_var == "GROQ_API_KEY"


def test_codebook_has_sip_behavior_tags() -> None:
    """codebook.yaml must define SIP behavior tags."""
    codebook = _load_yaml(os.path.join(PROJECT_ROOT, "codebook.yaml"))
    tags = codebook.get("sip_behavior_tags", [])
    assert len(tags) == 5
    tag_ids = {t["id"] for t in tags}
    assert tag_ids == {
        "start_sip",
        "continue_sip",
        "pause_sip",
        "reduce_sip",
        "stop_sip",
    }


def test_codebook_tag_fields_have_required_provenance() -> None:
    """codebook.yaml tag_fields must include provenance fields."""
    codebook = _load_yaml(os.path.join(PROJECT_ROOT, "codebook.yaml"))
    fields = {f["field"] for f in codebook.get("tag_fields", [])}
    assert "record_id" in fields
    assert "source_url" in fields
    assert "collected_at" in fields
