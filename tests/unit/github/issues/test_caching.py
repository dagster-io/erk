"""Tests for CachingGitHubIssues wrapper.

These tests verify the caching wrapper's behavior for:
1. Write operation delegation with cache invalidation
2. Read operation delegation for non-cached operations (comments, labels)
3. Cache key generation

Note: The actual caching logic (timestamp fetching, batch queries) requires
integration tests since it uses execute_gh_command directly.
"""

from pathlib import Path

from erk_shared.github.issues import CachingGitHubIssues, FakeGitHubIssues

from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.paths import sentinel_path


class TrackingGitHubIssues(FakeGitHubIssues):
    """FakeGitHubIssues with call tracking for testing delegation."""

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        super().__init__(**kwargs)
        self.get_issue_calls: list[tuple[Path, int]] = []
        self.add_comment_calls: list[tuple[Path, int, str]] = []
        self.update_issue_body_calls: list[tuple[Path, int, str]] = []
        self.ensure_label_on_issue_calls: list[tuple[Path, int, str]] = []
        self.remove_label_from_issue_calls: list[tuple[Path, int, str]] = []
        self.close_issue_calls: list[tuple[Path, int]] = []

    def get_issue(self, repo_root: Path, number: int):  # noqa: ANN201
        self.get_issue_calls.append((repo_root, number))
        return super().get_issue(repo_root, number)

    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        self.add_comment_calls.append((repo_root, number, body))
        super().add_comment(repo_root, number, body)

    def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
        self.update_issue_body_calls.append((repo_root, number, body))
        super().update_issue_body(repo_root, number, body)

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        self.ensure_label_on_issue_calls.append((repo_root, issue_number, label))
        super().ensure_label_on_issue(repo_root, issue_number, label)

    def remove_label_from_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        self.remove_label_from_issue_calls.append((repo_root, issue_number, label))
        super().remove_label_from_issue(repo_root, issue_number, label)

    def close_issue(self, repo_root: Path, number: int) -> None:
        self.close_issue_calls.append((repo_root, number))
        super().close_issue(repo_root, number)


# ============================================================================
# Write operation delegation tests
# ============================================================================


def test_add_comment_delegates_to_wrapped() -> None:
    """Test add_comment delegates to wrapped implementation."""
    issue = create_test_issue(42, "Test Issue", "Body")
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    caching.add_comment(repo, 42, "Test comment")

    assert len(wrapped.add_comment_calls) == 1
    assert wrapped.add_comment_calls[0] == (repo, 42, "Test comment")


def test_update_issue_body_delegates_to_wrapped() -> None:
    """Test update_issue_body delegates to wrapped implementation."""
    issue = create_test_issue(42, "Test Issue", "Original body")
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    caching.update_issue_body(repo, 42, "Updated body")

    assert len(wrapped.update_issue_body_calls) == 1
    assert wrapped.update_issue_body_calls[0] == (repo, 42, "Updated body")


def test_ensure_label_on_issue_delegates_to_wrapped() -> None:
    """Test ensure_label_on_issue delegates to wrapped implementation."""
    issue = create_test_issue(42, "Test Issue", "Body")
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    caching.ensure_label_on_issue(repo, 42, "bug")

    assert len(wrapped.ensure_label_on_issue_calls) == 1
    assert wrapped.ensure_label_on_issue_calls[0] == (repo, 42, "bug")


def test_remove_label_from_issue_delegates_to_wrapped() -> None:
    """Test remove_label_from_issue delegates to wrapped implementation."""
    issue = create_test_issue(42, "Test Issue", "Body", labels=["bug"])
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    caching.remove_label_from_issue(repo, 42, "bug")

    assert len(wrapped.remove_label_from_issue_calls) == 1
    assert wrapped.remove_label_from_issue_calls[0] == (repo, 42, "bug")


def test_close_issue_delegates_to_wrapped() -> None:
    """Test close_issue delegates to wrapped implementation."""
    issue = create_test_issue(42, "Test Issue", "Body")
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    caching.close_issue(repo, 42)

    assert len(wrapped.close_issue_calls) == 1
    assert wrapped.close_issue_calls[0] == (repo, 42)


# ============================================================================
# Non-cached read operation delegation tests
# ============================================================================


def test_get_issue_comments_delegates_to_wrapped() -> None:
    """Test get_issue_comments delegates to wrapped implementation."""
    comments = {42: ["Comment 1", "Comment 2"]}
    wrapped = FakeGitHubIssues(comments=comments)
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    result = caching.get_issue_comments(repo, 42)

    assert result == ["Comment 1", "Comment 2"]


def test_get_multiple_issue_comments_delegates_to_wrapped() -> None:
    """Test get_multiple_issue_comments delegates to wrapped implementation."""
    comments = {42: ["Comment 1"], 43: ["Comment 2", "Comment 3"]}
    wrapped = FakeGitHubIssues(comments=comments)
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    result = caching.get_multiple_issue_comments(repo, [42, 43])

    assert result == {42: ["Comment 1"], 43: ["Comment 2", "Comment 3"]}


