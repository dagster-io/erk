"""Unit tests for plan-update-issue command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_update_issue import plan_update_issue
from erk_shared.context import ErkContext
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueComment, IssueInfo
from erk_shared.learn.extraction.claude_installation.fake import FakeClaudeInstallation


def _make_issue(
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create a test IssueInfo."""
    now = datetime.now(UTC)
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


def _make_comment(comment_id: int, body: str) -> IssueComment:
    """Create a test IssueComment."""
    return IssueComment(
        body=body,
        url=f"https://github.com/test/repo/issues/1#issuecomment-{comment_id}",
        id=comment_id,
        author="testuser",
    )


def test_plan_update_issue_success() -> None:
    """Test successful plan update."""
    issue = _make_issue(42, "Test Plan [erk-plan]", "metadata body")
    comment = _make_comment(12345, "old plan content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    plan_content = """# Updated Plan

- New step 1
- New step 2"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--issue-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["comment_id"] == 12345
    assert "issuecomment-12345" in output["comment_url"]

    # Verify update_comment was called
    assert len(fake_gh.updated_comments) == 1
    updated_comment_id, updated_body = fake_gh.updated_comments[0]
    assert updated_comment_id == 12345
    assert "New step 1" in updated_body
    assert "New step 2" in updated_body


def test_plan_update_issue_display_format() -> None:
    """Test display output format."""
    issue = _make_issue(99, "My Feature [erk-plan]", "body")
    comment = _make_comment(55555, "plan content")
    fake_gh = FakeGitHubIssues(
        issues={99: issue},
        comments_with_urls={99: [comment]},
    )
    plan_content = """# Display Test

- Step"""
    fake_store = FakeClaudeInstallation.for_test(plans={"display-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--issue-number", "99", "--format", "display"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    assert "Plan updated on issue #99" in result.output
    assert "Title: My Feature [erk-plan]" in result.output
    assert "URL: " in result.output
    assert "Comment: " in result.output


def test_plan_update_issue_no_plan_found() -> None:
    """Test error when no plan found."""
    issue = _make_issue(42, "Test [erk-plan]", "body")
    comment = _make_comment(12345, "plan content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    # Empty store - no plans
    fake_store = FakeClaudeInstallation.for_test()
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--issue-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_plan_update_issue_issue_not_found() -> None:
    """Test error when issue does not exist."""
    # Empty issues dict - no issues
    fake_gh = FakeGitHubIssues()
    plan_content = """# Test

- Step"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--issue-number", "999", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]


def test_plan_update_issue_no_comments() -> None:
    """Test error when issue has no comments."""
    issue = _make_issue(42, "Test [erk-plan]", "body")
    # Issue exists but has no comments
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: []},  # Empty comments list
    )
    plan_content = """# Test

- Step"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--issue-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "no comments" in output["error"]


def test_plan_update_issue_updates_first_comment_only() -> None:
    """Test that only the first comment is updated (where plan body lives)."""
    issue = _make_issue(42, "Test [erk-plan]", "body")
    comment1 = _make_comment(111, "plan content - first")
    comment2 = _make_comment(222, "second comment")
    comment3 = _make_comment(333, "third comment")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment1, comment2, comment3]},
    )
    plan_content = """# Updated

- New"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--issue-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0

    # Verify only the FIRST comment was updated
    assert len(fake_gh.updated_comments) == 1
    updated_comment_id, _ = fake_gh.updated_comments[0]
    assert updated_comment_id == 111  # First comment ID


def test_plan_update_issue_formats_plan_content() -> None:
    """Test that plan content is properly formatted with metadata block."""
    issue = _make_issue(42, "Test [erk-plan]", "body")
    comment = _make_comment(12345, "old content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    plan_content = """# My Plan

- Step 1"""
    fake_store = FakeClaudeInstallation.for_test(plans={"format-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--issue-number", "42"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0

    # Verify the updated content is formatted (wrapped in metadata block)
    _, updated_body = fake_gh.updated_comments[0]
    # The format_plan_content_comment wraps in collapsible metadata block
    assert "plan-body" in updated_body or "erk:metadata-block" in updated_body
