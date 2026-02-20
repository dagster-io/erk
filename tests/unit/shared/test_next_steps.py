"""Tests for next_steps formatting functions."""

from erk_shared.output.next_steps import (
    DraftPRNextSteps,
    format_draft_pr_next_steps_plain,
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
            "erk br co plan-my-feature-02-20 && erk implement --dangerous"
        )


class TestFormatDraftPRNextStepsPlain:
    def test_contains_branch_name_in_checkout_command(self) -> None:
        output = format_draft_pr_next_steps_plain(42, branch_name="plan-my-feature-02-20")
        assert "erk br co plan-my-feature-02-20" in output

    def test_contains_pr_number_in_view_command(self) -> None:
        output = format_draft_pr_next_steps_plain(42, branch_name="plan-my-feature-02-20")
        assert "gh pr view 42 --web" in output

    def test_does_not_contain_pr_number_in_checkout_command(self) -> None:
        output = format_draft_pr_next_steps_plain(42, branch_name="plan-my-feature-02-20")
        assert "erk br co 42" not in output
