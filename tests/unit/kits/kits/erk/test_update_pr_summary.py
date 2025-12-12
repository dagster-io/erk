"""Unit tests for update_pr_summary kit CLI command.

Tests the PR body update functionality with commit message extraction and footer.
Uses FakeGit and FakeGitHub for dependency injection instead of mocking.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.update_pr_summary import (
    _build_pr_body,
    update_pr_summary,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo


def _create_pr_info(branch: str, pr_number: int) -> PullRequestInfo:
    """Create a PullRequestInfo for testing."""
    return PullRequestInfo(
        number=pr_number,
        state="OPEN",
        url=f"https://github.com/test/repo/pull/{pr_number}",
        is_draft=False,
        title="Test PR",
        checks_passing=None,
        owner="test",
        repo="repo",
        has_conflicts=None,
    )


def _create_pr_details(branch: str, pr_number: int) -> PRDetails:
    """Create a PRDetails for testing."""
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/test/repo/pull/{pr_number}",
        title="Test PR",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test",
        repo="repo",
    )


# ============================================================================
# 1. PR Body Building Tests (3 tests) - Pure function tests, no fakes needed
# ============================================================================


def test_build_pr_body_has_summary_section() -> None:
    """Test that PR body has summary section with commit message."""
    body = _build_pr_body(
        commit_message="Implement feature X\n\nDetails about the implementation.",
        pr_number=123,
        issue_number=456,
    )

    assert "## Summary" in body
    assert "Implement feature X" in body
    assert "Details about the implementation." in body


def test_build_pr_body_has_closes_reference() -> None:
    """Test that PR body includes issue closing reference."""
    body = _build_pr_body(
        commit_message="Fix bug",
        pr_number=123,
        issue_number=789,
    )

    assert "Closes #789" in body


def test_build_pr_body_has_checkout_instructions() -> None:
    """Test that PR body includes checkout instructions."""
    body = _build_pr_body(
        commit_message="Add feature",
        pr_number=42,
        issue_number=10,
    )

    assert "erk pr checkout 42" in body


# ============================================================================
# 2. CLI Command Tests (5 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command successfully updates PR body."""
    runner = CliRunner()
    branch = "my-branch"
    pr_number = 789
    commit_sha = "abc123"

    fake_git = FakeGit(
        commit_messages={commit_sha: "Implement feature"},
    )
    fake_github = FakeGitHub(
        prs={branch: _create_pr_info(branch, pr_number)},
        pr_details={pr_number: _create_pr_details(branch, pr_number)},
    )
    ctx = ErkContext.for_test(git=fake_git, github=fake_github, repo_root=tmp_path)

    result = runner.invoke(
        update_pr_summary,
        [
            "--branch-name",
            branch,
            "--issue-number",
            "123",
            "--commit-sha",
            commit_sha,
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == pr_number

    # Verify PR body was updated via mutation tracking
    assert len(fake_github.updated_pr_bodies) == 1
    updated_pr_num, updated_body = fake_github.updated_pr_bodies[0]
    assert updated_pr_num == pr_number
    assert "Implement feature" in updated_body


def test_cli_commit_not_found(tmp_path: Path) -> None:
    """Test CLI command handles missing commit."""
    runner = CliRunner()
    branch = "branch"
    pr_number = 123

    fake_git = FakeGit(
        commit_messages={},  # No commit messages configured
    )
    fake_github = FakeGitHub(
        prs={branch: _create_pr_info(branch, pr_number)},
        pr_details={pr_number: _create_pr_details(branch, pr_number)},
    )
    ctx = ErkContext.for_test(git=fake_git, github=fake_github, repo_root=tmp_path)

    result = runner.invoke(
        update_pr_summary,
        [
            "--branch-name",
            branch,
            "--issue-number",
            "123",
            "--commit-sha",
            "invalid",
        ],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "commit_not_found"


def test_cli_pr_not_found(tmp_path: Path) -> None:
    """Test CLI command handles missing PR."""
    runner = CliRunner()
    commit_sha = "abc123"

    fake_git = FakeGit(
        commit_messages={commit_sha: "Message"},
    )
    fake_github = FakeGitHub(
        prs={},  # No PRs configured
        pr_details={},
    )
    ctx = ErkContext.for_test(git=fake_git, github=fake_github, repo_root=tmp_path)

    result = runner.invoke(
        update_pr_summary,
        [
            "--branch-name",
            "no-pr",
            "--issue-number",
            "123",
            "--commit-sha",
            commit_sha,
        ],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "pr_not_found"


def test_cli_github_api_failure(tmp_path: Path) -> None:
    """Test CLI command handles GitHub API failure."""
    runner = CliRunner()
    branch = "branch"
    pr_number = 123
    commit_sha = "abc123"

    fake_git = FakeGit(
        commit_messages={commit_sha: "Message"},
    )
    fake_github = FakeGitHub(
        prs={branch: _create_pr_info(branch, pr_number)},
        pr_details={pr_number: _create_pr_details(branch, pr_number)},
        pr_update_should_succeed=False,  # Configure to fail on update
    )
    ctx = ErkContext.for_test(git=fake_git, github=fake_github, repo_root=tmp_path)

    result = runner.invoke(
        update_pr_summary,
        [
            "--branch-name",
            branch,
            "--issue-number",
            "456",
            "--commit-sha",
            commit_sha,
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
        update_pr_summary,
        ["--branch-name", "branch"],  # Missing other required options
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output
