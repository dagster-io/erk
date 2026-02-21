"""Unit tests for wt create-from command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_create_from_assigns_local_branch(tmp_path) -> None:
    """Happy path: local branch exists, allocates slot and navigates."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-auth"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["wt", "create-from", "feature-auth"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Assigned" in result.output
        assert "feature-auth" in result.output
        assert "erk-slot-01" in result.output

        # Verify state was persisted
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-auth"
        assert state.assignments[0].slot_name == "erk-slot-01"


def test_create_from_fetches_remote_branch(tmp_path) -> None:
    """Branch only on remote: creates tracking branch, then allocates."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/remote-feature"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["wt", "create-from", "remote-feature"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "exists on origin" in result.output
        assert "Assigned" in result.output

        # Verify fetch and tracking branch were called
        assert ("origin", "remote-feature") in git_ops.fetched_branches
        assert len(git_ops.created_tracking_branches) == 1


def test_create_from_fails_branch_not_found() -> None:
    """Branch doesn't exist locally or remotely: errors with suggestion."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["wt", "create-from", "nonexistent"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "does not exist" in result.output
        assert "erk br create" in result.output


def test_create_from_fails_trunk_branch() -> None:
    """Trunk branch: errors with appropriate message."""
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

        result = runner.invoke(
            cli, ["wt", "create-from", "main"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "trunk branch" in result.output
        assert "erk wt co root" in result.output


def test_create_from_already_assigned(tmp_path) -> None:
    """Branch already assigned: reports existing assignment."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        # Pre-create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="feature-auth"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "feature-auth"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-auth"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create pool state with existing assignment
        existing_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-auth",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, existing_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["wt", "create-from", "feature-auth"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "already assigned" in result.output


def test_create_from_force_unassigns_oldest(tmp_path) -> None:
    """Pool full with --force: evicts oldest, assigns new branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        # Pre-create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "old-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "old-branch", "new-feature"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a full pool with 1 slot
        full_state = PoolState.test(
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        result = runner.invoke(
            cli,
            ["wt", "create-from", "--force", "new-feature"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Unassigned" in result.output
        assert "old-branch" in result.output
        assert "Assigned" in result.output
        assert "new-feature" in result.output

        # Verify new state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "new-feature"


def test_create_from_pool_full_non_tty_fails() -> None:
    """Pool full without --force in non-TTY: errors with --force suggestion."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        # Pre-create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "old-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "old-branch", "new-feature"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a full pool with 1 slot
        full_state = PoolState.test(
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        console = FakeConsole(
            is_interactive=False, is_stdout_tty=None, is_stderr_tty=None, confirm_responses=None
        )
        test_ctx = env.build_context(
            git=git_ops, repo=repo, local_config=local_config, console=console
        )

        result = runner.invoke(
            cli,
            ["wt", "create-from", "new-feature"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "Pool is full" in result.output
        assert "--force" in result.output
