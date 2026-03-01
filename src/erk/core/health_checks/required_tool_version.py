"""Check that installed erk version matches the required version file."""

from pathlib import Path

from erk.core.health_checks.models import CheckResult
from erk.core.version_check import get_required_version, is_version_mismatch


def _get_installed_erk_version() -> str | None:
    """Get installed erk version, or None if not installed."""
    try:
        from importlib.metadata import version

        return version("erk")
    except Exception:
        return None


def check_required_tool_version(repo_root: Path) -> CheckResult:
    """Check that installed erk version matches the required version file.

    Args:
        repo_root: Path to the repository root

    Returns:
        CheckResult indicating:
        - FAIL if version file missing
        - FAIL with warning if versions mismatch
        - PASS if versions match
    """
    required_version = get_required_version(repo_root)
    if required_version is None:
        return CheckResult(
            name="required-version",
            passed=False,
            message="Required version file missing (.erk/required-erk-uv-tool-version)",
            remediation="Run 'erk init' to create this file",
        )

    installed_version = _get_installed_erk_version()
    if installed_version is None:
        return CheckResult(
            name="required-version",
            passed=False,
            message="Could not determine installed erk version",
        )

    if is_version_mismatch(installed_version, required_version):
        return CheckResult(
            name="required-version",
            passed=False,
            message=f"Version mismatch: installed {installed_version}, required {required_version}",
            remediation="Run 'uv sync' to update",
        )

    return CheckResult(
        name="required-version",
        passed=True,
        message=f"erk version matches required ({required_version})",
    )
