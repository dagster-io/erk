"""Unit tests for plan_review_complete exec command.

Tests closing of plan review PRs without merging.
Uses FakeGitHub and FakeGitHubIssues for fast, reliable testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_review_complete import plan_review_complete
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


def make_plan_header_body(
    *,
    review_pr: int | None,
) -> str:
    """Create a test issue body with plan-header metadata block including review_pr."""
    review_pr_line = f"review_pr: {review_pr}" if review_pr is not None else "review_pr: null"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
plan_comment_id: null
{review_pr_line}
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


def make_issue_info(
    number: int,
    body: str,
    title: str,
    labels: list[str] | None,
) -> IssueInfo:
    """Create test IssueInfo with given number, body, and labels."""
    if labels is None:
        labels = ["erk-plan"]
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=labels,
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# Success Cases
# ============================================================================


def test_plan_review_complete_success(tmp_path: Path) -> None:
    """Test successful PR closure."""
    issue_number = 1234
    review_pr_number = 555
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: Add feature X", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(
            github=fake_gh,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == issue_number
    assert output["pr_number"] == review_pr_number

    # Verify close_pr was called with correct PR number
    assert fake_gh.closed_prs == [review_pr_number]


def test_plan_review_complete_json_output_structure(tmp_path: Path) -> None:
    """Test success JSON output has correct structure and types."""
    issue_number = 4444
    review_pr_number = 777
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: JSON Test", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify all required fields present
    assert "success" in output
    assert "issue_number" in output
    assert "pr_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["pr_number"], int)


# ============================================================================
# Error Cases
# ============================================================================


def test_plan_review_complete_issue_not_found(tmp_path: Path) -> None:
    """Test error when issue doesn't exist."""
    repo_root = tmp_path / "repo"
    fake_gh_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        ["9999"],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "#9999" in output["message"]


def test_plan_review_complete_no_plan_header(tmp_path: Path) -> None:
    """Test error when issue has no plan-header metadata."""
    issue_number = 2222
    repo_root = tmp_path / "repo"

    # Issue body without plan-header metadata block
    body = "# Plan: Some Plan\n\nJust a regular issue body."
    issue = make_issue_info(issue_number, body, title="Plan: No Header", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_plan_header"


def test_plan_review_complete_no_review_pr(tmp_path: Path) -> None:
    """Test error when review_pr is null (no active review)."""
    issue_number = 3333
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=None)
    issue = make_issue_info(issue_number, body, title="Plan: No Review PR", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_review_pr"


def test_plan_review_complete_error_json_structure(tmp_path: Path) -> None:
    """Test error JSON output has correct structure and types."""
    repo_root = tmp_path / "repo"
    fake_gh_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        ["8888"],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify all required fields present
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)

    # Verify values
    assert output["success"] is False
