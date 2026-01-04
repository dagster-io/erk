"""Unit tests for pooled land command."""

from click.testing import CliRunner

from erk.cli.cli import cli
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
    """Test that pooled land merges the PR successfully."""
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
        assert "Branch and worktree preserved" in result.output
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


def test_pooled_land_preserves_worktree_message() -> None:
    """Test that pooled land shows message about preserving worktree."""
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
        assert "Branch and worktree preserved" in result.output
        assert "erk pooled unassign" in result.output
