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

    def test_checkout_and_implement_uses_plan_number(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout_and_implement == (
            'source "$(erk br co --for-plan 42 --script)" && erk implement --dangerous'
        )

    def test_checkout_new_slot(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout_new_slot == "erk br co --new-slot --for-plan 42"

    def test_checkout_new_slot_and_implement(self) -> None:
        steps = PlanNextSteps(
            plan_number=42,
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout_new_slot_and_implement == (
            'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement --dangerous'
        )


class TestFormatPlanNextStepsPlain:
    def test_contains_for_plan_command(self) -> None:
        output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk br co --for-plan 42" in output

    def test_contains_url_in_view(self) -> None:
        output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "https://github.com/org/repo/pull/42" in output

    def test_contains_implement_command(self) -> None:
        output = format_plan_next_steps_plain(42, url="https://github.com/org/repo/pull/42")
        assert "erk implement --dangerous" in output
