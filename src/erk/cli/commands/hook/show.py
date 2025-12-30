"""Show command for displaying hook details."""

import json
from pathlib import Path

import click
from pydantic import ValidationError

from erk.kits.cli.output import user_output
from erk.kits.hooks.settings import extract_hook_id_from_command, get_all_hooks, load_settings


@click.command(name="show")
@click.argument("hook_id")
def show_hook(hook_id: str) -> None:
    """Show details for a specific hook.

    HOOK_ID should be the hook identifier (e.g., session-id-injector-hook).
    """
    # Load settings
    settings_path = Path.cwd() / ".claude" / "settings.json"

    if not settings_path.exists():
        user_output(f"Error: Hook '{hook_id}' not found.")
        raise SystemExit(1)

    try:
        settings = load_settings(settings_path)
    except (json.JSONDecodeError, ValidationError) as e:
        user_output(f"Error loading settings.json: {e}")
        raise SystemExit(1) from None

    # Find matching hook
    hooks = get_all_hooks(settings)
    found = None

    for lifecycle, matcher, entry in hooks:
        entry_hook_id = extract_hook_id_from_command(entry.command)
        if entry_hook_id == hook_id:
            found = (lifecycle, matcher, entry)
            break

    if not found:
        user_output(f"Error: Hook '{hook_id}' not found.")
        raise SystemExit(1)

    # Display hook details
    lifecycle, matcher, entry = found
    user_output(f"Hook: {hook_id}")
    user_output(f"Lifecycle: {lifecycle}")
    user_output(f"Matcher: {matcher}")
    user_output(f"Timeout: {entry.timeout}s")
    user_output(f"Command: {entry.command}")
