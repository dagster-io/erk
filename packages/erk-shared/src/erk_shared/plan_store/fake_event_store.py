"""In-memory fake implementation for plan event storage."""

from pathlib import Path

from erk_shared.plan_store.event_store import PlanEvent, PlanEventStore, PlanEventType


class FakePlanEventStore(PlanEventStore):
    """In-memory fake implementation for testing.

    Stores events in memory, keyed by plan_identifier.
    Provides test helper properties for assertions.
    """

    def __init__(self) -> None:
        """Create FakePlanEventStore with empty event storage."""
        # plan_identifier -> list of events
        self._events: dict[str, list[PlanEvent]] = {}

    @property
    def all_events(self) -> dict[str, list[PlanEvent]]:
        """Read-only access to all events for test assertions.

        Returns:
            Mapping of plan_identifier to list of events
        """
        return self._events

    def append_event(
        self,
        repo_root: Path,
        plan_identifier: str,
        event: PlanEvent,
    ) -> None:
        """Append event to in-memory list.

        Args:
            repo_root: Repository root directory (ignored in fake)
            plan_identifier: Plan identifier
            event: Event to append
        """
        if plan_identifier not in self._events:
            self._events[plan_identifier] = []
        self._events[plan_identifier].append(event)

    def get_events(
        self,
        repo_root: Path,
        plan_identifier: str,
        event_types: list[PlanEventType] | None = None,
    ) -> list[PlanEvent]:
        """Get events from memory.

        Args:
            repo_root: Repository root directory (ignored in fake)
            plan_identifier: Plan identifier
            event_types: Optional filter (None = all events)

        Returns:
            List of events sorted chronologically (oldest first)
        """
        events = self._events.get(plan_identifier, [])
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        return sorted(events, key=lambda e: e.timestamp)

    def get_latest_event(
        self,
        repo_root: Path,
        plan_identifier: str,
        event_type: PlanEventType | None = None,
    ) -> PlanEvent | None:
        """Get most recent event.

        Args:
            repo_root: Repository root directory (ignored in fake)
            plan_identifier: Plan identifier
            event_type: Optional filter (None = any event type)

        Returns:
            Most recent event matching criteria, or None if no events
        """
        filter_types = [event_type] if event_type else None
        events = self.get_events(repo_root, plan_identifier, filter_types)
        return events[-1] if events else None
