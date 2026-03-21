"""Unit tests for slot goto command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
from erk_shared.gateway.git.abc import WorktreeInfo
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_slot_goto_navigates_to_assigned_slot() -> None:
    """Test that slot goto navigates to an assigned slot by number."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="feature-a"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "feature-a"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-a",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "goto", "1"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "erk-slot-01" in result.output
        assert "feature-a" in result.output


def test_slot_goto_by_full_name() -> None:
    """Test that slot goto accepts full slot name like erk-slot-01."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="feature-b"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "feature-b"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-b"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-b",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "goto", "erk-slot-01"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "erk-slot-01" in result.output
        assert "feature-b" in result.output


def test_slot_goto_unassigned_slot_fails() -> None:
    """Test that slot goto fails with an error when slot is not assigned."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pool with no assignments
        state = PoolState.test(pool_size=4, assignments=())
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "goto", "2"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "not assigned" in result.output
        assert "erk-slot-02" in result.output


def test_slot_goto_nonexistent_slot_fails() -> None:
    """Test that slot goto fails when slot number exceeds pool (no pool state)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # No pool.json exists, pool_json_path doesn't exist
        result = runner.invoke(cli, ["slot", "goto", "99"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "not assigned" in result.output


def test_slot_goto_shows_activation_instructions() -> None:
    """Test that slot goto shows activation instructions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="feature-a"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "feature-a"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-a",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["slot", "goto", "1"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "source" in result.output
        assert "activate.sh" in result.output
