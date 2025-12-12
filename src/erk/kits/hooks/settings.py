"""Settings.json I/O and hook manipulation operations."""

import json
import re
import tempfile
from pathlib import Path
from typing import NamedTuple

from erk.kits.hooks.models import ClaudeSettings, HookEntry, MatcherGroup


def extract_kit_id_from_command(command: str) -> str | None:
    """Extract kit_id from ERK_KIT_ID environment variable in command.

    Returns None if kit_id not found in command.
    """
    match = re.search(r"ERK_KIT_ID=(\S+)", command)
    if match:
        return match.group(1)
    return None


class InstalledHook(NamedTuple):
    """A hook entry with its lifecycle and matcher context."""

    lifecycle: str
    matcher: str
    entry: HookEntry


def load_settings(path: Path) -> ClaudeSettings:
    """Load and parse settings.json using Pydantic.

    Args:
        path: Path to settings.json file

    Returns:
        Parsed ClaudeSettings object

    Note:
        Returns empty ClaudeSettings if file doesn't exist.
    """
    if not path.exists():
        return ClaudeSettings()

    content = path.read_text(encoding="utf-8")
    data = json.loads(content)
    return ClaudeSettings.model_validate(data)


def save_settings(path: Path, settings: ClaudeSettings) -> None:
    """Save settings.json atomically using temp file + rename.

    Args:
        path: Path to settings.json file
        settings: ClaudeSettings object to save

    Note:
        Creates parent directory if it doesn't exist.
        Uses atomic write (temp + rename) to prevent corruption.
    """
    # Ensure parent directory exists
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict and write atomically
    data = settings.model_dump(mode="json", by_alias=True, exclude_none=True)

    # Create temp file in same directory to ensure atomic rename works
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp.write("\n")  # Add trailing newline
        tmp_path = Path(tmp.name)

    # Atomic rename
    tmp_path.replace(path)


def add_hook_to_settings(
    settings: ClaudeSettings,
    lifecycle: str,
    matcher: str,
    entry: HookEntry,
) -> ClaudeSettings:
    """Add a hook entry to settings.

    Args:
        settings: Current settings object
        lifecycle: Hook lifecycle (e.g., "user-prompt-submit")
        matcher: Matcher pattern (e.g., "**")
        entry: HookEntry to add

    Returns:
        New ClaudeSettings with hook added

    Note:
        Creates hooks dict and lifecycle list if they don't exist.
        Appends to existing matcher group or creates new one.
    """
    # Get current hooks or initialize
    current_hooks = settings.hooks if settings.hooks else {}

    # Get lifecycle groups or initialize
    lifecycle_groups = current_hooks.get(lifecycle, [])

    # Find existing matcher group
    existing_group = None
    for group in lifecycle_groups:
        if group.matcher == matcher:
            existing_group = group
            break

    if existing_group:
        # Add to existing group
        new_hooks = list(existing_group.hooks) + [entry]
        new_group = MatcherGroup(matcher=matcher, hooks=new_hooks)
        # Replace old group with new one
        new_groups = [new_group if g.matcher == matcher else g for g in lifecycle_groups]
    else:
        # Create new matcher group
        new_group = MatcherGroup(matcher=matcher, hooks=[entry])
        new_groups = lifecycle_groups + [new_group]

    # Build new hooks dict
    new_hooks_dict = dict(current_hooks)
    new_hooks_dict[lifecycle] = new_groups

    # Create new settings preserving extra fields
    extra_fields = settings.model_extra if settings.model_extra else {}
    return ClaudeSettings(
        permissions=settings.permissions,
        hooks=new_hooks_dict,
        **extra_fields,
    )


