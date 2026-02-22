"""Unit tests for upload-session command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.upload_session import upload_session
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_plan_issue(*, number: int) -> IssueInfo:
    """Create a test IssueInfo with plan-header metadata."""
    now = datetime.now(UTC)
    body = format_plan_header_body_for_test(
        created_at="2024-01-15T10:30:00Z",
        created_by="testuser",
        branch_name="test-branch",
    )
    return IssueInfo(
        number=number,
        title="Test Plan",
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _write_session_file(tmp_path: Path) -> Path:
    """Create a test session JSONL file."""
    session_file = tmp_path / "session.jsonl"
    session_file.write_text('{"type": "test"}\n', encoding="utf-8")
    return session_file


def test_upload_session_no_plan_id(tmp_path: Path) -> None:
    """Error when --plan-id not provided (required for branch-based upload)."""
    session_file = _write_session_file(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        upload_session,
        [
            "--session-file",
            str(session_file),
            "--session-id",
            "test-session-abc",
            "--source",
            "local",
        ],
        obj=ErkContext.for_test(cwd=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "--plan-id is required" in output["error"]


def test_upload_session_branch_created(tmp_path: Path) -> None:
    """Session branch created and pushed when --plan-id provided."""
    session_file = _write_session_file(tmp_path)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    fake_git = FakeGit(
        current_branches={repo_root: "plan/my-feature"},
        local_branches={repo_root: []},
    )
    runner = CliRunner()

    result = runner.invoke(
        upload_session,
        [
            "--session-file",
            str(session_file),
            "--session-id",
            "test-session-abc",
            "--source",
            "local",
            "--plan-id",
            "42",
        ],
        obj=ErkContext.for_test(git=fake_git, repo_root=repo_root, cwd=repo_root),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_branch"] == "async-learn/42"
    assert output["session_id"] == "test-session-abc"
    assert output["plan_id"] == 42

    # Verify branch was created, files committed via plumbing, and pushed
    assert any(b == "async-learn/42" for _, b, _, _ in fake_git.created_branches)
    assert len(fake_git.branch_commits) == 1
    bc = fake_git.branch_commits[0]
    assert bc.branch == "async-learn/42"
    assert ".erk/session/test-session-abc.jsonl" in bc.files
    assert bc.message == "Session test-session-abc for plan #42"
    assert any(pb.branch == "async-learn/42" and pb.force for pb in fake_git.pushed_branches)


def test_upload_session_with_issue_update(tmp_path: Path) -> None:
    """Session branch created and issue metadata updated when --plan-id provided."""
    session_file = _write_session_file(tmp_path)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    issue = _make_plan_issue(number=42)
    fake_gh_issues = FakeGitHubIssues(issues={42: issue})
    fake_git = FakeGit(
        current_branches={repo_root: "plan/my-feature"},
        local_branches={repo_root: []},
    )
    runner = CliRunner()

    result = runner.invoke(
        upload_session,
        [
            "--session-file",
            str(session_file),
            "--session-id",
            "test-session-xyz",
            "--source",
            "remote",
            "--plan-id",
            "42",
        ],
        obj=ErkContext.for_test(
            github_issues=fake_gh_issues,
            git=fake_git,
            repo_root=repo_root,
            cwd=repo_root,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_id"] == 42
    assert output["issue_updated"] is True

    # Verify the plan-header was updated with session branch info
    assert len(fake_gh_issues.updated_bodies) == 1
    _, updated_body = fake_gh_issues.updated_bodies[0]
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data["last_session_branch"] == "async-learn/42"
    assert block.data["last_session_id"] == "test-session-xyz"
    assert block.data["last_session_source"] == "remote"
    assert "last_session_at" in block.data


def test_upload_session_plan_not_found(tmp_path: Path) -> None:
    """Partial success: branch created but issue update fails for missing issue."""
    session_file = _write_session_file(tmp_path)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    fake_gh_issues = FakeGitHubIssues(issues={})
    fake_git = FakeGit(
        current_branches={repo_root: "plan/my-feature"},
        local_branches={repo_root: []},
    )
    runner = CliRunner()

    result = runner.invoke(
        upload_session,
        [
            "--session-file",
            str(session_file),
            "--session-id",
            "test-session-xyz",
            "--source",
            "local",
            "--plan-id",
            "999",
        ],
        obj=ErkContext.for_test(
            github_issues=fake_gh_issues,
            git=fake_git,
            repo_root=repo_root,
            cwd=repo_root,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_updated"] is False
    assert "issue_update_error" in output
    # Branch was still created
    assert output["session_branch"] == "async-learn/999"
