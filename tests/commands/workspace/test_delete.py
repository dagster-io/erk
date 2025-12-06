"""Tests for erk wt delete command.

This file tests the delete command which removes a worktree workspace.
"""

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.dry_run import DryRunGit
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from erk_shared.scratch.markers import PENDING_EXTRACTION_MARKER, create_marker

from erk.cli.cli import cli
from tests.fakes.shell import FakeShell
from tests.test_utils.cli_helpers import assert_cli_error, assert_cli_success
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_delete_force_removes_directory() -> None:
    """Test that delete with --force flag removes the worktree directory."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "foo"

        test_ctx = build_workspace_test_context(env, existing_paths={wt})
        result = runner.invoke(cli, ["wt", "delete", "foo", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert result.output.strip().endswith(str(wt))


def test_delete_prompts_and_aborts_on_no() -> None:
    """Test that delete prompts for confirmation and aborts when user says no."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "bar"

        test_ctx = build_workspace_test_context(env, existing_paths={wt})
        result = runner.invoke(cli, ["wt", "delete", "bar"], input="n\n", obj=test_ctx)

        assert_cli_success(result)
        # User aborted, so worktree should still exist (check via git_ops state)
        assert test_ctx.git.path_exists(wt)


def test_delete_dry_run_does_not_delete() -> None:
    """Test that dry-run mode prints actions but doesn't delete."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-stack"

        test_ctx = build_workspace_test_context(env, dry_run=True, existing_paths={wt})
        result = runner.invoke(cli, ["wt", "delete", "test-stack", "-f"], obj=test_ctx)

        assert_cli_success(
            result,
            "[DRY RUN]",
            "Would run: git worktree remove",
        )
        # Directory should still exist (check via git_ops state)
        assert test_ctx.git.path_exists(wt)


def test_delete_dry_run_with_branch() -> None:
    """Test dry-run with --branch flag prints but doesn't delete branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-branch"

        # Build fake git ops with worktree info
        fake_git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature")]},
            git_common_dirs={env.cwd: env.git_dir},
        )
        git_ops = DryRunGit(fake_git_ops)

        # Build graphite ops with branch metadata
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature"]),
            "feature": BranchMetadata.branch("feature", "main"),
        }

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(branches=branches),
            shell=FakeShell(),
            dry_run=True,
            existing_paths={wt},
        )

        result = runner.invoke(cli, ["wt", "delete", "test-branch", "-f", "-b"], obj=test_ctx)

        assert_cli_success(result, "[DRY RUN]", "Would run: gt delete")
        assert len(fake_git_ops.deleted_branches) == 0  # No actual deletion
        # Directory should still exist (check via git_ops state)
        assert test_ctx.git.path_exists(wt)


def test_delete_rejects_dot_dot() -> None:
    """Test that delete rejects '..' as a worktree name."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        test_ctx = build_workspace_test_context(env)
        result = runner.invoke(cli, ["wt", "delete", "..", "-f"], obj=test_ctx)

        assert_cli_error(result, 1, "Error: Cannot delete '..'", "directory references not allowed")


def test_delete_rejects_root_slash() -> None:
    """Test that delete rejects '/' as a worktree name."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        test_ctx = build_workspace_test_context(env)
        result = runner.invoke(cli, ["wt", "delete", "/", "-f"], obj=test_ctx)

        assert_cli_error(result, 1, "Error: Cannot delete '/'", "absolute paths not allowed")


def test_delete_rejects_path_with_slash() -> None:
    """Test that delete rejects worktree names containing path separators."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        test_ctx = build_workspace_test_context(env)
        result = runner.invoke(cli, ["wt", "delete", "foo/bar", "-f"], obj=test_ctx)

        assert_cli_error(result, 1, "Error: Cannot delete 'foo/bar'", "path separators not allowed")


def test_delete_rejects_root_name() -> None:
    """Test that delete rejects 'root' as a worktree name."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        test_ctx = build_workspace_test_context(env)
        result = runner.invoke(cli, ["wt", "delete", "root", "-f"], obj=test_ctx)

        assert_cli_error(result, 1, "Error: Cannot delete 'root'", "root worktree name not allowed")


