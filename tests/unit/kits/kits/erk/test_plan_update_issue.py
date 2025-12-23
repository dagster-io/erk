"""Unit tests for plan-update-issue command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.plan_update_issue import (
    plan_update_issue,
)
from erk_shared.context import ErkContext
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
)
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueComment, IssueInfo


def _create_plan_issue(
    issue_number: int = 1,
    title: str = "Test Plan [erk-plan]",
    comment_body: str = "<!-- plan-body -->\n# Original Plan\n<!-- /plan-body -->",
) -> tuple[FakeGitHubIssues, IssueInfo]:
    """Helper to create a FakeGitHubIssues with a plan issue and comment."""
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=issue_number,
        title=title,
        body="<!-- plan-header -->",
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{issue_number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )
    comment = IssueComment(
        body=comment_body,
        url=f"https://github.com/test/repo/issues/{issue_number}#issuecomment-123",
        id=123,
        author="testuser",
    )
    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    return fake_gh, issue


def test_plan_update_issue_success() -> None:
    """Test successful plan update."""
    fake_gh, _issue = _create_plan_issue()
    plan_content = "# Updated Plan\n\n- New Step 1\n- New Step 2"
    fake_store = FakeClaudeCodeSessionStore(
        plans={"updated-plan": plan_content},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["1", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["issue_url"] == "https://github.com/test/repo/issues/1"


def test_plan_update_issue_updates_comment() -> None:
    """Test that the comment is actually updated with new content."""
    fake_gh, _issue = _create_plan_issue()
    new_plan_content = "# Completely New Plan\n\n- Different steps"
    fake_store = FakeClaudeCodeSessionStore(
        plans={"new-plan": new_plan_content},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["1", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"

    # Verify the comment was updated
    assert len(fake_gh.updated_comments) == 1
    comment_id, new_body = fake_gh.updated_comments[0]
    assert comment_id == 123
    assert "Completely New Plan" in new_body
    assert "plan-body" in new_body  # Wrapped in plan-body markers


def test_plan_update_issue_no_plan() -> None:
    """Test error when no plan found."""
    fake_gh, _issue = _create_plan_issue()
    # Empty session store - no plans
    fake_store = FakeClaudeCodeSessionStore()
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["1", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_plan_update_issue_not_found() -> None:
    """Test error when issue not found."""
    fake_gh = FakeGitHubIssues()  # No issues
    plan_content = "# Updated Plan"
    fake_store = FakeClaudeCodeSessionStore(
        plans={"update-plan": plan_content},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["999", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to get issue #999" in output["error"]


def test_plan_update_issue_no_comments() -> None:
    """Test error when issue has no comments."""
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=1,
        title="Test Plan",
        body="",
        state="OPEN",
        url="https://github.com/test/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )
    fake_gh = FakeGitHubIssues(
        issues={1: issue},
        comments_with_urls={},  # No comments
    )
    plan_content = "# Updated Plan"
    fake_store = FakeClaudeCodeSessionStore(
        plans={"update-plan": plan_content},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["1", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "has no comments" in output["error"]


def test_plan_update_issue_display_format() -> None:
    """Test display output format."""
    fake_gh, _issue = _create_plan_issue()
    plan_content = "# Updated Feature\n\n- Implementation step"
    fake_store = FakeClaudeCodeSessionStore(
        plans={"display-test": plan_content},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["1", "--format", "display"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 0
    assert "Plan updated in GitHub issue #1" in result.output
    assert "URL: " in result.output


def test_plan_update_issue_with_plan_file(tmp_path: Path) -> None:
    """Test using --plan-file option."""
    fake_gh, _issue = _create_plan_issue()
    fake_store = FakeClaudeCodeSessionStore()  # Empty - not used

    # Create a plan file
    plan_file = tmp_path / "custom_plan.md"
    plan_file.write_text("# Custom Plan from File\n\n- Custom step", encoding="utf-8")

    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["1", "--format", "json", "--plan-file", str(plan_file)],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify the file content was used
    assert len(fake_gh.updated_comments) == 1
    _comment_id, new_body = fake_gh.updated_comments[0]
    assert "Custom Plan from File" in new_body


def test_plan_update_issue_error_display_format() -> None:
    """Test error output in display format."""
    fake_gh = FakeGitHubIssues()  # No issues
    plan_content = "# Updated Plan"
    fake_store = FakeClaudeCodeSessionStore(
        plans={"error-test": plan_content},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["999", "--format", "display"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            session_store=fake_store,
        ),
    )

    assert result.exit_code == 1
    assert "Error:" in result.output
