"""Tests for label scoping in reconcile_pipeline.py."""

from __future__ import annotations

from pathlib import Path

from erk.cli.commands.reconcile_pipeline import (
    ReconcileBranchInfo,
    process_merged_branch,
)
from erk.core.context import context_for_test
from erk_shared.context.types import RepoContext
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails


def _make_repo(tmp_path: Path) -> RepoContext:
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    worktrees_dir = repo_dir / "worktrees"
    worktrees_dir.mkdir(exist_ok=True)
    pool_json = repo_dir / "pool.json"
    return RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=worktrees_dir,
        pool_json_path=pool_json,
        main_repo_root=tmp_path,
    )


def _make_pr(number: int, *, head_ref_name: str = "feature-branch") -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Some PR",
        body="body",
        state="MERGED",
        is_draft=False,
        base_ref_name="master",
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


class TestReconcileLabelScoping:
    def test_erk_pr_gets_reconciled_label(self, tmp_path: Path) -> None:
        """PR with erk-pr label gets erk-reconciled stamped."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={42: _make_pr(42)},
        )
        fake_github.set_pr_labels(42, {"erk-pr"})

        ctx = context_for_test(
            github=fake_github,
            issues=fake_issues,
            cwd=tmp_path,
        )

        info = ReconcileBranchInfo(
            branch="feature-branch",
            pr_number=42,
            pr_title="Some PR",
            worktree_path=None,
            plan_id=None,
            objective_number=None,
        )

        result = process_merged_branch(
            ctx,
            info,
            main_repo_root=tmp_path,
            repo=_make_repo(tmp_path),
            cwd=tmp_path,
            dry_run=False,
            skip_learn=True,
        )

        # erk-reconciled was added
        assert any(label == "erk-reconciled" for _, label in fake_github._added_labels)
        assert result.error is None

    def test_non_erk_pr_does_not_get_reconciled_label(self, tmp_path: Path) -> None:
        """PR without erk-pr label does NOT get erk-reconciled stamped."""
        fake_issues = FakeGitHubIssues()
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={42: _make_pr(42)},
        )
        # No erk-pr label set

        ctx = context_for_test(
            github=fake_github,
            issues=fake_issues,
            cwd=tmp_path,
        )

        info = ReconcileBranchInfo(
            branch="feature-branch",
            pr_number=42,
            pr_title="Some PR",
            worktree_path=None,
            plan_id=None,
            objective_number=None,
        )

        result = process_merged_branch(
            ctx,
            info,
            main_repo_root=tmp_path,
            repo=_make_repo(tmp_path),
            cwd=tmp_path,
            dry_run=False,
            skip_learn=True,
        )

        # No labels were added
        assert len(fake_github._added_labels) == 0
        assert result.error is None
