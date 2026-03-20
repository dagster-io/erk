"""Tests for next_steps formatting functions."""

from erk_shared.output.next_steps import (
    PrNextSteps,
    format_pr_next_steps_plain,
)


class TestPrNextSteps:
    def test_construction(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.pr_number == 42

    def test_view_returns_url(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.view == "https://github.com/org/repo/pull/42"

    def test_dispatch_uses_pr_number(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.dispatch == "erk pr dispatch 42"

    def test_checkout_uses_pr_number(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout == "erk slot co --for-plan 42"

    def test_implement_current_wt(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_current_wt == "erk slot co --for-plan 42 && erk implement"

    def test_implement_current_wt_dangerous(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_current_wt_dangerous == "erk slot co --for-plan 42 && erk implement -d"

    def test_checkout_new_slot(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout_new_slot == "erk slot co --new-slot --for-plan 42"

    def test_implement_new_wt(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_new_wt == (
            'source "$(erk slot co --new-slot --for-plan 42 --script)" && erk implement'
        )

    def test_implement_new_wt_dangerous(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_new_wt_dangerous == (
            'source "$(erk slot co --new-slot --for-plan 42 --script)" && erk implement -d'
        )

    def test_dispatch_slash_command(self) -> None:
        steps = PrNextSteps(
            pr_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.dispatch_slash_command == "/erk:pr-dispatch"


class TestFormatPrNextStepsPlain:
    def test_contains_for_plan_command(self) -> None:
        output = format_pr_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk slot co --for-plan 42" in output

    def test_hierarchical_format(self) -> None:
        output = format_pr_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "Implement PR #42:" in output
        assert "In current wt:" in output
        assert "In new wt:" in output

    def test_contains_implement_command(self) -> None:
        output = format_pr_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk implement" in output
        assert "erk implement -d" in output

    def test_contains_dispatch(self) -> None:
        output = format_pr_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk pr dispatch 42" in output
        assert "/erk:pr-dispatch" in output
        assert "Dispatch PR #42:" in output

    def test_contains_checkout_new_slot(self) -> None:
        output = format_pr_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk slot co --new-slot --for-plan 42" in output
