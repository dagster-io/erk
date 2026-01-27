"""Tests for submitting multiple issues."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import ERK_PLAN_LABEL, submit_cmd
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from tests.commands.submit.conftest import create_plan, make_plan_body


def test_submit_multiple_issues_success(tmp_path: Path) -> None:
    """Test submit successfully handles multiple issue numbers (happy path)."""
    plan_123 = create_plan("123", "Feature A", body=make_plan_body("Implementation for A..."))
    plan_456 = create_plan("456", "Feature B", body=make_plan_body("Implementation for B..."))

    # Create a custom FakeGit subclass that cleans up .worker-impl/ on checkout
    # This simulates the real behavior where checking out a branch without
    # .worker-impl/ removes the folder from the working directory
    from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
    from erk_shared.gateway.git.branch_ops.fake import FakeGitBranchOps

    class FakeGitBranchOpsWithCheckoutCleanup(FakeGitBranchOps):
        def __init__(self, fs_repo_root: Path, **kwargs):
            super().__init__(**kwargs)
            self._fs_repo_root = fs_repo_root

        def checkout_branch(self, cwd: Path, branch: str) -> None:
            super().checkout_branch(cwd, branch)
            # Simulate git checkout: when switching to original branch,
            # files from the feature branch (like .worker-impl/) are removed
            worker_impl = self._fs_repo_root / ".worker-impl"
            if worker_impl.exists():
                shutil.rmtree(worker_impl)

    class FakeGitWithCheckoutCleanup(FakeGit):
        def __init__(self, fs_repo_root: Path, **kwargs):
            super().__init__(**kwargs)
            # Create custom branch gateway with cleanup behavior
            # Link to our mutable state and mutation tracking
            self._custom_branch_gateway = FakeGitBranchOpsWithCheckoutCleanup(
                fs_repo_root=fs_repo_root,
                worktrees=self._worktrees,
                current_branches=self._current_branches,
                local_branches=self._local_branches,
                delete_branch_raises=self._delete_branch_raises,
                tracking_branch_failures=self._tracking_branch_failures,
            )
            # Link mutation tracking so FakeGit properties see mutations
            self._custom_branch_gateway.link_mutation_tracking(
                created_branches=self._created_branches,
                deleted_branches=self._deleted_branches,
                checked_out_branches=self._checked_out_branches,
                detached_checkouts=self._detached_checkouts,
                created_tracking_branches=self._created_tracking_branches,
            )

        @property
        def branch(self) -> GitBranchOps:
            return self._custom_branch_gateway

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    from tests.test_utils.plan_helpers import create_plan_store_with_plans

    fake_plan_store, fake_github_issues = create_plan_store_with_plans(
        {"123": plan_123, "456": plan_456}
    )

    fake_git = FakeGitWithCheckoutCleanup(
        fs_repo_root=repo_root,
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        plan_store=fake_plan_store,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "456"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "2 issue(s) submitted successfully!" in result.output
    assert "#123: Feature A" in result.output
    assert "#456: Feature B" in result.output

    # Verify both branches were created via git.branch
    assert len(fake_git.created_branches) == 2
    created_branch_names = [b[1] for b in fake_git.created_branches]
    # Branch names include issue number prefix
    assert any("123-" in name for name in created_branch_names)
    assert any("456-" in name for name in created_branch_names)

    # Verify both workflows were triggered
    assert len(fake_github.triggered_workflows) == 2


def test_submit_multiple_issues_atomic_validation_failure(tmp_path: Path) -> None:
    """Test atomic validation: if second issue is invalid, nothing is submitted."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    now = datetime.now(UTC)
    # First issue is valid
    issue_123 = IssueInfo(
        number=123,
        title="Feature A",
        body=make_plan_body("Implementation for A..."),
        state="OPEN",
        url="https://github.com/test-owner/test-repo/issues/123",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )
    # Second issue is CLOSED (invalid)
    issue_456 = IssueInfo(
        number=456,
        title="Feature B",
        body=make_plan_body("Implementation for B..."),
        state="CLOSED",
        url="https://github.com/test-owner/test-repo/issues/456",
        labels=[ERK_PLAN_LABEL],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )

    fake_github_issues = FakeGitHubIssues(issues={123: issue_123, 456: issue_456})
    fake_git = FakeGit(
        current_branches={repo_root: "main"},
        trunk_branches={repo_root: "master"},
    )
    fake_github = FakeGitHub()

    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )
    ctx = context_for_test(
        cwd=repo_root,
        git=fake_git,
        github=fake_github,
        issues=fake_github_issues,
        repo=repo,
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "456"], obj=ctx)

    # Should fail on the second issue validation
    assert result.exit_code == 1
    assert "is CLOSED" in result.output or "Cannot submit closed issues" in result.output

    # Critical: First issue validated and created branch, but validation happens before submission
    # The branch was created during validation, but workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0
