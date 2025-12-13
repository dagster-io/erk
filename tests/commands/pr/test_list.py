"""Tests for erk pr list command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_list_shows_open_prs(tmp_path: Path) -> None:
    """Test that pr list shows open PRs authored by the user."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup multiple open PRs
        pr_details_123 = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Add feature A",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-a",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        pr_details_456 = PRDetails(
            number=456,
            url="https://github.com/owner/repo/pull/456",
            title="Fix bug B",
            body="",
            state="OPEN",
            is_draft=True,
            base_ref_name="main",
            head_ref_name="fix-bug-b",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )

        github = FakeGitHub(
            pr_details={123: pr_details_123, 456: pr_details_456},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["list"], obj=ctx)

        assert result.exit_code == 0
        assert "#123" in result.output
        assert "Add feature A" in result.output
        assert "#456" in result.output
        assert "Fix bug B" in result.output


def test_pr_list_shows_empty_message_when_no_prs(tmp_path: Path) -> None:
    """Test that pr list shows informative message when no open PRs exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # No PRs configured
        github = FakeGitHub(pr_details={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["list"], obj=ctx)

        assert result.exit_code == 0
        assert "No open pull requests found" in result.output


def test_pr_list_alias_ls_works(tmp_path: Path) -> None:
    """Test that 'pr ls' alias works."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Test PR",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )

        github = FakeGitHub(pr_details={123: pr_details})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["ls"], obj=ctx)

        assert result.exit_code == 0
        assert "#123" in result.output


def test_pr_list_excludes_closed_prs(tmp_path: Path) -> None:
    """Test that pr list only shows open PRs, not closed or merged ones."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Open PR should be shown
        pr_open = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Open PR",
            body="",
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="open-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        # Closed PR should NOT be shown
        pr_closed = PRDetails(
            number=456,
            url="https://github.com/owner/repo/pull/456",
            title="Closed PR",
            body="",
            state="CLOSED",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="closed-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        # Merged PR should NOT be shown
        pr_merged = PRDetails(
            number=789,
            url="https://github.com/owner/repo/pull/789",
            title="Merged PR",
            body="",
            state="MERGED",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="merged-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )

        github = FakeGitHub(
            pr_details={123: pr_open, 456: pr_closed, 789: pr_merged},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["list"], obj=ctx)

        assert result.exit_code == 0
        assert "#123" in result.output
        assert "Open PR" in result.output
        # Closed and merged PRs should not appear
        assert "#456" not in result.output
        assert "Closed PR" not in result.output
        assert "#789" not in result.output
        assert "Merged PR" not in result.output


def test_pr_list_shows_draft_indicator(tmp_path: Path) -> None:
    """Test that draft PRs show appropriate status indicator."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Draft PR
        pr_draft = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Draft feature",
            body="",
            state="OPEN",
            is_draft=True,
            base_ref_name="main",
            head_ref_name="draft-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )

        github = FakeGitHub(pr_details={123: pr_draft})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "main"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["list"], obj=ctx)

        assert result.exit_code == 0
        assert "#123" in result.output
        # Draft PRs show the construction emoji
        assert "🚧" in result.output
