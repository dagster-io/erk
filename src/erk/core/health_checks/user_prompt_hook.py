"""Check that the UserPromptSubmit hook is configured."""

from pathlib import Path

from erk.core.claude_settings import read_claude_settings
from erk.core.health_checks.models import CheckResult


def check_user_prompt_hook(repo_root: Path) -> CheckResult:
    """Check that the UserPromptSubmit hook is configured.

    Verifies that .claude/settings.json contains the erk exec user-prompt-hook
    command for the UserPromptSubmit event.

    Args:
        repo_root: Path to the repository root (where .claude/ should be located)
    """
    settings_path = repo_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return CheckResult(
            name="user-prompt-hook",
            passed=False,
            message="No .claude/settings.json found",
            remediation="Run 'erk init' to create settings with the hook configured",
        )
    # File exists, so read_claude_settings won't return None
    settings = read_claude_settings(settings_path)
    assert settings is not None  # file existence already checked

    # Look for UserPromptSubmit hooks
    hooks = settings.get("hooks", {})
    user_prompt_hooks = hooks.get("UserPromptSubmit", [])

    if not user_prompt_hooks:
        return CheckResult(
            name="user-prompt-hook",
            passed=False,
            message="No UserPromptSubmit hook configured",
            remediation="Add 'erk exec user-prompt-hook' hook to .claude/settings.json",
        )

    # Check if the unified hook is present (handles nested matcher structure)
    expected_command = "erk exec user-prompt-hook"
    for hook_entry in user_prompt_hooks:
        if not isinstance(hook_entry, dict):
            continue
        # Handle nested structure: {matcher: ..., hooks: [...]}
        nested_hooks = hook_entry.get("hooks", [])
        if nested_hooks:
            for hook in nested_hooks:
                if not isinstance(hook, dict):
                    continue
                command = hook.get("command", "")
                if expected_command in command:
                    return CheckResult(
                        name="user-prompt-hook",
                        passed=True,
                        message="UserPromptSubmit hook configured",
                    )
        # Handle flat structure: {type: command, command: ...}
        command = hook_entry.get("command", "")
        if expected_command in command:
            return CheckResult(
                name="user-prompt-hook",
                passed=True,
                message="UserPromptSubmit hook configured",
            )

    # Hook section exists but doesn't have the expected command
    return CheckResult(
        name="user-prompt-hook",
        passed=False,
        message="UserPromptSubmit hook command outdated",
        details=f"Expected command containing: {expected_command}",
        remediation="Run 'erk artifact sync' to update hook commands",
    )
