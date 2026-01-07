"""Tests for erk wt checkout command (and co alias)."""

import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_checkout_named_worktree() -> None:
    """Test navigating to an existing worktree by name using 'co' alias."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up worktrees: root on main, feature-work on feature-1
        worktree_path = env.repo.worktrees_dir / "feature-work"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature-1", is_root=False),
                ]
            },
            current_branches={env.cwd: "main", worktree_path: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Navigate to feature-work worktree using 'co' alias
        result = runner.invoke(
            cli,
            ["wt", "co", "feature-work", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: Script path is in stdout
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None

        # Assert: Script contains cd to worktree
        assert str(worktree_path) in script_content


def test_checkout_root() -> None:
    """Test navigating to root worktree using 'root' keyword."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up worktrees: root on main, feature-work on feature-1
        worktree_path = env.repo.worktrees_dir / "feature-work"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature-1", is_root=False),
                ]
            },
            current_branches={env.cwd: "main", worktree_path: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Navigate to root using special keyword
        result = runner.invoke(
            cli,
            ["wt", "co", "root", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: Script path is in stdout
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None

        # Assert: Script contains cd to root
        assert str(env.cwd) in script_content


def test_checkout_nonexistent_worktree() -> None:
    """Test error when worktree doesn't exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up worktrees: only root exists
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Try to navigate to non-existent worktree
        result = runner.invoke(
            cli,
            ["wt", "co", "nonexistent"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command failed
        assert result.exit_code == 1

        # Assert: Error message shows available worktrees
        assert "Error:" in result.output
        assert "Worktree 'nonexistent' not found" in result.output
        assert "Available worktrees:" in result.output
        assert "'root'" in result.output


def test_checkout_shows_branch_info_with_shell_integration() -> None:
    """Test that output includes branch name in non-script mode with shell integration."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up worktrees: root on main, feature-work on feature-1
        worktree_path = env.repo.worktrees_dir / "feature-work"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature-1", is_root=False),
                ]
            },
            current_branches={env.cwd: "main", worktree_path: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Navigate to feature-work worktree WITHOUT --script flag
        # With shell integration active, shows branch info
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                cli,
                ["wt", "co", "feature-work"],
                obj=test_ctx,
                catch_exceptions=False,
            )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: Output shows worktree name and branch
        assert "feature-work" in result.output
        assert "feature-1" in result.output


def test_checkout_spawns_subshell_without_shell_integration() -> None:
    """Test that non-script mode without shell integration spawns subshell."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up worktrees: root on main, feature-work on feature-1
        worktree_path = env.repo.worktrees_dir / "feature-work"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="feature-1", is_root=False),
                ]
            },
            current_branches={env.cwd: "main", worktree_path: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Navigate to feature-work worktree WITHOUT --script flag
        # Without shell integration, spawns subshell with welcome banner
        env_copy = {k: v for k, v in os.environ.items() if k != "ERK_SHELL"}
        with patch.dict(os.environ, env_copy, clear=True):
            result = runner.invoke(
                cli,
                ["wt", "co", "feature-work"],
                obj=test_ctx,
                catch_exceptions=False,
            )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: Output shows subshell welcome banner
        assert "worktree subshell" in result.output
        assert "exit" in result.output


def test_checkout_script_mode() -> None:
    """Test that --script flag generates activation script."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up worktrees
        worktree_path = env.repo.worktrees_dir / "my-feature"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch="my-feature", is_root=False),
                ]
            },
            current_branches={env.cwd: "main", worktree_path: "my-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Navigate with --script flag
        result = runner.invoke(
            cli,
            ["wt", "checkout", "my-feature", "--script"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: Output contains script path (not user messages)
        script_path_str = result.stdout.strip()
        assert script_path_str != ""

        # Assert: Script is valid and contains cd command
        script_path = Path(script_path_str)
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(worktree_path) in script_content


def test_checkout_branch_name_hint() -> None:
    """Test that providing a branch-like name shows helpful hint."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up worktrees: only root exists
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops)

        # Act: Try to navigate using a branch-like name (contains '/')
        result = runner.invoke(
            cli,
            ["wt", "co", "feature/branch-name"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command failed
        assert result.exit_code == 1

        # Assert: Error message suggests using checkout for branch names
        assert "Error:" in result.output
        assert "Hint:" in result.output
        assert "erk br co" in result.output
