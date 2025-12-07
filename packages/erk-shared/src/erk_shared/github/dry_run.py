"""No-op wrapper for GitHub operations."""

from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import (
    GitHubRepoLocation,
    PRDetails,
    PullRequestInfo,
    RepoInfo,
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

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str:
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

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
        subject: str | None = None,
        body: str | None = None,
    ) -> bool:
        """No-op for merging PR in dry-run mode."""
        # Do nothing - prevents actual PR merge
        return True

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

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_workflow_run(repo_root, run_id)

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_run_logs(repo_root, run_id)

    def get_prs_linked_to_issues(
        self,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> dict[int, list[PullRequestInfo]]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_prs_linked_to_issues(location, issue_numbers)

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

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.check_auth_status()

    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_workflow_runs_by_node_ids(repo_root, node_ids)

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_workflow_run_node_id(repo_root, run_id)

    def get_issues_with_pr_linkages(
        self,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_issues_with_pr_linkages(location, labels, state=state, limit=limit)

    def get_pr(self, repo_root: Path, pr_number: int) -> PRDetails:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr(repo_root, pr_number)

    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PRDetails | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_for_branch(repo_root, branch)

    def get_pr_title(self, repo_root: Path, pr_number: int) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_title(repo_root, pr_number)

    def get_pr_body(self, repo_root: Path, pr_number: int) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_body(repo_root, pr_number)

    def update_pr_title_and_body(
        self, repo_root: Path, pr_number: int, title: str, body: str
    ) -> None:
        """No-op for updating PR title and body in dry-run mode."""
        pass

    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> None:
        """No-op for marking PR ready in dry-run mode."""
        pass

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_diff(repo_root, pr_number)

    def get_pr_mergeability_status(self, repo_root: Path, pr_number: int) -> tuple[str, str]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_pr_mergeability_status(repo_root, pr_number)

    def get_repo_info(self, repo_root: Path) -> RepoInfo:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_repo_info(repo_root)

    def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
        """No-op for adding label to PR in dry-run mode."""
        pass

    def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.has_pr_label(repo_root, pr_number, label)
