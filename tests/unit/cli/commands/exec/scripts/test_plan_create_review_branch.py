"""Unit tests for plan_create_review_branch exec command.

Tests creation of plan review branches from GitHub issues.
Uses FakeGit and FakeGitHubIssues for fast, reliable testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_create_review_branch import (
    plan_create_review_branch,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo


def make_plan_header_body(
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


def make_plan_comment_body_v2(plan_content: str) -> str:
    """Create a comment body with plan-body metadata block (Schema v2)."""
    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details open>
<summary><strong>plan-body</strong></summary>

{plan_content}

</details>
<!-- /erk:metadata-block:plan-body -->"""


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


def make_issue_comment(
    comment_id: int,
    body: str,
) -> IssueComment:
    """Create test IssueComment with given ID and body."""
    return IssueComment(
        id=comment_id,
        body=body,
        url=f"https://github.com/test-owner/test-repo/issues/1234#issuecomment-{comment_id}",
        author="test-user",
    )


# ============================================================================
# Success Cases
# ============================================================================


def test_plan_create_review_branch_success(tmp_path: Path) -> None:
    """Test successful branch creation and file write."""
    plan_content = "## Implementation Plan\n\nThis is the plan content."
    comment_id = 123456789
    issue_number = 1234
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    # Create issue with plan-header
    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Plan: Add feature X", labels=None)

    # Create comment with plan-body block
    comment_body = make_plan_comment_body_v2(plan_content)
    comment = make_issue_comment(comment_id, comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )

    fake_git = FakeGit(
        local_branches={repo_root: []},
        remote_branches={repo_root: ["origin/master"]},
        current_branches={repo_root: "main"},
        repository_roots={repo_root: repo_root},
    )

    # FakeTime default: 2024-01-15 14:30:00 -> branch timestamp -01-15-1430
    expected_branch = f"plan-review-{issue_number}-01-15-1430"

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_branch,
        [str(issue_number)],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == issue_number
    assert output["branch"] == expected_branch
    assert output["file_path"] == f"PLAN-REVIEW-{issue_number}.md"
    assert output["plan_title"] == "Plan: Add feature X"

    # Verify branch was created from origin/master
    assert len(fake_git.created_branches) == 1
    created = fake_git.created_branches[0]
    assert created[0] == repo_root  # cwd
    assert created[1] == expected_branch  # branch_name
    assert created[2] == "origin/master"  # start_point
    assert created[3] is False  # force

    # Verify branch was checked out
    assert len(fake_git.branch.checked_out_branches) == 1
    assert fake_git.branch.checked_out_branches[0] == (repo_root, expected_branch)

    # Verify file was written (check via filesystem since FakeGit doesn't track file writes)
    file_path = repo_root / f"PLAN-REVIEW-{issue_number}.md"
    assert file_path.exists()
    assert file_path.read_text() == plan_content

    # Verify commit was created with the staged file
    assert len(fake_git.commit.commits) == 1
    commit = fake_git.commit.commits[0]
    assert commit.cwd == repo_root
    assert commit.message == f"Add plan #{issue_number} for review"
    assert f"PLAN-REVIEW-{issue_number}.md" in commit.staged_files

    # Verify branch was pushed with upstream tracking
    assert len(fake_git.pushed_branches) == 1
    pushed = fake_git.pushed_branches[0]
    assert pushed.remote == "origin"
    assert pushed.branch == expected_branch
    assert pushed.set_upstream is True
    assert pushed.force is False


def test_plan_create_review_branch_multiline_plan(tmp_path: Path) -> None:
    """Test creation with multi-line plan content."""
    plan_content = """# Plan: Complex Feature

## Context
Background info here

## Implementation
- Step 1
- Step 2
- Step 3

## Success Criteria
All tests pass"""

    comment_id = 111222333
    issue_number = 9999
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Complex Plan", labels=None)
    comment_body = make_plan_comment_body_v2(plan_content)
    comment = make_issue_comment(comment_id, comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )

    fake_git = FakeGit(
        local_branches={repo_root: []},
        remote_branches={repo_root: ["origin/master"]},
        current_branches={repo_root: "main"},
        repository_roots={repo_root: repo_root},
    )

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_branch,
        [str(issue_number)],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0

    # Verify file contains full multi-line content
    file_path = repo_root / f"PLAN-REVIEW-{issue_number}.md"
    assert file_path.exists()
    assert file_path.read_text() == plan_content


# ============================================================================
# Error Cases
# ============================================================================


def test_plan_create_review_branch_issue_not_found(tmp_path: Path) -> None:
    """Test error when issue doesn't exist."""
    repo_root = tmp_path / "repo"
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_branch,
        ["9999"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "#9999" in output["message"]


def test_plan_create_review_branch_missing_erk_plan_label(tmp_path: Path) -> None:
    """Test error when issue doesn't have erk-plan label."""
    issue_number = 1234
    repo_root = tmp_path / "repo"
    body = make_plan_header_body(plan_comment_id=123456789)
    issue = make_issue_info(
        issue_number, body, title="Test Plan Issue", labels=["bug", "enhancement"]
    )

    fake_gh = FakeGitHubIssues(issues={issue_number: issue})
    fake_git = FakeGit()
    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_branch,
        [str(issue_number)],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "missing_erk_plan_label"
    assert "#1234" in output["message"]


def test_plan_create_review_branch_no_plan_content(tmp_path: Path) -> None:
    """Test error when issue has no plan content."""
    issue_number = 1234
    repo_root = tmp_path / "repo"
    body = make_plan_header_body(plan_comment_id=None)
    issue = make_issue_info(issue_number, body, title="Test Plan Issue", labels=None)

    fake_gh = FakeGitHubIssues(issues={issue_number: issue})
    fake_git = FakeGit()
    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_branch,
        [str(issue_number)],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_plan_content"
    assert "no plan_comment_id" in output["message"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure on success."""
    plan_content = "## Plan content here"
    comment_id = 123456789
    issue_number = 1234
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Plan: Test Feature", labels=None)
    comment_body = make_plan_comment_body_v2(plan_content)
    comment = make_issue_comment(comment_id, comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )

    fake_git = FakeGit(
        local_branches={repo_root: []},
        remote_branches={repo_root: ["origin/master"]},
        current_branches={repo_root: "main"},
        repository_roots={repo_root: repo_root},
    )

    # FakeTime default: 2024-01-15 14:30:00 -> branch timestamp -01-15-1430
    expected_branch = f"plan-review-{issue_number}-01-15-1430"

    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_branch,
        [str(issue_number)],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "branch" in output
    assert "file_path" in output
    assert "plan_title" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["branch"], str)
    assert isinstance(output["file_path"], str)
    assert isinstance(output["plan_title"], str)

    # Verify values
    assert output["success"] is True
    assert output["issue_number"] == issue_number
    assert output["branch"] == expected_branch
    assert output["file_path"] == f"PLAN-REVIEW-{issue_number}.md"
    assert output["plan_title"] == "Plan: Test Feature"


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure on error."""
    repo_root = tmp_path / "repo"
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    result = runner.invoke(
        plan_create_review_branch,
        ["9999"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            repo_root=repo_root,
        ),
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
