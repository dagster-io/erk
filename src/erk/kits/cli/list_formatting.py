"""Shared formatting utilities for CLI list commands.

This module provides consistent formatting functions for all list commands
in the erk.kits CLI, following the standards defined in
docs/agent/cli-list-formatting.md.
"""

import re

import click


def format_level_indicator(level: str) -> str:
    """Format level indicator for display.

    Args:
        level: Level string ("user" or "project")

    Returns:
        Formatted indicator: [U] for user (blue, bold), [P] for project (green, bold)
    """
    if level == "user":
        return click.style("[U]", fg="blue", bold=True)
    return click.style("[P]", fg="green", bold=True)


def format_source_indicator(kit_id: str | None, version: str | None) -> str:
    """Format source indicator for display.

    Args:
        kit_id: Kit identifier (None for local artifacts)
        version: Kit version (None for local artifacts)

    Returns:
        Formatted source: [kit-id@version] (cyan) or [local] (yellow)
    """
    if kit_id and version:
        return click.style(f"[{kit_id}@{version}]", fg="cyan")
    if kit_id:
        return click.style(f"[{kit_id}]", fg="cyan")
    return click.style("[local]", fg="yellow")


def format_section_header(text: str) -> str:
    """Format section header for display.

    Args:
        text: Header text

    Returns:
        Formatted header: bold white text
    """
    return click.style(text, bold=True, fg="white")


def format_subsection_header(text: str, count: int | None = None) -> str:
    """Format subsection header with optional count.

    Args:
        text: Header text
        count: Optional count to append

    Returns:
        Formatted header: bold white text with optional count
    """
    if count is not None:
        return click.style(f"{text} ({count})", bold=True, fg="white")
    return click.style(text, bold=True, fg="white")


def get_visible_length(text: str) -> int:
    """Calculate visible length of text excluding ANSI codes.

    This is useful for alignment when text contains color codes.

    Args:
        text: Text that may contain ANSI escape codes

    Returns:
        Length of visible characters (excluding ANSI codes)
    """
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    plain_text = ansi_escape.sub("", text)
    return len(plain_text)


def format_item_name(name: str, bold: bool = True) -> str:
    """Format item name for display.

    Args:
        name: Item name
        bold: Whether to make the name bold (default: True)

    Returns:
        Formatted name: bold white text by default
    """
    if bold:
        return click.style(name, bold=True)
    return name


def format_metadata(text: str, dim: bool = True) -> str:
    """Format metadata or description text.

    Args:
        text: Metadata text
        dim: Whether to dim the text (default: True)

    Returns:
        Formatted text: dimmed white for secondary information
    """
    if dim:
        return click.style(text, fg="white", dim=True)
    return text


def format_kit_reference(kit_id: str, version: str) -> str:
    """Format kit reference for display.

    Args:
        kit_id: Kit identifier
        version: Kit version

    Returns:
        Formatted reference: kit-id@version in cyan
    """
    return click.style(f"{kit_id}@{version}", fg="cyan")
