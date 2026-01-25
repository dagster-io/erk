"""Data types for Beads (bd) issue operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BeadsIssue:
    """Issue from Beads CLI (bd).

    Maps to bd JSON output format.

    Attributes:
        id: Hash-based ID (e.g., "bd-a1b2c3d4")
        title: Issue title
        description: Body content
        status: Issue status (open, in_progress, blocked, deferred, closed, tombstone)
        labels: Tuple of label strings (immutable for frozen dataclass)
        assignee: Single assignee (bd has no multi-assignee), None if unassigned
        notes: Free-form text (for metadata JSON)
        created_at: ISO format string from bd
        updated_at: ISO format string from bd
    """

    id: str
    title: str
    description: str
    status: str
    labels: tuple[str, ...]
    assignee: str | None
    notes: str
    created_at: str
    updated_at: str
