"""Unit tests for get_pr_number_for_branch kit CLI command.

Tests looking up PR numbers from branch names via GitHub API.
Uses FakeGitHub for dependency injection instead of mocking subprocess.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.abc import GitHub
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo

from dot_agent_kit.data.kits.erk.scripts.erk.get_pr_number_for_branch import (
    LookupError,
    LookupSuccess,
    _get_pr_number_for_branch_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.get_pr_number_for_branch import (
    get_pr_number_for_branch as get_pr_number_for_branch_command,
)


@dataclass
class CLIContext:
    """Context for CLI command injection in tests."""

    github: GitHub
    repo_root: Path


# ============================================================================
# 1. Implementation Logic Tests (3 tests)
# ============================================================================


def test_impl_finds_pr_for_branch(tmp_path: Path) -> None:
    """Test that PR number is returned when PR exists for branch."""
    pr_details = PRDetails(
        number=1895,
        url="https://github.com/owner/repo/pull/1895",
        title="Feature: Add new thing",
        body="Description",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )
    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=1895,
                state="OPEN",
                url="https://github.com/owner/repo/pull/1895",
                is_draft=False,
                title="Feature: Add new thing",
                checks_passing=True,
                owner="owner",
                repo="repo",
            )
        },
        pr_details={1895: pr_details},
    )

    result = _get_pr_number_for_branch_impl(github, tmp_path, "feature-branch")

    assert isinstance(result, LookupSuccess)
    assert result.success is True
    assert result.pr_number == 1895


def test_impl_returns_error_when_no_pr(tmp_path: Path) -> None:
    """Test error when no PR exists for branch."""
    github = FakeGitHub()  # No PRs configured

    result = _get_pr_number_for_branch_impl(github, tmp_path, "no-pr-branch")

    assert isinstance(result, LookupError)
    assert result.success is False
    assert result.error == "pr_not_found"


def test_impl_handles_different_branches(tmp_path: Path) -> None:
    """Test that correct PR is returned for each branch."""
    pr_details_1 = PRDetails(
        number=100,
        url="https://github.com/owner/repo/pull/100",
        title="PR 1",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="branch-a",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )
    pr_details_2 = PRDetails(
        number=200,
        url="https://github.com/owner/repo/pull/200",
        title="PR 2",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="branch-b",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )
    github = FakeGitHub(
        prs={
            "branch-a": PullRequestInfo(
                number=100,
                state="OPEN",
                url="...",
                is_draft=False,
                title="PR 1",
                checks_passing=True,
                owner="owner",
                repo="repo",
            ),
            "branch-b": PullRequestInfo(
                number=200,
                state="OPEN",
                url="...",
                is_draft=False,
                title="PR 2",
                checks_passing=True,
                owner="owner",
                repo="repo",
            ),
        },
        pr_details={100: pr_details_1, 200: pr_details_2},
    )

    result_a = _get_pr_number_for_branch_impl(github, tmp_path, "branch-a")
    result_b = _get_pr_number_for_branch_impl(github, tmp_path, "branch-b")

    assert isinstance(result_a, LookupSuccess)
    assert result_a.pr_number == 100
    assert isinstance(result_b, LookupSuccess)
    assert result_b.pr_number == 200


# ============================================================================
# 2. CLI Command Tests (3 tests)
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI returns PR number when found."""
    runner = CliRunner()
    pr_details = PRDetails(
        number=1234,
        url="https://github.com/owner/repo/pull/1234",
        title="Test PR",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="my-feature",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )
    github = FakeGitHub(
        prs={
            "my-feature": PullRequestInfo(
                number=1234,
                state="OPEN",
                url="...",
                is_draft=False,
                title="Test PR",
                checks_passing=True,
                owner="owner",
                repo="repo",
            )
        },
        pr_details={1234: pr_details},
    )
    ctx = CLIContext(github=github, repo_root=tmp_path)

    result = runner.invoke(
        get_pr_number_for_branch_command,
        ["--branch", "my-feature"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 1234


def test_cli_error_pr_not_found(tmp_path: Path) -> None:
    """Test CLI exits with error when PR not found."""
    runner = CliRunner()
    github = FakeGitHub()
    ctx = CLIContext(github=github, repo_root=tmp_path)

    result = runner.invoke(
        get_pr_number_for_branch_command,
        ["--branch", "nonexistent-branch"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "pr_not_found"


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    runner = CliRunner()
    pr_details = PRDetails(
        number=5678,
        url="https://github.com/owner/repo/pull/5678",
        title="Test",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="test-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )
    github = FakeGitHub(
        prs={
            "test-branch": PullRequestInfo(
                number=5678,
                state="OPEN",
                url="...",
                is_draft=False,
                title="Test",
                checks_passing=True,
                owner="owner",
                repo="repo",
            )
        },
        pr_details={5678: pr_details},
    )
    ctx = CLIContext(github=github, repo_root=tmp_path)

    result = runner.invoke(
        get_pr_number_for_branch_command,
        ["--branch", "test-branch"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "pr_number" in output
    assert isinstance(output["success"], bool)
    assert isinstance(output["pr_number"], int)
