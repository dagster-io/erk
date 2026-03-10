"""Tests for erk stack sync command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.abc import BranchDivergence
from erk_shared.gateway.git.remote_ops.types import PullRebaseError
from erk_shared.gateway.graphite.disabled import (
    GraphiteDisabled,
    GraphiteDisabledReason,
)
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.cli_helpers import assert_cli_error
from tests.test_utils.env_helpers import erk_inmem_env


def test_sync_graphite_not_enabled() -> None:
    """Test stack sync command requires Graphite to be enabled."""
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

        graphite = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        test_ctx = env.build_context(git=git_ops, graphite=graphite, repo=repo)

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert_cli_error(
            result,
            1,
            "requires Graphite to be enabled",
            "erk config set use_graphite true",
        )


def _build_synced_stack(env, *, divergences):
    """Build a 3-branch stack with configurable divergences.

    Args:
        env: ErkInMemEnv instance
        divergences: Dict mapping branch name to BranchDivergence

    Returns:
        Tuple of (FakeGit, FakeGraphite)
    """
    git, graphite = env.build_ops_from_branches(
        {
            "main": BranchMetadata.trunk("main", children=["feat-1"]),
            "feat-1": BranchMetadata.branch(
                "feat-1",
                "main",
                children=["feat-2"],
            ),
            "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
        },
        current_branch="feat-2",
    )
    # Set remote branches on the subgateway directly
    remote_refs = ["origin/feat-1", "origin/feat-2"]
    git.branch._remote_branches[env.cwd] = remote_refs
    # Set divergence on the subgateway directly
    for branch, div in divergences.items():
        git.branch._branch_divergence[(env.cwd, branch, "origin")] = div
    return git, graphite


def test_sync_all_branches_in_sync() -> None:
    """Test stack sync when all branches are already in sync."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = _build_synced_stack(
            env,
            divergences={
                "feat-1": BranchDivergence(
                    is_diverged=False,
                    ahead=0,
                    behind=0,
                ),
                "feat-2": BranchDivergence(
                    is_diverged=False,
                    ahead=0,
                    behind=0,
                ),
            },
        )

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "already in sync" in result.output
        assert "2 in sync" in result.output


def test_sync_branch_behind_fast_forward_not_checked_out() -> None:
    """Test fast-forward when a non-current branch is behind remote."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = _build_synced_stack(
            env,
            divergences={
                "feat-1": BranchDivergence(
                    is_diverged=False,
                    ahead=0,
                    behind=3,
                ),
                "feat-2": BranchDivergence(
                    is_diverged=False,
                    ahead=0,
                    behind=0,
                ),
            },
        )
        # Remote ref for fast-forward
        git.branch._branch_heads["origin/feat-1"] = "abc123"

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "fast-forwarded" in result.output
        assert "1 fixed" in result.output

        # Verify update_local_ref was called
        assert len(git.updated_refs) == 1
        assert git.updated_refs[0] == (env.cwd, "feat-1", "abc123")


def test_sync_branch_behind_fast_forward_current() -> None:
    """Test fast-forward when current branch is behind remote."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                ),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            current_branch="feat-1",
        )
        git.branch._remote_branches[env.cwd] = ["origin/feat-1"]
        git.branch._branch_divergence[(env.cwd, "feat-1", "origin")] = BranchDivergence(
            is_diverged=False, ahead=0, behind=2
        )

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "fast-forwarded" in result.output

        # Current branch uses pull --rebase
        assert len(git.pull_rebase_calls) == 1
        assert git.pull_rebase_calls[0] == (env.cwd, "origin", "feat-1")


def test_sync_branch_diverged_rebase() -> None:
    """Test rebase when a branch is diverged from remote."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                ),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            current_branch="feat-1",
        )
        git.branch._remote_branches[env.cwd] = ["origin/feat-1"]
        git.branch._branch_divergence[(env.cwd, "feat-1", "origin")] = BranchDivergence(
            is_diverged=True, ahead=2, behind=3
        )

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "rebased" in result.output
        assert "1 fixed" in result.output


def test_sync_branch_no_remote_skipped() -> None:
    """Test that branches without remote tracking are skipped."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                ),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            current_branch="feat-1",
        )
        # No remote branches — branch_exists_on_remote returns False
        git.branch._remote_branches[env.cwd] = []

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "skipped (no remote)" in result.output
        assert "1 skipped" in result.output


