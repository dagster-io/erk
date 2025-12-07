"""Printing wrapper for GitHub operations."""

from pathlib import Path

import click

from erk_shared.github.abc import GitHub
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import (
    GitHubRepoLocation,
    PRDetails,
    PRNotFound,
    PullRequestInfo,
    RepoInfo,
    WorkflowRun,
)
from erk_shared.printing.base import PrintingBase


class PrintingGitHub(PrintingBase, GitHub):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or Noop).

    Usage:
        # For production
        printing_ops = PrintingGitHub(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGitHub(real_ops)
        printing_ops = PrintingGitHub(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # Read-only operations: delegate without printing

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str:
        """Get PR base branch (read-only, no printing)."""
        return self._wrapped.get_pr_base_branch(repo_root, pr_number)

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs (read-only, no printing)."""
        return self._wrapped.list_workflow_runs(repo_root, workflow, limit, user=user)

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun:
        """Get workflow run details (read-only, no printing)."""
        return self._wrapped.get_workflow_run(repo_root, run_id)

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Get run logs (read-only, no printing)."""
        return self._wrapped.get_run_logs(repo_root, run_id)

    def get_prs_linked_to_issues(
        self,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues (read-only, no printing)."""
        return self._wrapped.get_prs_linked_to_issues(location, issue_numbers)

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get workflow runs by branches (read-only, no printing)."""
        return self._wrapped.get_workflow_runs_by_branches(repo_root, workflow, branches)

    # Operations that need printing

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update PR base branch with printed output."""
        self._emit(self._format_command(f"gh pr edit {pr_number} --base {new_base}"))
        self._wrapped.update_pr_base_branch(repo_root, pr_number, new_base)

    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        """Update PR body with printed output."""
        self._emit(self._format_command(f"gh pr edit {pr_number} --body <body>"))
        self._wrapped.update_pr_body(repo_root, pr_number, body)

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
        """Merge PR with printed output."""
        merge_type = "--squash" if squash else "--merge"
        self._emit(self._format_command(f"gh pr merge {pr_number} {merge_type}"))
        return self._wrapped.merge_pr(
            repo_root, pr_number, squash=squash, verbose=verbose, subject=subject, body=body
        )

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Trigger workflow with printed output.

        Returns:
            The GitHub Actions run ID as a string
        """
        ref_arg = f"--ref {ref} " if ref else ""
        input_args = " ".join(f"-f {key}={value}" for key, value in inputs.items())
        self._emit(self._format_command(f"gh workflow run {workflow} {ref_arg}{input_args}"))
        self._emit(f"   Polling for run (max {15} attempts)...")
        run_id = self._wrapped.trigger_workflow(repo_root, workflow, inputs, ref=ref)
        self._emit(f"-> Run ID: {click.style(run_id, fg='green')}")
        return run_id

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
        """Create PR with printed output.

        Returns:
            PR number
        """
        draft_arg = "--draft " if draft else ""
        base_arg = f"--base {base} " if base is not None else ""
        self._emit(
            self._format_command(
                f'gh pr create --head {branch} {draft_arg}{base_arg}--title "{title}" --body <body>'
            )
        )
        pr_number = self._wrapped.create_pr(repo_root, branch, title, body, base=base, draft=draft)
        self._emit(f"-> PR #{pr_number}")
        return pr_number

    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        """Close PR with printed output."""
        self._emit(self._format_command(f"gh pr close {pr_number}"))
        self._wrapped.close_pr(repo_root, pr_number)

    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Poll for workflow run (read-only, no printing)."""
        return self._wrapped.poll_for_workflow_run(
            repo_root, workflow, branch_name, timeout, poll_interval
        )

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check auth status (read-only, no printing)."""
        return self._wrapped.check_auth_status()

    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Get workflow runs by node IDs (read-only, no printing)."""
        return self._wrapped.get_workflow_runs_by_node_ids(repo_root, node_ids)

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        """Get workflow run node ID (read-only, no printing)."""
        return self._wrapped.get_workflow_run_node_id(repo_root, run_id)

    def get_pr(self, repo_root: Path, pr_number: int) -> PRDetails | PRNotFound:
        """Get comprehensive PR details (read-only, no printing)."""
        return self._wrapped.get_pr(repo_root, pr_number)

    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PRDetails | PRNotFound:
        """Get comprehensive PR details for a branch (read-only, no printing)."""
        return self._wrapped.get_pr_for_branch(repo_root, branch)

    def get_pr_title(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR title (read-only, no printing)."""
        return self._wrapped.get_pr_title(repo_root, pr_number)

    def get_pr_body(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR body (read-only, no printing)."""
        return self._wrapped.get_pr_body(repo_root, pr_number)

    def update_pr_title_and_body(
        self, repo_root: Path, pr_number: int, title: str, body: str
    ) -> None:
        """Update PR title and body with printed output."""
        self._emit(self._format_command(f"gh pr edit {pr_number} --title <title> --body <body>"))
        self._wrapped.update_pr_title_and_body(repo_root, pr_number, title, body)

    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> None:
        """Mark PR as ready with printed output."""
        self._emit(self._format_command(f"gh pr ready {pr_number}"))
        self._wrapped.mark_pr_ready(repo_root, pr_number)

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Get PR diff (read-only, no printing)."""
        return self._wrapped.get_pr_diff(repo_root, pr_number)

    def get_pr_mergeability_status(self, repo_root: Path, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status (read-only, no printing)."""
        return self._wrapped.get_pr_mergeability_status(repo_root, pr_number)

    def get_repo_info(self, repo_root: Path) -> RepoInfo:
        """Get repository info (read-only, no printing)."""
        return self._wrapped.get_repo_info(repo_root)

    def get_issues_with_pr_linkages(
        self,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Get issues with PR linkages (read-only, no printing)."""
        return self._wrapped.get_issues_with_pr_linkages(location, labels, state=state, limit=limit)

    def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
        """Add label to PR with printed output."""
        self._emit(self._format_command(f"gh pr edit {pr_number} --add-label {label}"))
        self._wrapped.add_label_to_pr(repo_root, pr_number, label)

    def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
        """Check if PR has label (read-only, no printing)."""
        return self._wrapped.has_pr_label(repo_root, pr_number, label)
