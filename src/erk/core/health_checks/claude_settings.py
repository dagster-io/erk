"""Check Claude settings for misconfigurations."""

from pathlib import Path

from erk.core.claude_settings import read_claude_settings
from erk.core.health_checks.models import CheckResult


def check_claude_settings(repo_root: Path) -> CheckResult:
    """Check Claude settings for misconfigurations.

    Args:
        repo_root: Path to the repository root (where .claude/ should be located)

    Raises:
        json.JSONDecodeError: If settings.json contains invalid JSON
    """
    settings_path = repo_root / ".claude" / "settings.json"
    settings = read_claude_settings(settings_path)
    if settings is None:
        return CheckResult(
            name="claude-settings",
            passed=True,
            message="No .claude/settings.json (using defaults)",
        )

    return CheckResult(
        name="claude-settings",
        passed=True,
        message=".claude/settings.json looks valid",
    )
