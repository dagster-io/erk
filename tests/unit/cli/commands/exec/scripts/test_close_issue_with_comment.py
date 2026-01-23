"""Unit tests for close-issue-with-comment command.

Tests use FakeGitHubIssues for dependency injection.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

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
    """Test successfully closing an issue with a comment."""
    issue = _make_issue(42, "Test Issue", "This is the issue body")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        close_issue_with_comment,
        ["42", "--comment", "Closing: work is done."],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["comment_id"] == 1000  # FakeGitHubIssues starts at 1000

    # Verify the comment was added
    assert len(fake_gh.added_comments) == 1
    issue_number, comment_body, comment_id = fake_gh.added_comments[0]
    assert issue_number == 42
    assert comment_body == "Closing: work is done."
    assert comment_id == 1000

    # Verify the issue was closed
    assert 42 in fake_gh.closed_issues


def test_close_issue_with_comment_not_found() -> None:
    """Test error when issue does not exist."""
    fake_gh = FakeGitHubIssues()  # Empty issues dict
    runner = CliRunner()

    result = runner.invoke(
        close_issue_with_comment,
        ["999", "--comment", "This should fail"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]

    # Verify no mutations occurred
    assert len(fake_gh.added_comments) == 0
    assert len(fake_gh.closed_issues) == 0


def test_close_issue_with_comment_multiline() -> None:
    """Test closing with a multiline comment."""
    issue = _make_issue(100, "Plan Issue", "Implementation plan")
    fake_gh = FakeGitHubIssues(issues={100: issue})
    runner = CliRunner()

    multiline_comment = """Closing as superseded.

## Evidence
- Work merged in PR #1234
- Feature exists at src/foo.py

See #1234 for details."""

    result = runner.invoke(
        close_issue_with_comment,
        ["100", "--comment", multiline_comment],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 100

    # Verify the full comment was preserved
    _, comment_body, _ = fake_gh.added_comments[0]
    assert "superseded" in comment_body
    assert "PR #1234" in comment_body


def test_close_issue_with_comment_changes_state() -> None:
    """Test that the issue state changes to closed."""
    issue = _make_issue(55, "Open Issue", "Body")
    fake_gh = FakeGitHubIssues(issues={55: issue})
    runner = CliRunner()

    result = runner.invoke(
        close_issue_with_comment,
        ["55", "--comment", "Done"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0

    # Verify the issue state was updated in the fake
    closed_issue = fake_gh.get_issue(Path("/unused"), 55)  # repo_root not used in fake
    assert closed_issue.state == "closed"


def test_close_issue_with_comment_requires_comment_flag() -> None:
    """Test that --comment flag is required."""
    issue = _make_issue(10, "Test", "Body")
    fake_gh = FakeGitHubIssues(issues={10: issue})
    runner = CliRunner()

    result = runner.invoke(
        close_issue_with_comment,
        ["10"],  # Missing --comment
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # Click should reject missing required option
    assert result.exit_code == 2
    assert "comment" in result.output.lower()
