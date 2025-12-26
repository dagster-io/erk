"""Unit tests for render_events function.

Tests the event rendering helper for consuming operation generators.
"""

from collections.abc import Generator
from typing import TypeVar
from unittest.mock import patch

import pytest

from erk_shared.gateway.gt.cli import render_events
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent

T = TypeVar("T")


def _create_event_generator(
    events: list[ProgressEvent | CompletionEvent[T]],
) -> Generator[ProgressEvent | CompletionEvent[T], None, None]:
    """Helper to create a generator from a list of events."""
    yield from events


def test_render_events_returns_completion_result() -> None:
    """Test render_events returns the result from CompletionEvent."""
    events = [
        ProgressEvent(message="Step 1", style="info"),
        CompletionEvent(result="success_value"),
    ]

    result = render_events(_create_event_generator(events))

    assert result == "success_value"


def test_render_events_raises_without_completion() -> None:
    """Test render_events raises RuntimeError when no CompletionEvent."""
    events: list[ProgressEvent | CompletionEvent[str]] = [
        ProgressEvent(message="Step 1", style="info"),
    ]

    with pytest.raises(RuntimeError, match="without completion"):
        render_events(_create_event_generator(events))


def test_render_events_renders_to_stderr() -> None:
    """Test render_events outputs progress messages to stderr."""
    events = [
        ProgressEvent(message="Progress message", style="info"),
        CompletionEvent(result="done"),
    ]

    with patch("erk_shared.gateway.gt.cli.click.echo") as mock_echo:
        render_events(_create_event_generator(events))

        # Should have called click.echo with err=True
        mock_echo.assert_called()
        call_kwargs = mock_echo.call_args[1]
        assert call_kwargs.get("err") is True
