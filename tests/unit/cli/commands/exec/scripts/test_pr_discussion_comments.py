"""Unit tests for PR discussion comment kit CLI commands.

Tests get-pr-discussion-comments command.
Uses FakeGitHub and FakeGitHubIssues for fast, reliable testing.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_discussion_comments import (
    get_pr_discussion_comments,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment
from erk_shared.gateway.github.types import PRDetails


def make_pr_details(pr_number: int, branch: str = "feature-branch") -> PRDetails:
    """Create test PRDetails."""
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}",
        title=f"Test PR #{pr_number}",
        body="Test PR body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )


def make_issue_comment(
    comment_id: int,
    body: str,
    author: str = "reviewer",
    pr_number: int = 123,
) -> IssueComment:
    """Create test IssueComment."""
    return IssueComment(
        body=body,
        url=f"https://github.com/test-owner/test-repo/pull/{pr_number}#issuecomment-{comment_id}",
        id=comment_id,
        author=author,
    )


# ============================================================================
# get-pr-discussion-comments Success Cases
# ============================================================================


def test_get_pr_discussion_comments_with_pr_number(tmp_path: Path) -> None:
    """Test get-pr-discussion-comments with explicit PR number."""
    pr_details = make_pr_details(123)
    comments = [
        make_issue_comment(100, "First comment", "reviewer1"),
        make_issue_comment(101, "Second comment", "reviewer2"),
    ]

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: comments})
    fake_github = FakeGitHub(issues_gateway=fake_github_issues, pr_details={123: pr_details})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_discussion_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert len(output["comments"]) == 2
    assert output["comments"][0]["id"] == 100
    assert output["comments"][0]["author"] == "reviewer1"
    assert output["comments"][0]["body"] == "First comment"
    assert output["comments"][1]["id"] == 101
    assert output["comments"][1]["author"] == "reviewer2"


def test_get_pr_discussion_comments_no_comments(tmp_path: Path) -> None:
    """Test get-pr-discussion-comments returns empty list when no comments."""
    pr_details = make_pr_details(123)

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: []})
    fake_github = FakeGitHub(issues_gateway=fake_github_issues, pr_details={123: pr_details})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_discussion_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["comments"] == []


# ============================================================================
# get-pr-discussion-comments Error Cases
# ============================================================================


def test_get_pr_discussion_comments_pr_not_found(tmp_path: Path) -> None:
    """Test error when PR doesn't exist."""
    fake_github_issues = FakeGitHubIssues()
    fake_github = FakeGitHub(issues_gateway=fake_github_issues)
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_discussion_comments,
            ["--pr", "999"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0  # Graceful degradation
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "pr-not-found"


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_get_pr_discussion_comments_json_structure(tmp_path: Path) -> None:
    """Test JSON output structure for get-pr-discussion-comments."""
    pr_details = make_pr_details(123)
    comments = [make_issue_comment(100, "Test comment")]

    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: comments})
    fake_github = FakeGitHub(issues_gateway=fake_github_issues, pr_details={123: pr_details})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_discussion_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify top-level structure
    assert "success" in output
    assert "pr_number" in output
    assert "pr_url" in output
    assert "pr_title" in output
    assert "comments" in output

    # Verify comment structure
    comment_data = output["comments"][0]
    assert "id" in comment_data
    assert "author" in comment_data
    assert "body" in comment_data
    assert "url" in comment_data
