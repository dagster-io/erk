"""Core types for the objectives system.

These dataclasses define the structure of objectives and their associated data.
All types are frozen (immutable) for safety and hashability.
"""

from dataclasses import dataclass
from enum import Enum


class ObjectiveType(Enum):
    """Discriminator for objective behavior.

    - COMPLETABLE: Finite end state (e.g., "migrate all errors to Ensure class")
    - PERPETUAL: Ongoing guard (e.g., "no direct time.sleep() calls")
    """

    COMPLETABLE = "completable"
    PERPETUAL = "perpetual"


@dataclass(frozen=True)
class ObjectiveDefinition:
    """Parsed objective definition from README.md.

    Contains all the static configuration for an objective, including
    evaluation prompts and scope constraints.
    """

    name: str
    objective_type: ObjectiveType
    desired_state: str
    rationale: str
    examples: list[str]
    scope_includes: list[str]
    scope_excludes: list[str]
    evaluation_prompt: str
    plan_sizing_prompt: str


@dataclass(frozen=True)
class NoteEntry:
    """A single knowledge entry accumulated from a previous turn.

    Notes capture insights discovered during evaluation that should
    inform future turns.
    """

    timestamp: str  # ISO 8601 format
    content: str
    source_turn: str | None = None  # Reference to the turn that generated this note


@dataclass(frozen=True)
class ObjectiveNotes:
    """Accumulated knowledge from previous turns.

    Notes.md stores patterns, edge cases, and insights discovered
    during objective evaluation.
    """

    entries: list[NoteEntry]


@dataclass(frozen=True)
class TurnResult:
    """Result of running a turn.

    Captures whether a gap was found and any resulting plan.
    """

    objective_name: str
    gap_found: bool
    gap_description: str | None
    plan_issue_number: int | None
    plan_issue_url: str | None
    timestamp: str  # ISO 8601 format


@dataclass(frozen=True)
class WorkLogEntry:
    """A single entry in the work log.

    Work log provides chronological observability into objective turns.
    """

    timestamp: str  # ISO 8601 format
    event_type: str  # "turn_started", "turn_completed", "plan_created", etc.
    summary: str
    details: dict[str, str | int | bool | None] | None = None
