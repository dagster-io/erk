"""Check if Graphite CLI (gt) is installed and available in PATH."""

from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.shell.abc import Shell


def check_graphite_cli(shell: Shell) -> CheckResult:
    """Check if Graphite CLI (gt) is installed and available in PATH.

    This is an info-level check - it always passes, but informs users
    whether gt is configured. Graphite enables stacked PRs but is optional.

    Args:
        shell: Shell implementation for tool detection
    """
    gt_path = shell.get_installed_tool_path("gt")
    if gt_path is None:
        return CheckResult(
            name="graphite",
            passed=True,
            message="Graphite CLI (gt) not installed",
            info=True,
            remediation="Install from https://graphite.dev/docs/installing-the-cli for stacked PRs",
        )

    # Try to get version
    version_output = shell.get_tool_version("gt")
    if version_output is None:
        return CheckResult(
            name="graphite",
            passed=True,
            message="Graphite CLI found (version check failed)",
            details="unknown",
        )

    return CheckResult(
        name="graphite",
        passed=True,
        message=f"Graphite CLI installed: {version_output}",
    )
