"""Tests for pr-check-complete exec command.

Tests the PR completion invariant checker that validates implementation
is complete and ready for submission.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.pr_check_complete import pr_check_complete
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_details(
    *,
    number: int,
    body: str,
    branch: str,
) -> PRDetails:
    """Create PRDetails with standard test defaults."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Test PR",
        body=body,
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def _make_pr_info(
    *,
    number: int,
) -> PullRequestInfo:
    """Create PullRequestInfo with standard test defaults."""
    return PullRequestInfo(
        number=number,
        state="OPEN",
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title="Test PR",
        checks_passing=None,
        owner="owner",
        repo="repo",
        has_conflicts=None,
    )


def test_all_checks_pass(tmp_path: Path) -> None:
    """Test all checks pass when PR is properly configured and impl-context is absent."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Create .impl/ with plan-ref.json
        impl_dir = env.cwd / ".impl"
        impl_dir.mkdir()
        plan_ref_json = impl_dir / "plan-ref.json"
        plan_ref_json.write_text(
            json.dumps(
                {
                    "provider": "github",
                    "plan_id": "456",
                    "url": "https://github.com/owner/repo/issues/456",
                    "created_at": "2025-01-01T00:00:00Z",
                    "synced_at": "2025-01-01T00:00:00Z",
                }
            )
        )

        # No .erk/impl-context/ (properly cleaned up)

        pr_body = (
            "## Summary\nThis PR adds a feature.\n\n"
            "---\n\nCloses #456\n\n"
            "To checkout this PR in a fresh worktree and environment locally, run:\n\n"
            "```\nerk pr checkout 123\n```\n"
        )
        branch = "P456-add-feature-01-04-1234"
        pr_details = _make_pr_details(number=123, body=pr_body, branch=branch)
        github = FakeGitHub(
            prs={branch: _make_pr_info(number=123)},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch},
            existing_paths={env.cwd, impl_dir},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_check_complete, obj=ctx)

        assert result.exit_code == 0
        assert "[PASS] .erk/impl-context/ not present (cleaned up)" in result.output
        assert "[PASS] Branch name and plan reference agree (#456)" in result.output
        assert "[PASS] PR body contains issue closing reference (Closes #456)" in result.output
        assert "[PASS] PR body contains checkout footer" in result.output
        assert "All checks passed" in result.output


def test_fails_when_impl_context_present(tmp_path: Path) -> None:
    """Test failure when .erk/impl-context/ directory still exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Create .erk/impl-context/ (NOT cleaned up)
        impl_context_dir = env.cwd / ".erk" / "impl-context"
        impl_context_dir.mkdir(parents=True)

        pr_body = (
            "## Summary\nThis PR adds a feature.\n\n"
            "---\n\n"
            "To checkout this PR in a fresh worktree and environment locally, run:\n\n"
            "```\nerk pr checkout 123\n```\n"
        )
        branch = "feature-branch"
        pr_details = _make_pr_details(number=123, body=pr_body, branch=branch)
        github = FakeGitHub(
            prs={branch: _make_pr_info(number=123)},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_check_complete, obj=ctx)

        assert result.exit_code == 1
        assert "[FAIL] .erk/impl-context/ still present" in result.output
        assert "should be removed before submission" in result.output


def test_passes_when_impl_context_absent(tmp_path: Path) -> None:
    """Test impl-context check passes when directory does not exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # No .erk/impl-context/ (properly cleaned up)
        pr_body = (
            "## Summary\nThis PR adds a feature.\n\n"
            "---\n\n"
            "To checkout this PR in a fresh worktree and environment locally, run:\n\n"
            "```\nerk pr checkout 123\n```\n"
        )
        branch = "feature-branch"
        pr_details = _make_pr_details(number=123, body=pr_body, branch=branch)
        github = FakeGitHub(
            prs={branch: _make_pr_info(number=123)},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_check_complete, obj=ctx)

        assert "[PASS] .erk/impl-context/ not present (cleaned up)" in result.output


def test_fails_when_no_pr_exists(tmp_path: Path) -> None:
    """Test error when branch has no PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        github = FakeGitHub(prs={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "no-pr-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_check_complete, obj=ctx)

        assert result.exit_code == 1
        assert "No pull request found for branch 'no-pr-branch'" in result.output


def test_fails_when_not_on_branch(tmp_path: Path) -> None:
    """Test error when on detached HEAD."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},
        )

        ctx = build_workspace_test_context(env, git=git)
        result = runner.invoke(pr_check_complete, obj=ctx)

        assert result.exit_code == 1
        assert "Not on a branch" in result.output


def test_reports_multiple_failures(tmp_path: Path) -> None:
    """Test that multiple failures are counted correctly."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Create .erk/impl-context/ (not cleaned up)
        impl_context_dir = env.cwd / ".erk" / "impl-context"
        impl_context_dir.mkdir(parents=True)

        # Create .impl/issue.json
        impl_dir = env.cwd / ".impl"
        impl_dir.mkdir()
        issue_json = impl_dir / "issue.json"
        issue_json.write_text(
            json.dumps(
                {
                    "issue_number": 456,
                    "issue_url": "https://github.com/owner/repo/issues/456",
                    "created_at": "2025-01-01T00:00:00Z",
                    "synced_at": "2025-01-01T00:00:00Z",
                }
            )
        )

        # PR missing both closing reference AND footer
        pr_body = "Just a summary."
        branch = "feature-branch"
        pr_details = _make_pr_details(number=123, body=pr_body, branch=branch)
        github = FakeGitHub(
            prs={branch: _make_pr_info(number=123)},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch},
            existing_paths={env.cwd, impl_dir},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_check_complete, obj=ctx)

        assert result.exit_code == 1
        assert "[FAIL] .erk/impl-context/ still present" in result.output
        assert "[FAIL] PR body missing issue closing reference" in result.output
        assert "[FAIL] PR body missing checkout footer" in result.output
        assert "3 checks failed" in result.output


def test_draft_pr_plan_skips_closing_reference(tmp_path: Path) -> None:
    """Test that draft-PR plans skip the closing reference check."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Create .impl/plan-ref.json with draft-PR provider
        impl_dir = env.cwd / ".impl"
        impl_dir.mkdir()
        plan_ref_json = impl_dir / "plan-ref.json"
        plan_ref_json.write_text(
            json.dumps(
                {
                    "provider": "github-draft-pr",
                    "plan_id": "7656",
                    "url": "https://github.com/owner/repo/pull/7656",
                    "created_at": "2025-01-15T14:30:00Z",
                    "synced_at": "2025-01-15T14:30:00Z",
                    "labels": [],
                }
            )
        )

        pr_body = (
            "## Summary\nThis PR fixes a bug.\n\n"
            "---\n\n"
            "To checkout this PR in a fresh worktree and environment locally, run:\n\n"
            "```\nerk pr checkout 123\n```\n"
        )
        branch = "plan-fix-bug-01-15-1430"
        pr_details = _make_pr_details(number=123, body=pr_body, branch=branch)
        github = FakeGitHub(
            prs={branch: _make_pr_info(number=123)},
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch},
            existing_paths={env.cwd, impl_dir},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_check_complete, obj=ctx)

        assert result.exit_code == 0
        assert "[PASS] Draft PR plan" in result.output
        assert "no closing reference needed" in result.output
