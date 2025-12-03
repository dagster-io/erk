"""Shared test fixtures for GT operations tests."""

from collections.abc import Generator
from typing import TypeVar

from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent

T = TypeVar("T")


def collect_events[T](
    generator: Generator[ProgressEvent | CompletionEvent[T]],
) -> tuple[list[ProgressEvent], T]:
    """Collect progress events and final result from operation generator.

    Args:
        generator: Generator that yields ProgressEvent and ends with CompletionEvent

    Returns:
        Tuple of (list of progress events, final result from CompletionEvent)

    Raises:
        RuntimeError: If no CompletionEvent is yielded
    """
    progress_events = []
    for event in generator:
        if isinstance(event, ProgressEvent):
            progress_events.append(event)
        elif isinstance(event, CompletionEvent):
            return progress_events, event.result
    raise RuntimeError("No completion event")


def has_event_containing(events: list[ProgressEvent], substring: str) -> bool:
    """Check if any event message contains the given substring.

    Args:
        events: List of ProgressEvent to search
        substring: Substring to find in event messages

    Returns:
        True if any event message contains the substring
    """
    return any(substring in event.message for event in events)


def get_event_containing(events: list[ProgressEvent], substring: str) -> ProgressEvent | None:
    """Get the first event whose message contains the given substring.

    Args:
        events: List of ProgressEvent to search
        substring: Substring to find in event messages

    Returns:
        The first matching event, or None if not found
    """
    for event in events:
        if substring in event.message:
            return event
    return None