def test_delete_changes_directory_when_in_target_worktree() -> None:
    """Test that delete automatically changes to repo root when user is in target worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt_path = env.erk_root / "repos" / repo_name / "worktrees" / "feature"

        # Set up worktree paths
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt_path, branch="feature", is_root=False),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, wt_path: env.git_dir},
            current_branches={env.cwd: "main", wt_path: "feature"},
        )

        # Build context with cwd set to the worktree being deleted
        test_ctx = env.build_context(git=git_ops, cwd=wt_path, existing_paths={wt_path})

        # Execute delete command with --force to skip confirmation
        result = runner.invoke(cli, ["wt", "delete", "feature", "-f"], obj=test_ctx)

        # Should succeed and show directory change message
        assert_cli_success(result, "Changing directory to repository root", str(env.cwd))


def test_delete_with_branch_without_graphite() -> None:
    """Test that --branch works without Graphite enabled (uses git branch -d)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-branch"

        # Build fake git ops with worktree info
        fake_git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Build context with use_graphite=False (default)
        test_ctx = env.build_context(
            use_graphite=False,
            git=fake_git_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            existing_paths={wt},
        )

        # Execute: Run delete with --branch when graphite is disabled
        result = runner.invoke(
            cli,
            ["wt", "delete", "test-branch", "--branch", "-f"],
            obj=test_ctx,
        )

        # Assert: Command should succeed and use git branch -d
        assert_cli_success(result)
        assert "feature" in fake_git_ops.deleted_branches


def test_delete_with_branch_with_graphite() -> None:
    """Test that --branch with Graphite enabled uses gt delete."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-branch"

        # Build fake git ops with worktree info
        fake_git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Build graphite ops with branch metadata
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature"]),
            "feature": BranchMetadata.branch("feature", "main"),
        }

        test_ctx = env.build_context(
            use_graphite=True,
            git=fake_git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(branches=branches),
            shell=FakeShell(),
            existing_paths={wt},
        )

        # Execute: Run delete with --branch when graphite is enabled
        result = runner.invoke(
            cli,
            ["wt", "delete", "test-branch", "--branch", "-f"],
            obj=test_ctx,
        )

        # Assert: Command should succeed and branch should be deleted
        assert_cli_success(result)
        assert "feature" in fake_git_ops.deleted_branches


def test_delete_with_branch_graphite_enabled_but_untracked() -> None:
    """Test --branch falls back to git branch -D when Graphite enabled but branch untracked."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-branch"

        # Build fake git ops with worktree info
        fake_git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="untracked-feature")]},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Build graphite ops WITHOUT the branch being tracked
        # Only main is tracked, "untracked-feature" is not in Graphite's branches
        branches = {
            "main": BranchMetadata.trunk("main"),
        }

        test_ctx = env.build_context(
            use_graphite=True,
            git=fake_git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(branches=branches),
            shell=FakeShell(),
            existing_paths={wt},
        )

        # Execute: Run delete with --branch when graphite is enabled but branch is not tracked
        result = runner.invoke(
            cli,
            ["wt", "delete", "test-branch", "--branch", "-f"],
            obj=test_ctx,
        )

        # Assert: Command should succeed and use git branch -D (not gt delete)
        assert_cli_success(result)
        assert "untracked-feature" in fake_git_ops.deleted_branches
        # The branch should be deleted via git, not graphite
        # Since FakeGit.delete_branch is used, the branch appears in deleted_branches


def test_delete_blocks_when_pending_extraction_marker_exists() -> None:
    """Test that delete blocks when pending extraction marker exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "foo"

        # Create the pending extraction marker
        create_marker(wt, PENDING_EXTRACTION_MARKER)

        test_ctx = build_workspace_test_context(env, existing_paths={wt})
        result = runner.invoke(cli, ["wt", "delete", "foo"], obj=test_ctx)

        assert_cli_error(
            result,
            1,
            "Worktree has pending extraction",
            "erk plan extraction raw",
        )

        # Verify worktree was NOT deleted
        assert test_ctx.git.path_exists(wt)


def test_delete_force_bypasses_pending_extraction_marker() -> None:
    """Test that delete --force bypasses the pending extraction marker check."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "foo"

        # Create the pending extraction marker
        create_marker(wt, PENDING_EXTRACTION_MARKER)

        test_ctx = build_workspace_test_context(env, existing_paths={wt})
        result = runner.invoke(cli, ["wt", "delete", "foo", "-f"], obj=test_ctx)

        # Should succeed with warning
        assert result.exit_code == 0
        assert "Skipping pending extraction" in result.output

        # Verify worktree was deleted
        assert not test_ctx.git.path_exists(wt)
