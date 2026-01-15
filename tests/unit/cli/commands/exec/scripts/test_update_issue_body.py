"""Unit tests for update-issue-body command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_issue_body import update_issue_body
from erk_shared.context import ErkContext
from erk_shared.github.issues import FakeGitHubIssues
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


def test_update_issue_body_success() -> None:
    """Test successful issue body update."""
    issue = _make_issue(42, "Test Issue", "Old body content")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    new_body = "This is the new body content"
    result = runner.invoke(
        update_issue_body,
        ["42", "--body", new_body],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["url"] == "https://github.com/test/repo/issues/42"

    # Verify the body was actually updated
    assert len(fake_gh.updated_bodies) == 1
    updated_number, updated_body = fake_gh.updated_bodies[0]
    assert updated_number == 42
    assert updated_body == new_body


def test_update_issue_body_with_markdown() -> None:
    """Test updating issue body with markdown content."""
    issue = _make_issue(99, "Markdown Test [erk-plan]", "Old content")
    fake_gh = FakeGitHubIssues(issues={99: issue})
    runner = CliRunner()

    new_body = """# Updated Plan

## Summary
- New item 1
- New item 2

## Code
```python
def new_function():
    return "updated"
```
"""
    result = runner.invoke(
        update_issue_body,
        ["99", "--body", new_body],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify markdown content was preserved
    _, updated_body = fake_gh.updated_bodies[0]
    assert "# Updated Plan" in updated_body
    assert "```python" in updated_body


def test_update_issue_body_not_found() -> None:
    """Test error when issue does not exist."""
    fake_gh = FakeGitHubIssues()  # Empty issues dict
    runner = CliRunner()

    result = runner.invoke(
        update_issue_body,
        ["999", "--body", "new content"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]


def test_update_issue_body_empty_body() -> None:
    """Test updating to an empty body."""
    issue = _make_issue(42, "Test Issue", "Original content")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        update_issue_body,
        ["42", "--body", ""],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify empty body was set
    _, updated_body = fake_gh.updated_bodies[0]
    assert updated_body == ""


def test_update_issue_body_from_file(tmp_path: Path) -> None:
    """Test reading body content from a file."""
    issue = _make_issue(42, "Test Issue", "Old body content")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    # Create a file with body content
    body_file = tmp_path / "body.md"
    body_content = """# Updated via File

This content came from a file with special chars: "quotes" and `backticks`.
"""
    body_file.write_text(body_content, encoding="utf-8")

    result = runner.invoke(
        update_issue_body,
        ["42", "--body-file", str(body_file)],
        obj=ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42

    # Verify the body was updated with file content
    assert len(fake_gh.updated_bodies) == 1
    updated_number, updated_body = fake_gh.updated_bodies[0]
    assert updated_number == 42
    assert updated_body == body_content


def test_update_issue_body_fails_with_both_body_and_file(tmp_path: Path) -> None:
    """Test error when both --body and --body-file are specified."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Create a file
    body_file = tmp_path / "body.md"
    body_file.write_text("file content", encoding="utf-8")

    result = runner.invoke(
        update_issue_body,
        ["42", "--body", "inline content", "--body-file", str(body_file)],
        obj=ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Cannot specify both --body and --body-file" in output["error"]


def test_update_issue_body_fails_without_body_or_file() -> None:
    """Test error when neither --body nor --body-file is specified."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        update_issue_body,
        ["42"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Must specify --body or --body-file" in output["error"]
