"""Tests for wt list command filtering of empty slots (placeholder branches).

By default, `erk wt list` should hide worktrees that have placeholder branches
(e.g., `__erk-slot-07-placeholder__`), which represent unassigned slots in the
worktree pool. The `--all` flag overrides this to show all worktrees.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_wt_list_hides_placeholder_branches_by_default() -> None:
    """Placeholder branches are hidden by default in worktree listing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        empty_slot_path = repo_dir / "worktrees" / "erk-managed-wt-02"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_path, branch="my-feature", is_root=False),
                    WorktreeInfo(
                        path=empty_slot_path,
                        branch="__erk-slot-02-placeholder__",
                        is_root=False,
                    ),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                feature_path: env.git_dir,
                empty_slot_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={feature_path, empty_slot_path})

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Root and feature worktree should be visible
        assert "root" in result.output
        assert "erk-managed-wt-01" in result.output
        # Empty slot should be hidden
        assert "erk-managed-wt-02" not in result.output
        assert "__erk-slot-02-placeholder__" not in result.output


def test_wt_list_all_flag_shows_placeholder_branches() -> None:
    """The --all flag shows placeholder branches in worktree listing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        empty_slot_path = repo_dir / "worktrees" / "erk-managed-wt-02"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_path, branch="my-feature", is_root=False),
                    WorktreeInfo(
                        path=empty_slot_path,
                        branch="__erk-slot-02-placeholder__",
                        is_root=False,
                    ),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                feature_path: env.git_dir,
                empty_slot_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={feature_path, empty_slot_path})

        result = runner.invoke(cli, ["wt", "list", "--all"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # All worktrees should be visible with --all
        assert "root" in result.output
        assert "erk-managed-wt-01" in result.output
        assert "erk-managed-wt-02" in result.output


def test_wt_list_short_all_flag() -> None:
    """The -a short flag works the same as --all."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        empty_slot_path = repo_dir / "worktrees" / "erk-managed-wt-03"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(
                        path=empty_slot_path,
                        branch="__erk-slot-03-placeholder__",
                        is_root=False,
                    ),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                empty_slot_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={empty_slot_path})

        result = runner.invoke(cli, ["wt", "list", "-a"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Empty slot should be visible with -a flag
        assert "erk-managed-wt-03" in result.output


def test_wt_list_hides_multiple_placeholder_branches() -> None:
    """Multiple placeholder branches are all hidden by default."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        slot1_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        slot2_path = repo_dir / "worktrees" / "erk-managed-wt-02"
        slot3_path = repo_dir / "worktrees" / "erk-managed-wt-03"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(
                        path=slot1_path,
                        branch="__erk-slot-01-placeholder__",
                        is_root=False,
                    ),
                    WorktreeInfo(
                        path=slot2_path,
                        branch="__erk-slot-02-placeholder__",
                        is_root=False,
                    ),
                    WorktreeInfo(
                        path=slot3_path,
                        branch="__erk-slot-03-placeholder__",
                        is_root=False,
                    ),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                slot1_path: env.git_dir,
                slot2_path: env.git_dir,
                slot3_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(
            git=git_ops, existing_paths={slot1_path, slot2_path, slot3_path}
        )

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Only root should be visible
        assert "root" in result.output
        assert "erk-managed-wt-01" not in result.output
        assert "erk-managed-wt-02" not in result.output
        assert "erk-managed-wt-03" not in result.output


def test_wt_list_preserves_non_placeholder_worktrees() -> None:
    """Non-placeholder worktrees are always shown regardless of flags."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        wt1_path = repo_dir / "worktrees" / "feature-a"
        wt2_path = repo_dir / "worktrees" / "feature-b"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt1_path, branch="feature-a", is_root=False),
                    WorktreeInfo(path=wt2_path, branch="feature-b", is_root=False),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                wt1_path: env.git_dir,
                wt2_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={wt1_path, wt2_path})

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "root" in result.output
        assert "feature-a" in result.output
        assert "feature-b" in result.output


def test_wt_list_detached_head_not_filtered() -> None:
    """Worktrees with detached HEAD (branch=None) are not filtered."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        detached_path = repo_dir / "worktrees" / "detached-wt"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=detached_path, branch=None, is_root=False),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                detached_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={detached_path})

        result = runner.invoke(cli, ["wt", "list"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Detached HEAD worktree should still be visible
        assert "detached-wt" in result.output


def test_wt_list_ls_alias_respects_filtering() -> None:
    """The 'ls' alias also filters placeholder branches by default."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        empty_slot_path = repo_dir / "worktrees" / "erk-managed-wt-05"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(
                        path=empty_slot_path,
                        branch="__erk-slot-05-placeholder__",
                        is_root=False,
                    ),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                empty_slot_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={empty_slot_path})

        result = runner.invoke(cli, ["wt", "ls"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Empty slot should be hidden even with 'ls' alias
        assert "erk-managed-wt-05" not in result.output


def test_wt_list_ls_alias_all_flag() -> None:
    """The 'ls' alias supports the --all flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        empty_slot_path = repo_dir / "worktrees" / "erk-managed-wt-05"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(
                        path=empty_slot_path,
                        branch="__erk-slot-05-placeholder__",
                        is_root=False,
                    ),
                ]
            },
            git_common_dirs={
                env.cwd: env.git_dir,
                empty_slot_path: env.git_dir,
            },
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops, existing_paths={empty_slot_path})

        result = runner.invoke(cli, ["wt", "ls", "--all"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Empty slot should be visible with --all
        assert "erk-managed-wt-05" in result.output
