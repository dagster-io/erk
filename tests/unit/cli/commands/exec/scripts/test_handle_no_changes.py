"""Unit tests for handle_no_changes exec CLI command.

Tests the no-changes scenario handling for erk-impl workflow.
Uses FakeGitHub for dependency injection.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.handle_no_changes import (
    HandleNoChangesError,
    HandleNoChangesSuccess,
    _build_issue_comment,
    _build_pr_body,
)
from erk.cli.commands.exec.scripts.handle_no_changes import (
    handle_no_changes as handle_no_changes_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo


def _create_github_with_issue(issue_number: int) -> FakeGitHub:
    """Create FakeGitHub with a plan issue configured for adding comments."""
    test_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
    issues_gateway = FakeGitHubIssues(
        issues={
            issue_number: IssueInfo(
                number=issue_number,
                title="Test Plan",
                body="Test plan content",
                state="open",
                url=f"https://github.com/test-owner/test-repo/issues/{issue_number}",
                labels=["erk-plan"],
                assignees=[],
                created_at=test_time,
                updated_at=test_time,
                author="test-user",
            )
        }
    )
    return FakeGitHub(issues_gateway=issues_gateway)


# ============================================================================
# 1. Helper Function Tests
# ============================================================================


def test_build_pr_body_includes_all_sections() -> None:
    """Test that _build_pr_body includes all required sections."""
    body = _build_pr_body(
        issue_number=456,
        behind_count=5,
        base_branch="master",
        recent_commits="abc1234 Fix bug\ndef5678 Add feature",
        run_url="https://github.com/owner/repo/actions/runs/789",
    )

    assert "## No Code Changes" in body
    assert "Implementation completed but produced no code changes" in body
    assert "### Diagnosis" in body
    assert "Duplicate plan" in body
    assert "5 commits" in body
    assert "master" in body
    assert "Recent commits" in body
    assert "abc1234 Fix bug" in body
    assert "def5678 Add feature" in body
    assert "### Next Steps" in body
    assert "Closes #456" in body
    assert "https://github.com/owner/repo/actions/runs/789" in body


def test_build_pr_body_without_recent_commits() -> None:
    """Test that _build_pr_body works without recent commits."""
    body = _build_pr_body(
        issue_number=456,
        behind_count=0,
        base_branch="main",
        recent_commits=None,
        run_url=None,
    )

    assert "## No Code Changes" in body
    assert "### Diagnosis" in body
    assert "Closes #456" in body
    # Should not include commits section when behind_count is 0
    assert "commits** behind" not in body
    # Should not include run URL
    assert "View workflow run" not in body


def test_build_pr_body_with_empty_recent_commits() -> None:
    """Test that _build_pr_body handles empty recent commits string."""
    body = _build_pr_body(
        issue_number=123,
        behind_count=3,
        base_branch="master",
        recent_commits="",
        run_url=None,
    )

    assert "## No Code Changes" in body
    assert "3 commits" in body
    # Should not include recent commits section with empty string
    assert "Recent commits" not in body


def test_build_issue_comment() -> None:
    """Test that _build_issue_comment includes PR reference."""
    comment = _build_issue_comment(pr_number=123)

    assert "no code changes" in comment.lower()
    assert "PR #123" in comment
    assert "diagnostic" in comment.lower()


# ============================================================================
# 2. CLI Command Tests
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command succeeds with valid inputs."""
    github = _create_github_with_issue(456)

    ctx = ErkContext.for_test(github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--behind-count",
            "5",
            "--base-branch",
            "master",
            "--recent-commits",
            "abc1234 Fix bug\ndef5678 Add feature",
            "--run-url",
            "https://github.com/owner/repo/actions/runs/789",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert output["issue_number"] == 456


def test_cli_success_minimal_options(tmp_path: Path) -> None:
    """Test CLI command succeeds with only required options."""
    github = _create_github_with_issue(456)

    ctx = ErkContext.for_test(github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True


def test_cli_updates_pr_body(tmp_path: Path) -> None:
    """Test that CLI command updates PR body."""
    github = _create_github_with_issue(456)

    ctx = ErkContext.for_test(github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--behind-count",
            "5",
            "--base-branch",
            "master",
        ],
        obj=ctx,
    )

    # Verify PR body was updated (updated_pr_bodies is list of (pr_number, body) tuples)
    assert len(github.updated_pr_bodies) == 1
    pr_number, body = github.updated_pr_bodies[0]
    assert pr_number == 123
    assert "No Code Changes" in body
    assert "Closes #456" in body


def test_cli_adds_label_to_pr(tmp_path: Path) -> None:
    """Test that CLI command adds no-changes label to PR."""
    github = _create_github_with_issue(456)

    ctx = ErkContext.for_test(github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
        obj=ctx,
    )

    # Verify label was added (added_labels is list of (pr_number, label) tuples)
    assert len(github.added_labels) == 1
    pr_number, label = github.added_labels[0]
    assert pr_number == 123
    assert label == "no-changes"


def test_cli_adds_comment_to_issue(tmp_path: Path) -> None:
    """Test that CLI command adds comment to plan issue."""
    github = _create_github_with_issue(456)

    ctx = ErkContext.for_test(github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
        obj=ctx,
    )

    # Verify comment was added to issue
    # added_comments is list of (issue_number, body, comment_id) tuples
    assert len(github.issues.added_comments) == 1
    issue_number, body, _comment_id = github.issues.added_comments[0]
    assert issue_number == 456
    assert "PR #123" in body


def test_cli_requires_pr_number() -> None:
    """Test that --pr-number is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--issue-number",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_requires_issue_number() -> None:
    """Test that --issue-number is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_requires_behind_count() -> None:
    """Test that --behind-count is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--base-branch",
            "main",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_requires_base_branch() -> None:
    """Test that --base-branch is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--behind-count",
            "0",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_json_output_structure_success(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success."""
    github = _create_github_with_issue(456)

    ctx = ErkContext.for_test(github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "pr_number" in output
    assert "issue_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["pr_number"], int)
    assert isinstance(output["issue_number"], int)


def test_cli_exits_with_code_0_on_success(tmp_path: Path) -> None:
    """Test that CLI exits with code 0 on success (workflow succeeds)."""
    github = _create_github_with_issue(456)

    ctx = ErkContext.for_test(github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--issue-number",
            "456",
            "--behind-count",
            "5",
            "--base-branch",
            "master",
        ],
        obj=ctx,
    )

    # Critical: exit code 0 means workflow succeeds
    assert result.exit_code == 0


# ============================================================================
# 3. Dataclass Tests
# ============================================================================


def test_success_dataclass_frozen() -> None:
    """Test that HandleNoChangesSuccess is immutable."""
    success = HandleNoChangesSuccess(success=True, pr_number=123, issue_number=456)
    assert success.success is True
    assert success.pr_number == 123
    assert success.issue_number == 456


def test_error_dataclass_frozen() -> None:
    """Test that HandleNoChangesError is immutable."""
    error = HandleNoChangesError(
        success=False, error="github-api-failed", message="Failed to update PR"
    )
    assert error.success is False
    assert error.error == "github-api-failed"
    assert error.message == "Failed to update PR"
