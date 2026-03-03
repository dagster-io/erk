"""Tests for next_steps formatting."""

from erk_shared.output.next_steps import (
    PlanNextSteps,
    format_plan_next_steps_plain,
)


def test_plan_next_steps_constructs_with_all_params() -> None:
    """PlanNextSteps constructs correctly with plan_number and url."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.plan_number == 42
    assert s.url == "https://github.com/org/repo/pull/42"


def test_plan_next_steps_view_returns_url() -> None:
    """view returns the URL directly."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.view == "https://github.com/org/repo/pull/42"


def test_plan_next_steps_checkout_uses_plan_number() -> None:
    """checkout uses --for-plan with plan_number."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.checkout == "erk br co --for-plan 42"


def test_plan_next_steps_dispatch_uses_plan_number() -> None:
    """dispatch uses plan_number."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.dispatch == "erk pr dispatch 42"


def test_format_plan_next_steps_plain_uses_for_plan() -> None:
    """format_plan_next_steps_plain uses --for-plan command."""
    output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
    assert "erk br co --for-plan 42" in output


def test_format_plan_next_steps_plain_contains_url() -> None:
    """format_plan_next_steps_plain shows URL in view line."""
    output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
    assert "https://github.com/org/repo/pull/42" in output


def test_format_plan_next_steps_plain_contains_implement() -> None:
    """format_plan_next_steps_plain includes implement command."""
    output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
    assert "erk implement --dangerous" in output
