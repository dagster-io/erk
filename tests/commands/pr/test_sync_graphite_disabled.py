"""Tests for pr sync command with Graphite disabled (git-only mode).

This file verifies that pr sync works correctly when Graphite is disabled,
using the git-only sync path: fetch → rebase → force push.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.git.abc import RebaseResult
from erk_shared.git.fake import FakeGit, PushedBranch
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_info(
    number: int,
    branch: str,
    state: str = "OPEN",
) -> PullRequestInfo:
    """Create a PullRequestInfo for testing."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title=f"PR #{number}",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )


def _make_pr_details(
    number: int,
    head_ref_name: str,
    state: str = "OPEN",
    base_ref_name: str = "main",
    is_cross_repository: bool = False,
) -> PRDetails:
    """Create a PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}",
        body="",
        state=state,
        is_draft=False,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        is_cross_repository=is_cross_repository,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_pr_sync_git_only_happy_path(tmp_path: Path) -> None:
    """pr sync without Graphite: fetch → rebase → force push."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(123, "feature-branch")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        # GraphiteDisabled sentinel - triggers git-only mode
        graphite_disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite_disabled,
        )

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 0
        assert "Base branch: main" in result.output
        assert "Fetching origin/main" in result.output
        assert "Rebasing onto origin/main" in result.output
        assert "Rebase complete" in result.output
        assert "Force pushing" in result.output
        assert "synchronized" in result.output

        # Verify git operations were called
        assert len(git._fetched_branches) == 1
        assert git._fetched_branches[0] == ("origin", "main")

        assert len(git.rebase_onto_calls) == 1
        assert git.rebase_onto_calls[0] == (env.cwd, "origin/main")

        assert len(git._pushed_branches) == 1
        assert git._pushed_branches[0] == PushedBranch(
            remote="origin", branch="feature-branch", set_upstream=False, force=True
        )


def test_pr_sync_git_only_uses_pr_base_branch(tmp_path: Path) -> None:
    """Git-only sync uses PR base branch from GitHub, not assumptions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR targets "release/v1.0" not "main"
        pr_info = _make_pr_info(456, "hotfix-branch")
        pr_details = _make_pr_details(
            number=456,
            head_ref_name="hotfix-branch",
            base_ref_name="release/v1.0",
        )
        github = FakeGitHub(
            prs={"hotfix-branch": pr_info},
            pr_details={456: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "hotfix-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite_disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite_disabled,
        )

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 0
        assert "Base branch: release/v1.0" in result.output
        assert "Fetching origin/release/v1.0" in result.output

        # Verify correct base branch used
        assert git._fetched_branches[0] == ("origin", "release/v1.0")
        assert git.rebase_onto_calls[0] == (env.cwd, "origin/release/v1.0")


def test_pr_sync_git_only_handles_rebase_conflict(tmp_path: Path) -> None:
    """Git-only sync shows helpful error when rebase conflicts occur."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(789, "conflict-branch")
        pr_details = _make_pr_details(
            number=789,
            head_ref_name="conflict-branch",
        )
        github = FakeGitHub(
            prs={"conflict-branch": pr_info},
            pr_details={789: pr_details},
        )

        # Configure rebase to return conflict
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "conflict-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
            rebase_onto_result=RebaseResult(
                success=False,
                conflict_files=("file1.py", "file2.py"),
            ),
        )

        graphite_disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite_disabled,
        )

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        # Should exit with error code
        assert result.exit_code == 1
        # Should show conflict message
        assert "merge conflicts" in result.output
        # Should list conflicted files
        assert "file1.py" in result.output
        assert "file2.py" in result.output
        # Should show resolution instructions
        assert "git add" in result.output
        assert "git rebase --continue" in result.output
        assert "git push --force" in result.output

        # Should NOT have pushed (stopped at conflict)
        assert len(git._pushed_branches) == 0


def test_pr_sync_git_only_fails_on_closed_pr(tmp_path: Path) -> None:
    """Git-only sync fails when PR is closed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(999, "closed-branch", state="CLOSED")
        pr_details = _make_pr_details(
            number=999,
            head_ref_name="closed-branch",
            state="CLOSED",
        )
        github = FakeGitHub(
            prs={"closed-branch": pr_info},
            pr_details={999: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "closed-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite_disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite_disabled,
        )

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot sync CLOSED PR" in result.output


def test_pr_sync_git_only_fails_on_fork_pr(tmp_path: Path) -> None:
    """Git-only sync fails when PR is from a fork."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(111, "fork-branch")
        pr_details = _make_pr_details(
            number=111,
            head_ref_name="fork-branch",
            is_cross_repository=True,
        )
        github = FakeGitHub(
            prs={"fork-branch": pr_info},
            pr_details={111: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "fork-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite_disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite_disabled,
        )

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot sync fork PRs" in result.output


def test_pr_sync_git_only_does_not_require_dangerous_flag(tmp_path: Path) -> None:
    """Git-only sync works without --dangerous flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        pr_info = _make_pr_info(222, "feature-branch")
        pr_details = _make_pr_details(
            number=222,
            head_ref_name="feature-branch",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={222: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )

        graphite_disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite_disabled,
        )

        # Invoke WITHOUT --dangerous flag
        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        # Should succeed (git-only mode doesn't need --dangerous)
        assert result.exit_code == 0
        assert "synchronized" in result.output
