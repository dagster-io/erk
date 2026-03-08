"""Tests for next_steps formatting functions."""

from erk_shared.output.next_steps import (
    PlanNextSteps,
    format_plan_next_steps_plain,
)


class TestPlanNextSteps:
    def test_construction(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.plan_number == 42

    def test_view_returns_url(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.view == "https://github.com/org/repo/pull/42"

    def test_dispatch_uses_plan_number(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.dispatch == "erk pr dispatch 42"

    def test_checkout_uses_plan_number(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout == "erk br co --for-plan 42"

    def test_implement_current_wt(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_current_wt == "erk br co --for-plan 42 && erk implement"

    def test_implement_current_wt_dangerous(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_current_wt_dangerous == "erk br co --for-plan 42 && erk implement -d"

    def test_checkout_new_slot(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout_new_slot == "erk br co --new-slot --for-plan 42"

    def test_implement_new_wt(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_new_wt == (
            'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement'
        )

    def test_implement_new_wt_dangerous(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_new_wt_dangerous == (
            'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement -d'
        )

    def test_dispatch_slash_command(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.dispatch_slash_command == "/erk:pr-dispatch"


class TestFormatPlanNextStepsPlain:
    def test_contains_for_plan_command(self) -> None:
        output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk br co --for-plan 42" in output

    def test_hierarchical_format(self) -> None:
        output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "Implement plan #42:" in output
        assert "In current wt:" in output
        assert "In new wt:" in output

    def test_contains_implement_command(self) -> None:
        output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk implement" in output
        assert "erk implement -d" in output

    def test_contains_dispatch(self) -> None:
        output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk pr dispatch 42" in output
        assert "/erk:pr-dispatch" in output
        assert "Dispatch plan #42:" in output

    def test_contains_checkout_new_slot(self) -> None:
        output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk br co --new-slot --for-plan 42" in output
