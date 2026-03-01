"""Check if Claude CLI is installed and available in PATH."""

from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.shell.abc import Shell


def check_claude_cli(shell: Shell) -> CheckResult:
    """Check if Claude CLI is installed and available in PATH.

    Args:
        shell: Shell implementation for tool detection
    """
    claude_path = shell.get_installed_tool_path("claude")
    if claude_path is None:
        return CheckResult(
            name="claude",
            passed=False,
            message="Claude CLI not found in PATH",
            details="Install from: https://claude.com/download",
        )

    # Try to get version
    version_output = shell.get_tool_version("claude")
    if version_output is None:
        return CheckResult(
            name="claude",
            passed=True,
            message="Claude CLI found (version check failed)",
            details="unknown",
        )

    # Parse version from output (format: "claude X.Y.Z")
    version_str = version_output.split()[-1] if version_output else "unknown"
    return CheckResult(
        name="claude",
        passed=True,
        message=f"Claude CLI installed: {version_str}",
    )
