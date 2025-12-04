"""Production implementation of GitHub workflow operations."""

import json
import secrets
import string
from pathlib import Path
from typing import Any

from erk_shared.debug import debug_log
from erk_shared.github.types import GitHubRepoLocation
from erk_shared.github.workflow.abc import GitHubWorkflowGateway
from erk_shared.integrations.time.abc import Time
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitHubWorkflowGateway(GitHubWorkflowGateway):
    """Production implementation using gh CLI.

    All GitHub workflow operations execute actual gh commands via subprocess.
    """

    def __init__(self, time: Time) -> None:
        """Initialize RealGitHubWorkflowGateway.

        Args:
            time: Time abstraction for sleep operations
        """
        self._time = time

    def _generate_distinct_id(self) -> str:
        """Generate a random base36 ID for workflow dispatch correlation.

        Returns:
            6-character base36 string (e.g., 'a1b2c3')
        """
        # Base36 alphabet: 0-9 and a-z
        base36_chars = string.digits + string.ascii_lowercase
        # Generate 6 random characters (~2.2 billion possibilities)
        return "".join(secrets.choice(base36_chars) for _ in range(6))

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Trigger GitHub Actions workflow via gh CLI.

        Generates a unique distinct_id internally, passes it to the workflow,
        and uses it to reliably find the triggered run via displayTitle matching.

        Args:
            repo_root: Repository root path
            workflow: Workflow file name (e.g., "implement-plan.yml")
            inputs: Workflow inputs as key-value pairs
            ref: Branch or tag to run workflow from (default: repository default branch)

        Returns:
            The GitHub Actions run ID as a string
        """
        # Generate distinct ID for reliable run matching
        distinct_id = self._generate_distinct_id()
        debug_log(f"trigger_workflow: workflow={workflow}, distinct_id={distinct_id}, ref={ref}")

        cmd = ["gh", "workflow", "run", workflow]

        # Add --ref flag if specified
        if ref:
            cmd.extend(["--ref", ref])

        # Add distinct_id to workflow inputs automatically
        cmd.extend(["-f", f"distinct_id={distinct_id}"])

        # Add caller-provided workflow inputs
        for key, value in inputs.items():
            cmd.extend(["-f", f"{key}={value}"])

        debug_log(f"trigger_workflow: executing command: {' '.join(cmd)}")
        run_subprocess_with_context(
            cmd,
            operation_context=f"trigger workflow '{workflow}'",
            cwd=repo_root,
        )
        debug_log("trigger_workflow: workflow triggered successfully")

        # Poll for the run by matching displayTitle containing the distinct ID
        # The workflow uses run-name: "<issue_number>:<distinct_id>"
        # GitHub API eventual consistency: fast path (5×1s) then slow path (10×2s)
        max_attempts = 15
        runs_data: list[dict[str, Any]] = []
        for attempt in range(max_attempts):
            debug_log(f"trigger_workflow: polling attempt {attempt + 1}/{max_attempts}")

            runs_cmd = [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow,
                "--json",
                "databaseId,status,conclusion,displayTitle",
                "--limit",
                "10",
            ]

            runs_result = run_subprocess_with_context(
                runs_cmd,
                operation_context=f"get run ID for workflow '{workflow}'",
                cwd=repo_root,
            )

            runs_data = json.loads(runs_result.stdout)
            debug_log(f"trigger_workflow: found {len(runs_data)} runs")

            # Validate response structure (must be a list)
            if not isinstance(runs_data, list):
                msg = (
                    f"GitHub workflow '{workflow}' triggered but received invalid response format. "
                    f"Expected JSON array, got: {type(runs_data).__name__}. "
                    f"Raw output: {runs_result.stdout[:200]}"
                )
                raise RuntimeError(msg)

            # Empty list is valid - workflow hasn't appeared yet, continue polling
            if not runs_data:
                # Continue to retry logic below
                pass

            # Find run by matching distinct_id in displayTitle
            for run in runs_data:
                conclusion = run.get("conclusion")
                if conclusion in ("skipped", "cancelled"):
                    continue

                display_title = run.get("displayTitle", "")
                # Check for match pattern: :<distinct_id> (new format: issue_number:distinct_id)
                if f":{distinct_id}" in display_title:
                    run_id = run["databaseId"]
                    debug_log(f"trigger_workflow: found run {run_id}, title='{display_title}'")
                    return str(run_id)

            # No matching run found, retry if attempts remaining
            # Fast path: 1s delay for first 5 attempts, then 2s delay for remaining
            if attempt < max_attempts - 1:
                delay = 1 if attempt < 5 else 2
                self._time.sleep(delay)

        # All attempts exhausted without finding matching run
        msg_parts = [
            f"GitHub workflow triggered but could not find run ID after {max_attempts} attempts.",
            "",
            f"Workflow file: {workflow}",
            f"Correlation ID: {distinct_id}",
            "",
        ]

        if runs_data:
            msg_parts.append(f"Found {len(runs_data)} recent runs, but none matched.")
            msg_parts.append("Recent run titles:")
            for run in runs_data[:5]:
                title = run.get("displayTitle", "N/A")
                status = run.get("status", "N/A")
                msg_parts.append(f"  • {title} ({status})")
            msg_parts.append("")
        else:
            msg_parts.append("No workflow runs found at all.")
            msg_parts.append("")

        msg_parts.extend(
            [
                "Possible causes:",
                "  • GitHub API eventual consistency delay (rare but possible)",
                "  • Workflow file doesn't use 'run-name' with distinct_id",
                "  • All recent runs were cancelled/skipped",
                "",
                "Debug commands:",
                f"  gh run list --workflow {workflow} --limit 10",
                f"  gh workflow view {workflow}",
            ]
        )

        msg = "\n".join(msg_parts)
        debug_log(f"trigger_workflow: exhausted all attempts, error: {msg}")
        raise RuntimeError(msg)

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
