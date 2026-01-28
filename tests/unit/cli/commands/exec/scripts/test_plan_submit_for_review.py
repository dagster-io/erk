"""Unit tests for plan_submit_for_review exec command.

Tests GitHub issue plan content extraction for PR-based review workflow.
Uses FakeGitHubIssues for fast, reliable testing without subprocess mocking.
"""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_submit_for_review import (
    plan_submit_for_review,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo


def make_plan_header_body(
    plan_comment_id: int | None = 123456789,
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


def make_plan_comment_body_v1(plan_content: str) -> str:
    """Create a comment body with old format plan markers (backward compat)."""
    return f"""<!-- erk:plan-content -->
{plan_content}
<!-- /erk:plan-content -->"""


def make_issue_info(
    number: int,
    body: str,
    title: str = "Test Plan Issue",
    labels: list[str] | None = None,
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


def test_plan_submit_for_review_success_v2_format() -> None:
    """Test successful extraction with Schema v2 plan-body format."""
    plan_content = "## Implementation Plan\n\nThis is the plan content."
    comment_id = 123456789
    issue_number = 1234

    # Create issue with plan-header
    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Plan: Add feature X")

    # Create comment with plan-body block
    comment_body = make_plan_comment_body_v2(plan_content)
    comment = make_issue_comment(comment_id, comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        [str(issue_number)],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == issue_number
    assert output["title"] == "Plan: Add feature X"
    assert output["url"] == f"https://github.com/test-owner/test-repo/issues/{issue_number}"
    assert output["plan_content"] == plan_content
    assert output["plan_comment_id"] == comment_id
    assert (
        output["plan_comment_url"]
        == f"https://github.com/test-owner/test-repo/issues/1234#issuecomment-{comment_id}"
    )


def test_plan_submit_for_review_success_v1_format() -> None:
    """Test backward compatibility with old format (erk:plan-content markers)."""
    plan_content = "## Old Format Plan\n\nUsing legacy markers."
    comment_id = 987654321
    issue_number = 5678

    # Create issue with plan-header
    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body)

    # Create comment with old format markers
    comment_body = make_plan_comment_body_v1(plan_content)
    comment = make_issue_comment(comment_id, comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        [str(issue_number)],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_content"] == plan_content


def test_plan_submit_for_review_multiline_plan() -> None:
    """Test extraction of multi-line plan content."""
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

    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body)
    comment_body = make_plan_comment_body_v2(plan_content)
    comment = make_issue_comment(comment_id, comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        [str(issue_number)],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_content"] == plan_content


# ============================================================================
# Error Cases
# ============================================================================


def test_plan_submit_for_review_issue_not_found() -> None:
    """Test error when issue doesn't exist."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        ["9999"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "#9999" in output["message"]


def test_plan_submit_for_review_missing_erk_plan_label() -> None:
    """Test error when issue doesn't have erk-plan label."""
    issue_number = 1234
    body = make_plan_header_body()
    issue = make_issue_info(issue_number, body, labels=["bug", "enhancement"])

    fake_gh = FakeGitHubIssues(issues={issue_number: issue})
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        [str(issue_number)],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "missing_erk_plan_label"
    assert "#1234" in output["message"]


def test_plan_submit_for_review_no_plan_comment_id() -> None:
    """Test error when issue has no plan_comment_id in metadata."""
    issue_number = 1234
    body = make_plan_header_body(plan_comment_id=None)
    issue = make_issue_info(issue_number, body)

    fake_gh = FakeGitHubIssues(issues={issue_number: issue})
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        [str(issue_number)],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_plan_content"
    assert "no plan_comment_id" in output["message"]


def test_plan_submit_for_review_no_comments() -> None:
    """Test error when issue has no comments."""
    issue_number = 1234
    comment_id = 123456789
    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments={issue_number: []},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        [str(issue_number)],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_plan_content"
    assert "has no comments" in output["message"]


def test_plan_submit_for_review_comment_has_no_plan_markers() -> None:
    """Test error when comment exists but has no plan markers."""
    issue_number = 1234
    comment_id = 123456789
    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body)

    # Create comment without plan markers
    comment = make_issue_comment(comment_id, "Just a regular comment, no plan here.")

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        [str(issue_number)],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_plan_content"
    assert "has no plan markers" in output["message"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success() -> None:
    """Test JSON output structure on success."""
    plan_content = "## Plan content here"
    comment_id = 123456789
    issue_number = 1234

    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Plan: Test Feature")
    comment_body = make_plan_comment_body_v2(plan_content)
    comment = make_issue_comment(comment_id, comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        [str(issue_number)],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "title" in output
    assert "url" in output
    assert "plan_content" in output
    assert "plan_comment_id" in output
    assert "plan_comment_url" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["title"], str)
    assert isinstance(output["url"], str)
    assert isinstance(output["plan_content"], str)
    assert isinstance(output["plan_comment_id"], int)
    assert isinstance(output["plan_comment_url"], str)

    # Verify values
    assert output["success"] is True
    assert output["issue_number"] == issue_number
    assert output["title"] == "Plan: Test Feature"


def test_json_output_structure_error() -> None:
    """Test JSON output structure on error."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        plan_submit_for_review,
        ["9999"],
        obj=ErkContext.for_test(github_issues=fake_gh),
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
