"""Check that the ExitPlanMode hook is configured."""

from pathlib import Path

from erk.core.claude_settings import has_exit_plan_hook, read_claude_settings
from erk.core.health_checks.models import CheckResult


def check_exit_plan_hook(repo_root: Path) -> CheckResult:
    """Check that the ExitPlanMode hook is configured.

    Verifies that .claude/settings.json contains the erk exec exit-plan-mode-hook
    command for the PreToolUse ExitPlanMode matcher.

    Args:
        repo_root: Path to the repository root (where .claude/ should be located)
    """
    settings_path = repo_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return CheckResult(
            name="exit-plan-hook",
            passed=False,
            message="No .claude/settings.json found",
            remediation="Run 'erk init' to create settings with the hook configured",
        )
    # File exists, so read_claude_settings won't return None
    settings = read_claude_settings(settings_path)
    assert settings is not None  # file existence already checked

    if has_exit_plan_hook(settings):
        return CheckResult(
            name="exit-plan-hook",
            passed=True,
            message="ExitPlanMode hook configured",
        )

    return CheckResult(
        name="exit-plan-hook",
        passed=False,
        message="ExitPlanMode hook command outdated",
        remediation="Run 'erk artifact sync' to update hook commands",
    )
