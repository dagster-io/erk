"""Production implementation of GitHub Actions admin operations."""

import json
from typing import Any

from erk_shared.github.types import GitHubRepoLocation
from erk_shared.subprocess_utils import run_subprocess_with_context

from erk.core.implementation_queue.github.abc import GitHubAdmin


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
            cmd,
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
            cmd,
            operation_context=f"set workflow PR permissions for {repo_id.owner}/{repo_id.repo}",
            cwd=location.root,
        )
