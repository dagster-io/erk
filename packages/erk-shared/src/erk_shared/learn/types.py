"""Type definitions for the learn feature."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LearnResult:
    """Result of capturing documentation for learning.

    Attributes:
        success: Whether the capture completed successfully
        issue_url: Full GitHub URL of the created erk-learn issue (None on failure)
        issue_number: GitHub issue number (None on failure)
        error: Error message if failed, None if success
    """

    success: bool
    issue_url: str | None
    issue_number: int | None
    error: str | None
