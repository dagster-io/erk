"""Unit tests for get_pr_for_plan exec command.

Tests GitHub issue plan-header metadata extraction and PR lookup by branch.
Uses FakeGitHub and FakeGitHubIssues for fast, reliable testing.
"""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_for_plan import get_pr_for_plan
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo


def make_plan_header_body(
    *,
    branch_name: str | None = "P5103-feature-branch",
) -> str:
    """Create a test issue body with plan-header metadata block."""
    branch_line = f"branch_name: {branch_name}" if branch_name is not None else "branch_name: null"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
worktree_name: test-worktree
{branch_line}
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->"""


def make_issue_info(number: int, body: str) -> IssueInfo:
    """Create test IssueInfo with given number and body."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title="Test Issue",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


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


def make_pr_info(
    *,
    number: int,
    head_branch: str,
) -> PullRequestInfo:
    """Create test PullRequestInfo."""
    return PullRequestInfo(
        number=number,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        is_draft=False,
        title=f"PR #{number}",
        checks_passing=True,
        owner="test-owner",
        repo="test-repo",
        head_branch=head_branch,
    )


# ============================================================================
# Success Cases
# ============================================================================


def test_get_pr_for_plan_success() -> None:
    """Test successful PR lookup for plan branch."""
    branch_name = "P5103-feature-branch"
    body = make_plan_header_body(branch_name=branch_name)
    fake_issues = FakeGitHubIssues(issues={5103: make_issue_info(5103, body)})
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        prs={branch_name: make_pr_info(number=5104, head_branch=branch_name)},
        pr_details={5104: make_pr_details(number=5104, head_ref_name=branch_name)},
    )
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        ["5103"],
        obj=ErkContext.for_test(github=fake_gh, github_issues=fake_issues),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr"]["number"] == 5104
    assert output["pr"]["title"] == "PR #5104"
    assert output["pr"]["state"] == "OPEN"
    assert output["pr"]["head_ref_name"] == branch_name
    assert output["pr"]["base_ref_name"] == "master"


# ============================================================================
# Error Cases
# ============================================================================


def test_get_pr_for_plan_no_branch_in_metadata() -> None:
    """Test error when plan-header has no branch_name field."""
    # Create body with branch_name set to null
    body = make_plan_header_body(branch_name=None)
    fake_issues = FakeGitHubIssues(issues={5103: make_issue_info(5103, body)})
    fake_gh = FakeGitHub(issues_gateway=fake_issues)
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        ["5103"],
        obj=ErkContext.for_test(github=fake_gh, github_issues=fake_issues),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no-branch-in-plan"
    assert "branch_name" in output["message"]


def test_get_pr_for_plan_no_pr_for_branch() -> None:
    """Test error when branch exists but no PR for it."""
    branch_name = "P5103-feature-branch"
    body = make_plan_header_body(branch_name=branch_name)
    fake_issues = FakeGitHubIssues(issues={5103: make_issue_info(5103, body)})
    # No PRs configured
    fake_gh = FakeGitHub(issues_gateway=fake_issues, prs={}, pr_details={})
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        ["5103"],
        obj=ErkContext.for_test(github=fake_gh, github_issues=fake_issues),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no-pr-for-branch"
    assert branch_name in output["message"]


def test_get_pr_for_plan_issue_not_found() -> None:
    """Test error when plan issue doesn't exist."""
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
    assert output["error"] == "plan-not-found"
    assert "#9999" in output["message"]


def test_get_pr_for_plan_no_plan_header_block() -> None:
    """Test error when issue has no plan-header block."""
    body = """# Old Format Issue

This is an issue without plan-header metadata.
"""
    fake_issues = FakeGitHubIssues(issues={100: make_issue_info(100, body)})
    fake_gh = FakeGitHub(issues_gateway=fake_issues)
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        ["100"],
        obj=ErkContext.for_test(github=fake_gh, github_issues=fake_issues),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no-branch-in-plan"
    assert "plan-header" in output["message"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success() -> None:
    """Test JSON output structure on success."""
    branch_name = "P5103-feature-branch"
    body = make_plan_header_body(branch_name=branch_name)
    fake_issues = FakeGitHubIssues(issues={5103: make_issue_info(5103, body)})
    fake_gh = FakeGitHub(
        issues_gateway=fake_issues,
        prs={branch_name: make_pr_info(number=5104, head_branch=branch_name)},
        pr_details={5104: make_pr_details(number=5104, head_ref_name=branch_name)},
    )
    runner = CliRunner()

    result = runner.invoke(
        get_pr_for_plan,
        ["5103"],
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
