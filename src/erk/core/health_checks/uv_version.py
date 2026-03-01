"""Check if uv is installed."""

from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.shell.abc import Shell


def check_uv_version(shell: Shell) -> CheckResult:
    """Check if uv is installed.

    Shows version and upgrade instructions. erk works best with recent uv versions.

    Args:
        shell: Shell implementation for tool detection
    """
    uv_path = shell.get_installed_tool_path("uv")
    if uv_path is None:
        return CheckResult(
            name="uv",
            passed=False,
            message="uv not found in PATH",
            details="Install from: https://docs.astral.sh/uv/getting-started/installation/",
        )

    # Get installed version
    version_output = shell.get_tool_version("uv")
    if version_output is None:
        return CheckResult(
            name="uv",
            passed=True,
            message="uv found (version check failed)",
            details="Upgrade: uv self update",
        )

    # Parse version (format: "uv 0.9.2" or "uv 0.9.2 (Homebrew 2025-10-10)")
    parts = version_output.split()
    version = parts[1] if len(parts) >= 2 else version_output

    return CheckResult(
        name="uv",
        passed=True,
        message=f"uv installed: {version}",
    )
