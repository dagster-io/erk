"""Tests for next_steps formatting functions."""

from erk_shared.output.next_steps import (
    DraftPRNextSteps,
    IssueNextSteps,
    format_draft_pr_next_steps_plain,
    format_next_steps_plain,
)


class TestIssueNextSteps:
    def test_prepare_uses_co(self) -> None:
        steps = IssueNextSteps(issue_number=99)
        assert steps.prepare == "erk br co --for-plan 99"

    def test_prepare_and_implement_uses_co(self) -> None:
        steps = IssueNextSteps(issue_number=99)
        assert steps.prepare_and_implement == (
            'source "$(erk br co --for-plan 99 --script)" && erk implement --dangerous'
        )

    def test_prepare_new_slot(self) -> None:
        steps = IssueNextSteps(issue_number=99)
        assert steps.prepare_new_slot == "erk br co --new-slot --for-plan 99"

    def test_prepare_new_slot_and_implement(self) -> None:
        steps = IssueNextSteps(issue_number=99)
        assert steps.prepare_new_slot_and_implement == (
            'source "$(erk br co --new-slot --for-plan 99 --script)" && erk implement --dangerous'
        )


class TestDraftPRNextSteps:
    def test_construction(self) -> None:
        steps = DraftPRNextSteps(pr_number=42, branch_name="plan-my-feature-02-20")
        assert steps.pr_number == 42
        assert steps.branch_name == "plan-my-feature-02-20"

    def test_view_uses_pr_number(self) -> None:
        steps = DraftPRNextSteps(pr_number=42, branch_name="plan-my-feature-02-20")
        assert steps.view == "gh pr view 42 --web"

    def test_submit_uses_pr_number(self) -> None:
        steps = DraftPRNextSteps(pr_number=42, branch_name="plan-my-feature-02-20")
        assert steps.submit == "erk plan submit 42"

    def test_checkout_and_implement_uses_branch_name(self) -> None:
        steps = DraftPRNextSteps(pr_number=42, branch_name="plan-my-feature-02-20")
        assert steps.checkout_and_implement == (
            'source "$(erk br co plan-my-feature-02-20 --script)" && erk implement --dangerous'
        )

    def test_prepare_uses_pr_number(self) -> None:
        steps = DraftPRNextSteps(pr_number=42, branch_name="plan-my-feature-02-20")
        assert steps.prepare == "erk br co --for-plan 42"

    def test_prepare_and_implement_uses_pr_number(self) -> None:
        steps = DraftPRNextSteps(pr_number=42, branch_name="plan-my-feature-02-20")
        assert steps.prepare_and_implement == (
            'source "$(erk br co --for-plan 42 --script)" && erk implement --dangerous'
        )

    def test_prepare_new_slot(self) -> None:
        steps = DraftPRNextSteps(pr_number=42, branch_name="plan-my-feature-02-20")
        assert steps.prepare_new_slot == "erk br co --new-slot --for-plan 42"

    def test_prepare_new_slot_and_implement(self) -> None:
        steps = DraftPRNextSteps(pr_number=42, branch_name="plan-my-feature-02-20")
        assert steps.prepare_new_slot_and_implement == (
            'source "$(erk br co --new-slot --for-plan 42 --script)" && erk implement --dangerous'
        )


class TestFormatNextStepsPlain:
    def test_contains_co_commands(self) -> None:
        output = format_next_steps_plain(99)
        assert "erk br co --for-plan 99" in output

    def test_contains_implement_command(self) -> None:
        output = format_next_steps_plain(99)
        assert 'source "$(erk br co --for-plan 99 --script)" && erk implement --dangerous' in output

    def test_does_not_contain_create(self) -> None:
        output = format_next_steps_plain(99)
        assert "erk br create" not in output


class TestFormatDraftPRNextStepsPlain:
    def test_contains_for_plan_command(self) -> None:
        output = format_draft_pr_next_steps_plain(42, branch_name="plan-my-feature-02-20")
        assert "erk br co --for-plan 42" in output

    def test_contains_pr_number_in_view_command(self) -> None:
        output = format_draft_pr_next_steps_plain(42, branch_name="plan-my-feature-02-20")
        assert "gh pr view 42 --web" in output

    def test_contains_implement_command(self) -> None:
        output = format_draft_pr_next_steps_plain(42, branch_name="plan-my-feature-02-20")
        assert 'source "$(erk br co --for-plan 42 --script)" && erk implement --dangerous' in output