def test_ensure_label_exists_delegates_to_wrapped() -> None:
    """Test ensure_label_exists delegates to wrapped implementation."""
    wrapped = FakeGitHubIssues()
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    caching.ensure_label_exists(repo, "erk-plan", "Description", "0E8A16")

    assert "erk-plan" in wrapped.labels


def test_create_issue_delegates_to_wrapped() -> None:
    """Test create_issue delegates to wrapped implementation."""
    wrapped = FakeGitHubIssues(next_issue_number=100)
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    result = caching.create_issue(repo, "New Issue", "Body", ["bug"])

    assert result.number == 100
    assert wrapped.created_issues == [("New Issue", "Body", ["bug"])]


def test_get_current_username_delegates_to_wrapped() -> None:
    """Test get_current_username delegates to wrapped implementation."""
    wrapped = FakeGitHubIssues(username="testuser")
    caching = CachingGitHubIssues(wrapped)

    result = caching.get_current_username()

    assert result == "testuser"


# ============================================================================
# Cache invalidation tests
# ============================================================================


def test_add_comment_invalidates_cache() -> None:
    """Test add_comment removes issue from cache."""
    issue = create_test_issue(42, "Test Issue", "Body")
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    # Manually populate cache
    caching._cache[(str(repo), 42)] = issue

    # Add comment should invalidate
    caching.add_comment(repo, 42, "Comment")

    # Cache should be empty for this issue
    assert (str(repo), 42) not in caching._cache


def test_update_issue_body_invalidates_cache() -> None:
    """Test update_issue_body removes issue from cache."""
    issue = create_test_issue(42, "Test Issue", "Original body")
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    # Manually populate cache
    caching._cache[(str(repo), 42)] = issue

    # Update body should invalidate
    caching.update_issue_body(repo, 42, "New body")

    # Cache should be empty for this issue
    assert (str(repo), 42) not in caching._cache


def test_ensure_label_on_issue_invalidates_cache() -> None:
    """Test ensure_label_on_issue removes issue from cache."""
    issue = create_test_issue(42, "Test Issue", "Body")
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    # Manually populate cache
    caching._cache[(str(repo), 42)] = issue

    # Add label should invalidate
    caching.ensure_label_on_issue(repo, 42, "bug")

    # Cache should be empty for this issue
    assert (str(repo), 42) not in caching._cache


def test_remove_label_from_issue_invalidates_cache() -> None:
    """Test remove_label_from_issue removes issue from cache."""
    issue = create_test_issue(42, "Test Issue", "Body", labels=["bug"])
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    # Manually populate cache
    caching._cache[(str(repo), 42)] = issue

    # Remove label should invalidate
    caching.remove_label_from_issue(repo, 42, "bug")

    # Cache should be empty for this issue
    assert (str(repo), 42) not in caching._cache


def test_close_issue_invalidates_cache() -> None:
    """Test close_issue removes issue from cache."""
    issue = create_test_issue(42, "Test Issue", "Body")
    wrapped = TrackingGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    # Manually populate cache
    caching._cache[(str(repo), 42)] = issue

    # Close should invalidate
    caching.close_issue(repo, 42)

    # Cache should be empty for this issue
    assert (str(repo), 42) not in caching._cache


def test_invalidation_only_affects_specific_issue() -> None:
    """Test that cache invalidation only removes the specific issue."""
    issue_42 = create_test_issue(42, "Issue 42", "Body")
    issue_43 = create_test_issue(43, "Issue 43", "Body")
    wrapped = TrackingGitHubIssues(issues={42: issue_42, 43: issue_43})
    caching = CachingGitHubIssues(wrapped)
    repo = sentinel_path("/repo")

    # Populate cache for both issues
    caching._cache[(str(repo), 42)] = issue_42
    caching._cache[(str(repo), 43)] = issue_43

    # Add comment to issue 42 only
    caching.add_comment(repo, 42, "Comment")

    # Issue 42 should be invalidated, issue 43 should remain
    assert (str(repo), 42) not in caching._cache
    assert (str(repo), 43) in caching._cache


# ============================================================================
# Cache key tests
# ============================================================================


def test_cache_uses_repo_path_as_key() -> None:
    """Test that cache uses repo path to separate issues from different repos."""
    issue = create_test_issue(42, "Test Issue", "Body")
    wrapped = FakeGitHubIssues(issues={42: issue})
    caching = CachingGitHubIssues(wrapped)
    repo1 = sentinel_path("/repo1")
    repo2 = sentinel_path("/repo2")

    # Populate cache for repo1
    caching._cache[(str(repo1), 42)] = issue

    # Invalidate for repo2 should not affect repo1
    caching._invalidate(repo2, 42)

    # repo1 cache should still have the issue
    assert (str(repo1), 42) in caching._cache
