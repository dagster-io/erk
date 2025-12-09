"""CLI utilities for GT operations.

Provides event rendering helpers for consuming operation generators.
"""

import sys
from collections.abc import Generator
from typing import TypeVar

import click

from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent

T = TypeVar("T")

# Style mapping for progress events
STYLE_MAP: dict[str, dict[str, str | bool]] = {
    "info": {},
    "success": {"fg": "green"},
    "warning": {"fg": "yellow"},
    "error": {"fg": "red", "bold": True},
}


def render_events(
    events: Generator[ProgressEvent | CompletionEvent[T]],
) -> T:
    """Consume event stream, render progress to stderr, return result.

    Args:
        events: Generator yielding ProgressEvent and CompletionEvent

    Returns:
        The result from the final CompletionEvent

    Raises:
        RuntimeError: If operation ends without a CompletionEvent
    """
    for event in events:
        match event:
            case ProgressEvent(message=msg, style=style):
                click.echo(click.style(f"  {msg}", **STYLE_MAP[style]), err=True)
                sys.stderr.flush()  # Force immediate output through shell buffering
            case CompletionEvent(result=result):
                return result
    raise RuntimeError("Operation ended without completion")
