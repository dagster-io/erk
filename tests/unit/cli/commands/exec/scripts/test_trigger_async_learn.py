"""Unit tests for trigger-async-learn exec script.

Tests triggering the async learn workflow for plan issues.
Uses fakes for fast, reliable testing without subprocess calls.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.trigger_async_learn import trigger_async_learn
from erk_shared.context.context import ErkContext
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.metadata.core import find_metadata_block
from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.plan_helpers import format_plan_header_body_for_test

# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_trigger_async_learn_succeeds_with_remote_session(tmp_path: Path) -> None:
    """Test successful workflow dispatch for plan with remote session data."""
    # Create plan issue with remote implementation session
    plan_body = format_plan_header_body_for_test(
        last_remote_impl_run_id="12345678",
        last_remote_impl_session_id="abc-def-ghi",
    )
    plan_body += "\n\n# Plan\n\nThis is the plan content."

    test_issue = create_test_issue(
        123,
        "Test Plan #123",
        plan_body,
        labels=["erk-plan"],
    )
    fake_issues = FakeGitHubIssues(issues={123: test_issue})
    fake_github = FakeGitHub()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            trigger_async_learn,
            ["123"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["workflow_triggered"] is True
    assert "run_id" in output

    # Verify workflow was triggered
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "learn-dispatch.yml"
    assert inputs["issue_number"] == "123"


def test_trigger_async_learn_succeeds_with_local_session(tmp_path: Path) -> None:
    """Test successful workflow dispatch for plan with local session data."""
    # Create plan issue with local implementation session
    plan_body = format_plan_header_body_for_test(
        last_local_impl_session="local-session-xyz",
    )
    plan_body += "\n\n# Plan\n\nThis is the plan content."

    test_issue = create_test_issue(
        456,
        "Test Plan #456",
        plan_body,
        labels=["erk-plan"],
    )
    fake_issues = FakeGitHubIssues(issues={456: test_issue})
    fake_github = FakeGitHub()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            trigger_async_learn,
            ["456"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 456
    assert output["workflow_triggered"] is True


def test_trigger_async_learn_updates_learn_status(tmp_path: Path) -> None:
    """Test that learn_status is updated to pending after dispatch."""
    plan_body = format_plan_header_body_for_test(
        last_remote_impl_run_id="12345678",
    )
    plan_body += "\n\n# Plan\n\nThis is the plan content."

    test_issue = create_test_issue(
        789,
        "Test Plan #789",
        plan_body,
        labels=["erk-plan"],
    )
    fake_issues = FakeGitHubIssues(issues={789: test_issue})
    fake_github = FakeGitHub()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            trigger_async_learn,
            ["789"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 0, result.output

    # Verify issue was updated with learn_status=pending
    assert len(fake_issues.updated_bodies) == 1
    issue_number, updated_body = fake_issues.updated_bodies[0]
    assert issue_number == 789

    # Verify learn_status is set in the updated body
    block = find_metadata_block(updated_body, "plan-header")
    assert block is not None
    assert block.data.get("learn_status") == "pending"


# ============================================================================
# Error Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_trigger_async_learn_fails_not_erk_plan(tmp_path: Path) -> None:
    """Test error when issue is not an erk-plan."""
    test_issue = create_test_issue(
        123,
        "Not a Plan",
        "Just a regular issue",
        labels=["bug"],  # Not erk-plan
    )
    fake_issues = FakeGitHubIssues(issues={123: test_issue})
    fake_github = FakeGitHub()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            trigger_async_learn,
            ["123"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "is not an erk-plan" in output["error"]

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_trigger_async_learn_fails_no_session_data(tmp_path: Path) -> None:
    """Test error when plan has no session data available."""
    # Create plan issue without any session data
    plan_body = format_plan_header_body_for_test()  # No session data
    plan_body += "\n\n# Plan\n\nThis is the plan content."

    test_issue = create_test_issue(
        123,
        "Test Plan #123",
        plan_body,
        labels=["erk-plan"],
    )
    fake_issues = FakeGitHubIssues(issues={123: test_issue})
    fake_github = FakeGitHub()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            trigger_async_learn,
            ["123"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No session data available" in output["error"]

    # Verify workflow was NOT triggered
    assert len(fake_github.triggered_workflows) == 0


def test_trigger_async_learn_fails_issue_not_found(tmp_path: Path) -> None:
    """Test error when issue does not exist."""
    fake_issues = FakeGitHubIssues(issues={})  # No issues
    fake_github = FakeGitHub()

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            trigger_async_learn,
            ["999"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_issues,
                cwd=cwd,
                repo_root=cwd,
            ),
        )

    # FakeGitHubIssues raises RuntimeError for missing issues
    assert result.exit_code != 0
