"""Tests for the current command using fakes (fast integration tests).

These tests use FakeGit with pre-configured WorktreeInfo data instead of
real git operations, providing 5-10x speedup while maintaining full CLI coverage.
"""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit

from erk.cli.cli import cli
from erk.core.config_store import FakeConfigStore, GlobalConfig
from erk.core.context import context_for_test
from tests.test_utils.env_helpers import erk_inmem_env


def test_current_returns_worktree_name() -> None:
    """Test that current returns worktree name when in named worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Construct sentinel paths (no filesystem operations needed)
        work_dir = env.erk_root / env.cwd.name
        feature_x_path = work_dir / "feature-x"

        # Configure FakeGit with worktrees - feature-x is current
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_x_path, branch="feature-x", is_root=False),
                ]
            },
            current_branches={
                env.cwd: "main",
                feature_x_path: "feature-x",
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                feature_x_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        # Use env.build_context() helper to eliminate boilerplate
        test_ctx = env.build_context(git=git_ops, cwd=feature_x_path, repo=env.repo)

        # Run current command
        result = runner.invoke(cli, ["wt", "current"], obj=test_ctx)

        assert result.exit_code == 0
        assert result.output.strip() == "feature-x"


def test_current_returns_root_in_root_repository() -> None:
    """Test that current returns 'root' when in root repository."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Configure FakeGit with just root worktree
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Use env.build_context() helper to eliminate boilerplate
        test_ctx = env.build_context(git=git_ops, cwd=env.cwd, repo=env.repo)

        # Run current command
        result = runner.invoke(cli, ["wt", "current"], obj=test_ctx)

        assert result.exit_code == 0
        assert result.output.strip() == "root"


def test_current_exits_with_error_when_not_in_worktree() -> None:
    """Test that current exits with code 1 when not in any worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Construct sentinel path outside any worktree (no mkdir needed)
        outside_dir = env.cwd.parent / "outside"

        # Configure FakeGit with worktrees, but we'll run from outside
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # Use env.build_context() helper to eliminate boilerplate
        test_ctx = env.build_context(git=git_ops, cwd=outside_dir, repo=None)

        # Run current command from outside directory (no os.chdir needed)
        result = runner.invoke(cli, ["wt", "current"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Not in an erk worktree" in result.output


def test_current_works_from_subdirectory() -> None:
    """Test that current returns worktree name from subdirectory within worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Construct sentinel paths (no filesystem operations needed)
        work_dir = env.erk_root / env.cwd.name
        feature_y_path = work_dir / "feature-y"
        subdir = feature_y_path / "src" / "nested"

        # Configure FakeGit with worktrees
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_y_path, branch="feature-y", is_root=False),
                ]
            },
            current_branches={
                env.cwd: "main",
                feature_y_path: "feature-y",
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                feature_y_path: env.git_dir,
                subdir: env.git_dir,  # Subdirectory also maps to same git dir
            },
            default_branches={env.cwd: "main"},
        )

        # Use env.build_context() helper to eliminate boilerplate
        test_ctx = env.build_context(git=git_ops, cwd=subdir, repo=env.repo)

        # Run current command from subdirectory (no os.chdir needed)
        result = runner.invoke(cli, ["wt", "current"], obj=test_ctx)

        assert result.exit_code == 0
        assert result.output.strip() == "feature-y"


def test_current_handles_missing_git_gracefully(tmp_path: Path) -> None:
    """Test that current exits with code 1 when not in a git repository."""
    non_git_dir = tmp_path / "not-git"
    non_git_dir.mkdir()
    erk_root = tmp_path / "erks"

    # No git_common_dir configured = not in git repo
    git_ops = FakeGit(git_common_dirs={})

    # Create global config
    global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)
    global_config_ops = FakeConfigStore(config=global_config)

    ctx = context_for_test(
        cwd=non_git_dir,
        git=git_ops,
        config_store=global_config_ops,
        global_config=global_config,
        repo=None,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["wt", "current"], obj=ctx)

    assert result.exit_code == 1
    # When not in a git repo, discovery fails before we check worktrees
    assert result.output.strip() == ""


def test_current_handles_nested_worktrees(tmp_path: Path) -> None:
    """Test that current returns deepest worktree for nested structures."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    erk_root = tmp_path / "erks"
    parent_wt = erk_root / "repo" / "parent"
    parent_wt.mkdir(parents=True)
    nested_wt = parent_wt / "nested"
    nested_wt.mkdir()
    target_dir = nested_wt / "src"
    target_dir.mkdir()

    # Set up nested worktrees: root contains parent, parent contains nested
    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main", is_root=True),
                WorktreeInfo(path=parent_wt, branch="parent", is_root=False),
                WorktreeInfo(path=nested_wt, branch="nested", is_root=False),
            ]
        },
        git_common_dirs={
            target_dir: repo_root / ".git",
        },
        existing_paths={repo_root, parent_wt, nested_wt, target_dir, repo_root / ".git"},
        trunk_branches={repo_root: "main"},
    )

    # Create global config
    global_config = GlobalConfig.test(erk_root, use_graphite=False, shell_setup_complete=False)
    global_config_ops = FakeConfigStore(config=global_config)

    ctx = context_for_test(
        cwd=target_dir,
        git=git_ops,
        config_store=global_config_ops,
        global_config=global_config,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["wt", "current"], obj=ctx)

    # Should return the deepest (most specific) worktree
    assert result.exit_code == 0
    assert result.output.strip() == "nested"
