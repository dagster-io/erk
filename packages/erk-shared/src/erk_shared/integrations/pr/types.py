"""Type definitions for unified PR submission operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CoreSubmitResult:
    """Result from core PR submission (git push + gh pr create).

    This represents a successful PR creation/update via standard git + gh.
    The PR exists on GitHub and is ready for optional Graphite enhancement.
    """

    success: bool
    pr_number: int
    pr_url: str
    branch_name: str
    issue_number: int | None
    was_created: bool  # True if PR was created, False if updated existing PR
    message: str


@dataclass(frozen=True)
class CoreSubmitError:
    """Error from core PR submission."""

    success: bool  # Always False
    error_type: str
    message: str
    details: dict[str, str]


@dataclass(frozen=True)
class GraphiteEnhanceResult:
    """Result from Graphite enhancement (gt submit on existing PR)."""

    success: bool
    graphite_url: str
    message: str


@dataclass(frozen=True)
class GraphiteEnhanceError:
    """Error from Graphite enhancement."""

    success: bool  # Always False
    error_type: str
    message: str
    details: dict[str, str]


@dataclass(frozen=True)
class GraphiteSkipped:
    """Result when Graphite enhancement was skipped.

    This is a success case - used when Graphite is not available or
    the user requested --no-graphite.
    """

    success: bool  # Always True
    reason: str  # "not_authenticated", "not_tracked", "user_skipped"
    message: str
