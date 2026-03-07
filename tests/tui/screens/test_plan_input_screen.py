"""Tests for the PlanInputScreen modal."""

from erk.tui.screens.plan_input_screen import PlanInputScreen


def test_escape_binding_exists() -> None:
    """PlanInputScreen should have an escape binding."""
    screen = PlanInputScreen(pr_number=123)
    binding_keys = [b.key for b in screen.BINDINGS]
    assert "escape" in binding_keys


def test_ctrl_s_binding_exists() -> None:
    """PlanInputScreen should have a ctrl+s submit binding."""
    screen = PlanInputScreen(pr_number=123)
    binding_keys = [b.key for b in screen.BINDINGS]
    assert "ctrl+s" in binding_keys


def test_q_is_not_bound() -> None:
    """PlanInputScreen should NOT bind 'q' -- user needs it for typing."""
    screen = PlanInputScreen(pr_number=123)
    binding_keys = [b.key for b in screen.BINDINGS]
    assert "q" not in binding_keys


def test_pr_number_stored() -> None:
    """PlanInputScreen should store the PR number."""
    screen = PlanInputScreen(pr_number=456)
    assert screen._pr_number == 456
