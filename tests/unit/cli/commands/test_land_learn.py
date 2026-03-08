"""Tests for idempotent learn plan creation guards in land_learn.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from erk.cli.commands.land_learn import (
    _create_learn_pr_for_merged_branch,
)
from erk.core.context import context_for_test
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import DETAILS_CLOSE, DETAILS_OPEN
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_plan_pr(
    number: int,
    title: str,
    body: str,
) -> PRDetails:
    # Wrap body in plan lifecycle format (details tags + metadata block)
    pr_body = DETAILS_OPEN + "Plan content" + DETAILS_CLOSE + "\n\n" + body

    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=title,
        body=pr_body,
        state="OPEN",
        is_draft=True,
        base_ref_name="main",
        head_ref_name=f"plnd/test-{number}",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="owner",
        repo="repo",
        labels=("erk-pr", "erk-plan"),
    )


class TestLearnPrIdempotencyGuard:
    def test_skips_when_learn_plan_issue_already_set(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When learn_plan_issue is set, returns early with no new PR."""
        plan_body = format_plan_header_body_for_test(
            learn_plan_issue=789,
            learn_status="completed_with_plan",
        )

        fake_issues = FakeGitHubIssues()
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={
                100: _make_plan_pr(100, "Test Plan", plan_body),
            },
        )
        fake_github.set_pr_labels(100, {"erk-pr", "erk-plan"})

        backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
        ctx = context_for_test(
            github=fake_github,
            issues=fake_issues,
            plan_store=backend,
            cwd=tmp_path,
        )

        _create_learn_pr_for_merged_branch(
            ctx,
            plan_id="100",
            merged_pr_number=200,
            main_repo_root=tmp_path,
            cwd=tmp_path,
        )

        # No new PRs created
        assert len(fake_github.created_prs) == 0

        # Info message logged to stderr
        captured = capsys.readouterr()
        assert "Learn plan already exists (#789)" in captured.err
        assert "skipping" in captured.err

    def test_erk_learn_label_skips_before_idempotency_guard(self, tmp_path: Path) -> None:
        """Plans with erk-learn label skip (cycle prevention)."""
        plan_body = format_plan_header_body_for_test()

        fake_issues = FakeGitHubIssues()
        fake_github = FakeLocalGitHub(
            issues_gateway=fake_issues,
            pr_details={
                100: _make_plan_pr(100, "Learn: Something", plan_body),
            },
        )
        fake_github.set_pr_labels(100, {"erk-pr", "erk-plan", "erk-learn"})

        backend = PlannedPRBackend(fake_github, fake_issues, time=FakeTime())
        ctx = context_for_test(
            github=fake_github,
            issues=fake_issues,
            plan_store=backend,
            cwd=tmp_path,
        )

        _create_learn_pr_for_merged_branch(
            ctx,
            plan_id="100",
            merged_pr_number=200,
            main_repo_root=tmp_path,
            cwd=tmp_path,
        )

        # No new PRs created (cycle prevention)
        assert len(fake_github.created_prs) == 0
