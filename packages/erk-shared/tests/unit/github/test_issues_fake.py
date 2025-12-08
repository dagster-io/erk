"""Tests for FakeGitHubIssues - verifying test infrastructure works correctly."""

from pathlib import Path

from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueComment


class TestFakeGitHubIssuesComments:
    """Tests for issue comments functionality."""

    def test_get_issue_comments_with_urls_returns_configured_comments(self, tmp_path: Path) -> None:
        """Return configured IssueComment objects with all fields."""
        comments = [
            IssueComment(
                body="First comment",
                url="https://github.com/owner/repo/issues/1#issuecomment-100",
                id=100,
                author="reviewer1",
            ),
            IssueComment(
                body="Second comment",
                url="https://github.com/owner/repo/issues/1#issuecomment-101",
                id=101,
                author="reviewer2",
            ),
        ]
        fake_gh = FakeGitHubIssues(comments_with_urls={1: comments})

        result = fake_gh.get_issue_comments_with_urls(tmp_path, 1)

        assert len(result) == 2
        assert result[0].body == "First comment"
        assert result[0].url == "https://github.com/owner/repo/issues/1#issuecomment-100"
        assert result[0].id == 100
        assert result[0].author == "reviewer1"
        assert result[1].id == 101
        assert result[1].author == "reviewer2"

    def test_get_issue_comments_with_urls_returns_empty_for_unknown_issue(
        self, tmp_path: Path
    ) -> None:
        """Return empty list when no comments configured for issue."""
        fake_gh = FakeGitHubIssues()

        result = fake_gh.get_issue_comments_with_urls(tmp_path, 999)

        assert result == []


class TestFakeGitHubIssuesReactions:
    """Tests for reaction functionality."""

    def test_add_reaction_tracks_mutation(self, tmp_path: Path) -> None:
        """Track reactions added via add_reaction_to_comment."""
        fake_gh = FakeGitHubIssues()

        fake_gh.add_reaction_to_comment(tmp_path, 12345, "+1")
        fake_gh.add_reaction_to_comment(tmp_path, 67890, "rocket")

        assert len(fake_gh.added_reactions) == 2
        assert fake_gh.added_reactions[0] == (12345, "+1")
        assert fake_gh.added_reactions[1] == (67890, "rocket")

    def test_add_reaction_allows_multiple_to_same_comment(self, tmp_path: Path) -> None:
        """Allow multiple reactions to same comment (GitHub API is idempotent)."""
        fake_gh = FakeGitHubIssues()

        fake_gh.add_reaction_to_comment(tmp_path, 12345, "+1")
        fake_gh.add_reaction_to_comment(tmp_path, 12345, "+1")

        # Both are tracked (fake doesn't deduplicate, real API is idempotent)
        assert len(fake_gh.added_reactions) == 2

    def test_added_reactions_starts_empty(self) -> None:
        """Verify added_reactions list starts empty."""
        fake_gh = FakeGitHubIssues()

        assert fake_gh.added_reactions == []


class TestIssueCommentDataclass:
    """Tests for the IssueComment dataclass."""

    def test_issue_comment_has_all_fields(self) -> None:
        """Verify IssueComment has body, url, id, and author fields."""
        comment = IssueComment(
            body="Test body",
            url="https://example.com/comment",
            id=42,
            author="testuser",
        )

        assert comment.body == "Test body"
        assert comment.url == "https://example.com/comment"
        assert comment.id == 42
        assert comment.author == "testuser"

    def test_issue_comment_is_frozen(self) -> None:
        """Verify IssueComment is immutable."""
        comment = IssueComment(
            body="Test",
            url="https://example.com",
            id=1,
            author="user",
        )

        # Frozen dataclass should raise on attribute assignment
        try:
            comment.body = "Changed"  # type: ignore[misc]
            raise AssertionError("Expected frozen dataclass to raise")
        except AttributeError:
            pass  # Expected
