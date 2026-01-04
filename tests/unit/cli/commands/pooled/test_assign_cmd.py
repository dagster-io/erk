"""Unit tests for pooled assign command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pooled_assign_assigns_existing_branch(tmp_path) -> None:
    """Test that pooled assign assigns an existing branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create a FakeGit that reports the branch already exists
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
            cli, ["pooled", "assign", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Assigned feature-test to erk-managed-wt-01" in result.output

        # Verify state was persisted
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-test"
        assert state.assignments[0].slot_name == "erk-managed-wt-01"


def test_pooled_assign_fails_if_branch_does_not_exist() -> None:
    """Test that pooled assign fails if branch does not exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            # Only "main" exists, not "nonexistent-branch"
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
            cli, ["pooled", "assign", "nonexistent-branch"], obj=test_ctx, catch_exceptions=False
        )
        assert result.exit_code == 1
        assert "does not exist" in result.output
        assert "erk pooled create" in result.output


def test_pooled_assign_second_slot() -> None:
    """Test that pooled assign uses next available slot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
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

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # First assignment
        result1 = runner.invoke(
            cli, ["pooled", "assign", "feature-a"], obj=test_ctx, catch_exceptions=False
        )
        assert result1.exit_code == 0

        # Second assignment
        result2 = runner.invoke(
            cli, ["pooled", "assign", "feature-b"], obj=test_ctx, catch_exceptions=False
        )
        assert result2.exit_code == 0
        assert "Assigned feature-b to erk-managed-wt-02" in result2.output

        # Verify state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 2


def test_pooled_assign_branch_already_assigned() -> None:
    """Test that pooled assign fails if branch is already assigned."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
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

        # First assignment
        result1 = runner.invoke(
            cli, ["pooled", "assign", "feature-test"], obj=test_ctx, catch_exceptions=False
        )
        assert result1.exit_code == 0

        # Try to assign same branch again
        result2 = runner.invoke(
            cli, ["pooled", "assign", "feature-test"], obj=test_ctx, catch_exceptions=False
        )
        assert result2.exit_code == 1
        assert "already assigned" in result2.output


def test_pooled_assign_uses_config_pool_size() -> None:
    """Test that pooled assign uses pool size from config."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a", "feature-b", "feature-c"]},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Configure pool size of 2
        local_config = LoadedConfig.test(pool_size=2)
        test_ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        # Fill the pool with 2 branches
        runner.invoke(cli, ["pooled", "assign", "feature-a"], obj=test_ctx, catch_exceptions=False)
        runner.invoke(cli, ["pooled", "assign", "feature-b"], obj=test_ctx, catch_exceptions=False)

        # Verify pool state has pool_size=2
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert state.pool_size == 2
        assert len(state.assignments) == 2


def test_pooled_assign_force_unassigns_oldest() -> None:
    """Test that --force auto-unassigns oldest branch when pool is full."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pre-create worktree directory so we can configure FakeGit with it
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Build worktrees including the pool slot worktree
        from erk_shared.git.abc import WorktreeInfo

        worktrees = env.build_worktrees("main")
        # Add the pool slot worktree to the configuration
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

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

        # Pre-create a full pool with 1 slot
        full_state = PoolState(
            version="1.0",
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        # Try to assign with --force
        result = runner.invoke(
            cli, ["pooled", "assign", "--force", "new-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Unassigned" in result.output
        assert "old-branch" in result.output
        assert "Assigned new-branch" in result.output

        # Verify new state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "new-branch"


def test_pooled_assign_pool_full_non_tty_fails() -> None:
    """Test that pool-full without --force fails in non-TTY mode."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pre-create worktree directory so we can configure FakeGit with it
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Build worktrees including the pool slot worktree
        from erk_shared.git.abc import WorktreeInfo

        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="old-branch"))

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

        # Pre-create a full pool with 1 slot
        full_state = PoolState(
            version="1.0",
            pool_size=1,
            assignments=(
                SlotAssignment(
                    slot_name="erk-managed-wt-01",
                    branch_name="old-branch",
                    assigned_at="2024-01-01T10:00:00+00:00",
                    worktree_path=worktree_path,
                ),
            ),
        )
        save_pool_state(repo.pool_json_path, full_state)

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        # Try to assign without --force (CliRunner simulates non-TTY)
        result = runner.invoke(
            cli, ["pooled", "assign", "new-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "Pool is full" in result.output
        assert "--force" in result.output
