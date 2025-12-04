"""Fake GitHub workflow run operations for testing."""

from pathlib import Path

from erk_shared.github.run.abc import GitHubRunGateway
from erk_shared.github.types import WorkflowRun


class FakeGitHubRunGateway(GitHubRunGateway):
    """In-memory fake implementation of GitHub workflow run operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults.
    """

    def __init__(
        self,
        *,
        workflow_runs: list[WorkflowRun] | None = None,
        workflow_runs_by_node_id: dict[str, WorkflowRun] | None = None,
        run_logs: dict[str, str] | None = None,
        polled_run_id: str | None = None,
    ) -> None:
        """Create FakeGitHubRunGateway with pre-configured state.

        Args:
            workflow_runs: List of WorkflowRun objects to return from list_workflow_runs
            workflow_runs_by_node_id: Mapping of GraphQL node_id -> WorkflowRun for
                                     get_workflow_runs_by_node_ids()
            run_logs: Mapping of run_id -> log string
            polled_run_id: Run ID to return from poll_for_workflow_run (None for timeout)
        """
        self._workflow_runs = workflow_runs if workflow_runs is not None else []
        self._workflow_runs_by_node_id = workflow_runs_by_node_id or {}
        self._run_logs = run_logs or {}
        self._polled_run_id = polled_run_id
        self._poll_attempts: list[tuple[str, str, int, int]] = []

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow (returns pre-configured data).

        Returns the pre-configured list of workflow runs. The workflow, limit and user
        parameters are accepted but ignored - fake returns all pre-configured runs.
        """
        return self._workflow_runs

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Get details for a specific workflow run by ID (returns pre-configured data).

        Args:
            repo_root: Repository root directory (ignored in fake)
            run_id: GitHub Actions run ID to lookup

        Returns:
            WorkflowRun if found in pre-configured data, None otherwise
        """
        for run in self._workflow_runs:
            if run.run_id == run_id:
                return run
        return None

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Return pre-configured log string for run_id.

        Raises RuntimeError if run_id not found, mimicking gh CLI behavior.
        """
        if run_id not in self._run_logs:
            msg = f"Run {run_id} not found"
            raise RuntimeError(msg)
        return self._run_logs[run_id]

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Return pre-configured run ID without sleeping.

        Tracks poll attempts for test assertions but returns immediately
        without actual polling delays.

        Args:
            repo_root: Repository root directory (ignored)
            workflow: Workflow filename (ignored)
            branch_name: Expected branch name (ignored)
            timeout: Maximum seconds to poll (ignored)
            poll_interval: Seconds between poll attempts (ignored)

        Returns:
            Pre-configured run ID or None for timeout simulation
        """
        self._poll_attempts.append((workflow, branch_name, timeout, poll_interval))
        return self._polled_run_id

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get the most relevant workflow run for each branch.

        Returns a mapping of branch name -> WorkflowRun for branches that have
        matching workflow runs. Uses priority: in_progress/queued > failed > success > other.

        The workflow parameter is accepted but ignored - fake returns runs from
        all pre-configured workflow runs regardless of workflow name.
        """
        if not branches:
            return {}

        # Group runs by branch
        runs_by_branch: dict[str, list[WorkflowRun]] = {}
        for run in self._workflow_runs:
            if run.branch in branches:
                if run.branch not in runs_by_branch:
                    runs_by_branch[run.branch] = []
                runs_by_branch[run.branch].append(run)

        # Select most relevant run for each branch
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
        """Get workflow runs by GraphQL node IDs (returns pre-configured data).

        Looks up each node_id in the pre-configured workflow_runs_by_node_id mapping.

        Args:
            repo_root: Repository root directory (ignored in fake)
            node_ids: List of GraphQL node IDs to lookup

        Returns:
            Mapping of node_id -> WorkflowRun or None if not found
        """
        return {node_id: self._workflow_runs_by_node_id.get(node_id) for node_id in node_ids}

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        """Get node ID for a workflow run (returns pre-configured fake data).

        Looks up the run_id in the pre-configured workflow_runs_by_node_id mapping
        (reverse lookup) to find the corresponding node_id.

        Args:
            repo_root: Repository root directory (ignored in fake)
            run_id: GitHub Actions run ID

        Returns:
            Node ID if found in pre-configured data, or a generated fake node_id
        """
        # Reverse lookup: find node_id by run_id
        for node_id, run in self._workflow_runs_by_node_id.items():
            if run is not None and run.run_id == run_id:
                return node_id

        # If not in node_id mapping, check regular workflow runs and generate fake node_id
        for run in self._workflow_runs:
            if run.run_id == run_id:
                return f"WFR_fake_node_id_{run_id}"

        # Default: return a fake node_id for any run_id (convenience for tests)
        return f"WFR_fake_node_id_{run_id}"

    @property
    def poll_attempts(self) -> list[tuple[str, str, int, int]]:
        """Read-only access to tracked poll attempts for test assertions.

        Returns list of (workflow, branch_name, timeout, poll_interval) tuples.
        """
        return self._poll_attempts

    def add_workflow_run(self, run: WorkflowRun) -> None:
        """Add a workflow run to the fake (for test setup).

        Prepends to the list so the newest runs are first (matching real behavior).
        """
        self._workflow_runs.insert(0, run)
