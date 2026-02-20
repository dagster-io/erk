"""Unit tests for update-lifecycle-stage exec command."""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.update_lifecycle_stage import update_lifecycle_stage
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.metadata.core import find_metadata_block
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_issue_with_plan_header(number: int) -> IssueInfo:
    """Create a test issue with a plan-header metadata block."""
    body = format_plan_header_body_for_test(
        created_at="2025-01-01T00:00:00Z",
        created_by="testuser",
    )
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Plan",
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def test_updates_lifecycle_stage_successfully() -> None:
    """update-lifecycle-stage sets the lifecycle_stage field in plan-header."""
    issue = _make_issue_with_plan_header(42)
    fake_gh = FakeGitHubIssues(issues={42: issue})
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_lifecycle_stage,
        ["--plan-id", "42", "--stage", "implementing"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_id"] == "42"
    assert output["stage"] == "implementing"

    # Verify metadata was actually updated
    updated_issue = fake_gh.get_issue(repo_root, 42)
    block = find_metadata_block(updated_issue.body, "plan-header")
    assert block is not None
    assert block.data["lifecycle_stage"] == "implementing"


def test_rejects_invalid_stage() -> None:
    """update-lifecycle-stage rejects invalid stage values."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()
    result = runner.invoke(
        update_lifecycle_stage,
        ["--plan-id", "42", "--stage", "invalid-stage"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_fails_for_nonexistent_plan() -> None:
    """update-lifecycle-stage fails when plan doesn't exist."""
    fake_gh = FakeGitHubIssues()
    repo_root = Path("/fake/repo")

    runner = CliRunner()
    result = runner.invoke(
        update_lifecycle_stage,
        ["--plan-id", "999", "--stage", "planned"],
        obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1


def test_accepts_all_valid_stages() -> None:
    """update-lifecycle-stage accepts all valid lifecycle stage values."""
    valid_stages = ["pre-plan", "planning", "planned", "implementing", "review"]

    for stage in valid_stages:
        issue = _make_issue_with_plan_header(100)
        fake_gh = FakeGitHubIssues(issues={100: issue})
        repo_root = Path("/fake/repo")

        runner = CliRunner()
        result = runner.invoke(
            update_lifecycle_stage,
            ["--plan-id", "100", "--stage", stage],
            obj=ErkContext.for_test(github_issues=fake_gh, repo_root=repo_root),
        )

        assert result.exit_code == 0, f"Failed for stage {stage}: {result.output}"
        output = json.loads(result.output)
        assert output["stage"] == stage
