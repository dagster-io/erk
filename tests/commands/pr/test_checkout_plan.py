"""Tests for plan checkout via pr checkout command (P-prefix routing)."""

import os
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.github_parsing import parse_issue_identifier
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.github.issues.types import PRReference
from erk_shared.gateway.github.types import PRDetails
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.github_issues import FakeGitHubIssues
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env

# ============================================================================
# Tests for parse_issue_identifier P-prefix support
# ============================================================================


def test_parse_issue_identifier_p_prefix_uppercase() -> None:
    """Test parsing P-prefixed identifier with uppercase P."""
    result = parse_issue_identifier("P123")
    assert result == 123


def test_parse_issue_identifier_p_prefix_lowercase() -> None:
    """Test parsing P-prefixed identifier with lowercase p."""
    result = parse_issue_identifier("p456")
    assert result == 456


def test_parse_issue_identifier_p_prefix_large_number() -> None:
    """Test parsing P-prefixed identifier with large number."""
    result = parse_issue_identifier("P12345")
    assert result == 12345


def test_parse_issue_identifier_plain_number_still_works() -> None:
    """Test that plain numbers still parse correctly."""
    result = parse_issue_identifier("789")
    assert result == 789


# ============================================================================
# Tests for plan checkout via pr checkout command
# ============================================================================


