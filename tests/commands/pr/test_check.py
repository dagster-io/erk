"""Tests for erk pr check command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.impl_folder import get_impl_dir
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_check_passes_with_valid_footer(tmp_path: Path) -> None:
    """Test PR with valid footer passes all checks."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        pr_body = """## Summary
This PR adds a feature.

---

To checkout this PR in a fresh worktree and environment locally, run:

```
erk pr checkout 123
```
"""
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Add feature",
            body=pr_body,
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        github = FakeLocalGitHub(
            prs={
                "feature-branch": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Add feature",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 0
        assert "[PASS] PR body contains checkout footer" in result.output
        assert "All checks passed" in result.output
        assert "issue closing reference" not in result.output


def test_pr_check_fails_when_missing_footer(tmp_path: Path) -> None:
    """Test PR missing checkout footer fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Setup PR without footer
        pr_body = """## Summary
This PR adds a feature.
"""
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Add feature",
            body=pr_body,
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        github = FakeLocalGitHub(
            prs={
                "feature-branch": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Add feature",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 1
        assert "[FAIL] PR body missing checkout footer" in result.output
        assert "1 check failed" in result.output


def test_pr_check_fails_when_no_pr_exists(tmp_path: Path) -> None:
    """Test error when branch has no PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # No PR for this branch
        github = FakeLocalGitHub(prs={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "no-pr-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 1
        assert "No pull request found for branch 'no-pr-branch'" in result.output


def test_pr_check_fails_when_not_on_branch(tmp_path: Path) -> None:
    """Test error when on detached HEAD."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Detached HEAD (no current branch)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 1
        assert "Not on a branch" in result.output


def test_pr_check_handles_empty_pr_body(tmp_path: Path) -> None:
    """Test PR with empty body fails footer check."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # PR with empty body
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Add feature",
            body="",  # Empty body
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        github = FakeLocalGitHub(
            prs={
                "feature-branch": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Add feature",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 1
        assert "[FAIL] PR body missing checkout footer" in result.output


def test_pr_check_passes_when_branch_and_plan_ref_match(tmp_path: Path) -> None:
    """Test PR check passes with matching branch name and branch-scoped ref.json."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # Create branch-scoped impl dir with ref.json for plan 456
        impl_dir = get_impl_dir(env.cwd, branch_name="plnd/add-feature-01-04-1234")
        impl_dir.mkdir(parents=True)
        plan_ref_json = impl_dir / "ref.json"
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

        pr_body = """## Summary
This PR adds a feature.

---

To checkout this PR in a fresh worktree and environment locally, run:

```
erk pr checkout 123
```
"""
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Add feature",
            body=pr_body,
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="plnd/add-feature-01-04-1234",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        github = FakeLocalGitHub(
            prs={
                "plnd/add-feature-01-04-1234": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Add feature",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "plnd/add-feature-01-04-1234"},
            existing_paths={env.cwd, impl_dir},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 0
        assert "[PASS] Plan reference found (#456)" in result.output
        assert "[PASS] PR body contains checkout footer" in result.output
        assert "All checks passed" in result.output


def test_pr_check_passes_with_bottom_header(tmp_path: Path) -> None:
    """Test PR with header at bottom (new format) passes header position check."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # PR body with header at bottom (new format)
        pr_body = (
            "## Summary\nThis PR adds a feature.\n\n"
            "**Plan:** #456\n\n"
            "---\n\n"
            "To checkout this PR in a fresh worktree and environment locally, run:\n\n"
            "```\nerk pr checkout 123\n```\n"
        )
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Add feature",
            body=pr_body,
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        github = FakeLocalGitHub(
            prs={
                "feature-branch": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Add feature",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 0
        assert "[PASS] Plan-header metadata is at correct position" in result.output


def test_pr_check_fails_with_legacy_top_header(tmp_path: Path) -> None:
    """Test PR with header at top (legacy format) fails header position check."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        # PR body with header at top (legacy format)
        pr_body = (
            "**Plan:** #456\n\n"
            "## Summary\nThis PR adds a feature.\n\n"
            "---\n\n"
            "To checkout this PR in a fresh worktree and environment locally, run:\n\n"
            "```\nerk pr checkout 123\n```\n"
        )
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Add feature",
            body=pr_body,
            state="OPEN",
            is_draft=False,
            base_ref_name="main",
            head_ref_name="feature-branch",
            is_cross_repository=False,
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
            owner="owner",
            repo="repo",
        )
        github = FakeLocalGitHub(
            prs={
                "feature-branch": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Add feature",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 1
        assert "[FAIL] Plan-header metadata is at legacy top position" in result.output
        assert "should be above footer" in result.output


def test_pr_check_stage_impl_fails_when_impl_context_present(tmp_path: Path) -> None:
    """Test --stage=impl fails when .erk/impl-context/ directory still exists."""
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
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Test PR",
            body=pr_body,
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
        github = FakeLocalGitHub(
            prs={
                branch: PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Test PR",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["check", "--stage=impl"], obj=ctx)

        assert result.exit_code == 1
        assert "[FAIL] .erk/impl-context/ still present" in result.output
        assert "should be removed before submission" in result.output


def test_pr_check_stage_impl_passes_when_impl_context_absent(tmp_path: Path) -> None:
    """Test --stage=impl passes impl-context check when directory does not exist."""
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
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Test PR",
            body=pr_body,
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
        github = FakeLocalGitHub(
            prs={
                branch: PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Test PR",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["check", "--stage=impl"], obj=ctx)

        assert "[PASS] .erk/impl-context/ not present (cleaned up)" in result.output


def test_pr_check_stage_impl_all_checks_pass(tmp_path: Path) -> None:
    """Test --stage=impl checks pass when PR is properly configured and impl-context absent.

    After impl folder cleanup (git rm), the impl-context directory is not present on disk.
    The plan reference check is optional (only added if impl dir found), so this test
    verifies the impl-context cleanup check and other PR body checks pass.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        pr_body = (
            "## Summary\nThis PR adds a feature.\n\n"
            "---\n\n"
            "To checkout this PR in a fresh worktree and environment locally, run:\n\n"
            "```\nerk pr checkout 123\n```\n"
        )
        branch = "plnd/add-feature-01-04-1234"
        pr_details = PRDetails(
            number=123,
            url="https://github.com/owner/repo/pull/123",
            title="Test PR",
            body=pr_body,
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
        github = FakeLocalGitHub(
            prs={
                branch: PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Test PR",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                )
            },
            pr_details={123: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: branch},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["check", "--stage=impl"], obj=ctx)

        assert result.exit_code == 0
        assert "[PASS] .erk/impl-context/ not present (cleaned up)" in result.output
        assert "[PASS] PR body contains checkout footer" in result.output
        assert "All checks passed" in result.output
