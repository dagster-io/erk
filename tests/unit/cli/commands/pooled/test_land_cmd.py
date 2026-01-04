"""Unit tests for pooled land command."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _create_pr_details(
    number: int,
    branch: str,
    state: str = "OPEN",
    title: str = "Test PR",
    body: str = "Test body",
) -> PRDetails:
    """Create a PRDetails instance for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=title,
        body=body,
        state=state,
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def _create_pr_info(
    number: int,
    state: str = "OPEN",
    title: str = "Test PR",
) -> PullRequestInfo:
    """Create a PullRequestInfo instance for testing."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title=title,
        checks_passing=True,
        owner="owner",
        repo="repo",
    )


def test_pooled_land_success_merges_pr() -> None:
    """Test that pooled land merges the PR successfully (no pool slot)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        branch_name = "feature-branch"
        pr_number = 123

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: branch_name},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        github_ops = FakeGitHub(
            prs={branch_name: _create_pr_info(pr_number)},
            pr_details={pr_number: _create_pr_details(pr_number, branch_name)},
        )

        test_ctx = env.build_context(git=git_ops, github=github_ops)

        result = runner.invoke(cli, ["pooled", "land"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert f"Merged PR #{pr_number}" in result.output
        # No pool configured, so no unassign message
        assert "Unassigned" not in result.output
        # Verify PR was merged
        assert pr_number in github_ops.merged_prs


def test_pooled_land_no_pr_for_branch_error() -> None:
    """Test that pooled land shows error when no PR exists for branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        branch_name = "feature-branch"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: branch_name},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        # No PRs configured
        github_ops = FakeGitHub()

        test_ctx = env.build_context(git=git_ops, github=github_ops)

        result = runner.invoke(cli, ["pooled", "land"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "No pull request found for branch" in result.output


def test_pooled_land_pr_not_open_error() -> None:
    """Test that pooled land shows error when PR is not OPEN."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        branch_name = "feature-branch"
        pr_number = 123

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: branch_name},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        github_ops = FakeGitHub(
            prs={branch_name: _create_pr_info(pr_number, state="MERGED")},
            pr_details={pr_number: _create_pr_details(pr_number, branch_name, state="MERGED")},
        )

        test_ctx = env.build_context(git=git_ops, github=github_ops)

        result = runner.invoke(cli, ["pooled", "land"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "is not open" in result.output


def test_pooled_land_merge_failure_error() -> None:
    """Test that pooled land shows error when merge fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        branch_name = "feature-branch"
        pr_number = 123

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: branch_name},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        github_ops = FakeGitHub(
            prs={branch_name: _create_pr_info(pr_number)},
            pr_details={pr_number: _create_pr_details(pr_number, branch_name)},
            merge_should_succeed=False,
        )

        test_ctx = env.build_context(git=git_ops, github=github_ops)

        result = runner.invoke(cli, ["pooled", "land"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Failed to merge" in result.output


def test_pooled_land_detached_head_error() -> None:
    """Test that pooled land shows error when in detached HEAD state."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            # No current_branches configured = detached HEAD
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["pooled", "land"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "detached HEAD" in result.output


def test_pooled_land_force_skips_objective_prompt() -> None:
    """Test that --force skips objective update prompt."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        branch_name = "feature-branch"
        pr_number = 123

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: branch_name},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        github_ops = FakeGitHub(
            prs={branch_name: _create_pr_info(pr_number)},
            pr_details={pr_number: _create_pr_details(pr_number, branch_name)},
        )

        test_ctx = env.build_context(git=git_ops, github=github_ops)

        result = runner.invoke(
            cli, ["pooled", "land", "--force"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed without prompting
        assert result.exit_code == 0
        assert f"Merged PR #{pr_number}" in result.output
        assert pr_number in github_ops.merged_prs


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


def test_pooled_land_auto_unassigns_slot() -> None:
    """Test that pooled land automatically unassigns the pool slot after merge."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        worktree_path = repo_dir / "worktrees" / "erk-managed-wt-01"
        worktree_path.mkdir(parents=True)

        branch_name = "feature-branch"
        pr_number = 123

        # Set cwd to the worktree (simulating being inside the pool worktree)
        git_ops = FakeGit(
            worktrees={worktree_path: env.build_worktrees("main")[env.cwd]},
            current_branches={worktree_path: branch_name},
            git_common_dirs={worktree_path: env.git_dir, env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", branch_name]},
        )

        github_ops = FakeGitHub(
            prs={branch_name: _create_pr_info(pr_number)},
            pr_details={pr_number: _create_pr_details(pr_number, branch_name)},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        # Create pool state with assignment
        assignment = _create_test_assignment("erk-managed-wt-01", branch_name, worktree_path)
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            assignments=(assignment,),
        )
        save_pool_state(repo.pool_json_path, initial_state)

        # Use worktree_path as cwd (simulating being inside the pool worktree)
        test_ctx = env.build_context(git=git_ops, github=github_ops, repo=repo, cwd=worktree_path)

        result = runner.invoke(cli, ["pooled", "land"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert f"Merged PR #{pr_number}" in result.output
        assert "Unassigned" in result.output
        assert branch_name in result.output
        assert "erk-managed-wt-01" in result.output
        assert "Switched to placeholder branch" in result.output
        assert "erk wt co root" in result.output

        # Verify PR was merged
        assert pr_number in github_ops.merged_prs

        # Verify assignment was removed
        state = load_pool_state(repo.pool_json_path)
        assert state is not None
        assert len(state.assignments) == 0

        # Verify placeholder branch was checked out
        assert (worktree_path, "__erk-slot-01-placeholder__") in git_ops.checked_out_branches
