"""Fake implementation of SlackListener for testing."""

from collections.abc import Iterator

from erk.slack.listener.abc import SlackListener
from erk.slack.types import SlackEvent


class FakeSlackListener(SlackListener):
    """Fake implementation that yields pre-configured events for testing.

    This implementation allows tests to control exactly which events
    are yielded, enabling deterministic testing of event handling logic.

    Example:
        >>> listener = FakeSlackListener()
        >>> listener.add_event(SlackEvent(event_type="app_mention", message=msg))
        >>> for event in listener.listen():
        ...     handle_event(event)
    """

    def __init__(self) -> None:
        """Initialize with empty event queue."""
        self._events: list[SlackEvent] = []
        self._stopped = False

    def add_event(self, event: SlackEvent) -> None:
        """Add an event to be yielded by listen().

        Args:
            event: The SlackEvent to add to the queue
        """
        self._events.append(event)

    def add_events(self, events: list[SlackEvent]) -> None:
        """Add multiple events to be yielded by listen().

        Args:
            events: List of SlackEvent objects to add
        """
        self._events.extend(events)

    def listen(self) -> Iterator[SlackEvent]:
        """Yield pre-configured events.

        Unlike the real implementation, this does not block. It simply
        yields all configured events and returns.

        Yields:
            SlackEvent objects that were added via add_event/add_events
        """
        for event in self._events:
            if self._stopped:
                break
            yield event

    def stop(self) -> None:
        """Mark the listener as stopped."""
        self._stopped = True

    @property
    def events_added(self) -> list[SlackEvent]:
        """Read-only access to events that were added.

        Returns:
            Copy of the events list
        """
        return list(self._events)
