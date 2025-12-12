"""Show command for displaying hook details."""

import json
import re
from pathlib import Path

import click
from pydantic import ValidationError

from erk.kits.cli.output import user_output
from erk.kits.hooks.settings import extract_kit_id_from_command, get_all_hooks, load_settings


@click.command(name="show")
@click.argument("hook_spec")
def show_hook(hook_spec: str) -> None:
    """Show details for a specific hook.

    HOOK_SPEC should be in format: kit-id:hook-id
    """
    # Validate format
    if ":" not in hook_spec:
        user_output(
            f"Error: Invalid hook spec '{hook_spec}'. Expected format: kit-id:hook-id",
        )
        raise SystemExit(1)

    # Parse spec
    parts = hook_spec.split(":", 1)
    if len(parts) != 2:
        user_output(
            f"Error: Invalid hook spec '{hook_spec}'. Expected format: kit-id:hook-id",
        )
        raise SystemExit(1)

    kit_id, hook_id = parts

    # Load settings
    settings_path = Path.cwd() / ".claude" / "settings.json"

    if not settings_path.exists():
        user_output(f"Error: Hook '{hook_spec}' not found.")
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
        entry_kit_id = extract_kit_id_from_command(entry.command)
        if entry_kit_id:
            hook_id_match = re.search(r"ERK_HOOK_ID=(\S+)", entry.command)
            entry_hook_id = hook_id_match.group(1) if hook_id_match else None
            if entry_kit_id == kit_id and entry_hook_id == hook_id:
                found = (lifecycle, matcher, entry)
                break

    if not found:
        user_output(f"Error: Hook '{hook_spec}' not found.")
        raise SystemExit(1)

    # Display hook details
    lifecycle, matcher, entry = found
    user_output(f"Hook: {kit_id}:{hook_id}")
    user_output(f"Lifecycle: {lifecycle}")
    user_output(f"Matcher: {matcher}")
    user_output(f"Timeout: {entry.timeout}s")
    user_output(f"Command: {entry.command}")