def remove_hooks_by_kit(
    settings: ClaudeSettings,
    kit_id: str,
) -> tuple[ClaudeSettings, int]:
    """Remove all hooks installed by a specific kit.

    Args:
        settings: Current settings object
        kit_id: Kit ID to match in _dot_agent metadata

    Returns:
        Tuple of (new settings, count of removed hooks)

    Note:
        Removes empty matcher groups and lifecycle entries.
    """
    if not settings.hooks:
        return settings, 0

    removed_count = 0
    new_hooks_dict: dict[str, list[MatcherGroup]] = {}

    for lifecycle, groups in settings.hooks.items():
        new_groups: list[MatcherGroup] = []

        for group in groups:
            # Filter out hooks from this kit
            remaining_hooks = [
                hook for hook in group.hooks if extract_kit_id_from_command(hook.command) != kit_id
            ]

            removed_count += len(group.hooks) - len(remaining_hooks)

            # Only keep group if it has remaining hooks
            if remaining_hooks:
                new_groups.append(MatcherGroup(matcher=group.matcher, hooks=remaining_hooks))

        # Only keep lifecycle if it has groups
        if new_groups:
            new_hooks_dict[lifecycle] = new_groups

    # Create new settings preserving extra fields
    extra_fields = settings.model_extra if settings.model_extra else {}
    new_settings = ClaudeSettings(
        permissions=settings.permissions,
        hooks=new_hooks_dict if new_hooks_dict else None,
        **extra_fields,
    )

    return new_settings, removed_count


def get_all_hooks(settings: ClaudeSettings) -> list[InstalledHook]:
    """Extract all hooks from settings.

    Args:
        settings: Settings object to extract from

    Returns:
        List of InstalledHook entries with lifecycle, matcher, and entry

    Note:
        Returns empty list if no hooks present.
    """
    if not settings.hooks:
        return []

    results: list[InstalledHook] = []
    for lifecycle, groups in settings.hooks.items():
        for group in groups:
            for hook in group.hooks:
                results.append(InstalledHook(lifecycle, group.matcher, hook))

    return results


def merge_matcher_groups(groups: list[MatcherGroup]) -> list[MatcherGroup]:
    """Consolidate matcher groups with the same pattern.

    Args:
        groups: List of MatcherGroup objects

    Returns:
        List with duplicate matchers merged

    Note:
        Preserves order of first occurrence.
        Combines hooks from all groups with same matcher.
    """
    if not groups:
        return []

    seen_matchers: dict[str, list[HookEntry]] = {}
    matcher_order: list[str] = []

    for group in groups:
        if group.matcher in seen_matchers:
            # Merge hooks into existing matcher
            seen_matchers[group.matcher].extend(group.hooks)
        else:
            # First occurrence of this matcher
            seen_matchers[group.matcher] = list(group.hooks)
            matcher_order.append(group.matcher)

    # Build result preserving order
    return [
        MatcherGroup(matcher=matcher, hooks=seen_matchers[matcher]) for matcher in matcher_order
    ]


def load_settings_with_source(settings_path: Path, source_name: str) -> tuple[ClaudeSettings, str]:
    """Load settings from a single file and track its source.

    Args:
        settings_path: Path to settings file
        source_name: Name of the source file (e.g., "settings.json")

    Returns:
        Tuple of (Settings object, source_name)

    Note:
        Returns empty ClaudeSettings if file doesn't exist.
    """
    if not settings_path.exists():
        return ClaudeSettings(), source_name

    content = settings_path.read_text(encoding="utf-8")
    data = json.loads(content)
    return ClaudeSettings.model_validate(data), source_name


def discover_hooks_with_source(base_path: Path) -> list[tuple[InstalledHook, str]]:
    """Discover hooks from settings files and track their source.

    Args:
        base_path: Base directory containing settings files

    Returns:
        List of tuples (InstalledHook, source_name) where source_name is
        "settings.json" or "settings.local.json"

    Note:
        Returns empty list if directory doesn't exist.
        Checks both settings.json and settings.local.json.
    """
    if not base_path.exists():
        return []

    results: list[tuple[InstalledHook, str]] = []

    # Check settings.json
    settings_json = base_path / "settings.json"
    if settings_json.exists():
        settings, source = load_settings_with_source(settings_json, "settings.json")
        hooks = get_all_hooks(settings)
        for hook in hooks:
            results.append((hook, source))

    # Check settings.local.json
    settings_local = base_path / "settings.local.json"
    if settings_local.exists():
        settings, source = load_settings_with_source(settings_local, "settings.local.json")
        hooks = get_all_hooks(settings)
        for hook in hooks:
            results.append((hook, source))

    return results
