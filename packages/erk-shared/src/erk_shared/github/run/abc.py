"""Abstract base class for GitHub workflow run operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.types import WorkflowRun


class GitHubRunGateway(ABC):
    """Abstract interface for GitHub workflow run operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "implement-plan.yml")
            limit: Maximum number of runs to return (default: 50)
            user: Optional GitHub username to filter runs by (maps to --user flag)

        Returns:
            List of workflow runs, ordered by creation time (newest first)
        """
        ...

    @abstractmethod
    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun:
        """Get details for a specific workflow run by ID.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID

        Returns:
            WorkflowRun with status and conclusion
        """
        ...

    @abstractmethod
    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Get logs for a workflow run.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID

        Returns:
            Log text as string

        Raises:
            RuntimeError: If gh CLI command fails
        """
        ...

    @abstractmethod
    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Poll for a workflow run matching branch name within timeout.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "dispatch-erk-queue.yml")
            branch_name: Expected branch name to match
            timeout: Maximum seconds to poll (default: 30)
            poll_interval: Seconds between poll attempts (default: 2)

        Returns:
            Run ID as string if found within timeout, None otherwise
        """
        ...

    @abstractmethod
    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get the most relevant workflow run for each branch.

        Queries GitHub Actions for workflow runs and returns the most relevant
        run for each requested branch. Priority order:
        1. In-progress or queued runs (active runs take precedence)
        2. Failed completed runs (failures are more actionable than successes)
        3. Successful completed runs (most recent)

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "dispatch-erk-queue.yml")
            branches: List of branch names to query

        Returns:
            Mapping of branch name -> WorkflowRun or None if no runs found.
            Only includes entries for branches that have matching workflow runs.
        """
        ...

    @abstractmethod
    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Batch query workflow runs by GraphQL node IDs.

        Uses GraphQL nodes(ids: [...]) query to efficiently fetch multiple
        workflow runs in a single API call. This is dramatically faster than
        individual REST API calls for each run.

        Args:
            repo_root: Repository root directory
            node_ids: List of GraphQL node IDs (e.g., "WFR_kwLOPxC3hc8AAAAEnZK8rQ")

        Returns:
            Mapping of node_id -> WorkflowRun or None if not found.
            Node IDs that don't exist or are inaccessible will have None value.
        """
        ...

    @abstractmethod
    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        """Get the GraphQL node ID for a workflow run.

        This method fetches the node_id from the GitHub API given a workflow run ID.
        The node_id is required for batched GraphQL queries and for updating
        issue metadata synchronously after triggering a workflow.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID (numeric string)

        Returns:
            GraphQL node ID (e.g., "WFR_kwLOPxC3hc8AAAAEnZK8rQ") or None if not found
        """
        ...
