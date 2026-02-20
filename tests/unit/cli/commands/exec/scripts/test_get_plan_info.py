"""Unit tests for get_plan_info exec command.

Tests backend-aware plan info retrieval using FakeGitHubIssues and FakeGitHub.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_plan_info import get_plan_info
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend


def _make_issue_info(number: int, body: str) -> IssueInfo:
    """Create test IssueInfo with given number and body."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Plan Title",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


def _plan_header_body() -> str:
    """Create a minimal plan-header body for testing."""
    return """<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
objective_issue: 100

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


# ============================================================================
# Success Cases - GitHub Issues Backend
# ============================================================================


def test_get_plan_info_success() -> None:
    """Test successful plan info retrieval from GitHub issues backend."""
    fake_gh = FakeGitHubIssues(issues={42: _make_issue_info(42, _plan_header_body())})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        ["42"],
        obj=context_for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_id"] == "42"
    assert output["title"] == "Test Plan Title"
    assert output["state"] == "OPEN"
    assert "erk-plan" in output["labels"]
    assert isinstance(output["url"], str)
    assert output["backend"] == "github"


def test_get_plan_info_includes_objective_id() -> None:
    """Test that objective_id is included in the response."""
    fake_gh = FakeGitHubIssues(issues={42: _make_issue_info(42, _plan_header_body())})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        ["42"],
        obj=context_for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert "objective_id" in output


# ============================================================================
# Draft PR Backend
# ============================================================================


def test_get_plan_info_draft_pr_backend() -> None:
    """Test plan info retrieval from draft PR backend."""
    fake_github = FakeGitHub()
    backend = DraftPRPlanBackend(fake_github, fake_github.issues, time=FakeTime())

    create_result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Draft PR Plan",
        content="# Plan Content",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch-info"},
    )

    runner = CliRunner()
    result = runner.invoke(
        get_plan_info,
        [create_result.plan_id],
        obj=context_for_test(
            github=fake_github,
            github_issues=fake_github.issues,
            plan_store=backend,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_id"] == create_result.plan_id
    assert "Draft PR Plan" in output["title"]
    assert output["backend"] == "github-draft-pr"


# ============================================================================
# --include-body flag
# ============================================================================


def test_get_plan_info_include_body() -> None:
    """Test that --include-body adds body field to the response."""
    fake_gh = FakeGitHubIssues(issues={42: _make_issue_info(42, _plan_header_body())})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        ["42", "--include-body"],
        obj=context_for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "body" in output
    assert isinstance(output["body"], str)


def test_get_plan_info_excludes_body_by_default() -> None:
    """Test that body field is NOT present without --include-body."""
    fake_gh = FakeGitHubIssues(issues={42: _make_issue_info(42, _plan_header_body())})
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        ["42"],
        obj=context_for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "body" not in output


# ============================================================================
# Error Cases
# ============================================================================


def test_get_plan_info_not_found() -> None:
    """Test error when plan doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        get_plan_info,
        ["9999"],
        obj=context_for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "plan_not_found"
    assert "#9999" in output["message"]
