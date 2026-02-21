"""Tests for next_steps formatting."""

from erk_shared.output.next_steps import (
    DraftPRNextSteps,
    WorktreeContext,
    format_draft_pr_next_steps_plain,
    format_next_steps_plain,
)


def test_draft_pr_next_steps_constructs_with_both_params() -> None:
    """DraftPRNextSteps constructs correctly with pr_number and branch_name."""
    s = DraftPRNextSteps(pr_number=42, branch_name="plan-feature-foo")
    assert s.pr_number == 42
    assert s.branch_name == "plan-feature-foo"


def test_draft_pr_next_steps_checkout_and_implement_uses_branch_name() -> None:
    """checkout_and_implement uses branch_name, not pr_number."""
    s = DraftPRNextSteps(pr_number=42, branch_name="plan-feature-foo")
    assert "plan-feature-foo" in s.checkout_and_implement
    assert "42" not in s.checkout_and_implement


def test_format_draft_pr_next_steps_plain_contains_branch_name() -> None:
    """format_draft_pr_next_steps_plain includes branch name in checkout command."""
    output = format_draft_pr_next_steps_plain(
        42, branch_name="plan-feature-foo", worktree_context=None
    )
    assert "plan-feature-foo" in output
    assert 'source "$(erk br co' in output


def test_format_next_steps_plain_no_context_shows_local() -> None:
    """format_next_steps_plain without worktree context shows 'Local' label."""
    output = format_next_steps_plain(100, worktree_context=None)
    assert "Local:" in output
    assert "Stack here" not in output
    assert "Advanced" not in output


def test_format_next_steps_plain_in_slot_shows_stack_here() -> None:
    """format_next_steps_plain in slot shows 'Stack here' and 'Advanced' section."""
    wt_ctx = WorktreeContext(is_in_slot=True, slot_name="erk-slot-01")
    output = format_next_steps_plain(100, worktree_context=wt_ctx)
    assert "Stack here:" in output
    assert "Advanced" in output
    assert "root worktree" in output
    assert "Local:" not in output


def test_format_next_steps_plain_in_slot_shows_prepare_label() -> None:
    """format_next_steps_plain in slot shows stacking label for prepare."""
    wt_ctx = WorktreeContext(is_in_slot=True, slot_name="erk-slot-01")
    output = format_next_steps_plain(100, worktree_context=wt_ctx)
    assert "stacks in current worktree" in output


def test_format_draft_pr_next_steps_plain_no_context_shows_local() -> None:
    """format_draft_pr_next_steps_plain without context shows 'Local' label."""
    output = format_draft_pr_next_steps_plain(
        42, branch_name="plan-feature-foo", worktree_context=None
    )
    assert "Local:" in output
    assert "Stack here" not in output
    assert "Advanced" not in output


def test_format_draft_pr_next_steps_plain_in_slot_shows_stack_here() -> None:
    """format_draft_pr_next_steps_plain in slot shows 'Stack here' and 'Advanced'."""
    wt_ctx = WorktreeContext(is_in_slot=True, slot_name="erk-slot-01")
    output = format_draft_pr_next_steps_plain(
        42, branch_name="plan-feature-foo", worktree_context=wt_ctx
    )
    assert "Stack here:" in output
    assert "Advanced" in output
    assert "root worktree" in output
    assert "Local:" not in output
