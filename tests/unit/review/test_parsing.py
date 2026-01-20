"""Tests for review definition parsing and validation."""

from pathlib import Path

from erk.review.models import ParsedReview, ReviewFrontmatter
from erk.review.parsing import (
    check_duplicate_markers,
    discover_matching_reviews,
    discover_review_files,
    parse_frontmatter,
    parse_review_file,
    validate_review_frontmatter,
)


class TestParseFrontmatter:
    """Tests for frontmatter parsing."""

    def test_valid_frontmatter(self) -> None:
        """Parse valid YAML frontmatter from markdown."""
        content = """\
---
name: Test Review
paths:
  - "**/*.py"
marker: "<!-- test -->"
---

Body content here.
"""
        parsed, error, body = parse_frontmatter(content)

        assert error is None
        assert parsed is not None
        assert parsed["name"] == "Test Review"
        assert parsed["paths"] == ["**/*.py"]
        assert parsed["marker"] == "<!-- test -->"
        assert body.strip() == "Body content here."

    def test_no_frontmatter(self) -> None:
        """Return error when no frontmatter found."""
        content = "Just plain markdown without frontmatter."

        parsed, error, body = parse_frontmatter(content)

        assert parsed is None
        assert error == "No frontmatter found"
        assert body == content

    def test_invalid_yaml(self) -> None:
        """Return error for invalid YAML."""
        content = """\
---
name: [unclosed bracket
---

Body.
"""
        parsed, error, body = parse_frontmatter(content)

        assert parsed is None
        assert "Invalid YAML" in str(error)

    def test_non_dict_frontmatter(self) -> None:
        """Return error when frontmatter is not a dict."""
        content = """\
---
- just
- a
- list
---

Body.
"""
        parsed, error, body = parse_frontmatter(content)

        assert parsed is None
        assert "not a valid YAML mapping" in str(error)


