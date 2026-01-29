"""Unit tests for plan_create_review_pr exec command.

Tests creation of draft PRs for plan review from GitHub issues.
Uses FakeGitHub and FakeGitHubIssues for fast, reliable testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_create_review_pr import plan_create_review_pr
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


def make_plan_header_body(
    *,
    plan_comment_id: int | None,
) -> str:
    """Create a test issue body with plan-header metadata block."""
    comment_id_line = (
        f"plan_comment_id: {plan_comment_id}"
        if plan_comment_id is not None
        else "plan_comment_id: null"
    )

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
{comment_id_line}
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


def test_plan_create_review_pr_success(tmp_path: Path) -> None:
    """Test successful PR creation and metadata update."""
    issue_number = 1234
    branch_name = "plan-review-1234-01-15-1430"
    plan_title = "Add feature X"
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    # Create issue with plan-header
    body = make_plan_header_body(plan_comment_id=123456789)
    issue = make_issue_info(issue_number, body, title=f"Plan: {plan_title}", labels=None)

    fake_gh_issues = FakeGitHubIssues(
        issues={issue_number: issue},
    )

    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_pr,
        [str(issue_number), branch_name, plan_title],
        obj=ErkContext.for_test(
            github=fake_gh,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == issue_number
    assert output["pr_number"] == 999
    assert output["pr_url"] == "https://github.com/schrockn/erk/pull/999"

    # Verify PR was created as draft
    assert len(fake_gh.created_prs) == 1
    pr = fake_gh.created_prs[0]
    assert pr[0] == branch_name  # branch
    assert pr[1] == f"Plan Review: {plan_title} (#{issue_number})"  # title
    assert f"issue #{issue_number}" in pr[2]  # body contains issue reference
    assert pr[3] == "master"  # base
    assert pr[4] is True  # draft=True

    # Verify issue body was updated with review_pr field
    updated_issue = fake_gh_issues.get_issue(repo_root, issue_number)
    assert "review_pr: 999" in updated_issue.body


def test_plan_create_review_pr_title_format(tmp_path: Path) -> None:
    """Test PR title contains issue reference."""
    issue_number = 5678
    branch_name = "plan-review-5678-01-15-1430"
    plan_title = "Implement new backend"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(plan_comment_id=123)
    issue = make_issue_info(issue_number, body, title=f"Plan: {plan_title}", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_pr,
        [str(issue_number), branch_name, plan_title],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0

    # Verify PR title format
    pr = fake_gh.created_prs[0]
    assert pr[1] == f"Plan Review: {plan_title} (#{issue_number})"


def test_plan_create_review_pr_body_format(tmp_path: Path) -> None:
    """Test PR body has issue link and warning."""
    issue_number = 9999
    branch_name = "plan-review-9999-01-15-1430"
    plan_title = "Test Plan"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(plan_comment_id=456)
    issue = make_issue_info(issue_number, body, title=f"Plan: {plan_title}", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_pr,
        [str(issue_number), branch_name, plan_title],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0

    # Verify PR body format
    pr_body = fake_gh.created_prs[0][2]
    assert f"Plan Review: {plan_title}" in pr_body
    assert f"issue #{issue_number}" in pr_body
    assert "will not be merged" in pr_body
    assert "inline review comments" in pr_body


def test_plan_create_review_pr_draft_mode(tmp_path: Path) -> None:
    """Test PR is created in draft mode."""
    issue_number = 2222
    branch_name = "plan-review-2222-01-15-1430"
    plan_title = "Draft PR Test"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(plan_comment_id=789)
    issue = make_issue_info(issue_number, body, title=f"Plan: {plan_title}", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_pr,
        [str(issue_number), branch_name, plan_title],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0

    # Verify draft=True was passed
    pr = fake_gh.created_prs[0]
    assert pr[4] is True


def test_plan_create_review_pr_metadata_updated(tmp_path: Path) -> None:
    """Test issue metadata contains review_pr field after creation."""
    issue_number = 3333
    branch_name = "plan-review-3333-01-15-1430"
    plan_title = "Metadata Update Test"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(plan_comment_id=111)
    issue = make_issue_info(issue_number, body, title=f"Plan: {plan_title}", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_pr,
        [str(issue_number), branch_name, plan_title],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0

    # Verify metadata was updated
    updated_issue = fake_gh_issues.get_issue(repo_root, issue_number)
    assert "review_pr:" in updated_issue.body
    assert "review_pr: 999" in updated_issue.body


# ============================================================================
# Error Cases
# ============================================================================


def test_plan_create_review_pr_issue_not_found(tmp_path: Path) -> None:
    """Test error when issue doesn't exist."""
    repo_root = tmp_path / "repo"
    fake_gh_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_pr,
        ["9999", "test-branch", "Test Plan"],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "#9999" in output["message"]


# ============================================================================
# JSON Output Schema
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test success JSON output has correct structure."""
    issue_number = 4444
    branch_name = "plan-review-4444-01-15-1430"
    plan_title = "JSON Test"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(plan_comment_id=222)
    issue = make_issue_info(issue_number, body, title=f"Plan: {plan_title}", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_pr,
        [str(issue_number), branch_name, plan_title],
        obj=ErkContext.for_test(github=fake_gh, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify all required fields present
    assert "success" in output
    assert "issue_number" in output
    assert "pr_number" in output
    assert "pr_url" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["pr_number"], int)
    assert isinstance(output["pr_url"], str)


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test error JSON output has correct structure."""
    repo_root = tmp_path / "repo"
    fake_gh_issues = FakeGitHubIssues()
    fake_gh = FakeGitHub(issues_gateway=fake_gh_issues)

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_pr,
        ["8888", "test-branch", "Error Test"],
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
