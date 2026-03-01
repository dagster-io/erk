"""Check if GitHub CLI is authenticated."""

from erk.core.health_checks.models import CheckResult
from erk_shared.gateway.github_admin.abc import GitHubAdmin
from erk_shared.gateway.shell.abc import Shell


def check_github_auth(shell: Shell, admin: GitHubAdmin) -> CheckResult:
    """Check if GitHub CLI is authenticated.

    Args:
        shell: Shell implementation for tool detection
        admin: GitHubAdmin implementation for auth status check
    """
    gh_path = shell.get_installed_tool_path("gh")
    if gh_path is None:
        return CheckResult(
            name="github-auth",
            passed=False,
            message="Cannot check auth: gh not installed",
        )

    auth_status = admin.check_auth_status()

    if auth_status.error is not None:
        return CheckResult(
            name="github-auth",
            passed=False,
            message=f"Auth check failed: {auth_status.error}",
        )

    if auth_status.authenticated:
        if auth_status.username:
            return CheckResult(
                name="github-auth",
                passed=True,
                message=f"GitHub authenticated as {auth_status.username}",
            )
        return CheckResult(
            name="github-auth",
            passed=True,
            message="Authenticated to GitHub",
        )
    else:
        return CheckResult(
            name="github-auth",
            passed=False,
            message="Not authenticated to GitHub",
            remediation="Run 'gh auth login' to authenticate",
        )
