"""Tests for erk goto command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_goto_named_worktree() -> None:
    """Test navigating to an existing worktree by name."""
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

        # Act: Navigate to feature-work worktree
        result = runner.invoke(
            cli,
            ["wt", "goto", "feature-work", "--script"],
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


def test_goto_root() -> None:
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
            ["wt", "goto", "root", "--script"],
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


def test_goto_nonexistent_worktree() -> None:
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
            ["wt", "goto", "nonexistent"],
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


def test_goto_shows_branch_info() -> None:
    """Test that output includes branch name in non-script mode."""
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
        # (but shell integration not detected, so will show manual instructions)
        result = runner.invoke(
            cli,
            ["wt", "goto", "feature-work"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Assert: Output shows worktree name and branch
        assert "feature-work" in result.output
        assert "feature-1" in result.output


def test_goto_script_mode() -> None:
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
            ["wt", "goto", "my-feature", "--script"],
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


def test_goto_branch_name_hint() -> None:
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
            ["wt", "goto", "feature/branch-name"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        # Assert: Command failed
        assert result.exit_code == 1

        # Assert: Error message suggests using checkout for branch names
        assert "Error:" in result.output
        assert "Hint:" in result.output
        assert "erk checkout" in result.output
