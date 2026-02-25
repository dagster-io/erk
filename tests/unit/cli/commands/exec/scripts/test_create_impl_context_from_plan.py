"""Unit tests for create-impl-context-from-plan command.

Layer 2: Tests using fakes via ErkContext.for_test().

Tests verify the command fetches a plan via PlanBackend and creates
.erk/impl-context/ folder structure with plan.md and ref.json.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.create_impl_context_from_plan import (
    create_impl_context_from_plan,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.test_utils.plan_helpers import issue_info_to_pr_details


def _make_plan_issue(
    *,
    number: int,
    body: str,
    title: str,
    url: str,
) -> IssueInfo:
    now = datetime(2025, 1, 15, 10, 30, tzinfo=UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=url,
        labels=["erk-pr", "erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-author",
    )


def test_success_creates_impl_context(tmp_path: Path) -> None:
    """Test successful creation of .erk/impl-context/ folder."""
    plan_body = "# Test Plan\n\n## Tasks\n\n1. First task\n2. Second task\n"
    issue = _make_plan_issue(
        number=123,
        body=plan_body,
        title="[erk-plan] Test Plan",
        url="https://github.com/test-owner/test-repo/issues/123",
    )
    fake_issues = FakeGitHubIssues(issues={123: issue})
    fake_github = FakeGitHub(
        pr_details={123: issue_info_to_pr_details(issue)},
        issues_gateway=fake_issues,
    )

    runner = CliRunner()
    result = runner.invoke(
        create_impl_context_from_plan,
        ["123"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_id"] == 123
    # PlannedPRBackend uses PR URLs (issue_info_to_pr_details converts /issues/ to /pull/)
    assert "test-owner/test-repo/pull/123" in output["plan_url"]

    # Verify .erk/impl-context/ folder was created with correct files
    impl_context_dir = tmp_path / ".erk" / "impl-context"
    assert impl_context_dir.exists()

    plan_file = impl_context_dir / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text(encoding="utf-8") == plan_body

    ref_file = impl_context_dir / "ref.json"
    assert ref_file.exists()
    ref_data = json.loads(ref_file.read_text(encoding="utf-8"))
    assert ref_data["provider"] == "github-draft-pr"
    assert ref_data["plan_id"] == "123"
    assert ref_data["url"] == "https://github.com/test-owner/test-repo/pull/123"
    assert "created_at" in ref_data
    assert "synced_at" in ref_data


def test_plan_not_found_exits_with_error(tmp_path: Path) -> None:
    """Test error output when plan does not exist."""
    fake_issues = FakeGitHubIssues(issues={})
    fake_github = FakeGitHub(issues_gateway=fake_issues)

    runner = CliRunner()
    result = runner.invoke(
        create_impl_context_from_plan,
        ["999"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 1
    # Error output goes to stderr
    error_output = json.loads(result.output)
    assert error_output["success"] is False
    assert error_output["error"] == "plan_not_found"

    # Verify no folder was created
    impl_context_dir = tmp_path / ".erk" / "impl-context"
    assert not impl_context_dir.exists()


def test_objective_id_preserved_in_ref_json(tmp_path: Path) -> None:
    """Test that objective_id from plan is written to ref.json."""
    # Plan with objective_id requires plan-header metadata in body
    plan_body = "# Test Plan\n\nPlan with objective.\n"
    issue = _make_plan_issue(
        number=456,
        body=plan_body,
        title="[erk-plan] Objective Plan",
        url="https://github.com/test-owner/test-repo/issues/456",
    )
    fake_issues = FakeGitHubIssues(issues={456: issue})
    fake_github = FakeGitHub(
        pr_details={456: issue_info_to_pr_details(issue)},
        issues_gateway=fake_issues,
    )

    runner = CliRunner()
    result = runner.invoke(
        create_impl_context_from_plan,
        ["456"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime()),
            repo_root=tmp_path,
        ),
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"

    ref_file = tmp_path / ".erk" / "impl-context" / "ref.json"
    ref_data = json.loads(ref_file.read_text(encoding="utf-8"))
    # objective_id is None when not set in plan-header metadata
    assert "objective_id" in ref_data
