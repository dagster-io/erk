"""Tests for review definition parsing and validation."""

from pathlib import Path

from erk.review.parsing import (
    ParsedReview,
    ReviewFrontmatter,
    check_duplicate_markers,
    discover_matching_reviews,
    discover_review_files,
    parse_review_file,
)


def test_parse_valid_file(tmp_path: Path) -> None:
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


def test_parse_valid_full_frontmatter(tmp_path: Path) -> None:
    """Parse a review file with all optional fields."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
name: Custom Review
paths:
  - "**/*.py"
  - "**/*.sh"
marker: "<!-- custom-review -->"
model: claude-haiku-3
timeout_minutes: 15
allowed_tools: "Bash(git:*)"
enabled: false
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert result.is_valid
    assert result.parsed_review is not None
    fm = result.parsed_review.frontmatter
    assert fm.name == "Custom Review"
    assert fm.paths == ("**/*.py", "**/*.sh")
    assert fm.marker == "<!-- custom-review -->"
    assert fm.model == "claude-haiku-3"
    assert fm.timeout_minutes == 15
    assert fm.allowed_tools == "Bash(git:*)"
    assert fm.enabled is False


def test_parse_defaults(tmp_path: Path) -> None:
    """Parse a review file with only required fields, check defaults."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
name: Test Review
paths:
  - "**/*.py"
marker: "<!-- test -->"
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert result.is_valid
    assert result.parsed_review is not None
    fm = result.parsed_review.frontmatter
    assert fm.model == "claude-sonnet-4-5"
    assert fm.timeout_minutes == 30
    assert fm.enabled is True


def test_parse_nonexistent_file(tmp_path: Path) -> None:
    """Return error for nonexistent file."""
    review_file = tmp_path / "nonexistent.md"

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert "does not exist" in result.errors[0]


def test_parse_no_frontmatter(tmp_path: Path) -> None:
    """Return error when no frontmatter found."""
    review_file = tmp_path / "test.md"
    review_file.write_text("Just plain markdown.", encoding="utf-8")

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert "No frontmatter" in result.errors[0]


def test_parse_invalid_yaml(tmp_path: Path) -> None:
    """Return error for invalid YAML."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
name: [unclosed bracket
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert "Invalid YAML" in result.errors[0]


def test_parse_missing_name(tmp_path: Path) -> None:
    """Return error when name is missing."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
paths:
  - "**/*.py"
marker: "<!-- test -->"
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert any("name" in e.lower() for e in result.errors)


def test_parse_missing_paths(tmp_path: Path) -> None:
    """Return error when paths is missing."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
name: Test
marker: "<!-- test -->"
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert any("paths" in e.lower() for e in result.errors)


def test_parse_missing_marker(tmp_path: Path) -> None:
    """Return error when marker is missing."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
name: Test
paths:
  - "**/*.py"
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert any("marker" in e.lower() for e in result.errors)


def test_parse_empty_paths(tmp_path: Path) -> None:
    """Return error when paths is empty."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
name: Test
paths: []
marker: "<!-- test -->"
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert any("empty" in e.lower() for e in result.errors)


def test_parse_invalid_marker_format(tmp_path: Path) -> None:
    """Return error when marker is not an HTML comment."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
name: Test
paths:
  - "**/*.py"
marker: "not-a-comment"
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert any("html comment" in e.lower() for e in result.errors)


def test_parse_paths_not_list(tmp_path: Path) -> None:
    """Return error when paths is not a list."""
    review_file = tmp_path / "test.md"
    review_file.write_text(
        """\
---
name: Test
paths: "**/*.py"
marker: "<!-- test -->"
---

Body.
""",
        encoding="utf-8",
    )

    result = parse_review_file(review_file)

    assert not result.is_valid
    assert any("list" in e.lower() for e in result.errors)


def test_discover_files(tmp_path: Path) -> None:
    """Discover markdown files in directory."""
    reviews_dir = tmp_path / ".github" / "reviews"
    reviews_dir.mkdir(parents=True)

    (reviews_dir / "review-a.md").write_text("---\n---\n", encoding="utf-8")
    (reviews_dir / "review-b.md").write_text("---\n---\n", encoding="utf-8")
    (reviews_dir / "not-md.txt").write_text("ignored", encoding="utf-8")

    files = discover_review_files(reviews_dir)

    assert len(files) == 2
    assert all(f.suffix == ".md" for f in files)


def test_discover_empty_dir(tmp_path: Path) -> None:
    """Return empty list for empty directory."""
    reviews_dir = tmp_path / "empty"
    reviews_dir.mkdir()

    files = discover_review_files(reviews_dir)

    assert files == []


def test_discover_nonexistent_dir(tmp_path: Path) -> None:
    """Return empty list for nonexistent directory."""
    files = discover_review_files(tmp_path / "nonexistent")

    assert files == []


def _make_review(
    *,
    name: str,
    filename: str,
    marker: str,
) -> ParsedReview:
    """Create a ParsedReview for testing."""
    return ParsedReview(
        frontmatter=ReviewFrontmatter(
            name=name,
            paths=["**/*.py"],
            marker=marker,
        ),
        body="",
        filename=filename,
    )


def test_no_duplicate_markers() -> None:
    """Return empty dict when no duplicates."""
    reviews = [
        _make_review(name="A", filename="a.md", marker="<!-- a -->"),
        _make_review(name="B", filename="b.md", marker="<!-- b -->"),
    ]

    duplicates = check_duplicate_markers(reviews)

    assert duplicates == {}


def test_with_duplicate_markers() -> None:
    """Return dict mapping duplicate markers to filenames."""
    reviews = [
        _make_review(name="A", filename="a.md", marker="<!-- same -->"),
        _make_review(name="B", filename="b.md", marker="<!-- same -->"),
    ]

    duplicates = check_duplicate_markers(reviews)

    assert "<!-- same -->" in duplicates
    assert set(duplicates["<!-- same -->"]) == {"a.md", "b.md"}


def test_match_py_files(tmp_path: Path) -> None:
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


def test_skip_non_matching(tmp_path: Path) -> None:
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


def test_skip_disabled_reviews(tmp_path: Path) -> None:
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


def test_report_validation_errors(tmp_path: Path) -> None:
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


def test_report_duplicate_markers(tmp_path: Path) -> None:
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
    assert any("Duplicate" in e for e in result.errors["a.md"])


def test_multiple_path_patterns(tmp_path: Path) -> None:
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
