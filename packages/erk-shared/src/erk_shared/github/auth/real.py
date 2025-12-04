"""Production implementation of GitHub authentication operations."""

import subprocess

from erk_shared.github.auth.abc import GitHubAuthGateway
from erk_shared.github.parsing import parse_gh_auth_status_output
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitHubAuthGateway(GitHubAuthGateway):
    """Production implementation using gh CLI.

    All GitHub authentication operations execute actual gh commands via subprocess.
    """

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status.

        Runs `gh auth status` and parses the output to determine authentication status.
        Looks for patterns like:
        - "Logged in to github.com as USERNAME"
        - Success indicator (checkmark)

        Returns:
            Tuple of (is_authenticated, username, hostname)
        """
        result = run_subprocess_with_context(
            ["gh", "auth", "status"],
            operation_context="check GitHub authentication status",
            capture_output=True,
            check=False,
        )

        # gh auth status returns non-zero if not authenticated
        if result.returncode != 0:
            return (False, None, None)

        output = result.stdout + result.stderr
        return parse_gh_auth_status_output(output)

    def get_current_username(self) -> str | None:
        """Get current GitHub username via gh api user.

        Returns:
            GitHub username if authenticated, None otherwise
        """
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