class TestValidateReviewFrontmatter:
    """Tests for frontmatter validation."""

    def test_valid_minimal_frontmatter(self) -> None:
        """Validate frontmatter with only required fields."""
        data = {
            "name": "Test Review",
            "paths": ["**/*.py"],
            "marker": "<!-- test -->",
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert len(errors) == 0
        assert frontmatter is not None
        assert frontmatter.name == "Test Review"
        assert frontmatter.paths == ("**/*.py",)
        assert frontmatter.marker == "<!-- test -->"
        # Check defaults
        assert frontmatter.provider == "claude"
        assert frontmatter.model == "claude-sonnet-4-5"
        assert frontmatter.timeout_minutes == 30
        assert frontmatter.enabled is True

    def test_valid_full_frontmatter(self) -> None:
        """Validate frontmatter with all fields specified."""
        data = {
            "name": "Custom Review",
            "paths": ["**/*.py", "**/*.sh"],
            "marker": "<!-- custom-review -->",
            "provider": "codex",
            "model": "gpt-5-codex",
            "timeout_minutes": 15,
            "allowed_tools": "Bash(git:*)",
            "enabled": False,
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert len(errors) == 0
        assert frontmatter is not None
        assert frontmatter.name == "Custom Review"
        assert frontmatter.paths == ("**/*.py", "**/*.sh")
        assert frontmatter.marker == "<!-- custom-review -->"
        assert frontmatter.provider == "codex"
        assert frontmatter.model == "gpt-5-codex"
        assert frontmatter.timeout_minutes == 15
        assert frontmatter.allowed_tools == "Bash(git:*)"
        assert frontmatter.enabled is False

    def test_missing_name(self) -> None:
        """Return error when name is missing."""
        data = {
            "paths": ["**/*.py"],
            "marker": "<!-- test -->",
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert frontmatter is None
        assert any("name" in e for e in errors)

    def test_missing_paths(self) -> None:
        """Return error when paths is missing."""
        data = {
            "name": "Test",
            "marker": "<!-- test -->",
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert frontmatter is None
        assert any("paths" in e for e in errors)

    def test_missing_marker(self) -> None:
        """Return error when marker is missing."""
        data = {
            "name": "Test",
            "paths": ["**/*.py"],
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert frontmatter is None
        assert any("marker" in e for e in errors)

    def test_empty_paths(self) -> None:
        """Return error when paths is empty."""
        data = {
            "name": "Test",
            "paths": [],
            "marker": "<!-- test -->",
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert frontmatter is None
        assert any("empty" in e for e in errors)

    def test_invalid_marker_format(self) -> None:
        """Return error when marker is not an HTML comment."""
        data = {
            "name": "Test",
            "paths": ["**/*.py"],
            "marker": "not-a-comment",
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert frontmatter is None
        assert any("HTML comment" in e for e in errors)

    def test_paths_not_list(self) -> None:
        """Return error when paths is not a list."""
        data = {
            "name": "Test",
            "paths": "**/*.py",
            "marker": "<!-- test -->",
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert frontmatter is None
        assert any("must be a list" in e for e in errors)

    def test_invalid_provider(self) -> None:
        """Return error when provider is not valid."""
        data = {
            "name": "Test",
            "paths": ["**/*.py"],
            "marker": "<!-- test -->",
            "provider": "invalid-provider",
        }

        frontmatter, errors = validate_review_frontmatter(data)

        assert frontmatter is None
        assert any("Invalid provider" in e for e in errors)
        assert any("invalid-provider" in e for e in errors)


class TestParseReviewFile:
    """Tests for parsing review files from disk."""

    def test_parse_valid_file(self, tmp_path: Path) -> None:
        """Parse a valid review file."""
        review_file = tmp_path / "test.md"
        review_file.write_text(
            """\
---
name: Test Review
paths:
  - "**/*.py"
marker: "<!-- test -->"
---

Review instructions here.
""",
            encoding="utf-8",
        )

        result = parse_review_file(review_file)

        assert result.is_valid
        assert result.errors == ()
        assert result.parsed_review is not None
        assert result.parsed_review.frontmatter.name == "Test Review"
        assert result.parsed_review.body == "Review instructions here."
        assert result.parsed_review.filename == "test.md"

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        """Return error for nonexistent file."""
        review_file = tmp_path / "nonexistent.md"

        result = parse_review_file(review_file)

        assert not result.is_valid
        assert "does not exist" in result.errors[0]

    def test_parse_invalid_frontmatter(self, tmp_path: Path) -> None:
        """Return errors for invalid frontmatter."""
        review_file = tmp_path / "invalid.md"
        review_file.write_text(
            """\
---
name: Test
# Missing required fields
---

Body.
""",
            encoding="utf-8",
        )

        result = parse_review_file(review_file)

        assert not result.is_valid
        assert len(result.errors) > 0


class TestDiscoverReviewFiles:
    """Tests for discovering review files in a directory."""

    def test_discover_files(self, tmp_path: Path) -> None:
        """Discover markdown files in directory."""
        reviews_dir = tmp_path / ".github" / "reviews"
        reviews_dir.mkdir(parents=True)

        (reviews_dir / "review-a.md").write_text("---\n---\n", encoding="utf-8")
        (reviews_dir / "review-b.md").write_text("---\n---\n", encoding="utf-8")
        (reviews_dir / "not-md.txt").write_text("ignored", encoding="utf-8")

        files = discover_review_files(reviews_dir)

        assert len(files) == 2
        assert all(f.suffix == ".md" for f in files)

    def test_discover_empty_dir(self, tmp_path: Path) -> None:
        """Return empty list for empty directory."""
        reviews_dir = tmp_path / "empty"
        reviews_dir.mkdir()

        files = discover_review_files(reviews_dir)

        assert files == []

    def test_discover_nonexistent_dir(self, tmp_path: Path) -> None:
        """Return empty list for nonexistent directory."""
        files = discover_review_files(tmp_path / "nonexistent")

        assert files == []


class TestCheckDuplicateMarkers:
    """Tests for duplicate marker detection."""

    def test_no_duplicates(self) -> None:
        """Return empty dict when no duplicates."""
        reviews = [
            ParsedReview(
                frontmatter=ReviewFrontmatter(
                    name="A",
                    paths=("**/*.py",),
                    marker="<!-- a -->",
                    provider="claude",
                    model="claude-sonnet-4-5",
                    timeout_minutes=30,
                    allowed_tools="Read(*)",
                    enabled=True,
                ),
                body="",
                filename="a.md",
            ),
            ParsedReview(
                frontmatter=ReviewFrontmatter(
                    name="B",
                    paths=("**/*.py",),
                    marker="<!-- b -->",
                    provider="claude",
                    model="claude-sonnet-4-5",
                    timeout_minutes=30,
                    allowed_tools="Read(*)",
                    enabled=True,
                ),
                body="",
                filename="b.md",
            ),
        ]

        duplicates = check_duplicate_markers(reviews)

        assert duplicates == {}

    def test_with_duplicates(self) -> None:
        """Return dict mapping duplicate markers to filenames."""
        reviews = [
            ParsedReview(
                frontmatter=ReviewFrontmatter(
                    name="A",
                    paths=("**/*.py",),
                    marker="<!-- same -->",
                    provider="claude",
                    model="claude-sonnet-4-5",
                    timeout_minutes=30,
                    allowed_tools="Read(*)",
                    enabled=True,
                ),
                body="",
                filename="a.md",
            ),
            ParsedReview(
                frontmatter=ReviewFrontmatter(
                    name="B",
                    paths=("**/*.py",),
                    marker="<!-- same -->",
                    provider="claude",
                    model="claude-sonnet-4-5",
                    timeout_minutes=30,
                    allowed_tools="Read(*)",
                    enabled=True,
                ),
                body="",
                filename="b.md",
            ),
        ]

        duplicates = check_duplicate_markers(reviews)

        assert "<!-- same -->" in duplicates
        assert set(duplicates["<!-- same -->"]) == {"a.md", "b.md"}


class TestDiscoverMatchingReviews:
    """Tests for discovering reviews matching changed files."""

    def test_match_py_files(self, tmp_path: Path) -> None:
        """Match review with *.py pattern to .py files."""
        reviews_dir = tmp_path / "reviews"
        reviews_dir.mkdir()

        (reviews_dir / "python.md").write_text(
            """\
---
name: Python Review
paths:
  - "**/*.py"
marker: "<!-- python -->"
---

Body.
""",
            encoding="utf-8",
        )

        result = discover_matching_reviews(
            reviews_dir=reviews_dir,
            changed_files=["src/main.py", "tests/test_main.py"],
        )

        assert len(result.reviews) == 1
        assert result.reviews[0].frontmatter.name == "Python Review"
        assert len(result.skipped) == 0
        assert len(result.disabled) == 0
        assert len(result.errors) == 0

    def test_skip_non_matching(self, tmp_path: Path) -> None:
        """Skip reviews that don't match any changed files."""
        reviews_dir = tmp_path / "reviews"
        reviews_dir.mkdir()

        (reviews_dir / "python.md").write_text(
            """\
---
name: Python Review
paths:
  - "**/*.py"
marker: "<!-- python -->"
---

Body.
""",
            encoding="utf-8",
        )

        result = discover_matching_reviews(
            reviews_dir=reviews_dir,
            changed_files=["README.md", "package.json"],  # No .py files
        )

        assert len(result.reviews) == 0
        assert "python.md" in result.skipped

    def test_skip_disabled_reviews(self, tmp_path: Path) -> None:
        """Skip reviews with enabled: false."""
        reviews_dir = tmp_path / "reviews"
        reviews_dir.mkdir()

        (reviews_dir / "disabled.md").write_text(
            """\
---
name: Disabled Review
paths:
  - "**/*.py"
marker: "<!-- disabled -->"
enabled: false
---

Body.
""",
            encoding="utf-8",
        )

        result = discover_matching_reviews(
            reviews_dir=reviews_dir,
            changed_files=["src/main.py"],
        )

        assert len(result.reviews) == 0
        assert "disabled.md" in result.disabled

    def test_report_validation_errors(self, tmp_path: Path) -> None:
        """Report validation errors for invalid review files."""
        reviews_dir = tmp_path / "reviews"
        reviews_dir.mkdir()

        (reviews_dir / "invalid.md").write_text(
            """\
---
name: Missing Fields
# No paths or marker
---

Body.
""",
            encoding="utf-8",
        )

        result = discover_matching_reviews(
            reviews_dir=reviews_dir,
            changed_files=["src/main.py"],
        )

        assert len(result.reviews) == 0
        assert "invalid.md" in result.errors
        assert len(result.errors["invalid.md"]) > 0

    def test_report_duplicate_markers(self, tmp_path: Path) -> None:
        """Report duplicate markers as errors."""
        reviews_dir = tmp_path / "reviews"
        reviews_dir.mkdir()

        for name in ["a.md", "b.md"]:
            (reviews_dir / name).write_text(
                f"""\
---
name: Review {name}
paths:
  - "**/*.py"
marker: "<!-- duplicate -->"
---

Body.
""",
                encoding="utf-8",
            )

        result = discover_matching_reviews(
            reviews_dir=reviews_dir,
            changed_files=["src/main.py"],
        )

        assert len(result.reviews) == 0
        assert "a.md" in result.errors
        assert "b.md" in result.errors
        # Both should have errors mentioning duplicate
        assert any("Duplicate" in e for e in result.errors["a.md"])

    def test_multiple_path_patterns(self, tmp_path: Path) -> None:
        """Match files against multiple path patterns."""
        reviews_dir = tmp_path / "reviews"
        reviews_dir.mkdir()

        (reviews_dir / "multi.md").write_text(
            """\
---
name: Multi Review
paths:
  - "**/*.py"
  - "**/*.sh"
marker: "<!-- multi -->"
---

Body.
""",
            encoding="utf-8",
        )

        # Test with .py file
        result = discover_matching_reviews(
            reviews_dir=reviews_dir,
            changed_files=["script.py"],
        )
        assert len(result.reviews) == 1

        # Test with .sh file
        result = discover_matching_reviews(
            reviews_dir=reviews_dir,
            changed_files=["deploy.sh"],
        )
        assert len(result.reviews) == 1

        # Test with non-matching file
        result = discover_matching_reviews(
            reviews_dir=reviews_dir,
            changed_files=["README.md"],
        )
        assert len(result.reviews) == 0
