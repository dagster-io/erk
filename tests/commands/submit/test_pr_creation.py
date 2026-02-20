"""Tests for PR creation during submit."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import _add_planned_prefix, _strip_plan_markers, submit_cmd
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_strip_plan_markers() -> None:
    """Test _strip_plan_markers removes '[erk-plan]' prefix and 'Plan:' prefix from titles."""
    # Strip [erk-plan] prefix only
    assert _strip_plan_markers("[erk-plan] Implement feature X") == "Implement feature X"
    assert _strip_plan_markers("Implement feature X") == "Implement feature X"
    assert _strip_plan_markers("[erk-plan] ") == ""
    assert _strip_plan_markers("Planning [erk-plan] ahead") == "Planning [erk-plan] ahead"
    # Strip Plan: prefix only
    assert _strip_plan_markers("Plan: Implement feature X") == "Implement feature X"
    assert _strip_plan_markers("Plan: Already has prefix") == "Already has prefix"
    # Strip both [erk-plan] prefix and Plan: prefix
    assert _strip_plan_markers("[erk-plan] Plan: Implement feature X") == "Implement feature X"
    # No stripping needed
    assert _strip_plan_markers("Regular title") == "Regular title"


def test_submit_strips_plan_markers_from_pr_title(tmp_path: Path) -> None:
    """Test submit strips plan markers and adds planned/ prefix when creating PR."""
    # Plan with "[erk-plan]" prefix (standard format for erk-plan issues)
    plan = create_plan("123", "[erk-plan] Implement feature X")
    ctx, _, fake_github, _, _, _ = setup_submit_context(tmp_path, {"123": plan})

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify PR was created with stripped title and planned/ prefix
    assert len(fake_github.created_prs) == 1
    branch_name, title, body, base, draft = fake_github.created_prs[0]
    assert title == "planned/Implement feature X"  # Stripped AND prefixed with planned/

    # Verify PR body was updated: first with checkout footer, then with workflow run link
    assert len(fake_github.updated_pr_bodies) == 2
    pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert 'source "$(erk pr checkout 999 --script)" && erk pr sync --dangerous' in updated_body
    _, workflow_body = fake_github.updated_pr_bodies[1]
    assert "Workflow run:" in workflow_body


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

    # Verify PR body was updated: first with checkout footer, then with workflow run link
    assert len(fake_github.updated_pr_bodies) == 2
    pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert pr_number == 999  # FakeGitHub returns 999 for created PRs
    assert "Closes #123" in updated_body
    assert 'source "$(erk pr checkout 999 --script)" && erk pr sync --dangerous' in updated_body
    _, workflow_body = fake_github.updated_pr_bodies[1]
    assert "Workflow run:" in workflow_body


def test_planned_prefix_idempotent() -> None:
    """Test _add_planned_prefix is idempotent and doesn't double-prefix."""
    # Single application
    assert _add_planned_prefix("Implement feature X") == "planned/Implement feature X"

    # Double application should not double-prefix
    once = _add_planned_prefix("Implement feature X")
    twice = _add_planned_prefix(once)
    assert once == twice
    assert twice == "planned/Implement feature X"
    assert twice.count("planned/") == 1  # Only one prefix


def test_planned_prefix_added_to_pr_title() -> None:
    """Test planned/ prefix is added to PR titles from plan-originated submissions."""
    # Test various title formats
    assert _add_planned_prefix("Update docs") == "planned/Update docs"
    assert _add_planned_prefix("Fix bug in authentication") == "planned/Fix bug in authentication"
    assert _add_planned_prefix("") == "planned/"  # Edge case: empty title

    # Verify it's idempotent for already-prefixed titles
    assert _add_planned_prefix("planned/Already prefixed") == "planned/Already prefixed"
