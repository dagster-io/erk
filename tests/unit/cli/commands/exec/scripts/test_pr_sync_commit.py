"""Unit tests for pr-sync-commit exec CLI command.

Tests the PR sync from commit functionality using FakeGit and FakeGitHub
for dependency injection.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.pr_sync_commit import (
    SyncError,
    SyncSuccess,
    _sync_pr_from_commit,
)
from erk.cli.commands.exec.scripts.pr_sync_commit import (
    pr_sync_commit as pr_sync_commit_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo

# ============================================================================
# Implementation Logic Tests
# ============================================================================


def test_impl_success_basic(tmp_path: Path) -> None:
    """Test successful PR sync from commit."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "Fix the bug\n\nThis fixes issue #123"},
    )

    pr_details = PRDetails(
        number=456,
        url="https://github.com/owner/repo/pull/456",
        title="Old title",
        body="Old body content",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=456,
                state="OPEN",
                url="https://github.com/owner/repo/pull/456",
                is_draft=False,
                title="Old title",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={456: pr_details},
    )

    result = _sync_pr_from_commit(git=git, github=github, repo_root=tmp_path)

    assert isinstance(result, SyncSuccess)
    assert result.success is True
    assert result.pr_number == 456
    assert result.title == "Fix the bug"
    assert result.header_preserved is False
    assert result.footer_preserved is False


def test_impl_preserves_header(tmp_path: Path) -> None:
    """Test that header is preserved during sync."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "New title\n\nNew body content"},
    )

    pr_details = PRDetails(
        number=456,
        url="https://github.com/owner/repo/pull/456",
        title="Old title",
        body="**Plan:** #123\n\nOld body content",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=456,
                state="OPEN",
                url="https://github.com/owner/repo/pull/456",
                is_draft=False,
                title="Old title",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={456: pr_details},
    )

    result = _sync_pr_from_commit(git=git, github=github, repo_root=tmp_path)

    assert isinstance(result, SyncSuccess)
    assert result.header_preserved is True

    # Verify the updated body contains the header
    assert len(github.updated_pr_bodies) == 1
    _pr_num, updated_body = github.updated_pr_bodies[0]
    assert "**Plan:** #123" in updated_body
    assert "New body content" in updated_body


def test_impl_preserves_footer(tmp_path: Path) -> None:
    """Test that footer is preserved during sync."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "New title\n\nNew body content"},
    )

    pr_details = PRDetails(
        number=456,
        url="https://github.com/owner/repo/pull/456",
        title="Old title",
        body="Old body\n\n---\n\nCloses #789\n\nCheckout instructions",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=456,
                state="OPEN",
                url="https://github.com/owner/repo/pull/456",
                is_draft=False,
                title="Old title",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={456: pr_details},
    )

    result = _sync_pr_from_commit(git=git, github=github, repo_root=tmp_path)

    assert isinstance(result, SyncSuccess)
    assert result.footer_preserved is True

    # Verify the updated body contains the footer
    assert len(github.updated_pr_bodies) == 1
    _pr_num, updated_body = github.updated_pr_bodies[0]
    assert "Closes #789" in updated_body
    assert "New body content" in updated_body


def test_impl_preserves_both_header_and_footer(tmp_path: Path) -> None:
    """Test that both header and footer are preserved."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "New title\n\nNew body content"},
    )

    pr_details = PRDetails(
        number=456,
        url="https://github.com/owner/repo/pull/456",
        title="Old title",
        body=(
            "**Plan:** #123\n"
            "**Remotely executed:** [Run #999](https://example.com)\n\n"
            "Old body\n"
            "\n---\n"
            "Closes #789"
        ),
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=456,
                state="OPEN",
                url="https://github.com/owner/repo/pull/456",
                is_draft=False,
                title="Old title",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={456: pr_details},
    )

    result = _sync_pr_from_commit(git=git, github=github, repo_root=tmp_path)

    assert isinstance(result, SyncSuccess)
    assert result.header_preserved is True
    assert result.footer_preserved is True

    # Verify updated body structure
    _pr_num, updated_body = github.updated_pr_bodies[0]
    assert "**Plan:** #123" in updated_body
    assert "**Remotely executed:**" in updated_body
    assert "New body content" in updated_body
    assert "Closes #789" in updated_body


def test_impl_uses_title_as_body_when_no_body(tmp_path: Path) -> None:
    """Test that commit title is used as body when commit has no body."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "Single line commit message"},
    )

    pr_details = PRDetails(
        number=456,
        url="https://github.com/owner/repo/pull/456",
        title="Old title",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=456,
                state="OPEN",
                url="https://github.com/owner/repo/pull/456",
                is_draft=False,
                title="Old title",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={456: pr_details},
    )

    result = _sync_pr_from_commit(git=git, github=github, repo_root=tmp_path)

    assert isinstance(result, SyncSuccess)
    assert result.title == "Single line commit message"

    # Body should contain the title
    _pr_num, updated_body = github.updated_pr_bodies[0]
    assert "Single line commit message" in updated_body


