"""Tests for erk stack consolidate command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.test_utils.cli_helpers import assert_cli_error, assert_cli_success
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


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


def test_consolidate_graphite_not_enabled() -> None:
    """Test stack consolidate command requires Graphite to be enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Graphite is NOT enabled - use GraphiteDisabled sentinel
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        test_ctx = env.build_context(git=git_ops, graphite=graphite_disabled, repo=repo)

        result = runner.invoke(cli, ["stack", "consolidate"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result,
            1,
            "requires Graphite to be enabled",
            "erk config set use_graphite true",
        )


def test_consolidate_graphite_not_installed() -> None:
    """Test stack consolidate command shows appropriate error when Graphite CLI is not installed."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Graphite not installed - use GraphiteDisabled with NOT_INSTALLED reason
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)
        test_ctx = env.build_context(git=git_ops, graphite=graphite_disabled, repo=repo)

        result = runner.invoke(cli, ["stack", "consolidate"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result,
            1,
            "requires Graphite to be installed",
            "npm install -g @withgraphite/graphite-cli",
        )


def test_consolidate_slot_aware_unassigns_slot() -> None:
    """Test consolidate unassigns slots instead of removing worktree directories."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Worktree paths - one is a slot, one is regular
        slot_path = repo_dir / "worktrees" / "erk-slot-01"
        slot_path.mkdir(parents=True)
        regular_path = repo_dir / "worktrees" / "feature-a"
        regular_path.mkdir(parents=True)

        # Current branch is on the top of stack (feature-c)
        current_path = repo_dir / "worktrees" / "feature-c"
        current_path.mkdir(parents=True)

        # Set up stack: main -> feature-a -> feature-b -> feature-c
        # - feature-a is in a regular worktree
        # - feature-b is in a slot
        # - feature-c is the current worktree (stays)
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=regular_path, branch="feature-a", is_root=False),
                    WorktreeInfo(path=slot_path, branch="feature-b", is_root=False),
                    WorktreeInfo(path=current_path, branch="feature-c", is_root=False),
                ]
            },
            current_branches={
                env.cwd: "main",
                regular_path: "feature-a",
                slot_path: "feature-b",
                current_path: "feature-c",
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={
                env.cwd: env.git_dir,
                regular_path: env.git_dir,
                slot_path: env.git_dir,
                current_path: env.git_dir,
            },
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-a", "feature-b", "feature-c"]},
        )

        # Set up stack: main -> feature-a -> feature-b -> feature-c
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-a"], commit_sha="abc123"),
                "feature-a": BranchMetadata.branch(
                    "feature-a", "main", children=["feature-b"], commit_sha="aaa111"
                ),
                "feature-b": BranchMetadata.branch(
                    "feature-b", "feature-a", children=["feature-c"], commit_sha="bbb222"
                ),
                "feature-c": BranchMetadata.branch("feature-c", "feature-b", commit_sha="ccc333"),
            },
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with assignment for the slot
        assignment = _create_test_assignment("erk-slot-01", "feature-b", slot_path)
        initial_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, initial_state)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            repo=repo,
            use_graphite=True,
            cwd=current_path,
        )

        # Execute: erk stack consolidate --force
        result = runner.invoke(
            cli, ["stack", "consolidate", "-f"], obj=test_ctx, catch_exceptions=False
        )

        assert_cli_success(result)

        # Assert: Slot was unassigned (placeholder branch checked out)
        assert (
            slot_path,
            "__erk-slot-01-br-stub__",
        ) in git_ops.checked_out_branches, "Slot should be checked out to placeholder"

        # Assert: Regular worktree WAS removed
        assert regular_path in git_ops.removed_worktrees, "Regular worktree should be removed"

        # Assert: Slot worktree was NOT removed
        assert slot_path not in git_ops.removed_worktrees, "Slot worktree should NOT be removed"

        # Assert: Assignment was removed from pool state
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 0, "Assignment should be removed"

        # Assert: Output indicates slot unassignment
        assert "unassigned" in result.output.lower()
