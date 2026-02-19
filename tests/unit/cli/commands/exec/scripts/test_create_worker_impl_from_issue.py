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
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


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
    assert output["issue_number"] == 42

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
