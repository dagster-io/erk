"""Tests for next_steps formatting functions."""

from erk_shared.output.next_steps import (
    PrNextSteps,
    format_pr_next_steps_plain,
)

_URL = "https://github.com/org/repo/pull/42"
_BRANCH = "plnd/my-feature"


def _steps() -> PrNextSteps:
    return PrNextSteps(pr_number=42, url=_URL, branch_name=_BRANCH)


class TestPrNextSteps:
    def test_construction(self) -> None:
        steps = _steps()
        assert steps.pr_number == 42

    def test_view_returns_url(self) -> None:
        steps = _steps()
        assert steps.view == _URL

    def test_dispatch_uses_pr_number(self) -> None:
        steps = _steps()
        assert steps.dispatch == "erk pr dispatch 42"

    def test_checkout_uses_branch_name(self) -> None:
        steps = _steps()
        assert steps.checkout == "erk slot co plnd/my-feature"

    def test_implement_current_wt(self) -> None:
        steps = _steps()
        assert steps.implement_current_wt == "erk slot co plnd/my-feature && erk implement"

    def test_implement_current_wt_dangerous(self) -> None:
        steps = _steps()
        assert (
            steps.implement_current_wt_dangerous
            == "erk slot co plnd/my-feature && erk implement -d"
        )

    def test_checkout_new_slot(self) -> None:
        steps = _steps()
        assert steps.checkout_new_slot == "erk slot co plnd/my-feature --new-slot"

    def test_implement_new_wt(self) -> None:
        steps = _steps()
        assert steps.implement_new_wt == (
            'source "$(erk slot co plnd/my-feature --new-slot --script)" && erk implement'
        )

    def test_implement_new_wt_dangerous(self) -> None:
        steps = _steps()
        assert steps.implement_new_wt_dangerous == (
            'source "$(erk slot co plnd/my-feature --new-slot --script)" && erk implement -d'
        )

    def test_dispatch_slash_command(self) -> None:
        steps = _steps()
        assert steps.dispatch_slash_command == "/erk:pr-dispatch"


class TestFormatPrNextStepsPlain:
    def test_contains_slot_co_command(self) -> None:
        output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
        assert "erk slot co plnd/my-feature" in output

    def test_hierarchical_format(self) -> None:
        output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
        assert "Implement PR #42:" in output
        assert "In current wt:" in output
        assert "In new wt:" in output

    def test_contains_implement_command(self) -> None:
        output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
        assert "erk implement" in output
        assert "erk implement -d" in output

    def test_contains_dispatch(self) -> None:
        output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
        assert "erk pr dispatch 42" in output
        assert "/erk:pr-dispatch" in output
        assert "Dispatch PR #42:" in output

    def test_contains_checkout_new_slot(self) -> None:
        output = format_pr_next_steps_plain(42, url=_URL, branch_name=_BRANCH)
        assert "erk slot co plnd/my-feature --new-slot" in output
