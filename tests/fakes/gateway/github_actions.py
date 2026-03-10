"""In-memory fake implementation of GitHub Actions for testing."""

from pathlib import Path

from erk_shared.gateway.github.actions.abc import GitHubActions


class FakeGitHubActions(GitHubActions):
    """In-memory fake implementation for testing.

    All state is provided via constructor using keyword arguments.
    """

    def __init__(
        self,
        *,
        run_jobs: dict[str, str] | None = None,
        job_logs: dict[str, str | None] | None = None,
    ) -> None:
        """Create FakeGitHubActions with pre-configured state.

        Args:
            run_jobs: Mapping of run_id -> tab-separated job listing.
                Each value is "job_id\\tjob_name\\n..." format.
            job_logs: Mapping of job_id -> log text (or None for failure).
        """
        self._run_jobs: dict[str, str] = run_jobs if run_jobs is not None else {}
        self._job_logs: dict[str, str | None] = job_logs if job_logs is not None else {}

    def get_run_jobs(self, repo_root: Path, *, run_id: str) -> str:
        """Return pre-configured job listing for the run ID."""
        return self._run_jobs.get(run_id, "")

    def get_job_logs(self, repo_root: Path, *, job_id: str) -> str | None:
        """Return pre-configured log text for the job ID."""
        return self._job_logs.get(job_id)
