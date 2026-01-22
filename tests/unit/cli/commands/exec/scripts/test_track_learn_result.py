"""Unit tests for track-learn-result exec script.

Tests learn result tracking on plan issues.
Uses fakes for fast, reliable testing without subprocess calls.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.track_learn_result import track_learn_result
from erk_shared.context.context import ErkContext
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.metadata.core import find_metadata_block
from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.plan_helpers import format_plan_header_body_for_test

# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_track_learn_result_completed_no_plan(tmp_path: Path) -> None:
    """Test tracking completed_no_plan status."""
    plan_body = format_plan_header_body_for_test(learn_status="pending")
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_result,
            ["--issue", "42", "--status", "completed_no_plan"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["learn_status"] == "completed_no_plan"
    assert output["learn_plan_issue"] is None

    # Verify plan-header was updated
    updated_issue = fake_issues.get_issue(cwd, 42)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data.get("learn_status") == "completed_no_plan"
    assert "learn_plan_issue" not in block.data or block.data.get("learn_plan_issue") is None


def test_track_learn_result_completed_with_plan(tmp_path: Path) -> None:
    """Test tracking completed_with_plan status with plan issue."""
    plan_body = format_plan_header_body_for_test(learn_status="pending")
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_result,
            ["--issue", "42", "--status", "completed_with_plan", "--plan-issue", "456"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["learn_status"] == "completed_with_plan"
    assert output["learn_plan_issue"] == 456

    # Verify plan-header was updated with both status and plan issue
    updated_issue = fake_issues.get_issue(cwd, 42)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data.get("learn_status") == "completed_with_plan"
    assert block.data.get("learn_plan_issue") == 456


# ============================================================================
# Validation Error Cases
# ============================================================================


def test_track_learn_result_requires_plan_issue_for_completed_with_plan(tmp_path: Path) -> None:
    """Test error when completed_with_plan is missing --plan-issue."""
    plan_body = format_plan_header_body_for_test(learn_status="pending")
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_result,
            ["--issue", "42", "--status", "completed_with_plan"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "plan-issue is required" in output["error"]


def test_track_learn_result_rejects_plan_issue_for_completed_no_plan(tmp_path: Path) -> None:
    """Test error when completed_no_plan has --plan-issue."""
    plan_body = format_plan_header_body_for_test(learn_status="pending")
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_result,
            ["--issue", "42", "--status", "completed_no_plan", "--plan-issue", "456"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "should not be provided" in output["error"]


# ============================================================================
# pending_review Status Tests
# ============================================================================


def test_track_learn_result_pending_review_with_plan_pr(tmp_path: Path) -> None:
    """Test tracking pending_review status with plan PR."""
    plan_body = format_plan_header_body_for_test(learn_status="pending")
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_result,
            ["--issue", "42", "--status", "pending_review", "--plan-pr", "789"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 42
    assert output["learn_status"] == "pending_review"
    assert output["learn_plan_issue"] is None
    assert output["learn_plan_pr"] == 789

    # Verify plan-header was updated with both status and plan PR
    updated_issue = fake_issues.get_issue(cwd, 42)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data.get("learn_status") == "pending_review"
    assert block.data.get("learn_plan_pr") == 789


def test_track_learn_result_pending_review_requires_plan_pr(tmp_path: Path) -> None:
    """Test error when pending_review is missing --plan-pr."""
    plan_body = format_plan_header_body_for_test(learn_status="pending")
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_result,
            ["--issue", "42", "--status", "pending_review"],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "plan-pr is required" in output["error"]


def test_track_learn_result_pending_review_rejects_plan_issue(tmp_path: Path) -> None:
    """Test error when pending_review has --plan-issue."""
    plan_body = format_plan_header_body_for_test(learn_status="pending")
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_result,
            [
                "--issue",
                "42",
                "--status",
                "pending_review",
                "--plan-pr",
                "789",
                "--plan-issue",
                "456",
            ],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "plan-issue should not be provided" in output["error"]


def test_track_learn_result_completed_with_plan_rejects_plan_pr(tmp_path: Path) -> None:
    """Test error when completed_with_plan has --plan-pr."""
    plan_body = format_plan_header_body_for_test(learn_status="pending")
    fake_issues = FakeGitHubIssues(issues={42: create_test_issue(42, "Test Plan #42", plan_body)})

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            track_learn_result,
            [
                "--issue",
                "42",
                "--status",
                "completed_with_plan",
                "--plan-issue",
                "456",
                "--plan-pr",
                "789",
            ],
            obj=ErkContext.for_test(
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "plan-pr should not be provided" in output["error"]
