"""Abstract interface for plan event storage providers.

Events are append-only - they cannot be modified or deleted.
This provides an audit trail for plan lifecycle events.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class PlanEventType(Enum):
    """Domain event types for plan lifecycle.

    These represent key moments in a plan's execution:
    - CREATED: Plan was created
    - QUEUED: Plan was submitted for remote execution
    - WORKFLOW_STARTED: Remote workflow began execution
    - PROGRESS: Implementation progress update
    - COMPLETED: Plan implementation finished successfully
    - FAILED: Plan implementation failed
    - RETRY: Plan was retried after failure
    - WORKTREE_CREATED: Local worktree was created for plan
    """

    CREATED = "created"
    QUEUED = "queued"
    WORKFLOW_STARTED = "workflow_started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    WORKTREE_CREATED = "worktree_created"


@dataclass(frozen=True)
class PlanEvent:
    """Provider-agnostic representation of a plan event.

    Events are immutable and ordered by timestamp.
    The data dict contains event-specific fields.

    Attributes:
        event_type: Type of event (from PlanEventType enum)
        timestamp: When the event occurred
        data: Event-specific fields (varies by event_type)

    Event Data Schemas by Type:

    QUEUED:
        - submitted_by: str (GitHub username)
        - workflow_name: str
        - workflow_run_id: str
        - workflow_url: str
        - validation_results: dict[str, bool]

    WORKFLOW_STARTED:
        - workflow_run_id: str
        - workflow_run_url: str
        - branch_name: str | None
        - worktree_path: str | None

    PROGRESS:
        - status: str ("starting" | "in_progress" | "complete" | "failed")
        - completed_steps: int
        - total_steps: int
        - step_description: str | None
        - worktree: str | None
        - branch: str | None

    WORKTREE_CREATED:
        - worktree_name: str
        - branch_name: str

    RETRY:
        - retry_count: int
        - triggered_by: str
    """

    event_type: PlanEventType
    timestamp: datetime
    data: dict[str, object]


class PlanEventStore(ABC):
    """Abstract interface for plan event operations.

    Events are append-only - they cannot be modified or deleted.
    This provides an audit trail for plan lifecycle events.
    """

    @abstractmethod
    def append_event(
        self,
        repo_root: Path,
        plan_identifier: str,
        event: PlanEvent,
    ) -> None:
        """Append an event to a plan's timeline.

        Args:
            repo_root: Repository root directory
            plan_identifier: Plan identifier
            event: Event to append

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def get_events(
        self,
        repo_root: Path,
        plan_identifier: str,
        event_types: list[PlanEventType] | None = None,
    ) -> list[PlanEvent]:
        """Get events for a plan, optionally filtered by type.

        Args:
            repo_root: Repository root directory
            plan_identifier: Plan identifier
            event_types: Optional filter (None = all events)

        Returns:
            List of events sorted chronologically (oldest first)

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...

    @abstractmethod
    def get_latest_event(
        self,
        repo_root: Path,
        plan_identifier: str,
        event_type: PlanEventType | None = None,
    ) -> PlanEvent | None:
        """Get the most recent event, optionally of a specific type.

        Args:
            repo_root: Repository root directory
            plan_identifier: Plan identifier
            event_type: Optional filter (None = any event type)

        Returns:
            Most recent event matching criteria, or None if no events

        Raises:
            RuntimeError: If provider fails or plan not found
        """
        ...
