"""Tests for next_steps formatting functions."""

from erk_shared.output.next_steps import (
    DraftPRNextSteps,
    WorktreeContext,
    format_draft_pr_next_steps_plain,
    format_next_steps_plain,
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


class TestFormatDraftPRNextStepsPlain:
    def test_contains_branch_name_in_checkout_command(self) -> None:
        output = format_draft_pr_next_steps_plain(
            42, branch_name="plan-my-feature-02-20", worktree_context=None
        )
        assert "erk br co plan-my-feature-02-20" in output

    def test_contains_pr_number_in_view_command(self) -> None:
        output = format_draft_pr_next_steps_plain(
            42, branch_name="plan-my-feature-02-20", worktree_context=None
        )
        assert "gh pr view 42 --web" in output

    def test_does_not_contain_pr_number_in_checkout_command(self) -> None:
        output = format_draft_pr_next_steps_plain(
            42, branch_name="plan-my-feature-02-20", worktree_context=None
        )
        assert "erk br co 42" not in output

    def test_in_slot_shows_stack_here(self) -> None:
        wt_ctx = WorktreeContext(is_in_slot=True, slot_name="erk-slot-01")
        output = format_draft_pr_next_steps_plain(
            42, branch_name="plan-my-feature-02-20", worktree_context=wt_ctx
        )
        assert "Stack here:" in output
        assert "Advanced" in output
        assert "root worktree" in output
        assert "Local:" not in output


class TestFormatNextStepsPlain:
    def test_no_context_shows_local(self) -> None:
        output = format_next_steps_plain(100, worktree_context=None)
        assert "Local:" in output
        assert "Stack here" not in output

    def test_in_slot_shows_stack_here(self) -> None:
        wt_ctx = WorktreeContext(is_in_slot=True, slot_name="erk-slot-01")
        output = format_next_steps_plain(100, worktree_context=wt_ctx)
        assert "Stack here:" in output
        assert "Advanced" in output
        assert "root worktree" in output
        assert "Local:" not in output

    def test_in_slot_shows_stacking_prepare_label(self) -> None:
        wt_ctx = WorktreeContext(is_in_slot=True, slot_name="erk-slot-01")
        output = format_next_steps_plain(100, worktree_context=wt_ctx)
        assert "stacks in current worktree" in output


class TestWorktreeContext:
    def test_frozen(self) -> None:
        wt_ctx = WorktreeContext(is_in_slot=True, slot_name="erk-slot-01")
        assert wt_ctx.is_in_slot is True
        assert wt_ctx.slot_name == "erk-slot-01"

    def test_not_in_slot(self) -> None:
        wt_ctx = WorktreeContext(is_in_slot=False, slot_name=None)
        assert wt_ctx.is_in_slot is False
        assert wt_ctx.slot_name is None
