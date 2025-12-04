"""Production implementation of GitHub workflow run operations."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from erk_shared.github.parsing import execute_gh_command
from erk_shared.github.run.abc import GitHubRunGateway
from erk_shared.github.types import (
    BRANCH_NOT_AVAILABLE,
    DISPLAY_TITLE_NOT_AVAILABLE,
    WorkflowRun,
    WorkflowRunConclusion,
    WorkflowRunStatus,
)
from erk_shared.integrations.time.abc import Time
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitHubRunGateway(GitHubRunGateway):
    """Production implementation using gh CLI.

    All GitHub workflow run operations execute actual gh commands via subprocess.
    """

    def __init__(self, time: Time) -> None:
        """Initialize RealGitHubRunGateway.

        Args:
            time: Time abstraction for sleep operations
        """
        self._time = time

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow."""
        cmd = [
            "gh",
            "run",
            "list",
            "--workflow",
            workflow,
            "--json",
            "databaseId,status,conclusion,headBranch,headSha,displayTitle,createdAt",
            "--limit",
            str(limit),
        ]
        if user is not None:
            cmd.extend(["--user", user])

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"list workflow runs for '{workflow}'",
            cwd=repo_root,
        )

        # Parse JSON response
        data = json.loads(result.stdout)

        # Map to WorkflowRun dataclasses
        runs = []
        for run in data:
            # Parse created_at timestamp if present
            created_at = None
            created_at_str = run.get("createdAt")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            workflow_run = WorkflowRun(
                run_id=str(run["databaseId"]),
                status=run["status"],
                conclusion=run.get("conclusion"),
                branch=run["headBranch"],
                head_sha=run["headSha"],
                display_title=run.get("displayTitle"),
                created_at=created_at,
            )
            runs.append(workflow_run)

        return runs

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun:
        """Get details for a specific workflow run by ID.

        Uses the REST API to get workflow run details including node_id.
        The gh CLI's `gh run view --json` does not support the nodeId field,
        but the REST API does.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            # Use REST API - {owner}/{repo} placeholders are auto-filled by gh
            cmd = [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}",
            ]

            stdout = execute_gh_command(cmd, repo_root)
            data = json.loads(stdout)

            # Parse created_at timestamp if present
            created_at = None
            created_at_str = data.get("created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            return WorkflowRun(
                run_id=str(data["id"]),
                status=data["status"],
                conclusion=data.get("conclusion"),
                branch=data["head_branch"],
                head_sha=data["head_sha"],
                display_title=data.get("display_title"),
                created_at=created_at,
                node_id=data.get("node_id"),
            )

        except (RuntimeError, json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            # gh not installed, not authenticated, or command failed (e.g., 404)
            msg = f"Failed to get workflow run {run_id}"
            raise RuntimeError(msg) from e

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Get logs for a workflow run using gh CLI."""
        result = run_subprocess_with_context(
            ["gh", "run", "view", run_id, "--log"],
            operation_context=f"fetch logs for run {run_id}",
            cwd=repo_root,
        )
        return result.stdout

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Poll for a workflow run matching branch name within timeout.

        Uses multi-factor matching (creation time + event type + branch validation)
        to reliably find the correct workflow run even under high throughput.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "dispatch-erk-queue.yml")
            branch_name: Expected branch name to match
            timeout: Maximum seconds to poll (default: 30)
            poll_interval: Seconds between poll attempts (default: 2)

        Returns:
            Run ID as string if found within timeout, None otherwise
        """
        start_time = datetime.now(UTC)
        max_attempts = timeout // poll_interval

        for attempt in range(max_attempts):
            # Query for recent runs with branch info
            runs_cmd = [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow,
                "--json",
                "databaseId,status,conclusion,createdAt,event,headBranch",
                "--limit",
                "20",
            ]

            try:
                runs_result = run_subprocess_with_context(
                    runs_cmd,
                    operation_context=(
                        f"poll for workflow run (workflow: {workflow}, branch: {branch_name})"
                    ),
                    cwd=repo_root,
                )

                # Parse JSON output
                runs_data = json.loads(runs_result.stdout)
                if not runs_data or not isinstance(runs_data, list):
                    # No runs found, retry
                    if attempt < max_attempts - 1:
                        self._time.sleep(poll_interval)
                        continue
                    return None

                # Find run matching our criteria
                for run in runs_data:
                    # Skip skipped/cancelled runs
                    conclusion = run.get("conclusion")
                    if conclusion in ("skipped", "cancelled"):
                        continue

                    # Match by branch name
                    head_branch = run.get("headBranch")
                    if head_branch != branch_name:
                        continue

                    # Verify run was created after we started polling (within tolerance)
                    created_at_str = run.get("createdAt")
                    if created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        # Allow 5-second tolerance for runs created just before polling started
                        if created_at >= start_time - timedelta(seconds=5):
                            run_id = run["databaseId"]
                            return str(run_id)

                # No matching run found, retry if attempts remaining
                if attempt < max_attempts - 1:
                    self._time.sleep(poll_interval)

            except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
                # Command failed, retry if attempts remaining
                if attempt < max_attempts - 1:
                    self._time.sleep(poll_interval)
                    continue
                return None

        # Timeout reached without finding matching run
        return None

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get the most relevant workflow run for each branch.

        Queries GitHub Actions for workflow runs and returns the most relevant
        run for each requested branch. Priority order:
        1. In-progress or queued runs (active runs take precedence)
        2. Failed completed runs (failures are more actionable than successes)
        3. Successful completed runs (most recent)

        Note: Uses list_workflow_runs internally, which already handles gh CLI
        errors gracefully.
        """
        if not branches:
            return {}

        # Get all workflow runs
        all_runs = self.list_workflow_runs(repo_root, workflow, limit=100)

        # Filter to requested branches
        branch_set = set(branches)
        runs_by_branch: dict[str, list[WorkflowRun]] = {}
        for run in all_runs:
            if run.branch in branch_set:
                if run.branch not in runs_by_branch:
                    runs_by_branch[run.branch] = []
                runs_by_branch[run.branch].append(run)

        # Select most relevant run for each branch using priority rules
        result: dict[str, WorkflowRun | None] = {}
        for branch in branches:
            if branch not in runs_by_branch:
                continue

            branch_runs = runs_by_branch[branch]

            # Priority 1: in_progress or queued (active runs)
            active_runs = [r for r in branch_runs if r.status in ("in_progress", "queued")]
            if active_runs:
                result[branch] = active_runs[0]
                continue

            # Priority 2: failed completed runs
            failed_runs = [
                r for r in branch_runs if r.status == "completed" and r.conclusion == "failure"
            ]
            if failed_runs:
                result[branch] = failed_runs[0]
                continue

            # Priority 3: successful completed runs (most recent = first in list)
            completed_runs = [r for r in branch_runs if r.status == "completed"]
            if completed_runs:
                result[branch] = completed_runs[0]
                continue

            # Priority 4: any other runs (unknown status, etc.)
            if branch_runs:
                result[branch] = branch_runs[0]

        return result

    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Batch query workflow runs by GraphQL node IDs.

        Uses GraphQL nodes(ids: [...]) query to efficiently fetch multiple
        workflow runs in a single API call. This is dramatically faster than
        individual REST API calls for each run.
        """
        # Early exit for empty input
        if not node_ids:
            return {}

        # Build GraphQL query using nodes() interface
        query = self._build_workflow_runs_nodes_query(node_ids)
        response = self._execute_graphql_query(query, repo_root)

        # Parse response into WorkflowRun objects
        return self._parse_workflow_runs_nodes_response(response, node_ids)

    def _build_workflow_runs_nodes_query(self, node_ids: list[str]) -> str:
        """Build GraphQL query to fetch workflow runs by node IDs.

        Uses the nodes(ids: [...]) interface which efficiently fetches
        multiple objects in a single API call. WorkflowRun implements Node.

        Args:
            node_ids: List of GraphQL node IDs

        Returns:
            GraphQL query string
        """
        # Escape node IDs for use in JSON array
        node_ids_json = json.dumps(node_ids)

        query = f"""query {{
  nodes(ids: {node_ids_json}) {{
    ... on WorkflowRun {{
      id
      databaseId
      url
      createdAt
      checkSuite {{
        status
        conclusion
        commit {{
          oid
        }}
      }}
    }}
  }}
}}"""
        return query

    def _execute_graphql_query(self, query: str, repo_root: Path) -> dict:
        """Execute GraphQL query via gh CLI.

        Args:
            query: GraphQL query string
            repo_root: Repository root directory

        Returns:
            Parsed JSON response
        """
        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
        stdout = execute_gh_command(cmd, repo_root)
        return json.loads(stdout)

    def _parse_workflow_runs_nodes_response(
        self,
        response: dict,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Parse GraphQL nodes response into WorkflowRun objects.

        Maps the GraphQL checkSuite status/conclusion to WorkflowRun fields.

        Args:
            response: GraphQL response data
            node_ids: Original list of node IDs (for result ordering)

        Returns:
            Mapping of node_id -> WorkflowRun or None
        """
        result: dict[str, WorkflowRun | None] = {}
        nodes = response.get("data", {}).get("nodes", [])

        # Build mapping from id to parsed WorkflowRun
        for node in nodes:
            if node is None:
                continue

            node_id = node.get("id")
            if node_id is None:
                continue

            # Extract checkSuite data
            check_suite = node.get("checkSuite")
            status: WorkflowRunStatus | None = None
            conclusion: WorkflowRunConclusion | None = None
            head_sha: str | None = None

            if check_suite is not None:
                # Map GitHub checkSuite status to workflow run status
                cs_status = check_suite.get("status")
                cs_conclusion = check_suite.get("conclusion")

                # Map checkSuite.status to workflow run status
                if cs_status == "COMPLETED":
                    status = "completed"
                elif cs_status == "IN_PROGRESS":
                    status = "in_progress"
                elif cs_status == "QUEUED":
                    status = "queued"

                # Map checkSuite.conclusion to workflow run conclusion
                if cs_conclusion == "SUCCESS":
                    conclusion = "success"
                elif cs_conclusion == "FAILURE":
                    conclusion = "failure"
                elif cs_conclusion == "SKIPPED":
                    conclusion = "skipped"
                elif cs_conclusion == "CANCELLED":
                    conclusion = "cancelled"

                # Extract commit SHA
                commit = check_suite.get("commit")
                if commit is not None:
                    head_sha = commit.get("oid")

            # Parse created_at timestamp
            created_at = None
            created_at_str = node.get("createdAt")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            workflow_run = WorkflowRun(
                run_id=str(node.get("databaseId", "")),
                status=status or "unknown",  # Default for missing status
                conclusion=conclusion,
                branch=BRANCH_NOT_AVAILABLE,
                head_sha=head_sha or "",  # Default for missing SHA
                display_title=DISPLAY_TITLE_NOT_AVAILABLE,
                created_at=created_at,
            )
            result[node_id] = workflow_run

        # Ensure all requested node_ids are in result (with None for missing)
        for node_id in node_ids:
            if node_id not in result:
                result[node_id] = None

        return result

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        """Get the GraphQL node ID for a workflow run via gh API.

        Uses the REST API endpoint to get workflow run details including node_id.
        """
        cmd = [
            "gh",
            "api",
            f"/repos/{{owner}}/{{repo}}/actions/runs/{run_id}",
            "--jq",
            ".node_id",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        node_id = stdout.strip()
        return node_id if node_id else None
