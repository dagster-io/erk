"""Tests for erk pr checkout command."""

import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.git.abc import RebaseResult, WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_details(
    number: int,
    head_ref_name: str,
    is_cross_repository: bool,
    state: str,
    base_ref_name: str = "main",
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


def _make_pr_info(number: int, state: str = "OPEN") -> PullRequestInfo:
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


def test_pr_checkout_same_repo_branch_exists_on_remote() -> None:
    """Test checking out a same-repo PR where branch exists on remote."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Setup repo structure for worktrees_dir
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={123: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # Simulate shell integration active to test output messages
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "123"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree for PR #123" in result.output
        # Verify fetch was called
        assert ("origin", "feature-branch") in git.fetched_branches
        # Verify tracking branch was created
        assert ("feature-branch", "origin/feature-branch") in git.created_tracking_branches
        # Verify worktree was added
        assert len(git.added_worktrees) == 1


def test_pr_checkout_same_repo_branch_already_local() -> None:
    """Test checking out a same-repo PR where branch already exists locally."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=456,
            head_ref_name="existing-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={456: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "existing-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/existing-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["checkout", "456"], obj=ctx)

        assert result.exit_code == 0
        # No fetch needed since branch exists locally
        assert len(git.fetched_branches) == 0
        assert len(git.created_tracking_branches) == 0
        # Worktree should still be created
        assert len(git.added_worktrees) == 1


def test_pr_checkout_cross_repository_fork() -> None:
    """Test checking out a PR from a fork uses pr/<number> branch name."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=789,
            head_ref_name="contributor-branch",
            is_cross_repository=True,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={789: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # Simulate shell integration active to test output messages
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "789"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree for PR #789" in result.output
        # Should fetch via PR ref, not regular branch
        assert ("origin", "pull/789/head") in git.fetched_branches
        # Worktree should be at pr/789 path
        worktree_path = Path(git.added_worktrees[0][0])
        assert "pr" in worktree_path.parts[-1] or worktree_path.name == "789"


def test_pr_checkout_already_checked_out() -> None:
    """Test checking out a PR that's already in a worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=111,
            head_ref_name="existing-wt-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={111: pr_details})
        existing_wt_path = env.repo.worktrees_dir / "existing-wt-branch"
        existing_wt_path.mkdir(parents=True, exist_ok=True)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=existing_wt_path, branch="existing-wt-branch"),
                ]
            },
            local_branches={env.cwd: ["main", "existing-wt-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir, existing_wt_path},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # Simulate shell integration active to test output messages
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "111"], obj=ctx)

        assert result.exit_code == 0
        assert "already checked out" in result.output
        # No worktree should be added
        assert len(git.added_worktrees) == 0


def test_pr_checkout_pr_not_found() -> None:
    """Test error when PR does not exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        github = FakeGitHub(pr_details={})  # Empty - PR 999 not found
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["checkout", "999"], obj=ctx)

        assert result.exit_code == 1
        assert "Could not find PR #999" in result.output


def test_pr_checkout_warns_on_closed_pr() -> None:
    """Test warning displayed when checking out a closed PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=222,
            head_ref_name="closed-branch",
            is_cross_repository=False,
            state="CLOSED",
        )
        github = FakeGitHub(pr_details={222: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "closed-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["checkout", "222"], obj=ctx)

        assert result.exit_code == 0
        assert "CLOSED" in result.output


def test_pr_checkout_warns_on_merged_pr() -> None:
    """Test warning displayed when checking out a merged PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=333,
            head_ref_name="merged-branch",
            is_cross_repository=False,
            state="MERGED",
        )
        github = FakeGitHub(pr_details={333: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "merged-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["checkout", "333"], obj=ctx)

        assert result.exit_code == 0
        assert "MERGED" in result.output


def test_pr_checkout_with_github_url() -> None:
    """Test checking out a PR using GitHub URL instead of number."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=444,
            head_ref_name="url-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={444: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "url-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # Simulate shell integration active to test output messages
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                pr_group,
                ["checkout", "https://github.com/owner/repo/pull/444"],
                obj=ctx,
            )

        assert result.exit_code == 0
        assert "Created worktree for PR #444" in result.output


def test_pr_checkout_invalid_reference() -> None:
    """Test error on invalid PR reference format."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(pr_group, ["checkout", "not-a-number"], obj=ctx)

        assert result.exit_code == 1
        assert "Invalid PR number or URL" in result.output


def test_pr_checkout_script_mode_outputs_script_path() -> None:
    """Test that --script flag outputs activation script path."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=555,
            head_ref_name="script-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={555: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "script-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["checkout", "555", "--script"], obj=ctx)

        assert result.exit_code == 0
        # In script mode, output is just the script path
        script_path_str = result.stdout.strip()
        assert script_path_str != ""
        # Script file should exist and contain activation commands
        script_path = Path(script_path_str)
        assert script_path.exists()
        script_content = script_path.read_text()
        assert "cd " in script_content
        assert ".venv" in script_content