def test_sync_branch_checked_out_elsewhere_skipped() -> None:
    """Test that branches checked out in another worktree are skipped."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # feat-1 is checked out in a linked worktree
        env.create_linked_worktree("feat-1", "feat-1")
        git, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                ),
                "feat-1": BranchMetadata.branch(
                    "feat-1",
                    "main",
                    children=["feat-2"],
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1"),
            },
            current_branch="feat-2",
        )
        git.branch._remote_branches[env.cwd] = [
            "origin/feat-1",
            "origin/feat-2",
        ]
        git.branch._branch_divergence[(env.cwd, "feat-1", "origin")] = BranchDivergence(
            is_diverged=False, ahead=0, behind=3
        )
        git.branch._branch_divergence[(env.cwd, "feat-2", "origin")] = BranchDivergence(
            is_diverged=False, ahead=0, behind=0
        )

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "skipped" in result.output
        assert "1 skipped" in result.output


def test_sync_conflict_aborts_rebase() -> None:
    """Test that rebase conflicts are aborted and reported."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                ),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            current_branch="feat-1",
        )
        git.branch._remote_branches[env.cwd] = ["origin/feat-1"]
        git.branch._branch_divergence[(env.cwd, "feat-1", "origin")] = BranchDivergence(
            is_diverged=True, ahead=1, behind=2
        )
        # Configure pull_rebase to return error on the remote subgateway
        git.remote._pull_rebase_error = PullRebaseError(
            message="conflict in file.py",
        )
        # Rebase is in progress after failed pull
        git.rebase._rebase_in_progress = True

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "CONFLICT" in result.output
        assert "erk pr diverge-fix" in result.output
        assert "1 conflict" in result.output

        # Verify rebase was aborted
        assert len(git.rebase_abort_calls) == 1


def test_sync_restack_failure_reported() -> None:
    """Test that restack failures are displayed in output."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                ),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            current_branch="feat-1",
        )
        git.branch._remote_branches[env.cwd] = ["origin/feat-1"]
        git.branch._branch_divergence[(env.cwd, "feat-1", "origin")] = BranchDivergence(
            is_diverged=False, ahead=0, behind=0
        )

        # Override graphite with restack failure
        from tests.fakes.gateway.graphite import FakeGraphite

        graphite_with_failure = FakeGraphite(
            branches=graphite._branches,
            stacks=graphite._stacks,
            restack_result=(False, "merge conflict"),
        )

        test_ctx = env.build_context(
            git=git,
            graphite=graphite_with_failure,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "failed" in result.output
        assert "merge conflict" in result.output


def test_sync_branch_ahead_only_no_action() -> None:
    """Test branches only ahead of remote are reported as in sync."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                ),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            current_branch="feat-1",
        )
        git.branch._remote_branches[env.cwd] = ["origin/feat-1"]
        git.branch._branch_divergence[(env.cwd, "feat-1", "origin")] = BranchDivergence(
            is_diverged=False, ahead=5, behind=0
        )

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "already in sync" in result.output
        # No pull_rebase calls, no update_local_ref
        assert len(git.pull_rebase_calls) == 0
        assert len(git.updated_refs) == 0


def test_sync_calls_fetch_prune() -> None:
    """Test that fetch --prune is called before syncing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk(
                    "main",
                    children=["feat-1"],
                ),
                "feat-1": BranchMetadata.branch("feat-1", "main"),
            },
            current_branch="feat-1",
        )
        git.branch._remote_branches[env.cwd] = ["origin/feat-1"]
        git.branch._branch_divergence[(env.cwd, "feat-1", "origin")] = BranchDivergence(
            is_diverged=False, ahead=0, behind=0
        )

        test_ctx = env.build_context(
            git=git,
            graphite=graphite,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["stack", "sync"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Verify fetch_prune was called via FakeGit's remote subgateway
        assert len(git.remote.fetch_prune_calls) == 1
        assert git.remote.fetch_prune_calls[0] == (env.cwd, "origin")
