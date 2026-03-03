"""Tests for next_steps formatting functions."""

from erk_shared.output.next_steps import (
    IssueNextSteps,
    PlannedPRNextSteps,
    format_next_steps_plain,
    format_planned_pr_next_steps_plain,
)


class TestIssueNextSteps:
    def test_checkout_uses_co(self) -> None:
        steps = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
        assert steps.checkout == "erk br co --for-plan 99"

    def test_view_returns_url(self) -> None:
        steps = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
        assert steps.view == "https://github.com/org/repo/issues/99"

    def test_implement_new_br(self) -> None:
        steps = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
        assert steps.implement_new_br == (
            'source "$(erk br co --for-plan 99 --script)" && erk implement'
        )

    def test_implement_new_br_dangerous(self) -> None:
        steps = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
        assert steps.implement_new_br_dangerous == (
            'source "$(erk br co --for-plan 99 --script)" && erk implement -d'
        )

    def test_checkout_new_slot(self) -> None:
        steps = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
        assert steps.checkout_new_slot == "erk br co --new-slot --for-plan 99"

    def test_implement_new_wt(self) -> None:
        steps = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
        assert steps.implement_new_wt == (
            'source "$(erk br co --new-slot --for-plan 99 --script)" && erk implement'
        )

    def test_implement_new_wt_dangerous(self) -> None:
        steps = IssueNextSteps(plan_number=99, url="https://github.com/org/repo/issues/99")
        assert steps.implement_new_wt_dangerous == (
            'source "$(erk br co --new-slot --for-plan 99 --script)" && erk implement -d'
        )


class TestPlannedPRNextSteps:
    def test_construction(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.pr_number == 42
        assert steps.branch_name == "plan-my-feature-02-20"

    def test_view_returns_url(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.view == "https://github.com/org/repo/pull/42"

    def test_dispatch_uses_pr_number(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.dispatch == "erk pr dispatch 42"

    def test_checkout_uses_pr_number(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout == "erk br co --for-plan 42"

    def test_implement_new_br(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_new_br == (
            'source "$(erk br co --for-plan 42 --script)" && erk implement'
        )

    def test_implement_new_br_dangerous(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_new_br_dangerous == (
            'source "$(erk br co --for-plan 42 --script)" && erk implement -d'
        )

    def test_checkout_new_slot(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.checkout_new_slot == "erk br co --new-slot --for-plan 42"

    def test_implement_new_wt(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_new_wt == (
            'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement'
        )

    def test_implement_new_wt_dangerous(self) -> None:
        steps = PlannedPRNextSteps(
            pr_number=42,
            branch_name="plan-my-feature-02-20",
            url="https://github.com/org/repo/pull/42",
        )
        assert steps.implement_new_wt_dangerous == (
            'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement -d'
        )


class TestFormatNextStepsPlain:
    def test_hierarchical_format(self) -> None:
        output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
        assert "Implement plan #99:" in output
        assert "In new br:" in output
        assert "In new wt:" in output

    def test_contains_co_commands(self) -> None:
        output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
        assert "erk br co --for-plan 99" in output

    def test_does_not_contain_create(self) -> None:
        output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
        assert "erk br create" not in output

    def test_contains_implement_command(self) -> None:
        output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
        assert "erk implement" in output
        assert "erk implement -d" in output

    def test_contains_checkout_new_slot(self) -> None:
        output = format_next_steps_plain(99, url="https://github.com/org/repo/issues/99")
        assert "erk br co --new-slot --for-plan 99" in output


class TestFormatPlannedPRNextStepsPlain:
    def test_hierarchical_format(self) -> None:
        output = format_planned_pr_next_steps_plain(
            42, branch_name="plan-my-feature-02-20", url="https://github.com/org/repo/pull/42"
        )
        assert "Implement plan #42:" in output
        assert "In new br:" in output
        assert "In new wt:" in output

    def test_contains_for_plan_command(self) -> None:
        output = format_planned_pr_next_steps_plain(
            42, branch_name="plan-my-feature-02-20", url="https://github.com/org/repo/pull/42"
        )
        assert "erk br co --for-plan 42" in output

    def test_contains_implement_command(self) -> None:
        output = format_planned_pr_next_steps_plain(
            42, branch_name="plan-my-feature-02-20", url="https://github.com/org/repo/pull/42"
        )
        assert "erk implement" in output
        assert "erk implement -d" in output

    def test_contains_dispatch(self) -> None:
        output = format_planned_pr_next_steps_plain(
            42, branch_name="plan-my-feature-02-20", url="https://github.com/org/repo/pull/42"
        )
        assert "erk pr dispatch 42" in output
