"""Dry-run wrapper for GitHub Actions operations."""

from pathlib import Path

from erk_shared.gateway.github.actions.abc import GitHubActions


class DryRunGitHubActions(GitHubActions):
    """Dry-run wrapper for GitHub Actions operations.

    Both methods are read-only, so they delegate to the wrapped implementation.
    """

    def __init__(self, wrapped: GitHubActions) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real GitHubActions implementation to wrap
        """
        self._wrapped = wrapped

    def get_run_jobs(self, repo_root: Path, *, run_id: str) -> str:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_run_jobs(repo_root, run_id=run_id)

    def get_job_logs(self, repo_root: Path, *, job_id: str) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_job_logs(repo_root, job_id=job_id)
