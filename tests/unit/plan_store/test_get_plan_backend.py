"""Tests for get_plan_backend() two-tier resolution: env var > default."""

import pytest

from erk_shared.plan_store import get_plan_backend

# --- Tier 1: env var (highest priority) ---


def test_env_var_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env var 'github' returns 'github'."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "github")

    assert get_plan_backend() == "github"


def test_env_var_draft_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env var 'draft_pr' returns 'draft_pr'."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "draft_pr")

    assert get_plan_backend() == "draft_pr"


def test_env_var_invalid_falls_back_to_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid env var falls back to 'github'."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "invalid_backend")

    assert get_plan_backend() == "github"


# --- Tier 2: default (no env var) ---


def test_default_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns 'github' when no env var is set."""
    monkeypatch.delenv("ERK_PLAN_BACKEND", raising=False)

    assert get_plan_backend() == "github"
