"""Unit tests for add_plan_label exec command.

Tests backend-aware label addition using FakeGitHubIssues and FakeGitHub.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.add_plan_label import add_plan_label
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend


def _make_issue_info(number: int) -> IssueInfo:
    """Create test IssueInfo with given number."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Plan",
        body="Plan body",
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# Success Cases
# ============================================================================


def test_add_plan_label_success() -> None:
    """Test successful label addition via GitHub issues backend."""
    fake_gh = FakeGitHubIssues(issues={42: _make_issue_info(42)})
    runner = CliRunner()

    result = runner.invoke(
        add_plan_label,
        ["42", "--label", "erk-consolidated"],
        obj=context_for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_number"] == 42
    assert output["label"] == "erk-consolidated"

    # Verify label was actually added to the fake
    issue = fake_gh.get_issue(Path("/fake/repo"), 42)
    assert "erk-consolidated" in issue.labels


def test_add_plan_label_draft_pr_backend() -> None:
    """Test label addition via draft PR backend."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github, fake_github.issues, time=FakeTime())

    create_result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Draft PR Plan",
        content="# Plan Content",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch-label"},
    )

    runner = CliRunner()
    result = runner.invoke(
        add_plan_label,
        [create_result.plan_id, "--label", "erk-consolidated"],
        obj=context_for_test(
            github=fake_github,
            github_issues=fake_github.issues,
            plan_store=backend,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["label"] == "erk-consolidated"

    # Verify label was added via the fake GitHub PR label tracking
    assert (int(create_result.plan_id), "erk-consolidated") in fake_github._added_labels


# ============================================================================
# Error Cases
# ============================================================================


def test_add_plan_label_requires_label_flag() -> None:
    """Test that missing --label flag exits with code 2 (usage error)."""
    fake_gh = FakeGitHubIssues(issues={42: _make_issue_info(42)})
    runner = CliRunner()

    result = runner.invoke(
        add_plan_label,
        ["42"],
        obj=context_for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 2
