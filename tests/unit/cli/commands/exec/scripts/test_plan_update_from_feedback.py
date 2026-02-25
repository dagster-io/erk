"""Unit tests for plan_update_from_feedback exec command.

Tests updating plan content on GitHub PRs from reviewer feedback.
Uses PlannedPRBackend with FakeGitHub for fast, reliable testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_update_from_feedback import (
    plan_update_from_feedback,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from tests.test_utils.plan_helpers import issue_info_to_pr_details


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


def test_success_with_plan_content(tmp_path: Path) -> None:
    """Test successful update with --plan-content."""
    issue_number = 1234
    comment_id = 123456789
    new_plan = "## Updated Plan\n\nNew content after feedback."
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Plan: Feature X", labels=None)

    original_comment_body = make_plan_comment_body_v2("## Original Plan")
    comment = make_issue_comment(comment_id, original_comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    fake_github = FakeGitHub(
        pr_details={issue_number: issue_info_to_pr_details(issue)},
        issues_gateway=fake_gh,
    )

    runner = CliRunner()
    result = runner.invoke(
        plan_update_from_feedback,
        [str(issue_number), "--plan-content", new_plan],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_number"] == issue_number

    # PlannedPRBackend.update_plan_content updates the PR body via FakeGitHub
    assert len(fake_github.updated_pr_bodies) == 1
    updated_pr_number, updated_body = fake_github.updated_pr_bodies[0]
    assert updated_pr_number == issue_number
    # Updated body should contain the new plan content
    assert "Updated Plan" in updated_body


def test_success_with_plan_path(tmp_path: Path) -> None:
    """Test successful update with --plan-path."""
    issue_number = 5678
    comment_id = 987654321
    new_plan = "## Plan from file\n\nContent loaded from disk."
    repo_root = tmp_path / "repo"

    # Write plan to file
    plan_file = tmp_path / "updated-plan.md"
    plan_file.write_text(new_plan, encoding="utf-8")

    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Plan: Feature Y", labels=None)

    original_comment_body = make_plan_comment_body_v2("## Original Plan")
    comment = make_issue_comment(comment_id, original_comment_body)

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    fake_github = FakeGitHub(
        pr_details={issue_number: issue_info_to_pr_details(issue)},
        issues_gateway=fake_gh,
    )

    runner = CliRunner()
    result = runner.invoke(
        plan_update_from_feedback,
        [str(issue_number), "--plan-path", str(plan_file)],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_number"] == issue_number

    # PlannedPRBackend.update_plan_content updates the PR body via FakeGitHub
    assert len(fake_github.updated_pr_bodies) == 1
    _, updated_body = fake_github.updated_pr_bodies[0]
    assert "Plan from file" in updated_body


def test_updated_comment_contains_plan_body_markers(tmp_path: Path) -> None:
    """Test that the updated PR body contains the plan content."""
    issue_number = 1234
    comment_id = 123456789
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Plan: Markers", labels=None)
    comment = make_issue_comment(comment_id, make_plan_comment_body_v2("Original"))

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    fake_github = FakeGitHub(
        pr_details={issue_number: issue_info_to_pr_details(issue)},
        issues_gateway=fake_gh,
    )

    runner = CliRunner()
    result = runner.invoke(
        plan_update_from_feedback,
        [str(issue_number), "--plan-content", "## New Plan"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0

    # PlannedPRBackend.update_plan_content updates the PR body
    _, updated_body = fake_github.updated_pr_bodies[0]
    # The updated body should contain the new plan content
    assert "New Plan" in updated_body


# ============================================================================
# Error Cases
# ============================================================================


def test_error_issue_not_found(tmp_path: Path) -> None:
    """Test error when issue doesn't exist."""
    repo_root = tmp_path / "repo"
    fake_gh = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        plan_update_from_feedback,
        ["9999", "--plan-content", "content"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "#9999" in output["message"]


def test_error_missing_erk_plan_label(tmp_path: Path) -> None:
    """Test error when issue doesn't have erk-plan label."""
    issue_number = 1234
    comment_id = 123456789
    repo_root = tmp_path / "repo"

    body = make_plan_header_body(plan_comment_id=comment_id)
    issue = make_issue_info(issue_number, body, title="Not a plan", labels=["bug", "enhancement"])
    comment = make_issue_comment(comment_id, make_plan_comment_body_v2("Original"))

    fake_gh = FakeGitHubIssues(
        issues={issue_number: issue},
        comments_with_urls={issue_number: [comment]},
    )
    fake_github = FakeGitHub(
        pr_details={issue_number: issue_info_to_pr_details(issue)},
        issues_gateway=fake_gh,
    )
    runner = CliRunner()

    result = runner.invoke(
        plan_update_from_feedback,
        [str(issue_number), "--plan-content", "content"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "missing_erk_plan_label"
    assert "#1234" in output["message"]


def test_error_both_plan_path_and_content(tmp_path: Path) -> None:
    """Test error when both --plan-path and --plan-content are provided."""
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("content", encoding="utf-8")

    repo_root = tmp_path / "repo"
    fake_gh = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        plan_update_from_feedback,
        ["1234", "--plan-path", str(plan_file), "--plan-content", "content"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_input"
    assert "both" in output["message"].lower()


def test_error_neither_plan_path_nor_content(tmp_path: Path) -> None:
    """Test error when neither --plan-path nor --plan-content is provided."""
    repo_root = tmp_path / "repo"
    fake_gh = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_gh)
    runner = CliRunner()

    result = runner.invoke(
        plan_update_from_feedback,
        ["1234"],
        obj=ErkContext.for_test(
            github=fake_github,
            plan_store=PlannedPRBackend(fake_github, fake_gh, time=FakeTime()),
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_input"
    assert "either" in output["message"].lower()
