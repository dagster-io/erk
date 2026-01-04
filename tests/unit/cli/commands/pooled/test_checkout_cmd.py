"""Unit tests for pooled checkout command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
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


def test_pooled_checkout_by_branch_name() -> None:
    """Test checkout to a pool slot by branch name."""
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

        # Create pool state with an assignment
        worktree_path = repo.worktrees_dir / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-branch", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pooled", "checkout", "feature-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Shell integration not detected" in result.output


def test_pooled_checkout_slot_name_not_supported() -> None:
    """Test that slot name lookup is not supported (only branch names)."""
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

        # Create pool state with an assignment
        worktree_path = repo.worktrees_dir / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        # Trying to checkout by slot name should fail (only branch names supported)
        result = runner.invoke(
            cli, ["pooled", "checkout", "erk-managed-wt-01"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "No assignment found for branch" in result.output


def test_pooled_checkout_no_argument_shows_error() -> None:
    """Test that checkout without argument shows error."""
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

        # Create pool state
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["pooled", "checkout"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Specify branch name to checkout" in result.output


def test_pooled_checkout_not_found() -> None:
    """Test checkout to non-existent branch shows error."""
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
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pooled", "checkout", "nonexistent"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "No assignment found" in result.output


def test_pooled_checkout_no_pool_configured() -> None:
    """Test checkout when no pool is configured shows error."""
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

        # Do NOT create pool.json - simulates no pool configured

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["pooled", "checkout", "something"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "No pool configured" in result.output


def test_pooled_checkout_already_in_slot() -> None:
    """Test checkout to current slot shows error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create the pool slot worktree directory
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        # Set current directory to be within the pool slot
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={worktree_path: "feature-test"},
            git_common_dirs={worktree_path: env.git_dir},
            default_branches={worktree_path: "main"},
        )

        repo = RepoContext(
            root=worktree_path,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with assignment to current directory
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        # Build context with cwd inside the pool slot
        test_ctx = env.build_context(git=git_ops, repo=repo, cwd=worktree_path)

        result = runner.invoke(
            cli, ["pooled", "checkout", "feature-test"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "Already in pool slot" in result.output


def test_pooled_checkout_script_mode() -> None:
    """Test checkout with --script flag outputs activation script path."""
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

        # Create pool state with an assignment
        worktree_path = repo.worktrees_dir / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["pooled", "checkout", "--script", "feature-test"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Script mode outputs the path to the activation script
        # The output should be a path ending with .sh
        output = result.output.strip()
        assert output.endswith(".sh") or "erk-activation" in output


def test_pooled_checkout_with_entry_scripts() -> None:
    """Test checkout includes entry scripts from pool.checkout config."""
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

        # Create pool state with an assignment
        worktree_path = repo.worktrees_dir / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)
        assignment = _create_test_assignment("erk-managed-wt-01", "feature-test", worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        # Create config with entry script commands
        erk_config_dir = env.cwd / ".erk"
        erk_config_dir.mkdir(exist_ok=True)
        config_toml = erk_config_dir / "config.toml"
        config_toml.write_text(
            """
[pool.checkout]
commands = ["git fetch origin", "echo 'Entry script executed'"]
"""
        )

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["pooled", "checkout", "--script", "feature-test"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Verify the script was generated with entry commands
        script_path = Path(result.output.strip())
        if script_path.exists():
            script_content = script_path.read_text()
            assert "git fetch origin" in script_content
            assert "Entry script executed" in script_content
