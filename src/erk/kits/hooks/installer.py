"""Hook installation and removal operations."""

from pathlib import Path

from erk.kits.hooks.models import HookDefinition, HookEntry
from erk.kits.hooks.settings import (
    add_hook_to_settings,
    load_settings,
    remove_hooks_by_hook_ids,
    save_settings,
)


def install_hooks(
    kit_id: str,
    hooks: list[HookDefinition],
    project_root: Path,
) -> int:
    """Install hooks from a kit.

    Args:
        kit_id: Kit identifier
        hooks: List of hook definitions from kit manifest
        project_root: Project root directory

    Returns:
        Count of installed hooks

    Note:
        Updates settings.json with hook entries using invocation commands.
        Hook invocations are typically 'erk exec {hook_id}'.
    """
    if not hooks:
        return 0

    # Load current settings and remove any existing hooks with matching IDs
    settings_path = project_root / ".claude" / "settings.json"
    settings = load_settings(settings_path)
    hook_ids = {hook.id for hook in hooks}
    settings, _ = remove_hooks_by_hook_ids(settings, hook_ids)

    installed_count = 0

    for hook_def in hooks:
        # Inject environment variable for hook identification
        env_prefix = f"ERK_HOOK_ID={hook_def.id}"
        command_with_metadata = f"{env_prefix} {hook_def.invocation}"

        entry = HookEntry(
            type="command",
            command=command_with_metadata,
            timeout=hook_def.timeout,
        )

        # Use wildcard matcher if none specified
        matcher = hook_def.matcher if hook_def.matcher is not None else "*"

        # Add to settings
        settings = add_hook_to_settings(
            settings,
            lifecycle=hook_def.lifecycle,
            matcher=matcher,
            entry=entry,
        )

        installed_count += 1

    # Save updated settings
    if installed_count > 0:
        save_settings(settings_path, settings)

    return installed_count


def remove_hooks(hooks: list[HookDefinition], project_root: Path) -> int:
    """Remove hooks by their IDs.

    Args:
        hooks: List of hook definitions to remove
        project_root: Project root directory

    Returns:
        Count of removed hooks

    Note:
        Removes hook entries from settings.json by matching ERK_HOOK_ID.
    """
    if not hooks:
        return 0

    # Load current settings
    settings_path = project_root / ".claude" / "settings.json"
    settings = load_settings(settings_path)

    # Remove hooks by their IDs
    hook_ids = {hook.id for hook in hooks}
    updated_settings, removed_count = remove_hooks_by_hook_ids(settings, hook_ids)

    # Save if hooks were removed
    if removed_count > 0:
        save_settings(settings_path, updated_settings)

    return removed_count
