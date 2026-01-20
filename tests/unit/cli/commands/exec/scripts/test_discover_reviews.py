"""Tests for discover-reviews exec command.

Tests focus on the discovery logic, not subprocess calls to gh.
"""

import json

from erk.cli.commands.exec.scripts.discover_reviews import (
    _create_matrix,
    _review_to_dict,
)
from erk.review.models import ParsedReview, ReviewFrontmatter


def _make_review(
    *,
    name: str,
    filename: str,
    marker: str = "<!-- test -->",
) -> ParsedReview:
    """Create a ParsedReview for testing."""
    return ParsedReview(
        frontmatter=ReviewFrontmatter(
            name=name,
            paths=("**/*.py",),
            marker=marker,
            provider="claude",
            model="claude-sonnet-4-5",
            timeout_minutes=30,
            allowed_tools="Read(*)",
            enabled=True,
        ),
        body="Review body.",
        filename=filename,
    )


class TestReviewToDict:
    """Tests for _review_to_dict helper."""

    def test_converts_review_to_dict(self) -> None:
        """Convert ParsedReview to JSON-serializable dict."""
        review = _make_review(
            name="Test Review",
            filename="test.md",
            marker="<!-- test-marker -->",
        )

        result = _review_to_dict(review)

        assert result["name"] == "Test Review"
        assert result["filename"] == "test.md"
        assert result["marker"] == "<!-- test-marker -->"
        assert result["model"] == "claude-sonnet-4-5"
        assert result["timeout_minutes"] == 30
        assert result["allowed_tools"] == "Read(*)"
        assert result["paths"] == ["**/*.py"]


class TestCreateMatrix:
    """Tests for _create_matrix helper."""

    def test_empty_reviews(self) -> None:
        """Return empty include list for no reviews."""
        result = _create_matrix([])

        assert result == {"include": []}

    def test_single_review(self) -> None:
        """Create matrix with single review."""
        reviews = [_make_review(name="Test", filename="test.md")]

        result = _create_matrix(reviews)

        assert result == {
            "include": [
                {"name": "Test", "filename": "test.md"},
            ]
        }

    def test_multiple_reviews(self) -> None:
        """Create matrix with multiple reviews."""
        reviews = [
            _make_review(name="Review A", filename="a.md"),
            _make_review(name="Review B", filename="b.md"),
            _make_review(name="Review C", filename="c.md"),
        ]

        result = _create_matrix(reviews)

        assert result == {
            "include": [
                {"name": "Review A", "filename": "a.md"},
                {"name": "Review B", "filename": "b.md"},
                {"name": "Review C", "filename": "c.md"},
            ]
        }

    def test_matrix_is_json_serializable(self) -> None:
        """Matrix output can be JSON serialized."""
        reviews = [_make_review(name="Test", filename="test.md")]

        result = _create_matrix(reviews)

        # Should not raise
        json_str = json.dumps(result)
        assert "Test" in json_str
