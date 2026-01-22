"""Unit tests for close-issue-with-comment command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.close_issue_with_comment import (
    close_issue_with_comment,
)
from erk_shared.context.context import ErkContext
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


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


def test_close_issue_with_comment_success() -> None:
    """Test successful issue close with comment."""
    issue = _make_issue(42, "Test Issue", "This is the issue body")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        close_issue_with_comment,
        ["42", "--comment", "Closing: This work is already in master."],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert "comment_id" in output

    # Verify the comment was added
    assert len(fake_gh.added_comments) == 1
    issue_num, body, comment_id = fake_gh.added_comments[0]
    assert issue_num == 42
    assert "This work is already in master" in body
    assert comment_id == output["comment_id"]

    # Verify the issue was closed
    assert 42 in fake_gh.closed_issues


def test_close_issue_with_comment_issue_not_found() -> None:
    """Test error when issue does not exist."""
    fake_gh = FakeGitHubIssues()  # Empty issues dict
    runner = CliRunner()

    result = runner.invoke(
        close_issue_with_comment,
        ["999", "--comment", "Closing."],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]
    assert "not found" in output["error"].lower() or "Failed" in output["error"]

    # Verify no operations were performed
    assert len(fake_gh.added_comments) == 0
    assert len(fake_gh.closed_issues) == 0


def test_close_issue_with_comment_multiline() -> None:
    """Test closing issue with multiline comment."""
    issue = _make_issue(99, "Plan Issue", "Plan body")
    fake_gh = FakeGitHubIssues(issues={99: issue})
    runner = CliRunner()

    comment = """Closing: This work is already represented in master.

Evidence:
- src/erk/foo.py exists
- PR #123 merged the same functionality

See #123 for details."""

    result = runner.invoke(
        close_issue_with_comment,
        ["99", "--comment", comment],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify the full comment was preserved
    _, body, _ = fake_gh.added_comments[0]
    assert "Evidence:" in body
    assert "PR #123" in body


def test_close_issue_with_comment_verifies_order() -> None:
    """Test that comment is added before closing (correct order)."""
    issue = _make_issue(50, "Test", "Body")
    fake_gh = FakeGitHubIssues(issues={50: issue})
    runner = CliRunner()

    result = runner.invoke(
        close_issue_with_comment,
        ["50", "--comment", "Test comment"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0

    # Both operations should have completed
    assert len(fake_gh.added_comments) == 1
    assert len(fake_gh.closed_issues) == 1


def test_close_issue_with_comment_missing_comment_flag() -> None:
    """Test error when --comment flag is missing."""
    issue = _make_issue(42, "Test", "Body")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        close_issue_with_comment,
        ["42"],  # Missing --comment
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # Click should report missing required option
    assert result.exit_code != 0
    assert "comment" in result.output.lower()

    # No operations should have been performed
    assert len(fake_gh.added_comments) == 0
    assert len(fake_gh.closed_issues) == 0
