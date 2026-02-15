"""Unit tests for upload-session command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.upload_session import upload_session
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
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


def test_upload_session_gist_only(tmp_path: Path) -> None:
    """Gist created without issue update when no --issue-number."""
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

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert "gist_id" in output
    assert "gist_url" in output
    assert "raw_url" in output
    assert output["session_id"] == "test-session-abc"
    assert "issue_number" not in output
    assert "issue_updated" not in output


def test_upload_session_with_issue_update(tmp_path: Path) -> None:
    """Gist created and issue metadata updated when --issue-number provided."""
    session_file = _write_session_file(tmp_path)
    issue = _make_plan_issue(number=42)
    fake_gh = FakeGitHubIssues(issues={42: issue})
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
            "--issue-number",
            "42",
        ],
        obj=ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["issue_updated"] is True

    # Verify the plan-header was updated with session gist info
    assert len(fake_gh.updated_bodies) == 1
    _, updated_body = fake_gh.updated_bodies[0]
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert "last_session_gist_url" in block.data
    assert "last_session_gist_id" in block.data
    assert block.data["last_session_id"] == "test-session-xyz"
    assert block.data["last_session_source"] == "remote"
    assert "last_session_at" in block.data


def test_upload_session_issue_not_found(tmp_path: Path) -> None:
    """Partial success: gist created but issue update fails for missing issue."""
    session_file = _write_session_file(tmp_path)
    fake_gh = FakeGitHubIssues(issues={})
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
            "--issue-number",
            "999",
        ],
        obj=ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_updated"] is False
    assert "issue_update_error" in output
    # Gist was still created
    assert "gist_id" in output
    assert "gist_url" in output


def test_upload_session_gist_failure(tmp_path: Path) -> None:
    """Error when gist creation fails."""
    session_file = _write_session_file(tmp_path)
    fake_github = FakeGitHub(gist_create_error="API rate limit exceeded")
    runner = CliRunner()

    result = runner.invoke(
        upload_session,
        [
            "--session-file",
            str(session_file),
            "--session-id",
            "test-session-fail",
            "--source",
            "local",
        ],
        obj=ErkContext.for_test(github=fake_github, cwd=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "rate limit" in output["error"].lower()
