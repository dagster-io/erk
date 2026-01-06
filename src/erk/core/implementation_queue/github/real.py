"""Production implementation of GitHub Actions admin operations."""

import json
import subprocess
from typing import Any

from erk_shared.github.types import GitHubRepoLocation
from erk_shared.github_admin.abc import AuthStatus, GitHubAdmin
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitHubAdmin(GitHubAdmin):
    """Production implementation using gh CLI.

    All GitHub Actions admin operations execute actual gh commands via subprocess.
    """

    def get_workflow_permissions(self, location: GitHubRepoLocation) -> dict[str, Any]:
        """Get current workflow permissions using gh CLI.

        Args:
            location: GitHub repository location (local root + repo identity)

        Returns:
            Dict with keys:
            - default_workflow_permissions: "read" or "write"
            - can_approve_pull_request_reviews: bool

        Raises:
            RuntimeError: If gh CLI command fails
        """
        repo_id = location.repo_id
        # GH-API-AUDIT: REST - GET actions/permissions/workflow
        cmd = [
            "gh",
            "api",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            "X-GitHub-Api-Version: 2022-11-28",
            f"/repos/{repo_id.owner}/{repo_id.repo}/actions/permissions/workflow",
        ]

        result = run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"get workflow permissions for {repo_id.owner}/{repo_id.repo}",
            cwd=location.root,
        )

        return json.loads(result.stdout)

    def set_workflow_pr_permissions(self, location: GitHubRepoLocation, enabled: bool) -> None:
        """Enable/disable PR creation via workflow permissions API.

        Args:
            location: GitHub repository location (local root + repo identity)
            enabled: True to enable PR creation, False to disable

        Raises:
            RuntimeError: If gh CLI command fails
        """
        # CRITICAL: Must set both fields together
        # - default_workflow_permissions: Keep as "read" (workflows declare their own)
        # - can_approve_pull_request_reviews: This enables PR creation
        repo_id = location.repo_id
        # GH-API-AUDIT: REST - PUT actions/permissions/workflow
        cmd = [
            "gh",
            "api",
            "--method",
            "PUT",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            "X-GitHub-Api-Version: 2022-11-28",
            f"/repos/{repo_id.owner}/{repo_id.repo}/actions/permissions/workflow",
            "-f",
            "default_workflow_permissions=read",
            "-F",
            f"can_approve_pull_request_reviews={str(enabled).lower()}",
        ]

        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"set workflow PR permissions for {repo_id.owner}/{repo_id.repo}",
            cwd=location.root,
        )

    def check_auth_status(self) -> AuthStatus:
        """Check GitHub CLI authentication status using gh auth status."""
        try:
            # GH-API-AUDIT: REST - auth validation
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if result.returncode == 0:
                # Parse output to find username
                # Format: "✓ Logged in to github.com account username (keyring)"
                output = result.stdout.strip() or result.stderr.strip()
                username = None
                for line in output.split("\n"):
                    if "Logged in to" in line and "account" in line:
                        # Extract username from "... account username (...)"
                        parts = line.split("account")
                        if len(parts) > 1:
                            username_part = parts[1].strip()
                            username = username_part.split()[0] if username_part else None
                        break
                return AuthStatus(authenticated=True, username=username, error=None)
            else:
                return AuthStatus(authenticated=False, username=None, error=None)
        except subprocess.TimeoutExpired:
            return AuthStatus(authenticated=False, username=None, error="Auth check timed out")
        except OSError as e:
            return AuthStatus(authenticated=False, username=None, error=str(e))
