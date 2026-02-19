"""Tests for get_plan_backend() env var validation logic."""

import pytest

from erk_shared.plan_store import get_plan_backend


def test_defaults_to_github_when_env_var_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns 'github' when ERK_PLAN_BACKEND is not set."""
    monkeypatch.delenv("ERK_PLAN_BACKEND", raising=False)

    assert get_plan_backend() == "github"


def test_returns_github_when_set_to_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns 'github' when ERK_PLAN_BACKEND is 'github'."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "github")

    assert get_plan_backend() == "github"


def test_returns_draft_pr_when_set_to_draft_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns 'draft_pr' when ERK_PLAN_BACKEND is 'draft_pr'."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "draft_pr")

    assert get_plan_backend() == "draft_pr"


def test_falls_back_to_github_for_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns 'github' when ERK_PLAN_BACKEND has an invalid value."""
    monkeypatch.setenv("ERK_PLAN_BACKEND", "invalid_backend")

    assert get_plan_backend() == "github"
