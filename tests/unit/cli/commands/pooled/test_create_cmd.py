"""Unit tests for pooled create command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import load_pool_state
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pooled_create_creates_new_branch_and_assignment(tmp_path) -> None:
    """Test that pooled create creates a new branch and assignment."""
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
            cli, ["pooled", "create", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Created branch: feature-test" in result.output
        assert "Assigned feature-test to erk-managed-wt-01" in result.output

        # Verify state was persisted
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 1
        assert state.assignments[0].branch_name == "feature-test"
        assert state.assignments[0].slot_name == "erk-managed-wt-01"


def test_pooled_create_second_slot() -> None:
    """Test that pooled create uses next available slot."""
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

        # First create
        result1 = runner.invoke(
            cli, ["pooled", "create", "feature-a"], obj=test_ctx, catch_exceptions=False
        )
        assert result1.exit_code == 0

        # Second create
        result2 = runner.invoke(
            cli, ["pooled", "create", "feature-b"], obj=test_ctx, catch_exceptions=False
        )
        assert result2.exit_code == 0
        assert "Assigned feature-b to erk-managed-wt-02" in result2.output

        # Verify state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 2


def test_pooled_create_fails_if_branch_already_exists() -> None:
    """Test that pooled create fails if branch already exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create a FakeGit that reports the branch already exists
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

        # Try to create a branch that already exists
        result = runner.invoke(
            cli, ["pooled", "create", "existing-branch"], obj=test_ctx, catch_exceptions=False
        )
        assert result.exit_code == 1
        assert "already exists" in result.output
        assert "erk pooled assign" in result.output


def test_pooled_create_fails_if_branch_already_assigned() -> None:
    """Test that pooled create fails if branch is already assigned."""
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

        # First create
        result1 = runner.invoke(
            cli, ["pooled", "create", "feature-test"], obj=test_ctx, catch_exceptions=False
        )
        assert result1.exit_code == 0

        # Try to create same branch again
        result2 = runner.invoke(
            cli, ["pooled", "create", "feature-test"], obj=test_ctx, catch_exceptions=False
        )
        assert result2.exit_code == 1
        assert "already assigned" in result2.output
