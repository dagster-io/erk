"""Check if GitHub CLI (gh) is installed and available in PATH."""

from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.shell.abc import Shell


def check_github_cli(shell: Shell) -> CheckResult:
    """Check if GitHub CLI (gh) is installed and available in PATH.

    Args:
        shell: Shell implementation for tool detection
    """
    gh_path = shell.get_installed_tool_path("gh")
    if gh_path is None:
        return CheckResult(
            name="github",
            passed=False,
            message="GitHub CLI (gh) not found in PATH",
            details="Install from: https://cli.github.com/",
        )

    # Try to get version
    version_output = shell.get_tool_version("gh")
    if version_output is None:
        return CheckResult(
            name="github",
            passed=True,
            message="GitHub CLI found (version check failed)",
            details="unknown",
        )

    # Take first line only (gh version has multi-line output)
    version_first_line = version_output.split("\n")[0] if version_output else "unknown"
    return CheckResult(
        name="github",
        passed=True,
        message=f"GitHub CLI installed: {version_first_line}",
    )
