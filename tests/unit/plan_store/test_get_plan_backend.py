"""Tests for get_plan_backend() three-tier resolution: env > config > default."""

from pathlib import Path

import pytest

from erk_shared.context.types import GlobalConfig
from erk_shared.plan_store import get_plan_backend

# --- Tier 1: env var (highest priority) ---


def test_env_var_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env var 'github' wins over config and default."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "github")
    config = GlobalConfig.test(Path("/fake"), plan_backend="draft_pr")

    assert get_plan_backend(config) == "github"


def test_env_var_draft_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env var 'draft_pr' wins over config and default."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "draft_pr")
    config = GlobalConfig.test(Path("/fake"), plan_backend="github")

    assert get_plan_backend(config) == "draft_pr"


def test_env_var_invalid_falls_back_to_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid env var falls back to 'github', ignoring config."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "invalid_backend")
    config = GlobalConfig.test(Path("/fake"), plan_backend="draft_pr")

    assert get_plan_backend(config) == "github"


# --- Tier 2: config (when env var unset) ---


def test_config_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config 'github' used when env var is unset."""
    monkeypatch.delenv("ERK_PLAN_BACKEND", raising=False)
    config = GlobalConfig.test(Path("/fake"), plan_backend="github")

    assert get_plan_backend(config) == "github"


def test_config_draft_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config 'draft_pr' used when env var is unset."""
    monkeypatch.delenv("ERK_PLAN_BACKEND", raising=False)
    config = GlobalConfig.test(Path("/fake"), plan_backend="draft_pr")

    assert get_plan_backend(config) == "draft_pr"


# --- Tier 3: default (no env var, no config) ---


def test_default_when_no_env_and_no_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns 'github' when no env var and no config provided."""
    monkeypatch.delenv("ERK_PLAN_BACKEND", raising=False)

    assert get_plan_backend(None) == "github"


def test_default_when_no_env_and_no_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns 'github' when called with no arguments and no env var."""
    monkeypatch.delenv("ERK_PLAN_BACKEND", raising=False)

    assert get_plan_backend() == "github"
