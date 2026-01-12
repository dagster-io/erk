"""Unit tests for get-issue-body command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_issue_body import get_issue_body
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


def test_get_issue_body_success() -> None:
    """Test successful issue body fetch."""
    issue = _make_issue(42, "Test Issue", "This is the issue body")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        get_issue_body,
        ["42"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["title"] == "Test Issue"
    assert output["body"] == "This is the issue body"
    assert output["state"] == "OPEN"
    assert output["labels"] == ["erk-plan"]
    assert output["url"] == "https://github.com/test/repo/issues/42"


def test_get_issue_body_with_markdown() -> None:
    """Test issue body with markdown content."""
    body_markdown = """# Plan Title

## Summary

- Item 1
- Item 2

## Implementation

```python
def hello():
    return "world"
```
"""
    issue = _make_issue(99, "Markdown Test [erk-plan]", body_markdown)
    fake_gh = FakeGitHubIssues(issues={99: issue})
    runner = CliRunner()

    result = runner.invoke(
        get_issue_body,
        ["99"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "# Plan Title" in output["body"]
    assert "```python" in output["body"]


def test_get_issue_body_not_found() -> None:
    """Test error when issue does not exist."""
    fake_gh = FakeGitHubIssues()  # Empty issues dict
    runner = CliRunner()

    result = runner.invoke(
        get_issue_body,
        ["999"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]
    assert "not found" in output["error"].lower() or "Failed" in output["error"]
