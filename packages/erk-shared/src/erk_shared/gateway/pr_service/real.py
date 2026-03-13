"""Real implementation of PrService for production use."""

import subprocess
from pathlib import Path

from erk.core.context import ErkContext
from erk_shared.gateway.browser.abc import BrowserLauncher
from erk_shared.gateway.clipboard.abc import Clipboard
from erk_shared.gateway.github.ci_summary_parsing import parse_ci_summaries
from erk_shared.gateway.github.metadata.core import (
    extract_objective_from_comment,
    extract_objective_header_comment_id,
)
from erk_shared.gateway.github.types import (
    GitHubRepoLocation,
    PRCheckRun,
    PRNotFound,
    PRReviewThread,
)
from erk_shared.gateway.http.abc import HttpClient
from erk_shared.gateway.pr_service.abc import PrService


class RealPrService(PrService):
    """Production implementation of domain PR operations.

    Contains operations independent of TUI display: closing PRs,
    dispatching, fetching content, and GitHub PR data.
    """

    def __init__(
        self,
        ctx: ErkContext,
        *,
        location: GitHubRepoLocation,
        clipboard: Clipboard,
        browser: BrowserLauncher,
        http_client: HttpClient,
    ) -> None:
        """Initialize with context and repository info.

        Args:
            ctx: ErkContext with all dependencies
            location: GitHub repository location (local root + repo identity)
            clipboard: Clipboard interface for copy operations
            browser: BrowserLauncher interface for opening URLs
            http_client: HTTP client for direct API calls
        """
        self._ctx = ctx
        self._location = location
        self._clipboard = clipboard
        self._browser = browser
        self._http_client = http_client

    @property
    def repo_root(self) -> Path:
        """Get the repository root path."""
        return self._location.root

    @property
    def clipboard(self) -> Clipboard:
        """Get the clipboard interface for copy operations."""
        return self._clipboard

    @property
    def browser(self) -> BrowserLauncher:
        """Get the browser launcher interface for opening URLs."""
        return self._browser

    def close_pr(self, pr_number: int, pr_url: str) -> list[int]:
        """Close a PR using direct HTTP calls.

        Args:
            pr_number: The PR number to close
            pr_url: The PR URL for owner/repo extraction

        Returns:
            Empty list (no linked PRs to close)
        """
        owner_repo = _parse_owner_repo_from_url(pr_url)
        if owner_repo is None:
            return []
        owner, repo = owner_repo

        self._http_client.patch(
            f"repos/{owner}/{repo}/issues/{pr_number}",
            data={"state": "closed"},
        )

        return []

    def dispatch_to_queue(self, pr_number: int, pr_url: str) -> None:
        """Dispatch a PR to the implementation queue.

        Args:
            pr_number: The PR number to dispatch
            pr_url: The PR URL (unused, kept for interface consistency)
        """
        subprocess.run(
            ["erk", "pr", "dispatch", str(pr_number), "-f"],
            cwd=self._location.root,
            check=True,
            capture_output=True,
        )

    def fetch_pr_content(self, pr_number: int, pr_body: str) -> str | None:
        """Return PR content from the PR body.

        Args:
            pr_number: The GitHub PR number
            pr_body: The extracted PR content from the PR body

        Returns:
            The PR content, or None if empty
        """
        return pr_body if pr_body.strip() else None

    def fetch_objective_content(self, pr_number: int, pr_body: str) -> str | None:
        """Fetch objective content from the first comment of an issue.

        Args:
            pr_number: The GitHub issue number
            pr_body: The issue body (to extract objective_comment_id from metadata)

        Returns:
            The extracted objective content, or None if not found
        """
        comment_id = extract_objective_header_comment_id(pr_body)
        if comment_id is None:
            return None

        owner = self._location.repo_id.owner
        repo = self._location.repo_id.repo
        endpoint = f"repos/{owner}/{repo}/issues/comments/{comment_id}"

        response = self._http_client.get(endpoint)
        comment_body = response.get("body", "")

        return extract_objective_from_comment(comment_body)

    def get_branch_stack(self, branch: str) -> list[str] | None:
        """Get the Graphite stack containing a branch.

        Args:
            branch: The branch name to look up

        Returns:
            Ordered list of branch names in the stack, or None
        """
        return self._ctx.branch_manager.get_branch_stack(self._location.root, branch)

    def fetch_check_runs(self, pr_number: int) -> list[PRCheckRun]:
        """Fetch failing check runs for a pull request.

        Args:
            pr_number: The PR number to fetch check runs for

        Returns:
            List of PRCheckRun for failing checks, sorted by name
        """
        return self._ctx.github.get_pr_check_runs(self._location.root, pr_number)

    def fetch_unresolved_comments(self, pr_number: int) -> list[PRReviewThread]:
        """Fetch unresolved review threads for a pull request.

        Args:
            pr_number: The PR number to fetch threads for

        Returns:
            List of unresolved PRReviewThread objects sorted by (path, line)
        """
        return self._ctx.github.get_pr_review_threads(
            self._location.root, pr_number, include_resolved=False
        )

    def fetch_ci_summaries(self, pr_number: int, *, comment_id: int | None) -> dict[str, str]:
        """Fetch CI failure summaries for a pull request.

        If comment_id is provided, fetches the comment directly (1 API call).
        Otherwise falls back to the 4-call path: get PR → find run → find
        ci-summarize job → fetch logs.

        Args:
            pr_number: The PR number to fetch summaries for
            comment_id: Optional GitHub comment ID containing CI summaries

        Returns:
            Mapping of check name to summary text, or empty dict
        """
        # Fast path: fetch directly from comment
        if comment_id is not None:
            body = self._ctx.github.get_pr_comment(self._location.root, comment_id)
            if body is not None:
                summaries = parse_ci_summaries(body)
                if summaries:
                    return summaries
            # Fall through to slow path if comment missing or no markers

        # Slow path: get PR → find run → find ci-summarize job → fetch logs
        pr_result = self._ctx.github.get_pr(self._location.root, pr_number)
        if isinstance(pr_result, PRNotFound):
            return {}

        runs_by_branch = self._ctx.github.get_workflow_runs_by_branches(
            self._location.root, "ci.yml", [pr_result.head_ref_name]
        )
        run = runs_by_branch.get(pr_result.head_ref_name)
        if run is None:
            return {}

        log_text = self._ctx.github.get_ci_summary_logs(self._location.root, str(run.run_id))
        if log_text is None:
            return {}

        return parse_ci_summaries(log_text)


def _parse_owner_repo_from_url(url: str) -> tuple[str, str] | None:
    """Parse owner and repo from a GitHub URL.

    Args:
        url: GitHub URL (e.g., "https://github.com/owner/repo/issues/123")

    Returns:
        Tuple of (owner, repo) or None if parsing fails
    """
    if not url.startswith("https://github.com/"):
        return None
    parts = url.split("/")
    if len(parts) < 5:
        return None
    return (parts[3], parts[4])
