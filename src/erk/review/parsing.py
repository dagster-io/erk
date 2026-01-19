"""Parsing and validation for review definition files.

Review definitions are markdown files with YAML frontmatter that define
code review behavior. This module handles parsing and validation using Pydantic.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import frontmatter
import pathspec
from pydantic import BaseModel, ConfigDict, field_validator

# Default values for optional frontmatter fields
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_TIMEOUT_MINUTES = 30
DEFAULT_ALLOWED_TOOLS = "Bash(gh:*),Bash(erk exec:*),Bash(TZ=*),Read(*)"
DEFAULT_ENABLED = True

MARKER_PATTERN = re.compile(r"^<!--\s+.+\s+-->$")


class ReviewFrontmatter(BaseModel):
    """Parsed frontmatter from a review definition file.

    Required fields:
        name: Human-readable review name (e.g., "Tripwires Review")
        paths: Glob patterns for files to review (e.g., ["**/*.py"])
        marker: HTML comment marker for summary updates (e.g., "<!-- tripwires-review -->")

    Optional fields with defaults:
        model: Claude model to use (default: "claude-sonnet-4-5")
        timeout_minutes: Workflow timeout (default: 30)
        allowed_tools: Claude Code allowed tools pattern
        enabled: Whether this review is active (default: True)
    """

    model_config = ConfigDict(frozen=True)

    name: str
    paths: tuple[str, ...]
    marker: str
    model: str = DEFAULT_MODEL
    timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES
    allowed_tools: str = DEFAULT_ALLOWED_TOOLS
    enabled: bool = DEFAULT_ENABLED

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("paths", mode="before")
    @classmethod
    def validate_paths(cls, v: object) -> tuple[str, ...]:
        if not isinstance(v, list):
            raise ValueError("must be a list")
        if len(v) == 0:
            raise ValueError("must not be empty")
        validated: list[str] = []
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"paths[{i}] must be a string")
            if not item:
                raise ValueError(f"paths[{i}] must not be empty")
            validated.append(item)
        return tuple(validated)

    @field_validator("marker")
    @classmethod
    def validate_marker(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be empty")
        if not MARKER_PATTERN.match(v):
            raise ValueError(f"must be an HTML comment (<!-- ... -->), got: {v}")
        return v


@dataclass(frozen=True)
class ParsedReview:
    """A fully parsed review definition.

    Combines the frontmatter metadata with the markdown body that contains
    the review instructions.
    """

    frontmatter: ReviewFrontmatter
    body: str
    filename: str


@dataclass(frozen=True)
class ReviewValidationResult:
    """Result of validating a review definition file.

    If is_valid is True, parsed_review contains the parsed review.
    If is_valid is False, errors contains the validation failures.
    """

    filename: str
    parsed_review: ParsedReview | None
    errors: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        """Return True if validation passed."""
        return len(self.errors) == 0


@dataclass(frozen=True)
class DiscoveryResult:
    """Result of discovering reviews matching a PR's changed files.

    Contains:
        reviews: Reviews that match at least one changed file
        skipped: Review filenames that matched no files
        disabled: Review filenames with enabled: false
        errors: Validation errors keyed by filename
    """

    reviews: tuple[ParsedReview, ...]
    skipped: tuple[str, ...]
    disabled: tuple[str, ...]
    errors: dict[str, tuple[str, ...]]


def _parse_frontmatter(content: str) -> tuple[dict[str, object] | None, str | None, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: The markdown file content.

    Returns:
        Tuple of (parsed_dict, error_message, body_text).
        If parsing fails, parsed_dict is None and error_message describes the issue.
        body_text is the content after the frontmatter.
    """
    has_frontmatter_delimiters = content.startswith("---")

    try:
        post = frontmatter.loads(content)
    except Exception as e:
        return None, f"Invalid YAML: {e}", content

    if not isinstance(post.metadata, dict):
        return None, "Frontmatter is not a valid YAML mapping", post.content

    if not post.metadata:
        if has_frontmatter_delimiters:
            return None, "Frontmatter is not a valid YAML mapping", post.content
        return None, "No frontmatter found", content

    return dict(post.metadata), None, post.content


