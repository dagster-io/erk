"""Tests for PR creation during submit."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import _strip_plan_markers, submit_cmd
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_strip_plan_markers() -> None:
    """Test _strip_plan_markers removes 'Plan:' prefix and '[erk-plan]' suffix from titles."""
    # Strip [erk-plan] suffix only
    assert _strip_plan_markers("Implement feature X [erk-plan]") == "Implement feature X"
    assert _strip_plan_markers("Implement feature X") == "Implement feature X"
    assert _strip_plan_markers(" [erk-plan]") == ""
    assert _strip_plan_markers("Planning [erk-plan] ahead") == "Planning [erk-plan] ahead"
    # Strip Plan: prefix only
    assert _strip_plan_markers("Plan: Implement feature X") == "Implement feature X"
    assert _strip_plan_markers("Plan: Already has prefix") == "Already has prefix"
    # Strip both Plan: prefix and [erk-plan] suffix
    assert _strip_plan_markers("Plan: Implement feature X [erk-plan]") == "Implement feature X"
    # No stripping needed
    assert _strip_plan_markers("Regular title") == "Regular title"


def test_submit_strips_plan_markers_from_pr_title(tmp_path: Path) -> None:
    """Test submit strips plan markers from issue title when creating PR."""
    # Plan with "[erk-plan]" suffix (standard format for erk-plan issues)
    plan = create_plan("123", "Implement feature X [erk-plan]")
    ctx, _, fake_github, _, _, _ = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify PR was created with stripped title (no "[erk-plan]" suffix)
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert title == "Implement feature X"  # NOT "Implement feature X [erk-plan]"

    # Verify PR body was updated with checkout footer (includes && erk pr sync --dangerous)
    assert len(fake_github.updated_pr_bodies) == 1
    pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert "erk pr checkout 999 && erk pr sync --dangerous" in updated_body


def test_submit_includes_closes_issue_in_pr_body(tmp_path: Path) -> None:
    """Test submit includes 'Closes #N' in INITIAL PR body to enable willCloseTarget.

    GitHub's willCloseTarget API field is set at PR creation time and is NOT updated
    when the PR body is edited afterward. This test verifies that 'Closes #N' is
    included in the body passed to create_pr(), not just added via update_pr_body().
    """
    plan = create_plan("123", "Implement feature X")
    ctx, _, fake_github, _, _, _ = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # CRITICAL: Verify "Closes #123" is in the INITIAL body passed to create_pr()
    # GitHub's willCloseTarget API field is set at creation time and NOT updated afterward
    assert len(fake_github.created_prs) == 1
    branch, title, initial_body, base, draft = fake_github.created_prs[0]
    assert "Closes #123" in initial_body, (
        "Closes #123 must be in initial PR body for GitHub's willCloseTarget to work"
    )

    # Verify PR body was also updated (to add checkout command footer)
    assert len(fake_github.updated_pr_bodies) == 1
    pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert "Closes #123" in updated_body
    assert "erk pr checkout 999 && erk pr sync --dangerous" in updated_body
