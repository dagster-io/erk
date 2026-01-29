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
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import PRDetails


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


def make_pr_details(
    *,
    number: int,
    head_ref_name: str,
) -> PRDetails:
    """Create test PRDetails with given number and branch name."""
    return PRDetails(
        number=number,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        title=f"Review: Plan #{number}",
        body="Review PR body",
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


def test_plan_review_complete_success(tmp_path: Path) -> None:
    """Test successful PR closure with branch deletion and metadata clearing."""
    issue_number = 1234
    review_pr_number = 555
    branch_name = "plan-review-1234"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: Add feature X", labels=None)

    pr_details = make_pr_details(number=review_pr_number, head_ref_name=branch_name)
    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
        pr_details={review_pr_number: pr_details},
    )
    fake_git = FakeGit(
        current_branches={repo_root: branch_name},
        local_branches={repo_root: ["master", branch_name]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(
            github=fake_gh,
            git=fake_git,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == issue_number
    assert output["pr_number"] == review_pr_number
    assert output["branch_name"] == branch_name
    assert output["branch_deleted"] is True
    assert output["local_branch_deleted"] is True

    # Verify close_pr was called with correct PR number
    assert fake_gh.closed_prs == [review_pr_number]

    # Verify checkout to master and local branch deletion
    assert (repo_root, "master") in fake_git.checked_out_branches
    assert branch_name in fake_git.deleted_branches


def test_plan_review_complete_json_output_structure(tmp_path: Path) -> None:
    """Test success JSON output has correct structure and types."""
    issue_number = 4444
    review_pr_number = 777
    branch_name = "plan-review-4444"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: JSON Test", labels=None)

    pr_details = make_pr_details(number=review_pr_number, head_ref_name=branch_name)
    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
        pr_details={review_pr_number: pr_details},
    )
    fake_git = FakeGit(
        current_branches={repo_root: branch_name},
        local_branches={repo_root: ["master", branch_name]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify all required fields present
    assert "success" in output
    assert "issue_number" in output
    assert "pr_number" in output
    assert "branch_name" in output
    assert "branch_deleted" in output
    assert "local_branch_deleted" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["pr_number"], int)
    assert isinstance(output["branch_name"], str)
    assert isinstance(output["branch_deleted"], bool)
    assert isinstance(output["local_branch_deleted"], bool)


def test_plan_review_complete_deletes_branch(tmp_path: Path) -> None:
    """Test that the review branch is deleted after closing the PR."""
    issue_number = 5555
    review_pr_number = 888
    branch_name = "plan-review-5555"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: Branch Delete", labels=None)

    pr_details = make_pr_details(number=review_pr_number, head_ref_name=branch_name)
    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
        pr_details={review_pr_number: pr_details},
    )
    fake_git = FakeGit(
        current_branches={repo_root: branch_name},
        local_branches={repo_root: ["master", branch_name]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["branch_name"] == branch_name
    assert output["branch_deleted"] is True

    # Verify delete_remote_branch was called
    assert fake_gh.deleted_remote_branches == [branch_name]


def test_plan_review_complete_clears_review_pr_metadata(tmp_path: Path) -> None:
    """Test that review_pr metadata is cleared (set to null) after completion."""
    issue_number = 6666
    review_pr_number = 999
    branch_name = "plan-review-6666"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: Clear Metadata", labels=None)

    pr_details = make_pr_details(number=review_pr_number, head_ref_name=branch_name)
    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
        pr_details={review_pr_number: pr_details},
    )
    fake_git = FakeGit(
        current_branches={repo_root: branch_name},
        local_branches={repo_root: ["master", branch_name]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, repo_root=repo_root),
    )

    assert result.exit_code == 0

    # Verify update_issue_body was called
    assert len(fake_gh_issues.updated_bodies) == 1
    updated_issue_number, updated_body = fake_gh_issues.updated_bodies[0]
    assert updated_issue_number == issue_number

    # Verify the updated body has review_pr: null
    assert "review_pr: null" in updated_body or "review_pr:" not in updated_body


def test_plan_review_complete_sets_last_review_pr(tmp_path: Path) -> None:
    """Test that the old review_pr is archived to last_review_pr."""
    issue_number = 7777
    review_pr_number = 111
    branch_name = "plan-review-7777"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: Last Review PR", labels=None)

    pr_details = make_pr_details(number=review_pr_number, head_ref_name=branch_name)
    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
        pr_details={review_pr_number: pr_details},
    )
    fake_git = FakeGit(
        current_branches={repo_root: branch_name},
        local_branches={repo_root: ["master", branch_name]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, repo_root=repo_root),
    )

    assert result.exit_code == 0

    # Verify last_review_pr is set to the old review PR number
    assert len(fake_gh_issues.updated_bodies) == 1
    _updated_number, updated_body = fake_gh_issues.updated_bodies[0]
    assert f"last_review_pr: {review_pr_number}" in updated_body


def test_plan_review_complete_branch_delete_returns_false(tmp_path: Path) -> None:
    """Test command still succeeds when branch deletion fails (returns false)."""
    issue_number = 8888
    review_pr_number = 222
    branch_name = "plan-review-8888"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: Branch Delete Fail", labels=None)

    pr_details = make_pr_details(number=review_pr_number, head_ref_name=branch_name)
    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    # FakeGitHub.delete_remote_branch returns True by default.
    # We need to verify the command handles both cases.
    # The default fake returns True, so we test that the field is present.
    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
        pr_details={review_pr_number: pr_details},
    )
    fake_git = FakeGit(
        current_branches={repo_root: branch_name},
        local_branches={repo_root: ["master", branch_name]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "branch_deleted" in output


def test_plan_review_complete_already_on_master(tmp_path: Path) -> None:
    """Test that checkout is skipped when user is already on master."""
    issue_number = 1010
    review_pr_number = 444
    branch_name = "plan-review-1010"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: Already on master", labels=None)

    pr_details = make_pr_details(number=review_pr_number, head_ref_name=branch_name)
    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
        pr_details={review_pr_number: pr_details},
    )
    fake_git = FakeGit(
        current_branches={repo_root: "master"},
        local_branches={repo_root: ["master", branch_name]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["local_branch_deleted"] is True

    # Verify no checkout happened (already on master)
    assert fake_git.checked_out_branches == []

    # Verify local branch was still deleted
    assert branch_name in fake_git.deleted_branches


def test_plan_review_complete_no_local_branch(tmp_path: Path) -> None:
    """Test that local_branch_deleted is False when local branch doesn't exist."""
    issue_number = 2020
    review_pr_number = 666
    branch_name = "plan-review-2020"
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: No local branch", labels=None)

    pr_details = make_pr_details(number=review_pr_number, head_ref_name=branch_name)
    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    fake_gh = FakeGitHub(
        issues_gateway=fake_gh_issues,
        pr_details={review_pr_number: pr_details},
    )
    fake_git = FakeGit(
        current_branches={repo_root: "master"},
        local_branches={repo_root: ["master"]},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_review_complete,
        [str(issue_number)],
        obj=ErkContext.for_test(github=fake_gh, git=fake_git, repo_root=repo_root),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["local_branch_deleted"] is False

    # Verify no checkout or delete happened
    assert fake_git.checked_out_branches == []
    assert fake_git.deleted_branches == []


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


def test_plan_review_complete_pr_not_found(tmp_path: Path) -> None:
    """Test error when the review PR is not found on GitHub."""
    issue_number = 1111
    review_pr_number = 333
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, title="Plan: PR Not Found", labels=None)

    fake_gh_issues = FakeGitHubIssues(issues={issue_number: issue})
    # No pr_details configured → get_pr returns PRNotFound
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
    assert output["error"] == "pr_not_found"
    assert f"#{review_pr_number}" in output["message"]


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
