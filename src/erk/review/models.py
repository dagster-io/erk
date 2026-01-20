"""Data models for code review definitions.

Review definitions are markdown files with YAML frontmatter that define
automated code review behavior. These models represent the parsed structure.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewFrontmatter:
    """Parsed frontmatter from a review definition file.

    Required fields:
        name: Human-readable review name (e.g., "Tripwires Review")
        paths: Glob patterns for files to review (e.g., ["**/*.py"])
        marker: HTML comment marker for summary updates (e.g., "<!-- tripwires-review -->")

    Optional fields with defaults:
        provider: AI provider to use for review (default: "claude")
        model: Model to use (default: "claude-sonnet-4-5")
        timeout_minutes: Workflow timeout (default: 30)
        allowed_tools: Claude Code allowed tools pattern
        enabled: Whether this review is active (default: True)
    """

    name: str
    paths: tuple[str, ...]
    marker: str
    provider: str
    model: str
    timeout_minutes: int
    allowed_tools: str
    enabled: bool


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
