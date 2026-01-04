"""Unit tests for reply-to-discussion-comment kit CLI command.

Tests the new command that posts a formatted reply to PR discussion comments
with blockquote of original and action summary.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.reply_to_discussion_comment import (
    _format_reply,
    reply_to_discussion_comment,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueComment, IssueInfo
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


def make_issue_info(number: int) -> IssueInfo:
    """Create test IssueInfo (required for add_comment to succeed)."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test PR #{number}",
        body="Test PR body",
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        labels=[],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# _format_reply Unit Tests
# ============================================================================


def test_format_reply_simple() -> None:
    """Test basic reply formatting."""
    reply = _format_reply(
        author="reviewer",
        url="https://github.com/example/pull/1#issuecomment-123",
        body="Please fix this typo",
        action_summary="**Action taken:** Fixed the typo in line 42.",
    )

    assert "> **@reviewer** [commented]" in reply
    assert "https://github.com/example/pull/1#issuecomment-123" in reply
    assert "> Please fix this typo" in reply
    assert "**Action taken:** Fixed the typo in line 42." in reply
    assert "Addressed via `/erk:pr-address`" in reply


def test_format_reply_multiline_body() -> None:
    """Test formatting with multiline comment body."""
    body = "Line one\nLine two\nLine three"
    reply = _format_reply(
        author="reviewer",
        url="https://github.com/example",
        body=body,
        action_summary="Action taken.",
    )

    # Each line should be quoted
    assert "> Line one" in reply
    assert "> Line two" in reply
    assert "> Line three" in reply


def test_format_reply_truncates_long_body() -> None:
    """Test that very long comment bodies are truncated."""
    lines = [f"Line {i}" for i in range(20)]  # 20 lines
    body = "\n".join(lines)

    reply = _format_reply(
        author="reviewer",
        url="https://github.com/example",
        body=body,
        action_summary="Action taken.",
    )

    # Should truncate after 10 lines
    assert "> Line 0" in reply
    assert "> Line 9" in reply
    assert "> ..." in reply
    assert "Line 15" not in reply  # Later lines should not appear


# ============================================================================
# reply-to-discussion-comment Success Cases
# ============================================================================


def test_reply_to_discussion_comment_success(tmp_path: Path) -> None:
    """Test successfully replying to a discussion comment."""
    pr_details = make_pr_details(123)
    comments = [
        make_issue_comment(100, "Please update the docs"),
        make_issue_comment(101, "Looks good!"),
    ]

    fake_github = FakeGitHub(pr_details={123: pr_details})
    # FakeGitHubIssues.add_comment requires issue to exist, so register PR as issue
    fake_github_issues = FakeGitHubIssues(
        issues={123: make_issue_info(123)},
        comments_with_urls={123: comments},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reply_to_discussion_comment,
            [
                "--comment-id",
                "100",
                "--pr",
                "123",
                "--reply",
                "**Action taken:** Updated the README with new examples.",
            ],
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
    assert output["comment_id"] == 100
    assert output["pr_number"] == 123
    assert "reply_id" in output

    # Verify a comment was added
    assert len(fake_github_issues.added_comments) == 1
    issue_num, body, comment_id = fake_github_issues.added_comments[0]
    assert issue_num == 123
    assert "@reviewer" in body
    assert "Please update the docs" in body
    assert "Updated the README with new examples" in body
    assert "erk:pr-address" in body

    # Verify reaction was added
    assert (100, "+1") in fake_github_issues.added_reactions


def test_reply_to_discussion_comment_quotes_original(tmp_path: Path) -> None:
    """Test that reply correctly quotes the original comment."""
    pr_details = make_pr_details(123)
    original_body = "This is architectural feedback.\nPlease consider a gateway pattern."
    comments = [make_issue_comment(200, original_body, author="schrockn")]

    fake_github = FakeGitHub(pr_details={123: pr_details})
    # FakeGitHubIssues.add_comment requires issue to exist, so register PR as issue
    fake_github_issues = FakeGitHubIssues(
        issues={123: make_issue_info(123)},
        comments_with_urls={123: comments},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reply_to_discussion_comment,
            [
                "--comment-id",
                "200",
                "--pr",
                "123",
                "--reply",
                "**Action taken:** Investigated and filed as backlog item.",
            ],
            obj=ErkContext.for_test(
                github=fake_github,
                github_issues=fake_github_issues,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code == 0, result.output

    # Check the posted reply content
    _, body, _ = fake_github_issues.added_comments[0]
    assert "@schrockn" in body
    assert "> This is architectural feedback." in body
    assert "> Please consider a gateway pattern." in body


# ============================================================================
# reply-to-discussion-comment Error Cases
# ============================================================================


def test_reply_to_discussion_comment_pr_not_found(tmp_path: Path) -> None:
    """Test error when PR doesn't exist."""
    fake_github = FakeGitHub()
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reply_to_discussion_comment,
            ["--comment-id", "100", "--pr", "999", "--reply", "Action taken."],
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
    assert output["error_type"] == "pr-not-found"


def test_reply_to_discussion_comment_comment_not_found(tmp_path: Path) -> None:
    """Test error when comment ID doesn't exist in the PR."""
    pr_details = make_pr_details(123)
    comments = [make_issue_comment(100, "Existing comment")]

    fake_github = FakeGitHub(pr_details={123: pr_details})
    fake_github_issues = FakeGitHubIssues(comments_with_urls={123: comments})
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reply_to_discussion_comment,
            [
                "--comment-id",
                "999",  # Non-existent comment
                "--pr",
                "123",
                "--reply",
                "Action taken.",
            ],
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
    assert output["error_type"] == "comment-not-found"
    assert "999" in output["message"]


# ============================================================================
# CLI Argument Validation Tests
# ============================================================================


def test_reply_to_discussion_comment_missing_comment_id(tmp_path: Path) -> None:
    """Test error when comment-id is missing."""
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reply_to_discussion_comment,
            ["--pr", "123", "--reply", "Action taken."],  # Missing --comment-id
            obj=ErkContext.for_test(
                github_issues=fake_github_issues,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code != 0
    assert "comment-id" in result.output.lower()


def test_reply_to_discussion_comment_missing_reply(tmp_path: Path) -> None:
    """Test error when reply is missing."""
    fake_github_issues = FakeGitHubIssues()
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reply_to_discussion_comment,
            ["--comment-id", "100", "--pr", "123"],  # Missing --reply
            obj=ErkContext.for_test(
                github_issues=fake_github_issues,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    assert result.exit_code != 0
    assert "reply" in result.output.lower()


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_reply_to_discussion_comment_json_structure(tmp_path: Path) -> None:
    """Test JSON output structure for reply-to-discussion-comment success."""
    pr_details = make_pr_details(123)
    comments = [make_issue_comment(100, "Test comment")]

    fake_github = FakeGitHub(pr_details={123: pr_details})
    # FakeGitHubIssues.add_comment requires issue to exist, so register PR as issue
    fake_github_issues = FakeGitHubIssues(
        issues={123: make_issue_info(123)},
        comments_with_urls={123: comments},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            reply_to_discussion_comment,
            ["--comment-id", "100", "--pr", "123", "--reply", "Action taken."],
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

    # Verify success structure
    assert output["success"] is True
    assert output["comment_id"] == 100
    assert "reply_id" in output
    assert isinstance(output["reply_id"], int)
    assert output["pr_number"] == 123
