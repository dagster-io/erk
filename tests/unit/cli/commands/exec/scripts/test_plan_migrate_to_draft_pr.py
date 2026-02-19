"""Unit tests for plan-migrate-to-draft-pr command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_migrate_to_draft_pr import (
    plan_migrate_to_draft_pr,
)
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.plan_header import format_plan_header_body

PLAN_CONTENT = """# Migrate Auth System

This plan describes the migration of the auth system.

- Step 1: Update the auth module
- Step 2: Add new token handling
- Step 3: Write integration tests"""

NOW = datetime(2025, 1, 15, 14, 30, tzinfo=UTC)


def _make_issue(
    *,
    number: int,
    title: str,
    body: str,
    labels: list[str],
    state: str = "OPEN",
) -> IssueInfo:
    """Create an IssueInfo for testing.

    Args:
        number: Issue number
        title: Issue title
        body: Issue body
        labels: Issue labels
        state: Issue state (OPEN or CLOSED)
    """
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=labels,
        assignees=[],
        created_at=NOW,
        updated_at=NOW,
        author="testuser",
    )


def _make_issue_with_metadata(
    *,
    number: int,
    title: str,
    plan_content: str,
    labels: list[str],
    objective_issue: int | None,
    created_from_session: str | None,
) -> IssueInfo:
    """Create an IssueInfo with plan-header metadata block.

    Args:
        number: Issue number
        title: Issue title
        plan_content: Plan content (placed in comments, not body)
        labels: Issue labels
        objective_issue: Optional objective issue number
        created_from_session: Optional session ID
    """
    body = format_plan_header_body(
        created_at=NOW.isoformat(),
        created_by="testuser",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=objective_issue,
        created_from_session=created_from_session,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
    )
    return _make_issue(
        number=number,
        title=title,
        body=body,
        labels=labels,
    )


def _build_context(
    *,
    tmp_path: Path,
    fake_issues: FakeGitHubIssues,
    fake_github: FakeGitHub | None = None,
    fake_git: FakeGit | None = None,
) -> ErkContext:
    """Build test context with pre-configured fakes.

    Args:
        tmp_path: Pytest tmp_path fixture
        fake_issues: Pre-configured FakeGitHubIssues with test issues
        fake_github: Optional FakeGitHub (created from issues if None)
        fake_git: Optional FakeGit (defaults to main branch)
    """
    if fake_git is None:
        fake_git = FakeGit(current_branches={tmp_path: "main"})
    if fake_github is None:
        fake_github = FakeGitHub(issues_gateway=fake_issues)

    return context_for_test(
        github=fake_github,
        github_issues=fake_issues,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
    )


def test_migrate_success_json(tmp_path: Path) -> None:
    """Happy path: migrate issue to draft PR, JSON output."""
    issue = _make_issue(
        number=42,
        title="Migrate Auth System",
        body=PLAN_CONTENT,
        labels=["erk-plan"],
    )
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = _build_context(tmp_path=tmp_path, fake_issues=fake_issues, fake_github=fake_github)
    runner = CliRunner()

    result = runner.invoke(plan_migrate_to_draft_pr, ["42", "--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["original_issue_number"] == 42
    assert "pr_number" in output
    assert "pr_url" in output
    assert output["branch_name"].startswith("plan-")
    # Issue should be closed
    assert 42 in fake_issues.closed_issues
    # Comment should be added
    assert len(fake_issues.added_comments) == 1
    assert "Migrated to draft PR" in fake_issues.added_comments[0][1]
    # Draft PR should be created
    assert len(fake_github.created_prs) == 1


def test_migrate_success_display(tmp_path: Path) -> None:
    """Display format shows human-readable output."""
    issue = _make_issue(
        number=42,
        title="Migrate Auth System",
        body=PLAN_CONTENT,
        labels=["erk-plan"],
    )
    fake_issues = FakeGitHubIssues(issues={42: issue})
    ctx = _build_context(tmp_path=tmp_path, fake_issues=fake_issues)
    runner = CliRunner()

    result = runner.invoke(plan_migrate_to_draft_pr, ["42", "--format", "display"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Migrated issue #42 to draft PR" in result.output
    assert "Title: Migrate Auth System" in result.output
    assert "Branch: plan-" in result.output


def test_migrate_dry_run(tmp_path: Path) -> None:
    """--dry-run outputs intent but does not create PR or close issue."""
    issue = _make_issue(
        number=42,
        title="Migrate Auth System",
        body=PLAN_CONTENT,
        labels=["erk-plan"],
    )
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = _build_context(tmp_path=tmp_path, fake_issues=fake_issues, fake_github=fake_github)
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr, ["42", "--dry-run", "--format", "json"], obj=ctx
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["dry_run"] is True
    assert output["original_issue_number"] == 42
    assert output["title"] == "Migrate Auth System"
    assert output["branch_name"].startswith("plan-")
    # No mutations should have occurred
    assert 42 not in fake_issues.closed_issues
    assert len(fake_issues.added_comments) == 0
    assert len(fake_github.created_prs) == 0


def test_migrate_issue_not_found(tmp_path: Path) -> None:
    """Returns error JSON when issue doesn't exist."""
    fake_issues = FakeGitHubIssues()
    ctx = _build_context(tmp_path=tmp_path, fake_issues=fake_issues)
    runner = CliRunner()

    result = runner.invoke(plan_migrate_to_draft_pr, ["999", "--format", "json"], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "#999" in output["error"]


def test_migrate_not_an_erk_plan(tmp_path: Path) -> None:
    """Returns error when issue lacks erk-plan label."""
    issue = _make_issue(
        number=42,
        title="Not a Plan",
        body="Just a regular issue",
        labels=["bug"],
    )
    fake_issues = FakeGitHubIssues(issues={42: issue})
    ctx = _build_context(tmp_path=tmp_path, fake_issues=fake_issues)
    runner = CliRunner()

    result = runner.invoke(plan_migrate_to_draft_pr, ["42", "--format", "json"], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "not an erk-plan" in output["error"]


def test_migrate_preserves_objective_id(tmp_path: Path) -> None:
    """objective_id flows through to draft PR metadata."""
    issue = _make_issue_with_metadata(
        number=42,
        title="Auth Migration",
        plan_content=PLAN_CONTENT,
        labels=["erk-plan"],
        objective_issue=100,
        created_from_session=None,
    )
    fake_issues = FakeGitHubIssues(
        issues={42: issue},
        comments={42: [PLAN_CONTENT]},
    )
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = _build_context(tmp_path=tmp_path, fake_issues=fake_issues, fake_github=fake_github)
    runner = CliRunner()

    result = runner.invoke(plan_migrate_to_draft_pr, ["42", "--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # Branch should include objective ID
    assert "O100" in output["branch_name"]


def test_migrate_preserves_erk_learn_label(tmp_path: Path) -> None:
    """erk-learn label transferred to draft PR."""
    issue = _make_issue(
        number=42,
        title="Learn Plan",
        body=PLAN_CONTENT,
        labels=["erk-plan", "erk-learn"],
    )
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    ctx = _build_context(tmp_path=tmp_path, fake_issues=fake_issues, fake_github=fake_github)
    runner = CliRunner()

    result = runner.invoke(plan_migrate_to_draft_pr, ["42", "--format", "json"], obj=ctx)

    assert result.exit_code == 0, f"Failed: {result.output}"
    # Verify erk-learn label was added to the PR
    assert len(fake_github.added_labels) > 0
    pr_number = json.loads(result.output)["pr_number"]
    labels_for_pr = [label for num, label in fake_github.added_labels if num == pr_number]
    assert "erk-learn" in labels_for_pr
