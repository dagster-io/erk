"""Tests for discover-reviews exec command.

Tests the CLI command end-to-end using FakeGitHub for dependency injection.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.discover_reviews import (
    _create_matrix,
    _review_to_dict,
    discover_reviews,
)
from erk.review.models import ParsedReview, ReviewFrontmatter
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub


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
            model="claude-sonnet-4-5",
            timeout_minutes=30,
            allowed_tools="Read(*)",
            enabled=True,
        ),
        body="Review body.",
        filename=filename,
    )


def _create_review_file(reviews_dir: Path, filename: str, content: str) -> None:
    """Create a review definition file for testing."""
    reviews_dir.mkdir(parents=True, exist_ok=True)
    (reviews_dir / filename).write_text(content, encoding="utf-8")


# ============================================================================
# Helper function tests
# ============================================================================


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


# ============================================================================
# CLI command tests
# ============================================================================


def test_discover_reviews_with_matching_files(tmp_path: Path) -> None:
    """Test successful discovery when reviews match changed files."""
    fake_github = FakeGitHub(
        pr_changed_files={123: ["src/main.py", "tests/test_main.py"]},
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        reviews_dir = cwd / ".claude" / "reviews"
        _create_review_file(
            reviews_dir,
            "python-review.md",
            """---
name: Python Review
paths:
  - "**/*.py"
marker: <!-- python-review -->
---
Review Python code.
""",
        )

        result = runner.invoke(
            discover_reviews,
            ["--pr-number", "123"],
            obj=ErkContext.for_test(github=fake_github, cwd=cwd),
        )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["reviews"]) == 1
        assert output["reviews"][0]["name"] == "Python Review"


def test_discover_reviews_no_matching_files(tmp_path: Path) -> None:
    """Test discovery when no reviews match changed files."""
    # Changed files are all JavaScript, no Python
    fake_github = FakeGitHub(
        pr_changed_files={123: ["src/app.js", "lib/utils.js"]},
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        reviews_dir = cwd / ".claude" / "reviews"
        _create_review_file(
            reviews_dir,
            "python-review.md",
            """---
name: Python Review
paths:
  - "**/*.py"
marker: <!-- python-review -->
---
Review Python code.
""",
        )

        result = runner.invoke(
            discover_reviews,
            ["--pr-number", "123"],
            obj=ErkContext.for_test(github=fake_github, cwd=cwd),
        )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["reviews"]) == 0
        assert "python-review.md" in output["skipped"]


def test_discover_reviews_empty_pr(tmp_path: Path) -> None:
    """Test discovery when PR has no changed files."""
    # PR with no changed files returns empty list
    fake_github = FakeGitHub(
        pr_changed_files={123: []},
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        reviews_dir = cwd / ".claude" / "reviews"
        _create_review_file(
            reviews_dir,
            "review.md",
            """---
name: Test Review
paths:
  - "**/*"
marker: <!-- test -->
---
Test.
""",
        )

        result = runner.invoke(
            discover_reviews,
            ["--pr-number", "123"],
            obj=ErkContext.for_test(github=fake_github, cwd=cwd),
        )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["reviews"]) == 0


def test_discover_reviews_disabled_reviews(tmp_path: Path) -> None:
    """Test that disabled reviews are excluded but reported."""
    fake_github = FakeGitHub(
        pr_changed_files={123: ["file.py"]},
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        reviews_dir = cwd / ".claude" / "reviews"
        _create_review_file(
            reviews_dir,
            "disabled-review.md",
            """---
name: Disabled Review
paths:
  - "**/*.py"
marker: <!-- disabled -->
enabled: false
---
This review is disabled.
""",
        )

        result = runner.invoke(
            discover_reviews,
            ["--pr-number", "123"],
            obj=ErkContext.for_test(github=fake_github, cwd=cwd),
        )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["reviews"]) == 0
        assert "disabled-review.md" in output["disabled"]


def test_discover_reviews_multiple_reviews_partial_match(tmp_path: Path) -> None:
    """Test discovery with multiple reviews where only some match."""
    # Only Python files changed
    fake_github = FakeGitHub(
        pr_changed_files={123: ["src/main.py", "lib/utils.py"]},
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        reviews_dir = cwd / ".claude" / "reviews"

        # Python review
        _create_review_file(
            reviews_dir,
            "python-review.md",
            """---
name: Python Review
paths:
  - "**/*.py"
marker: <!-- python -->
---
Python review.
""",
        )

        # JavaScript review
        _create_review_file(
            reviews_dir,
            "js-review.md",
            """---
name: JavaScript Review
paths:
  - "**/*.js"
  - "**/*.ts"
marker: <!-- javascript -->
---
JavaScript review.
""",
        )

        result = runner.invoke(
            discover_reviews,
            ["--pr-number", "123"],
            obj=ErkContext.for_test(github=fake_github, cwd=cwd),
        )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["reviews"]) == 1
        assert output["reviews"][0]["name"] == "Python Review"
        assert "js-review.md" in output["skipped"]


def test_discover_reviews_matrix_format(tmp_path: Path) -> None:
    """Test that matrix output is correctly formatted for GitHub Actions."""
    fake_github = FakeGitHub(
        pr_changed_files={123: ["any/file.txt"]},
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        reviews_dir = cwd / ".claude" / "reviews"
        _create_review_file(
            reviews_dir,
            "review-a.md",
            """---
name: Review A
paths:
  - "**/*"
marker: <!-- a -->
---
Review A.
""",
        )
        _create_review_file(
            reviews_dir,
            "review-b.md",
            """---
name: Review B
paths:
  - "**/*"
marker: <!-- b -->
---
Review B.
""",
        )

        result = runner.invoke(
            discover_reviews,
            ["--pr-number", "123"],
            obj=ErkContext.for_test(github=fake_github, cwd=cwd),
        )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output)
        assert "matrix" in output
        assert "include" in output["matrix"]
        assert len(output["matrix"]["include"]) == 2

        # Verify matrix entries have required fields
        for entry in output["matrix"]["include"]:
            assert "name" in entry
            assert "filename" in entry


def test_discover_reviews_no_reviews_directory(tmp_path: Path) -> None:
    """Test behavior when reviews directory doesn't exist."""
    # Don't create any reviews directory
    fake_github = FakeGitHub(
        pr_changed_files={123: ["file.py"]},
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        result = runner.invoke(
            discover_reviews,
            ["--pr-number", "123"],
            obj=ErkContext.for_test(github=fake_github, cwd=cwd),
        )

        # Should succeed with empty reviews when directory doesn't exist
        assert result.exit_code == 0, result.output
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["reviews"]) == 0


def test_discover_reviews_custom_reviews_dir(tmp_path: Path) -> None:
    """Test using custom reviews directory."""
    fake_github = FakeGitHub(
        pr_changed_files={123: ["src/main.py"]},
    )

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        # Create reviews in custom location
        reviews_dir = cwd / ".github" / "reviews"
        _create_review_file(
            reviews_dir,
            "custom-review.md",
            """---
name: Custom Review
paths:
  - "**/*.py"
marker: <!-- custom -->
---
Custom review.
""",
        )

        result = runner.invoke(
            discover_reviews,
            ["--pr-number", "123", "--reviews-dir", ".github/reviews"],
            obj=ErkContext.for_test(github=fake_github, cwd=cwd),
        )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["reviews"]) == 1
        assert output["reviews"][0]["name"] == "Custom Review"
