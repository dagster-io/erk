"""Unit tests for create-worker-impl-from-issue command.

Tests use FakeGitHubIssues via ErkContext.for_test() for dependency injection.
The command now uses PlanBackend (which wraps GitHubIssues internally).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.create_worker_impl_from_issue import (
    create_worker_impl_from_issue,
)
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend


def _make_issue(
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create a test IssueInfo with erk-plan label."""
    # Use fixed timestamp for deterministic tests
    now = datetime(2025, 11, 25, 14, 37, 43, tzinfo=UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_create_worker_impl_success(tmp_path: Path) -> None:
    """Test successfully creating .worker-impl/ from a plan."""
    issue = _make_issue(42, "Test Plan", "# Plan\n\n- Step 1\n- Step 2")
    fake_gh = FakeGitHubIssues(issues={42: issue})
    runner = CliRunner()

    result = runner.invoke(
        create_worker_impl_from_issue,
        ["42"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_id"] == 42

    # Verify .worker-impl/ was created
    worker_impl = tmp_path / ".worker-impl"
    assert worker_impl.exists()
    assert (worker_impl / "plan.md").exists()
    plan_content = (worker_impl / "plan.md").read_text()
    assert "Step 1" in plan_content


def test_create_worker_impl_not_found() -> None:
    """Test error when plan does not exist."""
    fake_gh = FakeGitHubIssues()  # Empty
    runner = CliRunner()

    result = runner.invoke(
        create_worker_impl_from_issue,
        ["999"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    # Error output goes to stderr
    error_output = json.loads(result.output)
    assert error_output["success"] is False
    assert error_output["error"] == "plan_not_found"


def test_create_worker_impl_draft_pr_provider(tmp_path: Path) -> None:
    """Test that DraftPRPlanBackend sets provider to 'github-draft-pr' in plan-ref.json."""
    plan_content = "# Plan\n\n- Step 1\n- Step 2"
    pr_body = f"\n\n---\n\n{plan_content}"

    pr_details = PRDetails(
        number=42,
        url="https://github.com/test/repo/pull/42",
        title="[erk-plan] Test Plan",
        body=pr_body,
        state="OPEN",
        is_draft=True,
        base_ref_name="master",
        head_ref_name="plan-test-plan-01-01-0000",
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        labels=("erk-plan",),
    )

    fake_gh = FakeGitHub(pr_details={42: pr_details})
    fake_issues = FakeGitHubIssues()
    draft_pr_backend = DraftPRPlanBackend(fake_gh, fake_issues, time=FakeTime())

    runner = CliRunner()
    ctx = context_for_test(
        github=fake_gh,
        github_issues=fake_issues,
        plan_store=draft_pr_backend,
        repo_root=tmp_path,
    )

    result = runner.invoke(
        create_worker_impl_from_issue,
        ["42"],
        obj=ctx,
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify plan-ref.json has draft-PR provider
    plan_ref_file = tmp_path / ".worker-impl" / "plan-ref.json"
    plan_ref_data = json.loads(plan_ref_file.read_text(encoding="utf-8"))
    assert plan_ref_data["provider"] == "github-draft-pr"
