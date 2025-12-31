"""Pure functions for Claude Code settings management.

This module provides functions to read and modify Claude Code settings,
specifically for managing permissions in the repo's .claude/settings.json.
"""

import json
from collections import defaultdict
from pathlib import Path

# The permission pattern that allows Claude to run erk commands without prompting
ERK_PERMISSION = "Bash(erk:*)"

# Hook commands for erk integration
ERK_USER_PROMPT_HOOK_COMMAND = "uv run scripts/erk-user-prompt-hook.py"
ERK_EXIT_PLAN_HOOK_COMMAND = "ERK_HOOK_ID=exit-plan-mode-hook erk exec exit-plan-mode-hook"


def get_repo_claude_settings_path(repo_root: Path) -> Path:
    """Return the path to the repo's Claude settings file.

    Args:
        repo_root: Path to the repository root

    Returns:
        Path to {repo_root}/.claude/settings.json
    """
    return repo_root / ".claude" / "settings.json"


def has_erk_permission(settings: dict) -> bool:
    """Check if erk permission is configured in Claude settings.

    Args:
        settings: Parsed Claude settings dictionary

    Returns:
        True if Bash(erk:*) permission exists in permissions.allow list
    """
    permissions = settings.get("permissions", {})
    allow_list = permissions.get("allow", [])
    return ERK_PERMISSION in allow_list


def has_user_prompt_hook(settings: dict) -> bool:
    """Check if erk UserPromptSubmit hook is configured.

    Args:
        settings: Parsed Claude settings dictionary

    Returns:
        True if the erk UserPromptSubmit hook is configured
    """
    hooks = settings.get("hooks", {})
    user_prompt_hooks = hooks.get("UserPromptSubmit", [])
    for entry in user_prompt_hooks:
        for hook in entry.get("hooks", []):
            if hook.get("command") == ERK_USER_PROMPT_HOOK_COMMAND:
                return True
    return False


def has_exit_plan_hook(settings: dict) -> bool:
    """Check if erk ExitPlanMode hook is configured.

    Args:
        settings: Parsed Claude settings dictionary

    Returns:
        True if the erk ExitPlanMode PreToolUse hook is configured
    """
    hooks = settings.get("hooks", {})
    pre_tool_hooks = hooks.get("PreToolUse", [])
    for entry in pre_tool_hooks:
        if entry.get("matcher") == "ExitPlanMode":
            for hook in entry.get("hooks", []):
                if hook.get("command") == ERK_EXIT_PLAN_HOOK_COMMAND:
                    return True
    return False


def add_erk_hooks(settings: dict) -> dict:
    """Return a new settings dict with erk hooks added.

    This is a pure function that doesn't modify the input.
    Adds missing hooks while preserving existing settings.

    Args:
        settings: Parsed Claude settings dictionary

    Returns:
        New settings dict with erk hooks added
    """
    # Deep copy to avoid mutating input
    new_settings = json.loads(json.dumps(settings))

    # Use defaultdict for cleaner hook list initialization
    hooks: defaultdict[str, list] = defaultdict(list, new_settings.get("hooks", {}))

    # Add UserPromptSubmit hook if missing
    if not has_user_prompt_hook(settings):
        hooks["UserPromptSubmit"].append(
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": ERK_USER_PROMPT_HOOK_COMMAND,
                    }
                ],
            }
        )

    # Add PreToolUse hook for ExitPlanMode if missing
    if not has_exit_plan_hook(settings):
        hooks["PreToolUse"].append(
            {
                "matcher": "ExitPlanMode",
                "hooks": [
                    {
                        "type": "command",
                        "command": ERK_EXIT_PLAN_HOOK_COMMAND,
                    }
                ],
            }
        )

    new_settings["hooks"] = dict(hooks)
    return new_settings


def add_erk_permission(settings: dict) -> dict:
    """Return a new settings dict with erk permission added.

    This is a pure function that doesn't modify the input.

    Args:
        settings: Parsed Claude settings dictionary

    Returns:
        New settings dict with Bash(erk:*) added to permissions.allow
    """
    # Deep copy to avoid mutating input
    new_settings = json.loads(json.dumps(settings))

    # Ensure permissions.allow exists
    if "permissions" not in new_settings:
        new_settings["permissions"] = {}
    if "allow" not in new_settings["permissions"]:
        new_settings["permissions"]["allow"] = []

    # Add permission if not present
    if ERK_PERMISSION not in new_settings["permissions"]["allow"]:
        new_settings["permissions"]["allow"].append(ERK_PERMISSION)

    return new_settings


def read_claude_settings(settings_path: Path) -> dict | None:
    """Read and parse Claude settings from disk.

    Args:
        settings_path: Path to settings.json file

    Returns:
        Parsed settings dict, or None if file doesn't exist

    Raises:
        json.JSONDecodeError: If file contains invalid JSON
        OSError: If file cannot be read
    """
    if not settings_path.exists():
        return None

    content = settings_path.read_text(encoding="utf-8")
    return json.loads(content)


def write_claude_settings(settings_path: Path, settings: dict) -> None:
    """Write Claude settings to disk.

    Args:
        settings_path: Path to settings.json file
        settings: Settings dict to write

    Raises:
        PermissionError: If unable to write to file
        OSError: If unable to write to file
    """
    # Ensure parent directory exists
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with pretty formatting to match Claude's style
    content = json.dumps(settings, indent=2)
    settings_path.write_text(content, encoding="utf-8")
