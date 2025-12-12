"""Unit tests for PR discussion comment kit CLI commands.

Tests get-pr-discussion-comments and add-reaction-to-comment commands.
Uses FakeGitHub and FakeGitHubIssues for fast, reliable testing.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.add_reaction_to_comment import (
    add_reaction_to_comment,
)
from erk_kits.data.kits.erk.scripts.erk.get_pr_discussion_comments import (
    get_pr_discussion_comments,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueComment
from erk_shared.github.types import PRDetails


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

    fake_github = FakeGitHub(pr_details={123: pr_details})
    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: comments})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_discussion_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_github_issues,
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

    fake_github = FakeGitHub(pr_details={123: pr_details})
    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: []})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_discussion_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_github_issues,
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
    fake_github = FakeGitHub()
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_discussion_comments,
            ["--pr", "999"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_github_issues,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0  # Graceful degradation
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "pr_not_found"


# ============================================================================
# add-reaction-to-comment Success Cases
# ============================================================================


def test_add_reaction_to_comment_success(tmp_path: Path) -> None:
    """Test successfully adding a reaction to a comment."""
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_reaction_to_comment,
            ["--comment-id", "12345"],
            obj=ErkContext.for_test(
                github_issues=fake_github_issues,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["comment_id"] == 12345
    assert output["reaction"] == "+1"  # Default reaction

    # Verify reaction was tracked in the fake
    assert fake_github_issues.added_reactions == [(12345, "+1")]


def test_add_reaction_to_comment_custom_reaction(tmp_path: Path) -> None:
    """Test adding a custom reaction type."""
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_reaction_to_comment,
            ["--comment-id", "12345", "--reaction", "rocket"],
            obj=ErkContext.for_test(
                github_issues=fake_github_issues,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["reaction"] == "rocket"

    # Verify reaction was tracked with custom type
    assert fake_github_issues.added_reactions == [(12345, "rocket")]


def test_add_reaction_to_comment_multiple(tmp_path: Path) -> None:
    """Test adding reactions to multiple comments tracks all of them."""
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        ctx = ErkContext.for_test(
            github_issues=fake_github_issues,
            git=fake_git,
            repo_root=cwd,
            cwd=cwd,
        )

        # Add reaction to first comment
        runner.invoke(
            add_reaction_to_comment,
            ["--comment-id", "100"],
            obj=ctx,
        )

        # Add reaction to second comment
        runner.invoke(
            add_reaction_to_comment,
            ["--comment-id", "101"],
            obj=ctx,
        )

    # Both should be tracked
    assert (100, "+1") in fake_github_issues.added_reactions
    assert (101, "+1") in fake_github_issues.added_reactions


# ============================================================================
# add-reaction-to-comment CLI Argument Tests
# ============================================================================


def test_add_reaction_to_comment_missing_comment_id(tmp_path: Path) -> None:
    """Test error when comment-id is missing."""
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_reaction_to_comment,
            [],  # Missing --comment-id
            obj=ErkContext.for_test(
                github_issues=fake_github_issues,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    # Click should return error for missing required option
    assert result.exit_code != 0
    assert "comment-id" in result.output.lower()


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_get_pr_discussion_comments_json_structure(tmp_path: Path) -> None:
    """Test JSON output structure for get-pr-discussion-comments."""
    pr_details = make_pr_details(123)
    comments = [make_issue_comment(100, "Test comment")]

    fake_github = FakeGitHub(pr_details={123: pr_details})
    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: comments})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            get_pr_discussion_comments,
            ["--pr", "123"],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_github_issues,
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


def test_add_reaction_to_comment_json_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure for add-reaction-to-comment success."""
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            add_reaction_to_comment,
            ["--comment-id", "12345"],
            obj=ErkContext.for_test(
                github_issues=fake_github_issues,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify success structure
    assert output["success"] is True
    assert output["comment_id"] == 12345
    assert output["reaction"] == "+1"
