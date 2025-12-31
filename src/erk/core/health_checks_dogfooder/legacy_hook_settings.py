"""Check for legacy hook settings using erk kit exec commands.

This is a temporary check for early dogfooders. Delete this file once
all users have migrated their hooks to the unified hook script.
"""

import json
from pathlib import Path

from erk.core.health_checks import CheckResult


def detect_legacy_hook_commands(repo_root: Path) -> list[str]:
    """Detect legacy 'erk kit exec' hook commands in Claude settings.

    Checks .claude/settings.json for any hooks that use the old
    'erk kit exec' or 'uvx erk' patterns.

    Args:
        repo_root: Path to the repository root

    Returns:
        List of legacy hook command strings found
    """
    settings_path = repo_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return []

    content = settings_path.read_text(encoding="utf-8")
    settings = json.loads(content)

    hooks_section = settings.get("hooks", {})
    legacy_commands: list[str] = []

    # Check all hook types (UserPromptSubmit, etc.)
    for hook_entries in hooks_section.values():
        if not isinstance(hook_entries, list):
            continue
        for hook_entry in hook_entries:
            if not isinstance(hook_entry, dict):
                continue
            # Handle nested structure: {matcher: ..., hooks: [...]}
            nested_hooks = hook_entry.get("hooks", [])
            if nested_hooks:
                for hook in nested_hooks:
                    if not isinstance(hook, dict):
                        continue
                    command = hook.get("command", "")
                    if _is_legacy_hook_command(command):
                        legacy_commands.append(command)
            # Handle flat structure: {type: command, command: ...}
            command = hook_entry.get("command", "")
            if _is_legacy_hook_command(command):
                legacy_commands.append(command)

    return legacy_commands


def _is_legacy_hook_command(command: str) -> bool:
    """Check if a hook command uses legacy erk kit exec patterns."""
    if not command:
        return False
    # Check for 'erk kit exec' or 'uvx erk' patterns
    return "erk kit exec" in command or ("uvx" in command and "erk@" in command)


def check_legacy_hook_settings(repo_root: Path) -> CheckResult:
    """Check for legacy hook settings using erk kit exec commands.

    Detects .claude/settings.json hooks that use old 'erk kit exec' or
    'uvx erk@X.Y.Z kit exec' patterns. These won't work with current erk.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with failure if legacy hooks found
    """
    legacy_commands = detect_legacy_hook_commands(repo_root)

    if not legacy_commands:
        return CheckResult(
            name="legacy-hook-settings",
            passed=True,
            message="No legacy hook commands found",
        )

    # Build details with migration instructions
    details_lines: list[str] = ["Legacy hook commands found:"]
    for cmd in legacy_commands[:5]:  # Limit display to first 5
        # Truncate long commands
        truncated = cmd[:80] + "..." if len(cmd) > 80 else cmd
        details_lines.append(f"  - {truncated}")
    if len(legacy_commands) > 5:
        details_lines.append(f"  ... and {len(legacy_commands) - 5} more")
    details_lines.append("")
    details_lines.append("Run 'erk init' to update hook configuration")

    return CheckResult(
        name="legacy-hook-settings",
        passed=False,  # Failure - hooks won't work
        message=f"Found {len(legacy_commands)} legacy hook command(s)",
        details="\n".join(details_lines),
    )
