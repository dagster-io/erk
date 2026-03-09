"""Unit tests for GitHubChecks static methods."""

from pathlib import Path

from erk_shared.fakes.github_issues import FakeGitHubIssues
from erk_shared.gateway.github.checks import GitHubChecks
from erk_shared.gateway.github.issues.types import IssueComment, IssueComments
from erk_shared.non_ideal_state import GitHubAPIFailed


def _make_comment(comment_id: int) -> IssueComment:
    return IssueComment(
        body=f"Comment {comment_id}",
        url=f"https://github.com/owner/repo/issues/1#issuecomment-{comment_id}",
        id=comment_id,
        author="reviewer",
    )


# ============================================================================
# issue_comments() return type
# ============================================================================


def test_issue_comments_returns_issue_comments_wrapper() -> None:
    """issue_comments() returns IssueComments, not a raw list."""
    fake_issues = FakeGitHubIssues(comments_with_urls={1: [_make_comment(100)]})
    result = GitHubChecks.issue_comments(fake_issues, Path("/fake"), 1)
    assert isinstance(result, IssueComments)


def test_issue_comments_wraps_items_in_tuple() -> None:
    """issue_comments() wraps the raw list into a tuple inside IssueComments."""
    c1 = _make_comment(100)
    c2 = _make_comment(101)
    fake_issues = FakeGitHubIssues(comments_with_urls={1: [c1, c2]})
    result = GitHubChecks.issue_comments(fake_issues, Path("/fake"), 1)
    assert isinstance(result, IssueComments)
    assert list(result) == [c1, c2]


def test_issue_comments_empty_issue_returns_empty_wrapper() -> None:
    """issue_comments() wraps empty list into IssueComments with no items."""
    fake_issues = FakeGitHubIssues(comments_with_urls={1: []})
    result = GitHubChecks.issue_comments(fake_issues, Path("/fake"), 1)
    assert isinstance(result, IssueComments)
    assert list(result) == []


def test_issue_comments_unknown_issue_returns_empty_wrapper() -> None:
    """issue_comments() returns empty IssueComments when issue has no configured comments."""
    fake_issues = FakeGitHubIssues()
    result = GitHubChecks.issue_comments(fake_issues, Path("/fake"), 99)
    assert isinstance(result, IssueComments)
    assert list(result) == []


# ============================================================================
# issue_comments() error handling
# ============================================================================


def test_issue_comments_returns_github_api_failed_on_error() -> None:
    """issue_comments() returns GitHubAPIFailed when the API raises RuntimeError."""
    fake_issues = FakeGitHubIssues(get_comments_error="rate limit exceeded")
    result = GitHubChecks.issue_comments(fake_issues, Path("/fake"), 1)
    assert isinstance(result, GitHubAPIFailed)


def test_issue_comments_error_message_propagated() -> None:
    """issue_comments() preserves the original error message in GitHubAPIFailed."""
    fake_issues = FakeGitHubIssues(get_comments_error="rate limit exceeded")
    result = GitHubChecks.issue_comments(fake_issues, Path("/fake"), 1)
    assert isinstance(result, GitHubAPIFailed)
    assert "rate limit exceeded" in result.message


# ============================================================================
# IssueComments .ensure() integration
# ============================================================================


def test_issue_comments_result_is_ensurable() -> None:
    """.ensure() on the successful result returns the IssueComments itself."""
    fake_issues = FakeGitHubIssues(comments_with_urls={1: []})
    result = GitHubChecks.issue_comments(fake_issues, Path("/fake"), 1)
    assert isinstance(result, IssueComments)
    assert result.ensure() is result
