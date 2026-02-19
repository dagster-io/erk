"""Unit tests for next_steps formatting functions."""

from erk_shared.output.next_steps import format_next_steps_draft_pr, format_next_steps_plain


def test_format_next_steps_draft_pr_contains_view_pr() -> None:
    """Draft PR next steps should say 'View PR' not 'View Issue'."""
    result = format_next_steps_draft_pr(42)

    assert "View PR: gh pr view 42 --web" in result
    assert "View Issue" not in result


def test_format_next_steps_draft_pr_contains_submit_command() -> None:
    """Draft PR next steps should include submit slash command."""
    result = format_next_steps_draft_pr(42)

    assert "/erk:plan-submit" in result


def test_format_next_steps_draft_pr_contains_cli_commands() -> None:
    """Draft PR next steps should include CLI prepare/implement/submit commands."""
    result = format_next_steps_draft_pr(42)

    assert "erk prepare 42" in result
    assert "erk implement --dangerous" in result
    assert "erk plan submit 42" in result


def test_format_next_steps_plain_contains_view_issue() -> None:
    """Plain next steps should say 'View Issue'."""
    result = format_next_steps_plain(42)

    assert "View Issue: gh issue view 42 --web" in result
    assert "View PR" not in result


def test_format_next_steps_plain_contains_prepare_worktree() -> None:
    """Plain next steps should include prepare worktree slash command."""
    result = format_next_steps_plain(42)

    assert "/erk:prepare" in result
    assert "/erk:plan-submit" in result
