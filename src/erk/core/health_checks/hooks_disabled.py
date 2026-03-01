"""Check if Claude Code hooks are globally disabled."""

import json

from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.claude_installation.abc import ClaudeInstallation


def check_hooks_disabled(claude_installation: ClaudeInstallation) -> CheckResult:
    """Check if Claude Code hooks are globally disabled.

    Checks global settings for hooks.disabled=true via the ClaudeInstallation gateway.

    Args:
        claude_installation: Gateway for accessing Claude settings

    Returns a warning (not failure) if hooks are disabled, since the user
    may have intentionally disabled them.
    """
    disabled_in: list[str] = []

    # Check global settings via gateway
    settings = claude_installation.read_settings()
    if settings:
        hooks = settings.get("hooks", {})
        if hooks.get("disabled") is True:
            disabled_in.append("settings.json")

    # Check local settings file directly (not yet in gateway)
    local_settings_path = claude_installation.get_local_settings_path()
    if local_settings_path.exists():
        content = local_settings_path.read_text(encoding="utf-8")
        local_settings = json.loads(content)
        hooks = local_settings.get("hooks", {})
        if hooks.get("disabled") is True:
            disabled_in.append("settings.local.json")

    if disabled_in:
        return CheckResult(
            name="claude-hooks",
            passed=True,  # Don't fail, just warn
            warning=True,
            message=f"Hooks disabled in {', '.join(disabled_in)}",
            details="Set hooks.disabled=false or remove the setting to enable hooks",
        )

    return CheckResult(
        name="claude-hooks",
        passed=True,
        message="Hooks enabled (not globally disabled)",
    )
