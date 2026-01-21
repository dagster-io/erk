"""Unit tests for update-plan-remote-session command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_plan_remote_session import (
    update_plan_remote_session,
)
from erk_shared.context.context import ErkContext
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata.plan_header import (
    find_metadata_block,
    format_plan_header_body,
)


def _make_plan_issue(
    number: int,
    title: str,
) -> IssueInfo:
    """Create a test IssueInfo with plan-header metadata."""
    now = datetime.now(UTC)
    body = format_plan_header_body(
        created_at=now.isoformat(),
        created_by="testuser",
        worktree_name=None,
        branch_name="test-branch",
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
        objective_issue=None,
        created_from_session=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _make_non_plan_issue(
    number: int,
    title: str,
) -> IssueInfo:
    """Create a test IssueInfo without plan-header metadata."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body="Some issue body without plan-header",
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=[],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_update_plan_remote_session_success(tmp_path: Path) -> None:
    """Test successful update with valid inputs."""
    issue = _make_plan_issue(42, "Test Plan Issue")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_plan_remote_session,
        [
            "--issue-number",
            "42",
            "--run-id",
            "12345678",
            "--session-id",
            "test-session-abc",
        ],
        obj=ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42

    # Verify the body was actually updated
    assert len(fake_gh.updated_bodies) == 1
    updated_number, updated_body = fake_gh.updated_bodies[0]
    assert updated_number == 42

    # Verify the plan-header block was updated with remote session info
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["last_remote_impl_run_id"] == "12345678"
    assert block.data["last_remote_impl_session_id"] == "test-session-abc"
    assert "last_remote_impl_at" in block.data


def test_update_plan_remote_session_issue_not_found(tmp_path: Path) -> None:
    """Test graceful error when issue does not exist."""
    fake_gh = FakeGitHubIssues(issues={})  # Empty issues dict
    runner = CliRunner()

    result = runner.invoke(
        update_plan_remote_session,
        [
            "--issue-number",
            "999",
            "--run-id",
            "12345",
            "--session-id",
            "test-session",
        ],
        obj=ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path),
    )

    # Should exit 0 for graceful degradation
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "issue-not-found"
    assert "999" in output["message"]


def test_update_plan_remote_session_missing_plan_header(tmp_path: Path) -> None:
    """Test graceful error when issue lacks plan-header block."""
    issue = _make_non_plan_issue(42, "Regular Issue")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_plan_remote_session,
        [
            "--issue-number",
            "42",
            "--run-id",
            "12345",
            "--session-id",
            "test-session",
        ],
        obj=ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path),
    )

    # Should exit 0 for graceful degradation
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no-plan-header-block"


def test_update_plan_remote_session_preserves_existing_fields(tmp_path: Path) -> None:
    """Test that updating remote session preserves other plan-header fields."""
    now = datetime.now(UTC)
    body = format_plan_header_body(
        created_at=now.isoformat(),
        created_by="original-user",
        worktree_name="my-worktree",
        branch_name="feature-branch",
        plan_comment_id=None,
        last_dispatched_run_id="old-dispatch-123",
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at="2024-01-15T10:00:00Z",
        last_local_impl_event="ended",
        last_local_impl_session="local-session-xyz",
        last_local_impl_user="localuser",
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo="owner/repo",
        objective_issue=100,
        created_from_session="create-session-123",
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
    )
    issue = IssueInfo(
        number=42,
        title="Test Plan",
        body=body,
        state="OPEN",
        url="https://github.com/test/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_plan_remote_session,
        [
            "--issue-number",
            "42",
            "--run-id",
            "new-run-999",
            "--session-id",
            "new-session-xyz",
        ],
        obj=ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"

    _, updated_body = fake_gh.updated_bodies[0]
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None

    # New remote session fields
    assert block.data["last_remote_impl_run_id"] == "new-run-999"
    assert block.data["last_remote_impl_session_id"] == "new-session-xyz"

    # Preserved fields
    assert block.data["created_by"] == "original-user"
    assert block.data["worktree_name"] == "my-worktree"
    assert block.data["branch_name"] == "feature-branch"
    assert block.data["last_dispatched_run_id"] == "old-dispatch-123"
    assert block.data["last_local_impl_at"] == "2024-01-15T10:00:00Z"
    assert block.data["last_local_impl_event"] == "ended"
    assert block.data["last_local_impl_session"] == "local-session-xyz"
    assert block.data["last_local_impl_user"] == "localuser"
    assert block.data["source_repo"] == "owner/repo"
    assert block.data["objective_issue"] == 100
    assert block.data["created_from_session"] == "create-session-123"
