"""Unit tests for plan_update_from_feedback exec command.

Tests updating plan-body comments on GitHub issues from reviewer feedback.
Uses FakeGitHubIssues for fast, reliable testing.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_update_from_feedback import (
    plan_update_from_feedback,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from tests.unit.cli.commands.exec.scripts.test_plan_create_review_branch import (
    make_issue_comment,
    make_issue_info,
    make_plan_comment_body_v2,
    make_plan_header_body,
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

    runner = CliRunner()
    result = runner.invoke(
        plan_update_from_feedback,
        [str(issue_number), "--plan-content", new_plan],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == issue_number

    # Verify comment was updated
    assert len(fake_gh.updated_comments) == 1
    updated_id, updated_body = fake_gh.updated_comments[0]
    assert updated_id == comment_id
    # Updated body should contain the new plan content wrapped in metadata markers
    assert "Updated Plan" in updated_body
    assert "plan-body" in updated_body


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

    runner = CliRunner()
    result = runner.invoke(
        plan_update_from_feedback,
        [str(issue_number), "--plan-path", str(plan_file)],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == issue_number

    # Verify comment was updated with file content
    assert len(fake_gh.updated_comments) == 1
    _, updated_body = fake_gh.updated_comments[0]
    assert "Plan from file" in updated_body


def test_updated_comment_contains_plan_body_markers(tmp_path: Path) -> None:
    """Test that the updated comment contains plan-body metadata block markers."""
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

    runner = CliRunner()
    result = runner.invoke(
        plan_update_from_feedback,
        [str(issue_number), "--plan-content", "## New Plan"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 0

    _, updated_body = fake_gh.updated_comments[0]
    assert "<!-- erk:metadata-block:plan-body -->" in updated_body
    assert "<!-- /erk:metadata-block:plan-body -->" in updated_body


# ============================================================================
# Error Cases
# ============================================================================


def test_error_issue_not_found(tmp_path: Path) -> None:
    """Test error when issue doesn't exist."""
    repo_root = tmp_path / "repo"
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        plan_update_from_feedback,
        ["9999", "--plan-content", "content"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
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
    runner = CliRunner()

    result = runner.invoke(
        plan_update_from_feedback,
        [str(issue_number), "--plan-content", "content"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
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
    runner = CliRunner()

    result = runner.invoke(
        plan_update_from_feedback,
        ["1234", "--plan-path", str(plan_file), "--plan-content", "content"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
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
    runner = CliRunner()

    result = runner.invoke(
        plan_update_from_feedback,
        ["1234"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            repo_root=repo_root,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_input"
    assert "either" in output["message"].lower()
