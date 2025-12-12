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
# Using Any for value type since click.style accepts str for fg/bg and bool for bold/dim/etc
STYLE_MAP: dict[str, dict[str, str | bool]] = {
    "info": {},
    "success": {"fg": "green"},
    "warning": {"fg": "yellow"},
    "error": {"fg": "red", "bold": True},
}


def _style_text(text: str, style_key: str) -> str:
    """Apply click styling to text using the style map.

    This wrapper isolates the type coercion from STYLE_MAP to click.style().
    """
    styles = STYLE_MAP[style_key]
    fg = styles.get("fg")
    bold = styles.get("bold")
    # click.style expects specific types - coerce appropriately
    return click.style(
        text,
        fg=fg if isinstance(fg, str) else None,
        bold=bool(bold) if bold is not None else None,
    )


def render_events(
    events: Generator[ProgressEvent | CompletionEvent[T], None, None],
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
                click.echo(_style_text(f"  {msg}", style), err=True)
                sys.stderr.flush()  # Force immediate output through shell buffering
            case CompletionEvent(result=result):
                return result
    raise RuntimeError("Operation ended without completion")
