"""Abstract interface for GitHub Actions operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitHubActions(ABC):
    """Abstract interface for GitHub Actions operations.

    Provides access to workflow run jobs and job logs via the GitHub REST API.
    All implementations (real, dry-run, fake) must implement this interface.
    """

    @abstractmethod
    def get_run_jobs(self, repo_root: Path, *, run_id: str) -> str:
        """Get jobs for a workflow run as tab-separated lines.

        Uses the GitHub REST API to list jobs for the given run,
        returning each job as "job_id\\tjob_name" on separate lines.

        Args:
            repo_root: Repository root directory (for gh CLI context)
            run_id: Numeric GitHub Actions run ID

        Returns:
            Tab-separated job listing (one "id\\tname" per line),
            or empty string if the API call fails
        """
        ...

    @abstractmethod
    def get_job_logs(self, repo_root: Path, *, job_id: str) -> str | None:
        """Fetch full untruncated logs for a job via the REST API.

        Args:
            repo_root: Repository root directory (for gh CLI context)
            job_id: GitHub Actions job ID

        Returns:
            Full job log text, or None on failure
        """
        ...
