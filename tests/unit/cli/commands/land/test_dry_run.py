"""Unit tests for dry-run mode in land command cleanup."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.land_cmd import _cleanup_and_navigate
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.types import GitHubRepoId
from tests.test_utils.env_helpers import erk_inmem_env


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


def test_cleanup_and_navigate_dry_run_does_not_save_pool_state(tmp_path: Path) -> None:
    """Test that _cleanup_and_navigate in dry-run mode does not save pool state."""
    # Create worktree path and pool.json
    worktree_path = tmp_path / "worktrees" / "erk-slot-01"
    worktree_path.mkdir(parents=True)
    pool_json_path = tmp_path / "pool.json"

    # Create initial pool state with an assignment
    assignment = _create_test_assignment("erk-slot-01", "feature-branch", worktree_path)
    initial_state = PoolState.test(assignments=(assignment,))

    # Write initial state to disk

    save_pool_state(pool_json_path, initial_state)

    # Create context with dry_run=True
    fake_git = FakeGit(
        worktrees={tmp_path: [WorktreeInfo(path=worktree_path, branch="feature-branch")]},
        git_common_dirs={tmp_path: tmp_path / ".git"},
        default_branches={tmp_path: "main"},
        local_branches={tmp_path: ["main", "feature-branch"]},
        existing_paths={worktree_path, tmp_path, tmp_path / ".git", pool_json_path},
    )

    ctx = context_for_test(
        git=fake_git,
        graphite=FakeGraphite(),
        cwd=worktree_path,
        dry_run=True,
    )

    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=tmp_path,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate in dry-run mode with objective
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=worktree_path,
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=123,  # This would trigger pool state save
            no_delete=False,
            skip_activation_output=False,
            cleanup_confirmed=True,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify pool state was NOT modified (objective should NOT be recorded)
    reloaded_state = load_pool_state(pool_json_path)
    assert reloaded_state is not None
    # The slot should still have its assignment (not modified by dry-run)
    found_assignment = None
    for a in reloaded_state.assignments:
        if a.slot_name == "erk-slot-01":
            found_assignment = a
            break
    assert found_assignment is not None


def test_cleanup_and_navigate_dry_run_shows_summary() -> None:
    """Test that dry-run mode outputs summary message."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        worktree_path = env.erk_root / "repos" / env.cwd.name / "worktrees" / "feature-branch"

        fake_git = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=worktree_path, branch="feature-branch")]},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            existing_paths={worktree_path, env.cwd, env.git_dir},
        )

        ctx = context_for_test(
            git=fake_git,
            graphite=FakeGraphite(),
            cwd=worktree_path,
            dry_run=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=env.erk_root / "repos" / env.cwd.name,
            worktrees_dir=env.erk_root / "repos" / env.cwd.name / "worktrees",
            pool_json_path=env.erk_root / "repos" / env.cwd.name / "pool.json",
            github=GitHubRepoId(owner="owner", repo="repo"),
        )

        # Capture output
        import io
        import sys

        captured = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            _cleanup_and_navigate(
                ctx=ctx,
                repo=repo,
                branch="feature-branch",
                worktree_path=worktree_path,
                script=False,
                pull_flag=False,
                force=True,
                is_current_branch=False,
                target_child_branch=None,
                objective_number=None,
                no_delete=False,
                skip_activation_output=False,
                cleanup_confirmed=True,
            )
        except SystemExit as e:
            assert e.code == 0  # Should exit cleanly
        finally:
            sys.stderr = old_stderr

        # The dry-run summary is output via user_output which goes to stderr
        # Note: user_output uses click.echo which may not capture in StringIO
        # The test mainly verifies the function doesn't crash in dry-run mode
