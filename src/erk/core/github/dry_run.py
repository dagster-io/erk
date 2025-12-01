"""No-op wrapper for GitHub operations."""

from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.types import (
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
    WorkflowRun,
)


class DryRunGitHub(GitHub):
    """No-op wrapper for GitHub operations.

    Read operations are delegated to the wrapped implementation.
    Write operations return without executing (no-op behavior).

    This wrapper prevents destructive GitHub operations from executing in dry-run mode,
    while still allowing read operations for validation.
    """

    def __init__(self, wrapped: GitHub) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real GitHub operations implementation to wrap
        """
        self._wrapped = wrapped

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_prs_for_repo(repo_root, include_checks=include_checks)

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_status(repo_root, branch, debug=debug)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_base_branch(repo_root, pr_number)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """No-op for updating PR base branch in dry-run mode."""
        # Do nothing - prevents actual PR base update
        pass

    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        """No-op for updating PR body in dry-run mode."""
        # Do nothing - prevents actual PR body update
        pass

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_mergeability(repo_root, pr_number)

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.fetch_pr_titles_batch(prs, repo_root)

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.enrich_prs_with_ci_status_batch(prs, repo_root)

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """No-op for merging PR in dry-run mode."""
        # Do nothing - prevents actual PR merge
        pass

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """No-op for triggering workflow in dry-run mode.

        Returns:
            A fake run ID for dry-run mode
        """
        # Return fake run ID - prevents actual workflow trigger
        return "noop-run-12345"

    def create_pr(
        self,
        repo_root: Path,
        branch: str,
        title: str,
        body: str,
        base: str | None = None,
        *,
        draft: bool = False,
    ) -> int:
        """No-op for creating PR in dry-run mode.

        Returns:
            A sentinel value (-1) for dry-run mode
        """
        # Return sentinel value - prevents actual PR creation
        return -1

    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        """No-op for closing PR in dry-run mode."""
        pass

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.list_workflow_runs(repo_root, workflow, limit, user=user)

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_workflow_run(repo_root, run_id)

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_run_logs(repo_root, run_id)

    def get_prs_linked_to_issues(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[PullRequestInfo]]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_prs_linked_to_issues(repo_root, issue_numbers)

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_workflow_runs_by_branches(repo_root, workflow, branches)

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.poll_for_workflow_run(
            repo_root, workflow, branch_name, timeout, poll_interval
        )

    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_checkout_info(repo_root, pr_number)

    def get_workflow_runs_batch(
        self,
        repo_root: Path,
        run_ids: list[str],
        *,
        workflow: str | None = None,
        user: str | None = None,
    ) -> dict[str, WorkflowRun | None]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_workflow_runs_batch(
            repo_root, run_ids, workflow=workflow, user=user
        )

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.check_auth_status()
