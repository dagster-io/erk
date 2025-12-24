"""Unit tests for post_workflow_started_comment kit CLI command.

Tests the workflow started comment building and posting functionality.
Uses FakeGitHubIssues for dependency injection instead of mocking.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.post_workflow_started_comment import (
    _build_workflow_started_comment,
)
from erk_kits.data.kits.erk.scripts.erk.post_workflow_started_comment import (
    post_workflow_started_comment as post_workflow_started_comment_command,
)
from erk_shared.context import ErkContext
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


def _create_test_issue(issue_number: int) -> IssueInfo:
    """Create a test issue for FakeGitHubIssues."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=issue_number,
        title="Test Issue",
        body="Test body",
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{issue_number}",
        labels=[],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# 1. Comment Building Tests (6 tests) - Pure function tests, no fakes needed
# ============================================================================


def test_build_comment_contains_all_fields() -> None:
    """Test that built comment contains all required fields."""
    comment = _build_workflow_started_comment(
        issue_number=123,
        branch_name="my-feature",
        pr_number=456,
        run_id="99999",
        run_url="https://github.com/owner/repo/actions/runs/99999",
        repository="owner/repo",
    )

    assert "⚙️ GitHub Action Started" in comment
    assert "branch_name: my-feature" in comment
    assert "issue_number: 123" in comment
    assert 'workflow_run_id: "99999"' in comment
    assert "https://github.com/owner/repo/actions/runs/99999" in comment


def test_build_comment_has_metadata_block() -> None:
    """Test that comment has properly formatted metadata block."""
    comment = _build_workflow_started_comment(
        issue_number=123,
        branch_name="feat-auth",
        pr_number=456,
        run_id="12345",
        run_url="https://github.com/acme/app/actions/runs/12345",
        repository="acme/app",
    )

    assert "<!-- erk:metadata-block:workflow-started -->" in comment
    assert "<!-- /erk:metadata-block:workflow-started -->" in comment
    assert "schema: workflow-started" in comment
    assert "status: started" in comment


def test_build_comment_has_pr_link() -> None:
    """Test that comment has proper PR link."""
    comment = _build_workflow_started_comment(
        issue_number=10,
        branch_name="fix-bug",
        pr_number=42,
        run_id="888",
        run_url="https://github.com/test/repo/actions/runs/888",
        repository="test/repo",
    )

    assert "**PR:** [#42](https://github.com/test/repo/pull/42)" in comment


def test_build_comment_has_branch_display() -> None:
    """Test that comment displays branch name."""
    comment = _build_workflow_started_comment(
        issue_number=1,
        branch_name="feature-xyz",
        pr_number=2,
        run_id="3",
        run_url="https://example.com",
        repository="o/r",
    )

    assert "**Branch:** `feature-xyz`" in comment


def test_build_comment_has_workflow_link() -> None:
    """Test that comment has workflow run link."""
    comment = _build_workflow_started_comment(
        issue_number=1,
        branch_name="b",
        pr_number=2,
        run_id="3",
        run_url="https://github.com/owner/repo/actions/runs/3",
        repository="owner/repo",
    )

    assert "[View workflow run](https://github.com/owner/repo/actions/runs/3)" in comment


def test_build_comment_has_valid_timestamp() -> None:
    """Test that comment contains a valid ISO 8601 timestamp."""
    comment = _build_workflow_started_comment(
        issue_number=1,
        branch_name="b",
        pr_number=2,
        run_id="3",
        run_url="https://example.com",
        repository="o/r",
    )

    # Extract timestamp from comment
    match = re.search(r"started_at: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", comment)
    assert match is not None
    timestamp = match.group(1)
    # Verify format (ISO 8601 UTC)
    assert timestamp.endswith("Z")


# ============================================================================
# 2. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command successfully posts comment."""
    runner = CliRunner()
    fake_github = FakeGitHubIssues(
        issues={123: _create_test_issue(123)},
    )
    ctx = ErkContext.for_test(github_issues=fake_github, repo_root=tmp_path)

    result = runner.invoke(
        post_workflow_started_comment_command,
        [
            "--issue-number",
            "123",
            "--branch-name",
            "my-branch",
            "--pr-number",
            "456",
            "--run-id",
            "99999",
            "--run-url",
            "https://github.com/owner/repo/actions/runs/99999",
            "--repository",
            "owner/repo",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123

    # Verify comment was added via mutation tracking
    assert len(fake_github.added_comments) == 1
    issue_num, comment_body, _comment_id = fake_github.added_comments[0]
    assert issue_num == 123
    assert "my-branch" in comment_body


def test_cli_github_api_failure(tmp_path: Path) -> None:
    """Test CLI command handles GitHub API failure."""
    runner = CliRunner()
    # Issue not in the fake, so add_comment will raise RuntimeError
    fake_github = FakeGitHubIssues(issues={})
    ctx = ErkContext.for_test(github_issues=fake_github, repo_root=tmp_path)

    result = runner.invoke(
        post_workflow_started_comment_command,
        [
            "--issue-number",
            "123",
            "--branch-name",
            "branch",
            "--pr-number",
            "456",
            "--run-id",
            "999",
            "--run-url",
            "https://example.com",
            "--repository",
            "o/r",
        ],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "github_api_failed"


def test_cli_missing_required_option() -> None:
    """Test CLI command requires all options."""
    runner = CliRunner()

    result = runner.invoke(
        post_workflow_started_comment_command,
        ["--issue-number", "123"],  # Missing other required options
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_cli_passes_correct_args_to_github(tmp_path: Path) -> None:
    """Test CLI command passes correct arguments to GitHub API."""
    runner = CliRunner()
    fake_github = FakeGitHubIssues(
        issues={789: _create_test_issue(789)},
    )
    ctx = ErkContext.for_test(github_issues=fake_github, repo_root=tmp_path)

    runner.invoke(
        post_workflow_started_comment_command,
        [
            "--issue-number",
            "789",
            "--branch-name",
            "test-branch",
            "--pr-number",
            "101",
            "--run-id",
            "55555",
            "--run-url",
            "https://github.com/foo/bar/actions/runs/55555",
            "--repository",
            "foo/bar",
        ],
        obj=ctx,
    )

    # Verify add_comment was called with correct issue number
    assert len(fake_github.added_comments) == 1
    issue_num, comment_body, _comment_id = fake_github.added_comments[0]
    assert issue_num == 789
    # Comment body should contain the branch name
    assert "test-branch" in comment_body
