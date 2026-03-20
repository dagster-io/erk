"""Unit tests for slot checkout command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.git.abc import WorktreeInfo
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_slot_checkout_allocates_new_slot() -> None:
    """Test that slot checkout allocates a new slot for an existing branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-test"]},
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
            cli, ["slot", "checkout", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "feature-test" in result.output

        # Verify state was persisted
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-test"


def test_slot_checkout_fails_if_branch_does_not_exist() -> None:
    """Test that slot checkout fails if branch does not exist locally or remotely."""
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
            cli, ["slot", "checkout", "nonexistent"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "does not exist" in result.output


def test_slot_checkout_stack_in_place() -> None:
    """Test that slot checkout updates assignment tip when running inside a slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a", "feature-b"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a pool state with cwd assigned as a slot
        initial_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-a",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-b"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Stacked" in result.output
        assert "feature-b" in result.output
        assert "in place" in result.output

        # Verify assignment was updated to new branch
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-b"
        assert state.assignments[0].slot_name == "erk-slot-01"


def test_slot_checkout_new_slot_forces_allocation() -> None:
    """Test that --new-slot forces new slot allocation even inside a slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a", "feature-b"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a pool state with cwd assigned as a slot
        initial_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-a",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["slot", "checkout", "--new-slot", "feature-b"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "feature-b" in result.output

        # Verify we got a second slot (not in-place update)
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 2


def test_slot_checkout_force_evicts_oldest() -> None:
    """Test that --force auto-unassigns oldest when pool is full."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

        from erk.cli.config import LoadedConfig

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "old-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "old-branch", "new-branch"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

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
            ["slot", "checkout", "--force", "new-branch"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "new-branch" in result.output

        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "new-branch"


def test_slot_checkout_pool_full_no_force_fails() -> None:
    """Test that pool full without --force fails in non-TTY mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

        from erk.cli.config import LoadedConfig
        from tests.fakes.gateway.console import FakeConsole

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "old-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "old-branch", "new-branch"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

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
            cli, ["slot", "checkout", "new-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "Pool is full" in result.output
        assert "--force" in result.output


def test_slot_checkout_already_assigned_returns_existing() -> None:
    """Test that slot checkout returns existing assignment if branch already assigned."""
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

        existing_state = PoolState.test(
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
        save_pool_state(repo.pool_json_path, existing_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-a"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "already assigned" in result.output
        assert "erk-slot-01" in result.output


def test_slot_checkout_already_assigned_shows_activation_instructions() -> None:
    """Test that already-assigned checkout shows activation instructions."""
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

        existing_state = PoolState.test(
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
        save_pool_state(repo.pool_json_path, existing_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-a"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "source" in result.output
        assert "activate.sh" in result.output


def test_slot_checkout_new_allocation_shows_activation_instructions() -> None:
    """Test that new allocation shows activation instructions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-test"]},
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
            cli, ["slot", "checkout", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "source" in result.output
        assert "activate.sh" in result.output


def test_slot_checkout_stack_in_place_suppresses_navigation() -> None:
    """Test that stack-in-place does NOT print activation instructions (same_worktree=True)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a", "feature-b"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Pre-create a pool state with cwd assigned as a slot
        initial_state = PoolState.test(
            pool_size=4,
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="feature-a",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-b"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Stacked" in result.output
        # same_worktree=True → activation instructions should be suppressed
        assert "source" not in result.output


def test_slot_checkout_reuses_inactive_worktree() -> None:
    """Test that slot checkout reuses an inactive worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        repo_dir = env.setup_repo_structure()

        worktree_path = repo_dir / "worktrees" / "erk-slot-01"
        worktree_path.mkdir(parents=True)

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="placeholder"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "placeholder"},
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

        # Pool has an initialized slot but no assignments — slot is inactive
        state = PoolState.test(pool_size=4, assignments=())
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["slot", "checkout", "feature-a"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "feature-a" in result.output

        # Should have reused erk-slot-01 (not created erk-slot-02)
        updated = load_pool_state(repo.pool_json_path)
        assert updated is not None
        assert len(updated.assignments) == 1
        assert updated.assignments[0].slot_name == "erk-slot-01"