def _make_pr_details(
    number: int,
    head_ref_name: str,
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
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_checkout_local_branch_exists() -> None:
    """Test checkout when a PR's branch already has a worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        branch_name = "plnd/fix-bug-01-15-1430"
        worktree_path = env.repo.worktrees_dir / "fix-bug"
        worktree_path.mkdir(parents=True)

        pr_details = _make_pr_details(number=200, head_ref_name=branch_name, state="OPEN")
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", branch_name]},
            remote_branches={env.cwd: ["origin/main", f"origin/{branch_name}"]},
            existing_paths={env.cwd, env.repo.worktrees_dir, worktree_path},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=branch_name, is_root=False),
                ]
            },
        )
        fake_issues = FakeGitHubIssues(
            pr_references={123: [PRReference(number=200, state="OPEN", is_draft=False)]},
        )
        github = FakeLocalGitHub(
            pr_details={200: pr_details},
            issues_gateway=fake_issues,
        )
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(cli, ["pr", "checkout", "P123"], obj=ctx)

        assert result.exit_code == 0
        assert "already checked out" in result.output


def test_checkout_with_plain_number() -> None:
    """Test checkout using plain number (now requires P-prefix for plan checkout)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=200,
            head_ref_name="plnd/feature-02-20-0900",
            state="OPEN",
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/plnd/feature-02-20-0900"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        fake_issues = FakeGitHubIssues(
            pr_references={456: [PRReference(number=200, state="OPEN", is_draft=False)]},
        )
        github = FakeLocalGitHub(
            pr_details={200: pr_details},
            issues_gateway=fake_issues,
        )
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(cli, ["pr", "checkout", "P456"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree for PR #456 (PR #200)" in result.output


def test_checkout_branch_already_in_worktree() -> None:
    """Test checkout when PR's branch is already checked out in a worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        branch_name = "plnd/existing-03-01-1200"
        worktree_path = env.repo.worktrees_dir / "existing"
        worktree_path.mkdir(parents=True)

        pr_details = _make_pr_details(number=300, head_ref_name=branch_name, state="OPEN")
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", branch_name]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir, worktree_path},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=worktree_path, branch=branch_name, is_root=False),
                ]
            },
        )
        fake_issues = FakeGitHubIssues(
            pr_references={789: [PRReference(number=300, state="OPEN", is_draft=False)]},
        )
        github = FakeLocalGitHub(
            pr_details={300: pr_details},
            issues_gateway=fake_issues,
        )
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(cli, ["pr", "checkout", "P789"], obj=ctx)

        assert result.exit_code == 0
        assert "already checked out" in result.output
        # No new worktree should be created
        assert len(git.added_worktrees) == 0


def test_checkout_no_local_branch_fetches_pr() -> None:
    """Test checkout fetches PR when no local branch exists but PR does."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=200,
            head_ref_name="plnd/from-pr-04-15-1400",
            state="OPEN",
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},  # No matching branch
            remote_branches={env.cwd: ["origin/main", "origin/plnd/from-pr-04-15-1400"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        # PR references the issue
        fake_issues = FakeGitHubIssues(
            pr_references={42: [PRReference(number=200, state="OPEN", is_draft=False)]},
        )
        github = FakeLocalGitHub(
            pr_details={200: pr_details},
            issues_gateway=fake_issues,
        )
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(cli, ["pr", "checkout", "P42"], obj=ctx)

        assert result.exit_code == 0
        assert "Created worktree for PR #42 (PR #200)" in result.output
        # Verify fetch was called
        assert ("origin", "plnd/from-pr-04-15-1400") in git.fetched_branches


def test_checkout_multiple_open_prs_shows_table() -> None:
    """Test checkout shows table when multiple open PRs reference the issue."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        # Multiple PRs reference the issue
        fake_issues = FakeGitHubIssues(
            pr_references={
                50: [
                    PRReference(number=300, state="OPEN", is_draft=False),
                    PRReference(number=301, state="OPEN", is_draft=True),
                ]
            },
        )
        github = FakeLocalGitHub(issues_gateway=fake_issues)
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        result = runner.invoke(cli, ["pr", "checkout", "P50"], obj=ctx)

        assert result.exit_code == 0  # Should exit cleanly after showing table
        assert "Multiple open PRs found" in result.output
        assert "#300" in result.output
        assert "#301" in result.output
        assert "erk pr checkout" in result.output


def test_checkout_filters_to_open_prs_only() -> None:
    """Test checkout only considers OPEN PRs, not CLOSED or MERGED."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr_details = _make_pr_details(
            number=400,
            head_ref_name="plnd/still-open-05-01-1200",
            state="OPEN",
        )
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/plnd/still-open-05-01-1200"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        # Multiple PRs, but only one is OPEN
        fake_issues = FakeGitHubIssues(
            pr_references={
                60: [
                    PRReference(number=400, state="OPEN", is_draft=False),
                    PRReference(number=401, state="CLOSED", is_draft=False),
                    PRReference(number=402, state="MERGED", is_draft=False),
                ]
            },
        )
        github = FakeLocalGitHub(
            pr_details={400: pr_details},
            issues_gateway=fake_issues,
        )
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(cli, ["pr", "checkout", "P60"], obj=ctx)

        # Should checkout the single OPEN PR, not show table
        assert result.exit_code == 0
        assert "Created worktree for PR #60 (PR #400)" in result.output


def test_checkout_no_branch_no_pr_shows_help() -> None:
    """Test checkout shows helpful message when nothing found."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        fake_issues = FakeGitHubIssues(pr_references={})
        github = FakeLocalGitHub(issues_gateway=fake_issues)
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        result = runner.invoke(cli, ["pr", "checkout", "P999"], obj=ctx)

        assert result.exit_code == 1
        assert "No open PR found for PR #999" in result.output
        assert "erk br co --for-plan 999" in result.output


def test_checkout_invalid_identifier() -> None:
    """Test checkout with invalid identifier shows error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(cli, ["pr", "checkout", "invalid-input"], obj=ctx)

        assert result.exit_code == 1
        assert "Invalid PR number, plan ID, or URL" in result.output
        assert "P123" in result.output  # Should mention P-prefix format


def test_checkout_with_github_url() -> None:
    """Test checkout accepts GitHub issue URL and finds PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        branch = "plnd/url-test-06-01-0800"
        wt = env.repo.worktrees_dir / "url-test"
        wt.mkdir(parents=True)

        pr_details = _make_pr_details(number=600, head_ref_name=branch, state="OPEN")
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", branch]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir, wt},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt, branch=branch, is_root=False),
                ]
            },
        )
        fake_issues = FakeGitHubIssues(
            pr_references={555: [PRReference(number=600, state="OPEN", is_draft=False)]},
        )
        github = FakeLocalGitHub(
            pr_details={600: pr_details},
            issues_gateway=fake_issues,
        )
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(
                cli,
                ["pr", "checkout", "https://github.com/owner/repo/issues/555"],
                obj=ctx,
            )

        assert result.exit_code == 0
        assert "already checked out" in result.output


def test_checkout_worktree_with_existing_pr_branch() -> None:
    """Test checkout finds existing worktree via PR branch lookup."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        branch = "plnd/old-style-branch"
        wt = env.repo.worktrees_dir / "old-style"
        wt.mkdir(parents=True)

        pr_details = _make_pr_details(number=800, head_ref_name=branch, state="OPEN")
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", branch]},
            remote_branches={env.cwd: ["origin/main"]},
            existing_paths={env.cwd, env.repo.worktrees_dir, wt},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt, branch=branch, is_root=False),
                ]
            },
        )
        fake_issues = FakeGitHubIssues(
            pr_references={777: [PRReference(number=800, state="OPEN", is_draft=False)]},
        )
        github = FakeLocalGitHub(
            pr_details={800: pr_details},
            issues_gateway=fake_issues,
        )
        ctx = build_workspace_test_context(env, git=git, github=github, issues=fake_issues)

        with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
            result = runner.invoke(cli, ["pr", "checkout", "P777"], obj=ctx)

        assert result.exit_code == 0
        assert "already checked out" in result.output
