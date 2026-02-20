"""Unit tests for plan-migrate-to-draft-pr command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_migrate_to_draft_pr import plan_migrate_to_draft_pr
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.plan_header import (
    format_plan_content_comment,
    format_plan_header_body,
)

_NOW = datetime(2025, 1, 15, 14, 30, tzinfo=UTC)

PLAN_CONTENT = """# Fix authentication bug

This plan describes fixing a bug in the auth flow.

- Step 1: Identify the root cause
- Step 2: Write a failing test
- Step 3: Implement the fix
"""


def _make_issue(
    *,
    number: int = 42,
    title: str = "Fix authentication bug",
    body: str = PLAN_CONTENT,
    labels: list[str] | None = None,
    state: str = "OPEN",
) -> IssueInfo:
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state=state,
        url=f"https://github.com/org/repo/issues/{number}",
        labels=labels or ["erk-plan"],
        assignees=[],
        created_at=_NOW,
        updated_at=_NOW,
        author="testuser",
    )


def _make_context(
    *,
    tmp_path: Path,
    issue: IssueInfo | None = None,
    fake_git: FakeGit | None = None,
    comments: dict[int, list[str]] | None = None,
) -> object:
    """Build test context with a pre-seeded issue."""
    issues_dict: dict[int, IssueInfo] = {issue.number: issue} if issue is not None else {}

    fake_issues = FakeGitHubIssues(
        issues=issues_dict,
        comments=comments or {},
    )
    fake_github = FakeGitHub(issues_gateway=fake_issues)

    if fake_git is None:
        fake_git = FakeGit(current_branches={tmp_path: "main"})

    return context_for_test(
        github_issues=fake_issues,
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
    )


def test_migrate_success_json(tmp_path: Path) -> None:
    """Happy path: issue migrated, returns JSON with pr_number and closes issue."""
    issue = _make_issue()
    ctx = _make_context(tmp_path=tmp_path, issue=issue)
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["original_issue_number"] == 42
    assert "pr_number" in output
    assert "pr_url" in output
    assert output["branch_name"].startswith("plan-")


def test_migrate_success_display(tmp_path: Path) -> None:
    """Display format shows human-readable migration summary."""
    issue = _make_issue()
    ctx = _make_context(tmp_path=tmp_path, issue=issue)
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--format", "display"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "42" in result.output
    assert "Fix authentication bug" in result.output


def test_migrate_dry_run(tmp_path: Path) -> None:
    """--dry-run outputs intent but does not create draft PR or close issue."""
    issue = _make_issue()
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = context_for_test(
        github_issues=fake_issues,
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--dry-run", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["dry_run"] is True
    assert output["original_issue_number"] == 42
    assert "branch_name" in output
    # Issue should NOT be closed
    assert 42 not in fake_issues._closed_issues
    # No PRs should be created
    assert len(fake_github._created_prs) == 0


def test_migrate_issue_not_found(tmp_path: Path) -> None:
    """Returns error JSON when issue does not exist."""
    ctx = _make_context(tmp_path=tmp_path, issue=None)
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["999", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"


def test_migrate_not_an_erk_plan(tmp_path: Path) -> None:
    """Returns error when issue lacks erk-plan label."""
    issue = _make_issue(labels=["bug", "enhancement"])
    ctx = _make_context(tmp_path=tmp_path, issue=issue)
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "not_an_erk_plan"


def test_migrate_preserves_objective_id(tmp_path: Path) -> None:
    """objective_id from plan-header flows through to draft PR metadata."""
    header_body = format_plan_header_body(
        created_at="2025-01-15T00:00:00Z",
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
        objective_issue=99,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )
    plan_comment = format_plan_content_comment(PLAN_CONTENT)
    issue = _make_issue(body=header_body)
    ctx = _make_context(
        tmp_path=tmp_path,
        issue=issue,
        comments={42: [plan_comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    # Branch name should include objective slug
    assert "plan-" in output["branch_name"]


def test_migrate_preserves_erk_learn_label(tmp_path: Path) -> None:
    """erk-learn label on original issue is transferred to the draft PR."""
    issue = _make_issue(labels=["erk-plan", "erk-learn"])
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = context_for_test(
        github_issues=fake_issues,
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True


def test_migrate_closes_original_issue(tmp_path: Path) -> None:
    """Original issue is closed after successful migration."""
    issue = _make_issue()
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = context_for_test(
        github_issues=fake_issues,
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert 42 in fake_issues._closed_issues


def test_migrate_preserves_operational_metadata(tmp_path: Path) -> None:
    """Operational metadata (dispatch, impl, session) carries over to draft PR."""
    header_body = format_plan_header_body(
        created_at="2025-01-15T00:00:00Z",
        created_by="testuser",
        worktree_name="erk",
        branch_name="P42-fix-auth-01-15-0000",
        plan_comment_id=None,
        last_dispatched_run_id="22119449865",
        last_dispatched_node_id="WFR_kwLOPxC3hc8AAAAFJmwFCQ",
        last_dispatched_at="2025-01-15T10:00:00",
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at="2025-01-15T12:00:00+00:00",
        last_remote_impl_run_id="22117566993",
        last_remote_impl_session_id="42215c6c-6b4c-4482-a711-bf2f09b754d5",
        source_repo=None,
        objective_issue=99,
        created_from_session="original-session-id",
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )
    plan_comment = format_plan_content_comment(PLAN_CONTENT)
    issue = _make_issue(body=header_body)
    fake_issues = FakeGitHubIssues(issues={42: issue}, comments={42: [plan_comment]})
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = context_for_test(
        github_issues=fake_issues,
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    pr_number = output["pr_number"]

    # Check the final PR body has the operational metadata
    final_body = fake_github._pr_details[pr_number].body
    assert "22119449865" in final_body  # last_dispatched_run_id
    assert "WFR_kwLOPxC3hc8AAAAFJmwFCQ" in final_body  # last_dispatched_node_id
    assert "22117566993" in final_body  # last_remote_impl_run_id
    assert "42215c6c-6b4c-4482-a711-bf2f09b754d5" in final_body  # last_remote_impl_session_id
    assert "erk" in final_body  # worktree_name


def test_migrate_posts_migration_comment(tmp_path: Path) -> None:
    """Migration notice comment is posted to original issue."""
    issue = _make_issue()
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub(issues_gateway=fake_issues)
    fake_git = FakeGit(current_branches={tmp_path: "main"})
    ctx = context_for_test(
        github_issues=fake_issues,
        github=fake_github,
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_migrate_to_draft_pr,
        ["42", "--format", "json"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    # A comment should have been posted to issue 42
    comments_on_42 = [
        body for (issue_num, body, _) in fake_issues.added_comments if issue_num == 42
    ]
    assert len(comments_on_42) > 0
    assert "Migrated to draft PR" in comments_on_42[0]