def test_impl_no_pr_for_branch(tmp_path: Path) -> None:
    """Test error when no PR exists for the branch."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "Commit message"},
    )

    github = FakeGitHub()  # No PRs configured

    result = _sync_pr_from_commit(git=git, github=github, repo_root=tmp_path)

    assert isinstance(result, SyncError)
    assert result.success is False
    assert result.error == "pr-not-found"


def test_impl_not_on_branch(tmp_path: Path) -> None:
    """Test error when in detached HEAD state."""
    git = FakeGit(
        current_branches={tmp_path: None},  # Detached HEAD
        head_commit_messages_full={tmp_path: "Commit message"},
    )

    github = FakeGitHub()

    result = _sync_pr_from_commit(git=git, github=github, repo_root=tmp_path)

    assert isinstance(result, SyncError)
    assert result.success is False
    assert result.error == "not-on-branch"


# ============================================================================
# CLI Command Tests
# ============================================================================


def test_cli_success_human_readable(tmp_path: Path) -> None:
    """Test CLI command with human-readable output."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "Fix the bug\n\nDescription here"},
    )

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Old title",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Old title",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
    )

    ctx = ErkContext.for_test(git=git, github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(pr_sync_commit_command, [], obj=ctx)

    assert result.exit_code == 0
    assert "PR #123 updated" in result.output
    assert "Title: Fix the bug" in result.output
    assert "Header preserved: no" in result.output
    assert "Footer preserved: no" in result.output


def test_cli_success_json(tmp_path: Path) -> None:
    """Test CLI command with JSON output."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "Fix the bug\n\nDescription here"},
    )

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Old title",
        body="**Plan:** #456\n\nOld body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Old title",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
    )

    ctx = ErkContext.for_test(git=git, github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(pr_sync_commit_command, ["--json"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert output["title"] == "Fix the bug"
    assert output["header_preserved"] is True
    assert output["footer_preserved"] is False


def test_cli_error_exit_code(tmp_path: Path) -> None:
    """Test CLI command exits with error code on failure."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "Commit message"},
    )

    github = FakeGitHub()  # No PRs

    ctx = ErkContext.for_test(git=git, github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(pr_sync_commit_command, [], obj=ctx)

    assert result.exit_code == 1


def test_cli_error_json_structure(tmp_path: Path) -> None:
    """Test CLI command JSON error output structure."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "Commit message"},
    )

    github = FakeGitHub()  # No PRs

    ctx = ErkContext.for_test(git=git, github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(pr_sync_commit_command, ["--json"], obj=ctx)

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "error" in output
    assert "message" in output


def test_cli_updates_pr_title(tmp_path: Path) -> None:
    """Test that CLI command updates the PR title."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        head_commit_messages_full={tmp_path: "New commit title\n\nBody text"},
    )

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Old title",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Old title",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
    )

    ctx = ErkContext.for_test(git=git, github=github, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(pr_sync_commit_command, [], obj=ctx)

    assert result.exit_code == 0

    # Verify title was updated
    assert len(github.updated_pr_titles) == 1
    pr_num, new_title = github.updated_pr_titles[0]
    assert pr_num == 123
    assert new_title == "New commit title"
