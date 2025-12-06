"""Unit tests for post_issue_comments kit CLI command.

Tests posting multiple comments to GitHub issues using FakeGitHubIssues.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_issue_comments import (
    post_issue_comments,
)


def _make_issue(number: int) -> IssueInfo:
    """Create a minimal IssueInfo for testing."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Issue {number}",
        body="Test body",
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=[],
        assignees=[],
        created_at=now,
        updated_at=now,
    )


# ============================================================================
# 1. CLI Success Tests (6 tests)
# ============================================================================


def test_cli_posts_single_comment(tmp_path: Path) -> None:
    """Test posting a single comment."""
    fake_issues = FakeGitHubIssues(issues={123: _make_issue(123)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    input_data = {"comment_bodies": ["Comment 1"]}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "123"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["comments_posted"] == 1

    # Verify comment was posted via fake
    assert len(fake_issues.added_comments) == 1
    assert fake_issues.added_comments[0] == (123, "Comment 1")


def test_cli_posts_multiple_comments(tmp_path: Path) -> None:
    """Test posting multiple comments."""
    fake_issues = FakeGitHubIssues(issues={456: _make_issue(456)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    input_data = {"comment_bodies": ["First", "Second", "Third"]}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "456"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["comments_posted"] == 3

    # Verify all comments posted
    assert len(fake_issues.added_comments) == 3
    bodies = [body for _, body in fake_issues.added_comments]
    assert bodies == ["First", "Second", "Third"]


def test_cli_accepts_array_input(tmp_path: Path) -> None:
    """Test that direct array input is accepted."""
    fake_issues = FakeGitHubIssues(issues={789: _make_issue(789)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    # Direct array instead of {"comment_bodies": [...]}
    input_data = ["Comment A", "Comment B"]

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "789"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["comments_posted"] == 2


def test_cli_output_structure(tmp_path: Path) -> None:
    """Test that output has expected structure."""
    fake_issues = FakeGitHubIssues(issues={100: _make_issue(100)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    input_data = {"comment_bodies": ["Test"]}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "100"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    assert "success" in output
    assert "issue_number" in output
    assert "comments_posted" in output
    assert output["success"] is True
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["comments_posted"], int)


def test_cli_posts_to_correct_issue(tmp_path: Path) -> None:
    """Test that comments are posted to the correct issue number."""
    fake_issues = FakeGitHubIssues(issues={999: _make_issue(999)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    input_data = {"comment_bodies": ["Test comment"]}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "999"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 0
    issue_number, body = fake_issues.added_comments[0]
    assert issue_number == 999
    assert body == "Test comment"


def test_cli_preserves_comment_content(tmp_path: Path) -> None:
    """Test that comment content is preserved exactly."""
    fake_issues = FakeGitHubIssues(issues={123: _make_issue(123)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    complex_body = """<!-- erk:metadata-block -->
<details>
<summary><strong>Session Data</strong></summary>

```xml
<session>content</session>
```

</details>
<!-- /erk:metadata-block -->"""

    input_data = {"comment_bodies": [complex_body]}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "123"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 0
    _, body = fake_issues.added_comments[0]
    assert body == complex_body


# ============================================================================
# 2. Error Handling Tests (5 tests)
# ============================================================================


def test_cli_invalid_json_error(tmp_path: Path) -> None:
    """Test error when input is invalid JSON."""
    fake_issues = FakeGitHubIssues(issues={123: _make_issue(123)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "123"],
        input="not valid json",
        obj=context,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Invalid JSON" in output["error"]


def test_cli_empty_bodies_error(tmp_path: Path) -> None:
    """Test error when comment_bodies is empty."""
    fake_issues = FakeGitHubIssues(issues={123: _make_issue(123)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    input_data = {"comment_bodies": []}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "123"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No comment_bodies" in output["error"]


def test_cli_non_string_body_error(tmp_path: Path) -> None:
    """Test error when comment body is not a string."""
    fake_issues = FakeGitHubIssues(issues={123: _make_issue(123)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    input_data = {"comment_bodies": ["valid", 123, "also valid"]}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "123"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "not a string" in output["error"]


def test_cli_invalid_structure_error(tmp_path: Path) -> None:
    """Test error when input has invalid structure."""
    fake_issues = FakeGitHubIssues(issues={123: _make_issue(123)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    # Send a string instead of array/object
    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "123"],
        input='"just a string"',
        obj=context,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False


def test_cli_missing_issue_number_error(tmp_path: Path) -> None:
    """Test error when issue number is not provided."""
    fake_issues = FakeGitHubIssues(issues={123: _make_issue(123)})
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=tmp_path)

    input_data = {"comment_bodies": ["test"]}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        [],  # No --issue-number
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 2  # Click error for missing required option


# ============================================================================
# 3. Context Tests (2 tests)
# ============================================================================


def test_cli_uses_repo_root(tmp_path: Path) -> None:
    """Test that repo_root from context is used."""
    fake_issues = FakeGitHubIssues(issues={123: _make_issue(123)})
    custom_root = tmp_path / "custom_repo"
    custom_root.mkdir()
    context = DotAgentContext.for_test(github_issues=fake_issues, repo_root=custom_root)

    input_data = {"comment_bodies": ["test"]}

    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "123"],
        input=json.dumps(input_data),
        obj=context,
    )

    assert result.exit_code == 0
    # added_comments stores (issue_number, body) tuples, repo_root is not tracked
    # Just verify comment was posted successfully
    assert len(fake_issues.added_comments) == 1


def test_cli_no_context_error() -> None:
    """Test error when context is not initialized."""
    runner = CliRunner()
    result = runner.invoke(
        post_issue_comments,
        ["--issue-number", "123"],
        input='{"comment_bodies": ["test"]}',
        obj=None,  # No context
    )

    assert result.exit_code == 1
