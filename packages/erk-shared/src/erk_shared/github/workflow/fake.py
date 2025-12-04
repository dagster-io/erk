"""Fake GitHub workflow operations for testing."""

from pathlib import Path
from typing import Any

from erk_shared.github.types import GitHubRepoLocation, WorkflowRun
from erk_shared.github.workflow.abc import GitHubWorkflowGateway


class FakeGitHubWorkflowGateway(GitHubWorkflowGateway):
    """In-memory fake implementation of GitHub workflow operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults.
    """

    def __init__(
        self,
        *,
        workflow_runs: list[WorkflowRun] | None = None,
        workflow_permissions: dict[str, Any] | None = None,
        polled_run_id: str | None = None,
    ) -> None:
        """Create FakeGitHubWorkflowGateway with pre-configured state.

        Args:
            workflow_runs: List of WorkflowRun objects (used to track triggered runs)
            workflow_permissions: Default workflow permissions to return
            polled_run_id: Run ID to return from poll_for_workflow_run (None for timeout)
        """
        self._workflow_runs = workflow_runs if workflow_runs is not None else []
        self._workflow_permissions = workflow_permissions or {
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": True,
        }
        self._polled_run_id = polled_run_id
        self._triggered_workflows: list[tuple[str, dict[str, str], str | None]] = []
        self._set_permissions_calls: list[tuple[GitHubRepoLocation, bool]] = []
        self._poll_attempts: list[tuple[str, str, int, int]] = []

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Record workflow trigger in mutation tracking list.

        Note: In production, trigger_workflow() generates a distinct_id internally
        and adds it to the inputs. Tests should verify the workflow was called
        with expected inputs; the distinct_id is an internal implementation detail.

        Also creates a WorkflowRun entry so get_workflow_run() can find it.
        This simulates the real behavior where triggering a workflow creates a run.

        Returns:
            A fake run ID for testing
        """
        self._triggered_workflows.append((workflow, inputs, ref))
        run_id = "1234567890"

        # Create a WorkflowRun entry so related queries can find it
        branch = inputs.get("branch_name", "main")
        triggered_run = WorkflowRun(
            run_id=run_id,
            status="queued",
            conclusion=None,
            branch=branch,
            head_sha="abc123",
            node_id=f"WFR_{run_id}",
        )
        # Prepend to list so it's found first (most recent)
        self._workflow_runs.insert(0, triggered_run)
        return run_id

    def get_workflow_permissions(self, location: GitHubRepoLocation) -> dict[str, Any]:
        """Return pre-configured workflow permissions."""
        return self._workflow_permissions.copy()

    def set_workflow_pr_permissions(self, location: GitHubRepoLocation, enabled: bool) -> None:
        """Record permission change in mutation tracking list."""
        self._set_permissions_calls.append((location, enabled))
        # Update internal state
        self._workflow_permissions["can_approve_pull_request_reviews"] = enabled

    @property
    def triggered_workflows(self) -> list[tuple[str, dict[str, str], str | None]]:
        """Read-only access to tracked workflow triggers for test assertions.

        Returns list of (workflow, inputs, ref) tuples.
        """
        return self._triggered_workflows

    @property
    def set_permissions_calls(self) -> list[tuple[GitHubRepoLocation, bool]]:
        """Read-only access to tracked permission changes for test assertions.

        Returns list of (location, enabled) tuples.
        """
        return self._set_permissions_calls

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

    @property
    def poll_attempts(self) -> list[tuple[str, str, int, int]]:
        """Read-only access to tracked poll attempts for test assertions.

        Returns list of (workflow, branch_name, timeout, poll_interval) tuples.
        """
        return self._poll_attempts