def test_pr_checkout_non_script_mode_spawns_subshell() -> None:
    """Test that non-script mode without shell integration spawns subshell."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=666,
            head_ref_name="manual-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(pr_details={666: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "manual-branch"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # Without ERK_SHELL set, the command spawns a subshell
        # Ensure ERK_SHELL is NOT set
        env_copy = {k: v for k, v in os.environ.items() if k != "ERK_SHELL"}
        with patch.dict(os.environ, env_copy, clear=True):
            result = runner.invoke(pr_group, ["checkout", "666"], obj=ctx)

        # Subshell shows welcome banner
        assert result.exit_code == 0
        assert "worktree subshell" in result.output
        assert "exit" in result.output


def test_pr_checkout_stacked_pr_rebases_onto_base() -> None:
    """Test that checking out a stacked PR rebases onto base branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        # PR-B is based on PR-A (not trunk)
        pr_details = _make_pr_details(
            number=777,
            head_ref_name="feature-b",
            is_cross_repository=False,
            state="OPEN",
            base_ref_name="feature-a",  # Not trunk - this is a stacked PR
        )
        github = FakeGitHub(pr_details={777: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-b"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-a", "origin/feature-b"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # Simulate shell integration active to test output messages
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "777"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree for PR #777" in result.output
        # Verify base branch was fetched
        assert ("origin", "feature-a") in git.fetched_branches
        # Verify rebase was called
        assert len(git.rebase_onto_calls) == 1
        _cwd, target_ref = git.rebase_onto_calls[0]
        assert target_ref == "origin/feature-a"


def test_pr_checkout_stacked_pr_with_conflicts_warns_user() -> None:
    """Test that stacked PR checkout with rebase conflicts warns user."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=888,
            head_ref_name="feature-conflict",
            is_cross_repository=False,
            state="OPEN",
            base_ref_name="feature-base",  # Stacked PR
        )
        github = FakeGitHub(pr_details={888: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-conflict"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-base"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
            rebase_onto_result=RebaseResult(
                success=False,
                conflict_files=("file1.py", "file2.py"),
            ),
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # Simulate shell integration active to test output messages
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "888"], obj=ctx)

        assert result.exit_code == 0
        # Worktree should still be created
        assert "Created worktree for PR #888" in result.output
        # Warning about conflicts (prefixed with "Warning:")
        assert "Warning: Rebase had conflicts" in result.output
        assert "git rebase origin/feature-base" in result.output
        # Verify rebase was aborted
        assert len(git.rebase_abort_calls) == 1


def test_pr_checkout_trunk_pr_skips_rebase() -> None:
    """Test that PRs targeting trunk don't trigger a rebase."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()
        # This PR targets trunk (main), not another branch
        pr_details = _make_pr_details(
            number=999,
            head_ref_name="trunk-feature",
            is_cross_repository=False,
            state="OPEN",
            base_ref_name="main",  # Targets trunk - not a stacked PR
        )
        github = FakeGitHub(pr_details={999: pr_details})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "trunk-feature"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)

        # Simulate shell integration active to test output messages
        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(pr_group, ["checkout", "999"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree for PR #999" in result.output
        # No rebase should have been called
        assert len(git.rebase_onto_calls) == 0
