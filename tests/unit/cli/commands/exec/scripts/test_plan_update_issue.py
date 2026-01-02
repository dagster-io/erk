"""Unit tests for plan-update-issue command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_update_issue import plan_update_issue
from erk_shared.context import ErkContext
from erk_shared.extraction.claude_code_session_store import FakeClaudeCodeSessionStore
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueComment, IssueInfo
from erk_shared.github.metadata import format_plan_header_body


def _create_issue_with_plan_header(
    issue_number: int,
    plan_comment_id: int,
) -> IssueInfo:
    """Helper to create an IssueInfo with valid plan-header."""
    issue_body = format_plan_header_body(
        created_at="2025-01-01T00:00:00Z",
        created_by="testuser",
        plan_comment_id=plan_comment_id,
    )
    now = datetime.now(UTC)

    return IssueInfo(
        number=issue_number,
        title="Test Plan [erk-plan]",
        body=issue_body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{issue_number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_plan_update_issue_with_plan_file_success(tmp_path: Path) -> None:
    """Test successful update using --plan-file."""
    issue = _create_issue_with_plan_header(42, plan_comment_id=1000)
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={
            42: [
                IssueComment(
                    body="Original plan",
                    url="https://github.com/test/repo/issues/42#issuecomment-1000",
                    id=1000,
                    author="testuser",
                )
            ]
        },
    )

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Updated Plan\n\n- Step 1", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        plan_update_issue,
        ["--issue", "42", "--plan-file", str(plan_file), "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["comment_id"] == 1000


def test_plan_update_issue_with_session_id_success(tmp_path: Path) -> None:
    """Test successful update using --session-id."""
    issue = _create_issue_with_plan_header(42, plan_comment_id=1000)
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={
            42: [
                IssueComment(
                    body="Original plan",
                    url="https://github.com/test/repo/issues/42#issuecomment-1000",
                    id=1000,
                    author="testuser",
                )
            ]
        },
    )

    plan_content = "# Plan from Session\n\n- Implementation step"
    fake_store = FakeClaudeCodeSessionStore(
        plans={"session-plan": plan_content},
    )

    runner = CliRunner()
    result = runner.invoke(
        plan_update_issue,
        ["--issue", "42", "--session-id", "test-session", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42


def test_plan_update_issue_no_plan_content_error() -> None:
    """Test error when no plan content provided."""
    fake_gh = FakeGitHubIssues()
    fake_store = FakeClaudeCodeSessionStore()  # No plans

    runner = CliRunner()
    result = runner.invoke(
        plan_update_issue,
        ["--issue", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
        input="",  # Empty stdin
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan content provided" in output["error"]


def test_plan_update_issue_issue_not_found_error() -> None:
    """Test error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()  # No issues
    plan_content = "# New Plan\n\n- Step 1"
    fake_store = FakeClaudeCodeSessionStore(
        plans={"update-plan": plan_content},
    )

    runner = CliRunner()
    result = runner.invoke(
        plan_update_issue,
        ["--issue", "999", "--session-id", "test-session", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to get issue #999" in output["error"]


def test_plan_update_issue_display_format_success(tmp_path: Path) -> None:
    """Test display format output on success."""
    issue = _create_issue_with_plan_header(42, plan_comment_id=1000)
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={
            42: [
                IssueComment(
                    body="Original plan",
                    url="https://github.com/test/repo/issues/42#issuecomment-1000",
                    id=1000,
                    author="testuser",
                )
            ]
        },
    )

    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Updated Plan", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        plan_update_issue,
        ["--issue", "42", "--plan-file", str(plan_file), "--format", "display"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "Plan updated in issue #42" in result.output
    assert "Comment ID: 1000" in result.output


def test_plan_update_issue_display_format_error(tmp_path: Path) -> None:
    """Test display format output on error."""
    fake_gh = FakeGitHubIssues()  # No issues
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Updated Plan", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        plan_update_issue,
        ["--issue", "999", "--plan-file", str(plan_file), "--format", "display"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
        ),
    )

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_plan_update_issue_stdin_input(tmp_path: Path) -> None:
    """Test reading plan from stdin."""
    issue = _create_issue_with_plan_header(42, plan_comment_id=1000)
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={
            42: [
                IssueComment(
                    body="Original plan",
                    url="https://github.com/test/repo/issues/42#issuecomment-1000",
                    id=1000,
                    author="testuser",
                )
            ]
        },
    )
    fake_store = FakeClaudeCodeSessionStore()  # No plans in store

    runner = CliRunner()
    result = runner.invoke(
        plan_update_issue,
        ["--issue", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
            cwd=tmp_path,
        ),
        input="# Plan from Stdin\n\n- Step 1",
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify the plan content was used
    assert len(fake_gh.updated_comments) == 1
    _, body = fake_gh.updated_comments[0]
    assert "Plan from Stdin" in body


def test_plan_update_issue_requires_issue_number() -> None:
    """Test that --issue is required."""
    runner = CliRunner()
    result = runner.invoke(
        plan_update_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(),
    )

    assert result.exit_code != 0
    assert "Missing option '--issue'" in result.output
