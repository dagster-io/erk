"""Tests for erk branch delete command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, save_pool_state
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_delete_branch_no_worktree() -> None:
    """Delete a branch that has no associated worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            local_branches={env.cwd: ["main", "feature-x"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
        )

        result = runner.invoke(
            cli,
            ["br", "delete", "feature-x", "-f"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "feature-x" in git_ops.deleted_branches


def test_delete_branch_with_vanilla_worktree() -> None:
    """Delete a branch with a vanilla (non-slot) worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "feature-y"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-y", is_root=False),
                ]
            },
            local_branches={env.cwd: ["main", "feature-y"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli,
            ["br", "delete", "feature-y", "-f"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "feature-y" in git_ops.deleted_branches
        # Worktree should have been removed
        assert feature_wt in git_ops.removed_worktrees


def test_delete_branch_with_slot_worktree_unassigns_slot() -> None:
    """Delete a branch in a slot worktree: unassign slot, keep directory."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        slot_wt = repo_dir / "worktrees" / "erk-managed-wt-01"
        slot_wt.mkdir(parents=True)

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=slot_wt, branch="feature-slot", is_root=False),
                ]
            },
            local_branches={env.cwd: ["main", "feature-slot", "__erk-slot-01-placeholder__"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, slot_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with an assignment and save it to file
        # SlotAssignment has: slot_name, branch_name, assigned_at, worktree_path
        assignment = SlotAssignment(
            slot_name="erk-managed-wt-01",
            worktree_path=slot_wt,
            branch_name="feature-slot",
            assigned_at=datetime.now(UTC).isoformat(),
        )
        pool_state = PoolState.test(assignments=(assignment,))
        save_pool_state(repo.pool_json_path, pool_state)

        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(
            cli,
            ["br", "delete", "feature-slot", "-f"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Branch should be deleted
        assert "feature-slot" in git_ops.deleted_branches
        # Worktree should NOT have been removed (slot keeps directory)
        assert slot_wt not in git_ops.removed_worktrees
        # Check that slot was unassigned (placeholder branch checked out)
        # checked_out_branches is a list of (Path, str) tuples
        assert (slot_wt, "__erk-slot-01-placeholder__") in git_ops.checked_out_branches


def test_delete_branch_nonexistent_branch_fails() -> None:
    """Deleting a nonexistent branch should fail with error message."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
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
            cli,
            ["br", "delete", "nonexistent-branch", "-f"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "does not exist" in result.output


def test_delete_trunk_branch_fails() -> None:
    """Deleting the trunk branch should fail with error message."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
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
            cli,
            ["br", "delete", "main", "-f"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "Cannot delete trunk branch" in result.output


def test_delete_branch_with_all_flag_closes_pr() -> None:
    """Delete branch with --all flag closes associated PR."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            local_branches={env.cwd: ["main", "feature-pr"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up GitHub with a PR for the branch
        # PullRequestInfo: number, state, url, is_draft, title, checks_passing, owner, repo
        github = FakeGitHub(
            prs={
                "feature-pr": PullRequestInfo(
                    number=123,
                    title="My Feature",
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    checks_passing=True,
                    owner="owner",
                    repo="repo",
                )
            },
            pr_details={
                # PRDetails has: number, url, title, body, state, is_draft,
                # base_ref_name, head_ref_name, is_cross_repository,
                # mergeable, merge_state_status, owner, repo
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="My Feature",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-pr",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            github=github,
            repo=repo,
        )

        result = runner.invoke(
            cli,
            ["br", "delete", "feature-pr", "-f", "-a"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "feature-pr" in git_ops.deleted_branches
        # PR should have been closed
        assert 123 in github.closed_prs


def test_delete_branch_force_skips_confirmation() -> None:
    """Force flag skips confirmation prompt."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "feature-force"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-force", is_root=False),
                ]
            },
            local_branches={env.cwd: ["main", "feature-force"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            existing_paths={feature_wt},
        )

        # With -f flag, should not prompt
        result = runner.invoke(
            cli,
            ["br", "delete", "feature-force", "-f"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "feature-force" in git_ops.deleted_branches


def test_delete_branch_displays_planning_output() -> None:
    """Command displays planning output before executing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "feature-plan"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-plan", is_root=False),
                ]
            },
            local_branches={env.cwd: ["main", "feature-plan"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli,
            ["br", "delete", "feature-plan", "-f"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Should show planning output
        assert "Planning to perform" in result.output
        assert "Delete worktree" in result.output
        assert "Delete branch" in result.output


def test_delete_branch_uses_graphite_when_tracked() -> None:
    """Uses Graphite for branch deletion when branch is tracked."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # FakeGraphite uses branches: dict[str, BranchMetadata]
        # is_branch_tracked returns True if branch is in self._branches
        graphite = FakeGraphite(
            branches={
                "feature-gt": BranchMetadata(
                    name="feature-gt",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                ),
            },
        )

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
            local_branches={env.cwd: ["main", "feature-gt"]},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            repo=repo,
            use_graphite=True,
        )

        result = runner.invoke(
            cli,
            ["br", "delete", "feature-gt", "-f"],
            obj=test_ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Branch should be deleted (both delete_branch and delete_branch_with_graphite
        # track in deleted_branches)
        assert "feature-gt" in git_ops.deleted_branches