def parse_review_file(file_path: Path) -> ReviewValidationResult:
    """Parse and validate a single review definition file.

    Args:
        file_path: Path to the review markdown file.

    Returns:
        Validation result with parsed review if successful.
    """
    filename = file_path.name

    if not file_path.exists():
        return ReviewValidationResult(
            filename=filename,
            parsed_review=None,
            errors=("File does not exist",),
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return ReviewValidationResult(
            filename=filename,
            parsed_review=None,
            errors=(f"Cannot read file: {e}",),
        )

    parsed, parse_error, body = _parse_frontmatter(content)
    if parse_error is not None:
        return ReviewValidationResult(
            filename=filename,
            parsed_review=None,
            errors=(parse_error,),
        )

    assert parsed is not None

    # Validate using Pydantic
    try:
        fm = ReviewFrontmatter.model_validate(parsed)
    except Exception as e:
        # Extract validation errors from Pydantic
        errors = _extract_pydantic_errors(e)
        return ReviewValidationResult(
            filename=filename,
            parsed_review=None,
            errors=tuple(errors),
        )

    return ReviewValidationResult(
        filename=filename,
        parsed_review=ParsedReview(
            frontmatter=fm,
            body=body.strip(),
            filename=filename,
        ),
        errors=(),
    )


def _extract_pydantic_errors(exc: Exception) -> list[str]:
    """Extract human-readable error messages from Pydantic validation exception."""
    from pydantic import ValidationError

    if not isinstance(exc, ValidationError):
        return [str(exc)]

    errors: list[str] = []
    for error in exc.errors():
        loc = error.get("loc", ())
        msg = error.get("msg", "validation error")
        # Build field path
        field_path = ".".join(str(part) for part in loc)
        if field_path:
            # Handle missing field vs validation error
            if error.get("type") == "missing":
                errors.append(f"Missing required field: {field_path}")
            else:
                errors.append(f"Field '{field_path}' {msg}")
        else:
            errors.append(msg)
    return errors


def discover_review_files(reviews_dir: Path) -> list[Path]:
    """Discover all review definition files in a directory.

    Args:
        reviews_dir: Path to the reviews directory (e.g., .github/reviews/).

    Returns:
        List of paths to markdown files, sorted alphabetically.
    """
    if not reviews_dir.exists():
        return []

    files = [f for f in reviews_dir.glob("*.md") if f.is_file()]
    return sorted(files)


def _matches_any_path(
    *,
    filename: str,
    review_paths: tuple[str, ...],
) -> bool:
    """Check if a filename matches any of the review path patterns.

    Uses pathspec for proper gitignore-style glob matching, including
    support for ** patterns.

    Args:
        filename: File path to check.
        review_paths: Glob patterns to match against.

    Returns:
        True if the file matches at least one pattern.
    """
    spec = pathspec.PathSpec.from_lines("gitwildmatch", review_paths)
    return spec.match_file(filename)


def check_duplicate_markers(reviews: list[ParsedReview]) -> dict[str, list[str]]:
    """Check for duplicate markers across review definitions.

    Args:
        reviews: List of parsed reviews.

    Returns:
        Dict mapping duplicate markers to list of filenames that use them.
        Empty dict if no duplicates.
    """
    marker_to_files: dict[str, list[str]] = {}
    for review in reviews:
        marker = review.frontmatter.marker
        if marker not in marker_to_files:
            marker_to_files[marker] = []
        marker_to_files[marker].append(review.filename)

    return {marker: files for marker, files in marker_to_files.items() if len(files) > 1}


def discover_matching_reviews(
    *,
    reviews_dir: Path,
    changed_files: list[str],
) -> DiscoveryResult:
    """Discover reviews that match the PR's changed files.

    Parses all review files, validates them, checks for duplicate markers,
    and returns reviews whose path patterns match at least one changed file.

    Args:
        reviews_dir: Path to the reviews directory.
        changed_files: List of file paths changed in the PR.

    Returns:
        DiscoveryResult with matching reviews, skipped reviews, and errors.
    """
    review_files = discover_review_files(reviews_dir)

    valid_reviews: list[ParsedReview] = []
    disabled_filenames: list[str] = []
    errors: dict[str, tuple[str, ...]] = {}

    for review_file in review_files:
        result = parse_review_file(review_file)

        if not result.is_valid:
            errors[result.filename] = result.errors
            continue

        assert result.parsed_review is not None

        if not result.parsed_review.frontmatter.enabled:
            disabled_filenames.append(result.filename)
            continue

        valid_reviews.append(result.parsed_review)

    # Check for duplicate markers among valid, enabled reviews
    duplicates = check_duplicate_markers(valid_reviews)
    if duplicates:
        for marker, files in duplicates.items():
            error_msg = f"Duplicate marker {marker} used by: {', '.join(files)}"
            for filename in files:
                if filename not in errors:
                    errors[filename] = ()
                errors[filename] = (*errors[filename], error_msg)

        # Filter out reviews with duplicate markers
        duplicate_files = {f for files in duplicates.values() for f in files}
        valid_reviews = [r for r in valid_reviews if r.filename not in duplicate_files]

    # Match reviews against changed files
    matching_reviews: list[ParsedReview] = []
    skipped_filenames: list[str] = []

    for review in valid_reviews:
        has_match = False
        for changed_file in changed_files:
            if _matches_any_path(
                filename=changed_file,
                review_paths=review.frontmatter.paths,
            ):
                has_match = True
                break

        if has_match:
            matching_reviews.append(review)
        else:
            skipped_filenames.append(review.filename)

    return DiscoveryResult(
        reviews=tuple(matching_reviews),
        skipped=tuple(skipped_filenames),
        disabled=tuple(disabled_filenames),
        errors=errors,
    )
