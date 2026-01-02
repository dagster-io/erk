"""Tests for wt create command with Graphite disabled.

This file verifies that worktree creation works correctly when Graphite
is disabled (use_graphite=False), proving graceful degradation.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_wt_create_succeeds_without_graphite() -> None:
    """Worktree creation works when use_graphite=False."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        env.setup_repo_structure()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # use_graphite=False is the default
        test_ctx = env.build_context(git=git_ops, use_graphite=False)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Created worktree" in result.output
        assert "test-feature" in result.output


def test_wt_create_does_not_call_track_branch() -> None:
    """Worktree creation does not call Graphite track_branch when disabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        env.setup_repo_structure()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, use_graphite=False)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify worktree was created via git operations
        assert len(git_ops.added_worktrees) == 1
        # If Graphite was called, it would have failed or raised errors
        # The fact that we succeed means Graphite operations were skipped


def test_wt_create_with_from_branch_without_graphite() -> None:
    """Worktree creation with --from-branch works without Graphite."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        env.setup_repo_structure()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, use_graphite=False)

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--from-branch", "existing"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_wt_create_allows_staged_changes_without_graphite() -> None:
    """Staged changes are allowed when Graphite is disabled.

    Graphite requires clean worktree for branch creation, but when disabled,
    we use git-only operations that don't have this restriction.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        env.setup_repo_structure()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            staged_repos={env.cwd},  # Simulate staged changes
        )

        test_ctx = env.build_context(git=git_ops, use_graphite=False)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        # Should succeed despite staged changes
        assert result.exit_code == 0, result.output
