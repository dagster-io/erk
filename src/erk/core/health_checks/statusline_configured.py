"""Check if erk-statusline is configured in global Claude settings."""

from erk.core.claude_settings import (
    StatuslineNotConfigured,
    get_statusline_config,
    has_erk_statusline,
)
from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.claude_installation.abc import ClaudeInstallation


def check_statusline_configured(claude_installation: ClaudeInstallation) -> CheckResult:
    """Check if erk-statusline is configured in global Claude settings.

    This is an info-level check - it always passes, but informs users
    they can configure the erk statusline feature.

    Args:
        claude_installation: Gateway for accessing Claude settings

    Returns:
        CheckResult with info about statusline status
    """
    # Read settings via gateway
    if not claude_installation.settings_exists():
        return CheckResult(
            name="statusline",
            passed=True,
            message="No global Claude settings (statusline not configured)",
            details="Run 'erk init --statusline' to enable erk statusline",
            info=True,
        )

    settings = claude_installation.read_settings()

    if has_erk_statusline(settings):
        return CheckResult(
            name="statusline",
            passed=True,
            message="erk-statusline configured",
        )

    # Check if a different statusline is configured
    statusline_config = get_statusline_config(settings)
    if not isinstance(statusline_config, StatuslineNotConfigured):
        return CheckResult(
            name="statusline",
            passed=True,
            message=f"Different statusline configured: {statusline_config.command}",
            details="Run 'erk init --statusline' to switch to erk statusline",
            info=True,
        )

    return CheckResult(
        name="statusline",
        passed=True,
        message="erk-statusline not configured",
        details="Run 'erk init --statusline' to enable erk statusline",
        info=True,
    )
