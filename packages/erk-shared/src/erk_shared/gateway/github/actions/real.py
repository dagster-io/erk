"""Production implementation of GitHub Actions operations using gh CLI."""

from pathlib import Path

from erk_shared.gateway.github.actions.abc import GitHubActions
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitHubActions(GitHubActions):
    """Production implementation using gh CLI.

    All GitHub Actions operations execute actual gh commands via subprocess.
    """

    def __init__(self, target_repo: str | None) -> None:
        """Initialize RealGitHubActions.

        Args:
            target_repo: Target repository in "owner/repo" format.
                If set, {owner}/{repo} placeholders are substituted in gh api commands.
                If None, gh CLI uses cwd-based repo detection.
        """
        self._target_repo = target_repo

    def _substitute_repo(self, endpoint: str) -> str:
        """Substitute {owner}/{repo} placeholder in API endpoint."""
        if self._target_repo is not None:
            return endpoint.replace("{owner}/{repo}", self._target_repo)
        return endpoint

    def get_run_jobs(self, repo_root: Path, *, run_id: str) -> str:
        """Get jobs for a workflow run via GitHub REST API."""
        result = run_subprocess_with_context(
            cmd=[
                "gh",
                "api",
                self._substitute_repo(f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}/jobs"),
                "--paginate",
                "--jq",
                '.jobs[] | "\\(.id)\\t\\(.name)"',
            ],
            operation_context=f"fetch jobs for run {run_id}",
            cwd=repo_root,
            check=False,
        )

        if result.returncode != 0:
            return ""

        return result.stdout

    def get_job_logs(self, repo_root: Path, *, job_id: str) -> str | None:
        """Fetch full untruncated logs for a job via the REST API."""
        result = run_subprocess_with_context(
            cmd=[
                "gh",
                "api",
                self._substitute_repo(f"repos/{{owner}}/{{repo}}/actions/jobs/{job_id}/logs"),
            ],
            operation_context=f"fetch logs for job {job_id}",
            cwd=repo_root,
            check=False,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        return result.stdout
