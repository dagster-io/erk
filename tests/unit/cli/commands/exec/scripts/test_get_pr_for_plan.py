"""Unit tests for get_pr_for_plan exec command.

Tests PR lookup by plan_id (PR number) for the draft-PR backend.
Uses FakeGitHub for fast, reliable testing.
"""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_for_plan import get_pr_for_plan
from erk_shared.context.context import ErkContext
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend


def make_pr_details(
    *,
    number: int,
    head_ref_name: str,
) -> PRDetails:
    """Create test PRDetails."""
    return PRDetails(
        number=number,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        title=f"PR #{number}",
        body="Test PR body",
        state="OPEN",
        is_draft=False,
        base_ref_name="master",
        head_ref_name=head_ref_name,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )




# ============================================================================
# Success Cases
# ============================================================================


def test_get_pr_for_plan_success() -> None:
    """Test successful PR lookup by plan_id (which IS the PR number in draft-PR backend)."""
    pr_number = 5104
    branch_name = "P5104-feature-branch"
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        pr_details={pr_number: make_pr_details(number=pr_number, head_ref_name=branch_name)},
    )
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        [str(pr_number)],
        obj=ErkContext.for_test(github=fake_gh, github_issues=fake_issues),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr"]["number"] == pr_number
    assert output["pr"]["title"] == f"PR #{pr_number}"
    assert output["pr"]["state"] == "OPEN"
    assert output["pr"]["head_ref_name"] == branch_name
    assert output["pr"]["base_ref_name"] == "master"


# ============================================================================
# Error Cases
# ============================================================================


def test_get_pr_for_plan_pr_not_found() -> None:
    """Test error when PR doesn't exist."""
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_issues)
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        ["9999"],
        obj=ErkContext.for_test(github=fake_gh, github_issues=fake_issues),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no-pr-for-branch"
    assert "#9999" in output["message"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success() -> None:
    """Test JSON output structure on success."""
    pr_number = 5104
    branch_name = "P5104-feature-branch"
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        pr_details={pr_number: make_pr_details(number=pr_number, head_ref_name=branch_name)},
    )
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        [str(pr_number)],
        obj=ErkContext.for_test(github=fake_gh, github_issues=fake_issues),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "pr" in output

    # Verify PR structure
    pr = output["pr"]
    assert "number" in pr
    assert "title" in pr
    assert "state" in pr
    assert "url" in pr
    assert "head_ref_name" in pr
    assert "base_ref_name" in pr

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(pr["number"], int)
    assert isinstance(pr["title"], str)
    assert isinstance(pr["state"], str)
    assert isinstance(pr["url"], str)


def test_json_output_structure_error() -> None:
    """Test JSON output structure on error."""
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_issues)
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        ["999"],
        obj=ErkContext.for_test(github=fake_gh, github_issues=fake_issues),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)

    # Verify values
    assert output["success"] is False


# ============================================================================
# Draft-PR Backend Tests
# ============================================================================


def test_get_pr_for_plan_planned_pr_backend() -> None:
    """Test that planned-PR backend looks up PR directly by plan_id (which IS the PR number)."""
    pr_number = 7670
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        pr_details={pr_number: make_pr_details(number=pr_number, head_ref_name="plan-fix-learn")},
    )
    planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=FakeTime())
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        [str(pr_number)],
        obj=context_for_test(
            github=fake_gh, github_issues=fake_issues, plan_store=planned_pr_backend
        ),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr"]["number"] == pr_number
    assert output["pr"]["head_ref_name"] == "plan-fix-learn"
    assert output["pr"]["base_ref_name"] == "master"


def test_get_pr_for_plan_planned_pr_backend_not_found() -> None:
    """Test that planned-PR backend returns error when PR doesn't exist."""
    fake_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_issues)
    planned_pr_backend = PlannedPRBackend(fake_gh, fake_issues, time=FakeTime())
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        ["9999"],
        obj=context_for_test(
            github=fake_gh, github_issues=fake_issues, plan_store=planned_pr_backend
        ),
    )

    assert result.exit_code == 1
    # Error goes to stderr for _exit_with_error
    error_output = result.stderr if result.stderr else result.output
    output = json.loads(error_output)
    assert output["success"] is False
    assert output["error"] == "no-pr-for-branch"
    assert "#9999" in output["message"]
