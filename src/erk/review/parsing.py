"""Parsing and validation for review definition files.

Review definitions are markdown files with YAML frontmatter that define
code review behavior. This module handles parsing and validation.
"""

import re
from collections.abc import Mapping
from pathlib import Path

import frontmatter
import pathspec

from erk.review.models import (
    DiscoveryResult,
    ParsedReview,
    ReviewFrontmatter,
    ReviewValidationResult,
)

MARKER_PATTERN = re.compile(r"^<!--\s+.+\s+-->$")

# Default values for optional frontmatter fields
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_TIMEOUT_MINUTES = 30
DEFAULT_ALLOWED_TOOLS = "Bash(gh:*),Bash(erk exec:*),Bash(TZ=*),Read(*)"
DEFAULT_ENABLED = True



def parse_frontmatter(content: str) -> tuple[dict[str, object] | None, str | None, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: The markdown file content.

    Returns:
        Tuple of (parsed_dict, error_message, body_text).
        If parsing fails, parsed_dict is None and error_message describes the issue.
        body_text is the content after the frontmatter.
    """
    # Check if content has frontmatter delimiters before parsing
    has_frontmatter_delimiters = content.startswith("---")

    try:
        post = frontmatter.loads(content)
    except Exception as e:
        return None, f"Invalid YAML: {e}", content

    # Check if metadata is a dict (frontmatter library stores non-dict YAML differently)
    if not isinstance(post.metadata, dict):
        return None, "Frontmatter is not a valid YAML mapping", post.content

    # Distinguish between "no frontmatter" vs "frontmatter was non-dict YAML"
    # When frontmatter library encounters non-dict YAML, it returns empty metadata
    if not post.metadata:
        if has_frontmatter_delimiters:
            return None, "Frontmatter is not a valid YAML mapping", post.content
        return None, "No frontmatter found", content

    return dict(post.metadata), None, post.content


def _validate_paths(paths_data: object) -> tuple[tuple[str, ...], list[str]]:
    """Validate the paths field from frontmatter.

    Args:
        paths_data: Raw paths data from YAML.

    Returns:
        Tuple of (paths, errors).
    """
    errors: list[str] = []
    paths: list[str] = []

    if not isinstance(paths_data, list):
        errors.append("Field 'paths' must be a list")
        return (), errors

    if len(paths_data) == 0:
        errors.append("Field 'paths' must not be empty")
        return (), errors

    for i, item in enumerate(paths_data):
        if not isinstance(item, str):
            errors.append(f"Field 'paths[{i}]' must be a string")
            continue
        if not item:
            errors.append(f"Field 'paths[{i}]' must not be empty")
            continue
        paths.append(item)

    return tuple(paths), errors


def _validate_marker(marker: object) -> tuple[str | None, list[str]]:
    """Validate the marker field.

    Markers must be HTML comments of the form <!-- ... -->.

    Args:
        marker: Raw marker data from YAML.

    Returns:
        Tuple of (validated_marker, errors).
    """
    errors: list[str] = []

    if not isinstance(marker, str):
        errors.append("Field 'marker' must be a string")
        return None, errors

    if not marker:
        errors.append("Field 'marker' must not be empty")
        return None, errors

    if not MARKER_PATTERN.match(marker):
        errors.append(f"Field 'marker' must be an HTML comment (<!-- ... -->), got: {marker}")
        return None, errors

    return marker, errors


def validate_review_frontmatter(
    data: Mapping[str, object],
) -> tuple[ReviewFrontmatter | None, list[str]]:
    """Validate parsed frontmatter against the review schema.

    Args:
        data: Parsed YAML dictionary.

    Returns:
        Tuple of (frontmatter, errors). If validation succeeds,
        errors is empty. If validation fails, frontmatter is None.
    """
    errors: list[str] = []

    # Required: name
    name = data.get("name")
    if not name:
        errors.append("Missing required field: name")
    elif not isinstance(name, str):
        errors.append("Field 'name' must be a string")

    # Required: paths
    paths_data = data.get("paths")
    if paths_data is None:
        errors.append("Missing required field: paths")
        paths: tuple[str, ...] = ()
    else:
        paths, path_errors = _validate_paths(paths_data)
        errors.extend(path_errors)

    # Required: marker
    marker_data = data.get("marker")
    if marker_data is None:
        errors.append("Missing required field: marker")
        marker: str | None = None
    else:
        marker, marker_errors = _validate_marker(marker_data)
        errors.extend(marker_errors)

    # Optional: model (default: claude-sonnet-4-5)
    model = data.get("model", DEFAULT_MODEL)
    if not isinstance(model, str):
        errors.append("Field 'model' must be a string")
        model = DEFAULT_MODEL

    # Optional: timeout_minutes (default: 30)
    timeout_minutes = data.get("timeout_minutes", DEFAULT_TIMEOUT_MINUTES)
    if not isinstance(timeout_minutes, int):
        errors.append("Field 'timeout_minutes' must be an integer")
        timeout_minutes = DEFAULT_TIMEOUT_MINUTES

    # Optional: allowed_tools (default: standard set)
    allowed_tools = data.get("allowed_tools", DEFAULT_ALLOWED_TOOLS)
    if not isinstance(allowed_tools, str):
        errors.append("Field 'allowed_tools' must be a string")
        allowed_tools = DEFAULT_ALLOWED_TOOLS

    # Optional: enabled (default: true)
    enabled = data.get("enabled", DEFAULT_ENABLED)
    if not isinstance(enabled, bool):
        errors.append("Field 'enabled' must be a boolean")
        enabled = DEFAULT_ENABLED

    if errors:
        return None, errors

    # Type narrowing: at this point all required fields are valid
    assert isinstance(name, str)
    assert marker is not None

    return ReviewFrontmatter(
        name=name,
        paths=paths,
        marker=marker,
        model=model,
        timeout_minutes=timeout_minutes,
        allowed_tools=allowed_tools,
        enabled=enabled,
    ), []


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

    parsed, parse_error, body = parse_frontmatter(content)
    if parse_error is not None:
        return ReviewValidationResult(
            filename=filename,
            parsed_review=None,
            errors=(parse_error,),
        )

    assert parsed is not None
    frontmatter_result, validation_errors = validate_review_frontmatter(parsed)

    if validation_errors:
        return ReviewValidationResult(
            filename=filename,
            parsed_review=None,
            errors=tuple(validation_errors),
        )

    assert frontmatter_result is not None
    return ReviewValidationResult(
        filename=filename,
        parsed_review=ParsedReview(
            frontmatter=frontmatter_result,
            body=body.strip(),
            filename=filename,
        ),
        errors=(),
    )


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
