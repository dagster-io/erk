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


def test_plan_next_steps_checkout_new_slot() -> None:
    """checkout_new_slot uses --new-slot --for-plan."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.checkout_new_slot == "erk br co --new-slot --for-plan 42"


def test_plan_next_steps_implement_current_wt() -> None:
    """implement_current_wt uses --for-plan with erk implement (non-dangerous)."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.implement_current_wt == 'source "$(erk br co --for-plan 42 --script)" && erk implement'


def test_plan_next_steps_implement_current_wt_dangerous() -> None:
    """implement_current_wt_dangerous uses -d flag."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.implement_current_wt_dangerous == (
        'source "$(erk br co --for-plan 42 --script)" && erk implement -d'
    )


def test_plan_next_steps_implement_new_wt() -> None:
    """implement_new_wt uses --new-slot with erk implement (non-dangerous)."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.implement_new_wt == (
        'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement'
    )


def test_plan_next_steps_implement_new_wt_dangerous() -> None:
    """implement_new_wt_dangerous uses --new-slot with -d flag."""
    s = PlanNextSteps(plan_number=42, url="https://github.com/org/repo/pull/42")
    assert s.implement_new_wt_dangerous == (
        'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement -d'
    )


def test_format_plan_next_steps_plain_hierarchical_format() -> None:
    """format_plan_next_steps_plain produces hierarchical output."""
    output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
    assert "Implement plan #42:" in output
    assert "In current wt:" in output
    assert "In new wt:" in output
    assert "(dangerously):" in output
    assert "Checkout plan #42:" in output
    assert "Dispatch to queue:" in output


def test_format_plan_next_steps_plain_contains_implement() -> None:
    """format_plan_next_steps_plain includes implement commands."""
    output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
    assert "erk implement" in output
    assert "erk implement -d" in output


def test_format_plan_next_steps_plain_contains_for_plan_command() -> None:
    """format_plan_next_steps_plain includes --for-plan command."""
    output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
    assert "erk br co --for-plan 42" in output


def test_format_plan_next_steps_plain_contains_checkout_new_slot() -> None:
    """format_plan_next_steps_plain includes checkout new slot command."""
    output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
    assert "erk br co --new-slot --for-plan 42" in output


def test_format_plan_next_steps_plain_contains_dispatch() -> None:
    """format_plan_next_steps_plain includes dispatch command."""
    output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
    assert "erk pr dispatch 42" in output
