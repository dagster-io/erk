"""Unit tests for pooled check command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _create_test_assignment(
    slot_name: str,
    branch_name: str,
    worktree_path: Path,
) -> SlotAssignment:
    """Create a test assignment with current timestamp."""
    return SlotAssignment(
        slot_name=slot_name,
        branch_name=branch_name,
        assigned_at=datetime.now(UTC).isoformat(),
        worktree_path=worktree_path,
    )


def test_pooled_check_no_pool_configured() -> None:
    """Test sync when no pool is configured shows error."""
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

        result = runner.invoke(cli, ["pooled", "check"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "No pool configured" in result.output


def test_pooled_check_no_issues() -> None:
    """Test sync with consistent pool state shows no issues."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create pool slot directory
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Build worktrees including the pool slot
        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="feature-test"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "feature-test"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            # Branch exists - branch_heads maps branch name -> SHA
            branch_heads={"feature-test": "abc123", "main": "def456"},
            # Directory exists
            existing_paths={worktree_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create consistent pool state
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "check"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Pool Check Report" in result.output
        assert "1 assignments" in result.output
        assert "No issues found" in result.output


def test_pooled_check_orphan_state() -> None:
    """Test sync detects orphan state (assignment without directory)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Do NOT create the worktree directory - simulate orphan state
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_heads={"feature-test": "abc123", "main": "def456"},
            # Directory does NOT exist - pass paths we know exist
            # so that path_exists() will check real filesystem for worktree_path
            existing_paths={env.cwd},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with assignment to non-existent directory
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "check"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Issues Found:" in result.output
        assert "[orphan-state]" in result.output
        assert "directory does not exist" in result.output


def test_pooled_check_orphan_dir() -> None:
    """Test sync detects orphan directory (directory without assignment)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory on filesystem
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            existing_paths={worktree_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create empty pool state (no assignments)
        state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "check"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Issues Found:" in result.output
        assert "[orphan-dir]" in result.output
        assert "not in pool state" in result.output


def test_pooled_check_missing_branch() -> None:
    """Test sync detects missing branch (assignment to deleted branch)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            # Branch does NOT exist (not in branch_heads)
            branch_heads={"main": "def456"},
            existing_paths={worktree_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with assignment to deleted branch
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-deleted", worktree_path)
        state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "check"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Issues Found:" in result.output
        assert "[missing-branch]" in result.output
        assert "feature-deleted" in result.output
        assert "deleted" in result.output


def test_pooled_check_git_registry_mismatch() -> None:
    """Test sync detects mismatch between pool state and git worktree registry."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Build worktrees with DIFFERENT branch than pool state
        worktrees = env.build_worktrees("main")
        worktrees[env.cwd].append(WorktreeInfo(path=worktree_path, branch="different-branch"))

        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: "main", worktree_path: "different-branch"},
            git_common_dirs={env.cwd: env.git_dir, worktree_path: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_heads={"feature-test": "abc123", "different-branch": "xyz789", "main": "def456"},
            existing_paths={worktree_path},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with DIFFERENT branch than git registry
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "check"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Issues Found:" in result.output
        assert "[branch-mismatch]" in result.output
        assert "pool says 'feature-test'" in result.output
        assert "git says 'different-branch'" in result.output


def test_pooled_check_empty_pool() -> None:
    """Test sync with empty pool shows clean state."""
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

        # Create empty pool state
        state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(),
        )
        save_pool_state(repo.pool_json_path, state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "check"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Pool Check Report" in result.output
        assert "0 assignments" in result.output
        assert "No issues found" in result.output
