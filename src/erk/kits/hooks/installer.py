"""Hook installation and removal operations."""

from pathlib import Path

from erk.kits.hooks.models import HookDefinition, HookEntry
from erk.kits.hooks.settings import (
    add_hook_to_settings,
    load_settings,
    remove_hooks_by_kit,
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
        Hook invocations are typically 'erk kit exec {kit_id} {hook_id}'.
    """
    if not hooks:
        return 0

    # Load current settings and remove any existing hooks from this kit
    settings_path = project_root / ".claude" / "settings.json"
    settings = load_settings(settings_path)
    settings, _ = remove_hooks_by_kit(settings, kit_id)

    installed_count = 0

    for hook_def in hooks:
        # Inject environment variables for metadata tracking
        env_prefix = f"ERK_KIT_ID={kit_id} ERK_HOOK_ID={hook_def.id}"
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


def remove_hooks(kit_id: str, project_root: Path) -> int:
    """Remove all hooks installed by a kit.

    Args:
        kit_id: Kit identifier
        project_root: Project root directory

    Returns:
        Count of removed hooks

    Note:
        Removes hook entries from settings.json.
    """
    # Load current settings
    settings_path = project_root / ".claude" / "settings.json"
    settings = load_settings(settings_path)

    # Remove hooks from settings
    updated_settings, removed_count = remove_hooks_by_kit(settings, kit_id)

    # Save if hooks were removed
    if removed_count > 0:
        save_settings(settings_path, updated_settings)

    return removed_count
