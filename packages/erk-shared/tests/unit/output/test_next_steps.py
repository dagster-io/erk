"""Tests for next_steps formatting."""

from erk_shared.output.next_steps import (
    PrNextSteps,
    format_pr_next_steps_plain,
)

_URL = "https://github.com/org/repo/pull/42"
_BRANCH = "plnd/my-feature"


def _steps() -> PrNextSteps:
    return PrNextSteps(pr_number=42, url=_URL, branch_name=_BRANCH)


def test_plan_next_steps_constructs_with_all_params() -> None:
    """PrNextSteps constructs correctly with plan_number and url."""
    s = _steps()
    assert s.pr_number == 42
    assert s.url == _URL


def test_plan_next_steps_view_returns_url() -> None:
    """view returns the URL directly."""
    s = _steps()
    assert s.view == _URL


def test_plan_next_steps_checkout_uses_branch_name() -> None:
    """checkout uses erk slot co with branch_name."""
    s = _steps()
    assert s.checkout == "erk slot co plnd/my-feature"


def test_plan_next_steps_dispatch_uses_plan_number() -> None:
    """dispatch uses plan_number."""
    s = _steps()
    assert s.dispatch == "erk pr dispatch 42"


def test_plan_next_steps_checkout_new_slot() -> None:
    """checkout_new_slot uses erk slot co with --new-slot."""
    s = _steps()
    assert s.checkout_new_slot == "erk slot co plnd/my-feature --new-slot"


def test_plan_next_steps_implement_current_wt() -> None:
    """implement_current_wt uses erk slot co with erk implement."""
    s = _steps()
    assert s.implement_current_wt == "erk slot co plnd/my-feature && erk implement"


def test_plan_next_steps_implement_current_wt_dangerous() -> None:
    """implement_current_wt_dangerous uses -d flag."""
    s = _steps()
    assert s.implement_current_wt_dangerous == "erk slot co plnd/my-feature && erk implement -d"


def test_plan_next_steps_implement_new_wt() -> None:
    """implement_new_wt uses erk slot co --new-slot with erk implement."""
    s = _steps()
    assert s.implement_new_wt == (
        'source "$(erk slot co plnd/my-feature --new-slot --script)" && erk implement'
    )


def test_plan_next_steps_implement_new_wt_dangerous() -> None:
    """implement_new_wt_dangerous uses --new-slot with -d flag."""
    s = _steps()
    assert s.implement_new_wt_dangerous == (
        'source "$(erk slot co plnd/my-feature --new-slot --script)" && erk implement -d'
    )


def test_format_pr_next_steps_plain_hierarchical_format() -> None:
    """format_pr_next_steps_plain produces hierarchical output."""
    output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
    assert "Implement PR #42:" in output
    assert "In current wt:" in output
    assert "In new wt:" in output
    assert "(dangerously):" in output
    assert "Checkout PR #42:" in output
    assert "Dispatch PR #42:" in output


def test_format_pr_next_steps_plain_contains_implement() -> None:
    """format_pr_next_steps_plain includes implement commands."""
    output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
    assert "erk implement" in output
    assert "erk implement -d" in output


def test_format_pr_next_steps_plain_contains_slot_co_command() -> None:
    """format_pr_next_steps_plain includes erk slot co command."""
    output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
    assert "erk slot co plnd/my-feature" in output


def test_format_pr_next_steps_plain_contains_checkout_new_slot() -> None:
    """format_pr_next_steps_plain includes checkout new slot command."""
    output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
    assert "erk slot co plnd/my-feature --new-slot" in output


def test_format_pr_next_steps_plain_contains_dispatch() -> None:
    """format_pr_next_steps_plain includes dispatch command."""
    output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
    assert "erk pr dispatch 42" in output
