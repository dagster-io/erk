"""List command for showing installed hooks."""

import json
import re
from pathlib import Path
from typing import NamedTuple

import click
from pydantic import ValidationError

from erk.kits.cli.list_formatting import (
    format_item_name,
    format_level_indicator,
    format_metadata,
    format_section_header,
    format_source_indicator,
)
from erk.kits.cli.output import user_output
from erk.kits.hooks.settings import discover_hooks_with_source, extract_kit_id_from_command


class HookDisplayData(NamedTuple):
    """Display data for a single hook."""

    lifecycle: str
    matcher: str
    level: str
    source: str
    kit_id: str | None
    hook_id: str | None
    version: str | None


def _extract_hook_metadata(command: str) -> tuple[str | None, str | None, str | None]:
    """Extract kit_id, hook_id, and version from hook command.

    Args:
        command: Hook command string

    Returns:
        Tuple of (kit_id, hook_id, version) - any can be None
    """
    kit_id = extract_kit_id_from_command(command)

    hook_id = None
    hook_id_match = re.search(r"ERK_HOOK_ID=(\S+)", command)
    if hook_id_match:
        hook_id = hook_id_match.group(1)

    version = None
    version_match = re.search(r"ERK_KIT_VERSION=(\S+)", command)
    if version_match:
        version = version_match.group(1)

    return kit_id, hook_id, version


def _format_hook_line(
    kit_id: str | None, hook_id: str | None, version: str | None, level: str
) -> str:
    """Format a single hook line with level and source indicators.

    Args:
        kit_id: Kit identifier
        hook_id: Hook identifier
        version: Kit version
        level: Level indicator ("user" or "project")

    Returns:
        Formatted line: [level] name [source]
    """
    level_indicator = format_level_indicator(level)

    if kit_id and hook_id:
        name = format_item_name(f"{kit_id}:{hook_id}")
        source = format_source_indicator(kit_id, version)
    else:
        name = format_item_name("local-hook")
        source = format_source_indicator(None, None)

    return f"{level_indicator} {name} {source}"


def _list_hooks_impl(verbose: bool) -> None:
    """Implementation of list command logic.

    Args:
        verbose: Whether to show detailed information
    """
    # Discover hooks from both user and project levels
    user_path = Path.home() / ".claude"
    project_path = Path.cwd() / ".claude"

    try:
        user_hooks = discover_hooks_with_source(user_path)
        project_hooks = discover_hooks_with_source(project_path)
    except (json.JSONDecodeError, ValidationError) as e:
        user_output(f"Error loading settings.json: {e}")
        raise SystemExit(1) from None

    # Combine and track level
    all_hooks: list[HookDisplayData] = []

    for hook, source in user_hooks:
        kit_id, hook_id, version = _extract_hook_metadata(hook.entry.command)
        all_hooks.append(
            HookDisplayData(
                lifecycle=hook.lifecycle,
                matcher=hook.matcher,
                level="user",
                source=source,
                kit_id=kit_id,
                hook_id=hook_id,
                version=version,
            )
        )

    for hook, source in project_hooks:
        kit_id, hook_id, version = _extract_hook_metadata(hook.entry.command)
        all_hooks.append(
            HookDisplayData(
                lifecycle=hook.lifecycle,
                matcher=hook.matcher,
                level="project",
                source=source,
                kit_id=kit_id,
                hook_id=hook_id,
                version=version,
            )
        )

    if not all_hooks:
        user_output("No hooks installed.")
        raise SystemExit(0)

    # Group by lifecycle
    by_lifecycle: dict[str, list[HookDisplayData]] = {}
    for hook_data in all_hooks:
        if hook_data.lifecycle not in by_lifecycle:
            by_lifecycle[hook_data.lifecycle] = []
        by_lifecycle[hook_data.lifecycle].append(hook_data)

    # Display hooks grouped by lifecycle
    user_output(format_section_header("Hooks by Lifecycle:"))

    for lifecycle in sorted(by_lifecycle.keys()):
        hooks = by_lifecycle[lifecycle]
        user_output(format_section_header(f"  {lifecycle}:"))

        for hook_data in hooks:
            hook_line = _format_hook_line(
                hook_data.kit_id, hook_data.hook_id, hook_data.version, hook_data.level
            )
            user_output(f"    {hook_line}")

            if verbose:
                # Show matcher and source details
                user_output(f"        Matcher: {format_metadata(hook_data.matcher)}")
                if hook_data.source:
                    user_output(f"        Settings: {format_metadata(hook_data.source)}")
                user_output("")


@click.command(name="list")
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
def list_hooks(verbose: bool) -> None:
    """List all installed hooks (alias: ls)."""
    _list_hooks_impl(verbose)


@click.command(name="ls", hidden=True)
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
def ls(verbose: bool) -> None:
    """List all installed hooks (alias for list)."""
    _list_hooks_impl(verbose)
