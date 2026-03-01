"""Check if erk permission is configured in repo's Claude Code settings."""

from pathlib import Path

from erk.core.claude_settings import (
    ERK_PERMISSION,
    get_repo_claude_settings_path,
    has_erk_permission,
    read_claude_settings,
)
from erk.core.health_checks.models import CheckResult


def check_claude_erk_permission(repo_root: Path) -> CheckResult:
    """Check if erk permission is configured in repo's Claude Code settings.

    This is an info-level check - it always passes, but shows whether
    the permission is configured or not. The permission allows Claude
    to run erk commands without prompting.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult with info about permission status
    """
    settings_path = get_repo_claude_settings_path(repo_root)
    settings = read_claude_settings(settings_path)
    if settings is None:
        return CheckResult(
            name="claude-erk-permission",
            passed=True,  # Info level - always passes
            message="No .claude/settings.json in repo",
        )

    # Check for permission
    if has_erk_permission(settings):
        return CheckResult(
            name="claude-erk-permission",
            passed=True,
            message=f"erk permission configured ({ERK_PERMISSION})",
        )
    else:
        return CheckResult(
            name="claude-erk-permission",
            passed=True,  # Info level - always passes
            message="erk permission not configured",
            details=f"Run 'erk init' to add {ERK_PERMISSION} to .claude/settings.json",
        )
