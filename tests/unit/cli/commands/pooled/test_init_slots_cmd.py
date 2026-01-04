"""Unit tests for pooled init-slots command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import load_pool_state
from erk_shared.git.dry_run import DryRunGit
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_init_slots_dry_run_does_not_create_worktrees() -> None:
    """Test that dry-run mode prevents worktree creation.

    This test passes dry_run=True to the context (not via CLI flag) to verify
    that when ctx.dry_run is True, no filesystem modifications occur.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
        )

        # Wrap in DryRunGit to simulate dry-run behavior
        dry_run_git = DryRunGit(git_ops)

        local_config = LoadedConfig.test(pool_size=2)
        test_ctx = env.build_context(
            git=dry_run_git,
            repo=env.repo,
            local_config=local_config,
            dry_run=True,
        )

        # Note: Don't pass --dry-run flag because that would call create_context()
        # which replaces our fake context with a real one. Instead, the context
        # already has dry_run=True which is what we're testing.
        result = runner.invoke(cli, ["pooled", "init-slots"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Verify dry-run messages are shown
        assert "[DRY RUN]" in result.output

        # The custom guards output these messages
        assert "Would create directory" in result.output
        assert "Would save pool state" in result.output

        # Verify no branches were created (DryRunGit is a no-op)
        assert len(git_ops.created_branches) == 0

        # Verify pool state was not saved
        state = load_pool_state(env.repo.pool_json_path)
        assert state is None


def test_init_slots_dry_run_shows_slot_count() -> None:
    """Test that dry-run shows the number of slots that would be initialized."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
        )

        dry_run_git = DryRunGit(git_ops)

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(
            git=dry_run_git,
            repo=env.repo,
            local_config=local_config,
            dry_run=True,
        )

        result = runner.invoke(
            cli, ["pooled", "init-slots", "-n", "1"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Check that slot name is mentioned in the output
        assert "erk-managed-wt-01" in result.output
        # Check for either the per-slot message or the summary message
        assert "Would initialize" in result.output


def test_init_slots_creates_worktrees_without_dry_run() -> None:
    """Test that init-slots actually creates worktrees when dry_run=False."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
        )

        # Create RepoContext with explicit paths (following test_assign_cmd pattern)
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        local_config = LoadedConfig.test(pool_size=1)
        test_ctx = env.build_context(git=git_ops, repo=repo, local_config=local_config)

        # Ensure worktrees directory exists
        (repo_dir / "worktrees").mkdir(parents=True, exist_ok=True)

        result = runner.invoke(
            cli, ["pooled", "init-slots", "-n", "1"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify success message (not dry-run)
        assert "[DRY RUN]" not in result.output
        assert "Initialized erk-managed-wt-01" in result.output

        # Verify worktree directory was created
        slot1_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        assert slot1_path.exists()

        # Verify pool state was saved
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.slots) == 1
        assert state.slots[0].name == "erk-managed-wt-01"
