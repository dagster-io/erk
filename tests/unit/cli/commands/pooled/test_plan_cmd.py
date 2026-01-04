"""Unit tests for pooled plan command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import load_pool_state
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pooled_plan_creates_branch_and_assignment_when_branch_does_not_exist() -> None:
    """Test that pooled plan creates new branch and assigns to pool."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
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
            cli, ["pooled", "plan", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        # Command exits with 0 on success (activation raises SystemExit(0))
        assert result.exit_code == 0
        assert "Created branch: feature-test" in result.output
        assert "Assigned feature-test to erk-managed-wt-01" in result.output

        # Verify state was persisted
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-test"
        assert state.assignments[0].slot_name == "erk-managed-wt-01"


def test_pooled_plan_assigns_existing_branch() -> None:
    """Test that pooled plan assigns existing branch to pool."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Branch already exists but not in pool
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "existing-branch"]},
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
            cli, ["pooled", "plan", "existing-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should NOT create branch - it already exists
        assert "Created branch:" not in result.output
        assert "Assigned existing-branch to erk-managed-wt-01" in result.output

        # Verify state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "existing-branch"


def test_pooled_plan_uses_existing_assignment() -> None:
    """Test that pooled plan uses existing assignment if branch already in pool."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # First call - creates and assigns
        result1 = runner.invoke(
            cli, ["pooled", "plan", "feature-a"], obj=test_ctx, catch_exceptions=False
        )
        assert result1.exit_code == 0
        assert "Assigned feature-a to erk-managed-wt-01" in result1.output

        # Second call - uses existing assignment
        result2 = runner.invoke(
            cli, ["pooled", "plan", "feature-a"], obj=test_ctx, catch_exceptions=False
        )
        assert result2.exit_code == 0
        # Should NOT create or assign again
        assert "Created branch:" not in result2.output
        assert "Assigned" not in result2.output

        # Verify state - still only 1 assignment
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1


def test_pooled_plan_script_mode_outputs_activation_script_path() -> None:
    """Test that --script outputs activation script path."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
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
            cli, ["pooled", "plan", "feature-test", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Script mode outputs the script path (contains .sh)
        assert ".sh" in result.output


def test_pooled_plan_force_unassigns_oldest_when_pool_full() -> None:
    """Test that --force unassigns oldest branch when pool is full."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Configure pool size of 2 for quicker test
        local_config = LoadedConfig.test(pool_size=2)
        test_ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        # Fill pool
        runner.invoke(cli, ["pooled", "plan", "feature-a"], obj=test_ctx, catch_exceptions=False)
        runner.invoke(cli, ["pooled", "plan", "feature-b"], obj=test_ctx, catch_exceptions=False)

        # Now pool is full - use --force to add another
        result = runner.invoke(
            cli, ["pooled", "plan", "feature-c", "--force"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Unassigned" in result.output
        assert "feature-a" in result.output  # Oldest was unassigned
        assert "Assigned feature-c" in result.output

        # Verify final state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 2
        branch_names = {a.branch_name for a in state.assignments}
        assert "feature-b" in branch_names
        assert "feature-c" in branch_names
        assert "feature-a" not in branch_names  # Was unassigned
