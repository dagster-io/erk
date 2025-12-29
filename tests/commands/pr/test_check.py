"""Tests for erk pr check command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_check_passes_with_valid_footer_and_issue_reference(tmp_path: Path) -> None:
    """Test PR with valid footer and issue reference passes all checks."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Create .impl/issue.json at repo root
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

        # Setup PR with both closing reference and footer
        pr_body = """## Summary
This PR adds a feature.

---

Closes #456

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
        github = FakeGitHub(
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
            existing_paths={env.cwd, impl_dir},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 0
        assert "[PASS] PR body contains issue closing reference (Closes #456)" in result.output
        assert "[PASS] PR body contains checkout footer" in result.output
        assert "All checks passed" in result.output


def test_pr_check_fails_when_missing_issue_reference(tmp_path: Path) -> None:
    """Test PR missing 'Closes #N' when issue.json exists fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Create .impl/issue.json at repo root
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

        # Setup PR with footer but NO closing reference
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
        github = FakeGitHub(
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
            existing_paths={env.cwd, impl_dir},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 1
        expected_msg = "[FAIL] PR body missing issue closing reference (expected: Closes #456)"
        assert expected_msg in result.output
        assert "[PASS] PR body contains checkout footer" in result.output
        assert "1 check failed" in result.output


def test_pr_check_fails_when_missing_footer(tmp_path: Path) -> None:
    """Test PR missing checkout footer fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
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
        github = FakeGitHub(
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


def test_pr_check_passes_without_issue_json(tmp_path: Path) -> None:
    """Test PR without issue.json skips issue reference check."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # No .impl/issue.json - issue reference check should be skipped
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
        github = FakeGitHub(
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
        # Issue reference check should not appear
        assert "issue closing reference" not in result.output
        assert "[PASS] PR body contains checkout footer" in result.output
        assert "All checks passed" in result.output


def test_pr_check_fails_when_no_pr_exists(tmp_path: Path) -> None:
    """Test error when branch has no PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # No PR for this branch
        github = FakeGitHub(prs={})

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
    with erk_isolated_fs_env(runner) as env:
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
    with erk_isolated_fs_env(runner) as env:
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
        github = FakeGitHub(
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


def test_pr_check_case_insensitive_closes_pattern(tmp_path: Path) -> None:
    """Test 'closes' pattern is case-insensitive."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Create .impl/issue.json at repo root
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

        # Setup PR with lowercase 'closes'
        pr_body = """## Summary
This PR adds a feature.

closes #456

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
        github = FakeGitHub(
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
            existing_paths={env.cwd, impl_dir},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 0
        assert "[PASS] PR body contains issue closing reference (Closes #456)" in result.output


def test_pr_check_reports_multiple_failures(tmp_path: Path) -> None:
    """Test that multiple failures are counted correctly."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Create .impl/issue.json at repo root
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

        # PR missing BOTH closing reference AND footer
        pr_body = "Just a summary."

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
        github = FakeGitHub(
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
            existing_paths={env.cwd, impl_dir},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["check"], obj=ctx)

        assert result.exit_code == 1
        assert "[FAIL] PR body missing issue closing reference" in result.output
        assert "[FAIL] PR body missing checkout footer" in result.output
        assert "2 checks failed" in result.output
