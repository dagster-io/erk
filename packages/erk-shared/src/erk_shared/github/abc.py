"""Abstract base class for GitHub operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.types import (
    GitHubRepoLocation,
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
    WorkflowRun,
)


class GitHub(ABC):
    """Abstract interface for GitHub operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches in the repository.

        Args:
            repo_root: Repository root directory
            include_checks: If True, fetch CI check status (slower). If False, skip check status

        Returns:
            Mapping of branch name -> PullRequestInfo
            - checks_passing is None when include_checks=False
            Empty dict if gh CLI is not available or not authenticated
        """
        ...

    @abstractmethod
    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status for a specific branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name to check
            debug: If True, print debug information

        Returns:
            PRInfo with state, pr_number, and title
            - state: "OPEN", "MERGED", "CLOSED", or "NONE" if no PR exists
            - pr_number: PR number or None if no PR exists
            - title: PR title or None if no PR exists
        """
        ...

    @abstractmethod
    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str:
        """Get current base branch of a PR from GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            Name of the base branch
        """
        ...

    @abstractmethod
    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update base branch of a PR on GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to update
            new_base: New base branch name
        """
        ...

    @abstractmethod
    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        """Update body of a PR on GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to update
            body: New PR body (markdown)
        """
        ...

    @abstractmethod
    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from GitHub.

        Returns None if PR not found or API error.
        """
        ...

    @abstractmethod
    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Fetch PR titles for all PRs in a single batched GraphQL query.

        This is a lighter-weight alternative to enrich_prs_with_ci_status_batch
        that only fetches titles, not CI status or mergeability.

        Args:
            prs: Mapping of branch name to PullRequestInfo (without titles)
            repo_root: Repository root directory

        Returns:
            Mapping of branch name to PullRequestInfo (with titles enriched)
        """
        ...

    @abstractmethod
    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PR information with CI check status and mergeability using batched GraphQL query.

        Fetches both CI status and mergeability for all PRs in a single GraphQL API call,
        dramatically improving performance over serial fetching.

        Args:
            prs: Mapping of branch name to PullRequestInfo (without CI status or mergeability)
            repo_root: Repository root directory

        Returns:
            Mapping of branch name to PullRequestInfo (with CI status and has_conflicts enriched)
        """
        ...

    @abstractmethod
    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Merge a pull request on GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to merge
            squash: If True, use squash merge strategy (default: True)
            verbose: If True, show detailed output
        """
        ...

    @abstractmethod
    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Trigger a GitHub Actions workflow via gh CLI.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "implement-plan.yml")
            inputs: Workflow inputs as key-value pairs
            ref: Branch or tag to run workflow from (default: repository default branch)

        Returns:
            The GitHub Actions run ID as a string
        """
        ...

    @abstractmethod
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
        """Create a pull request.

        Args:
            repo_root: Repository root directory
            branch: Source branch for the PR
            title: PR title
            body: PR body (markdown)
            base: Target base branch (defaults to trunk branch if None)
            draft: If True, create as draft PR

        Returns:
            PR number
        """
        ...

    @abstractmethod
    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        """Close a pull request without deleting its branch.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to close
        """
        ...

    @abstractmethod
    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "implement-plan.yml")
            limit: Maximum number of runs to return (default: 50)
            user: Optional GitHub username to filter runs by (maps to --user flag)

        Returns:
            List of workflow runs, ordered by creation time (newest first)
        """
        ...

    @abstractmethod
    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun:
        """Get details for a specific workflow run by ID.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID

        Returns:
            WorkflowRun with status and conclusion
        """
        ...

    @abstractmethod
    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Get logs for a workflow run.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID

        Returns:
            Log text as string

        Raises:
            RuntimeError: If gh CLI command fails
        """
        ...

    @abstractmethod
    def get_prs_linked_to_issues(
        self,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues via GitHub's native branch linking.

        Queries GitHub for PRs associated with branches created via
        `gh issue develop`. Returns a mapping of issue numbers to PRs.

        Args:
            location: GitHub repository location (local path + owner/repo identity)
            issue_numbers: List of issue numbers to query

        Returns:
            Mapping of issue_number -> list of PRs linked to that issue.
            Returns empty dict if no PRs link to any of the issues.
        """
        ...

    @abstractmethod
    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get the most relevant workflow run for each branch.

        Queries GitHub Actions for workflow runs and returns the most relevant
        run for each requested branch. Priority order:
        1. In-progress or queued runs (active runs take precedence)
        2. Failed completed runs (failures are more actionable than successes)
        3. Successful completed runs (most recent)

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "dispatch-erk-queue.yml")
            branches: List of branch names to query

        Returns:
            Mapping of branch name -> WorkflowRun or None if no runs found.
            Only includes entries for branches that have matching workflow runs.
        """
        ...

    @abstractmethod
    def poll_for_workflow_run(
        self,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Poll for a workflow run matching branch name within timeout.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "dispatch-erk-queue.yml")
            branch_name: Expected branch name to match
            timeout: Maximum seconds to poll (default: 30)
            poll_interval: Seconds between poll attempts (default: 2)

        Returns:
            Run ID as string if found within timeout, None otherwise
        """
        ...

    @abstractmethod
    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo:
        """Get PR details needed for checkout.

        Fetches the minimal information required to checkout a PR into a worktree:
        - head_ref_name: The branch name in the source repository
        - is_cross_repository: Whether this PR is from a fork
        - state: The PR state (OPEN, CLOSED, MERGED)

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            PRCheckoutInfo with checkout details
        """
        ...

    @abstractmethod
    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status.

        Runs `gh auth status` and parses the output to determine authentication status.
        This is a LBYL check to validate GitHub CLI authentication before operations
        that require it.

        Returns:
            Tuple of (is_authenticated, username, hostname):
            - is_authenticated: True if gh CLI is authenticated
            - username: Authenticated username (e.g., "octocat") or None if not authenticated
            - hostname: GitHub hostname (e.g., "github.com") or None

        Example:
            >>> github.check_auth_status()
            (True, "octocat", "github.com")
            >>> # If not authenticated:
            (False, None, None)
        """
        ...

    @abstractmethod
    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Batch query workflow runs by GraphQL node IDs.

        Uses GraphQL nodes(ids: [...]) query to efficiently fetch multiple
        workflow runs in a single API call. This is dramatically faster than
        individual REST API calls for each run.

        Args:
            repo_root: Repository root directory
            node_ids: List of GraphQL node IDs (e.g., "WFR_kwLOPxC3hc8AAAAEnZK8rQ")

        Returns:
            Mapping of node_id -> WorkflowRun or None if not found.
            Node IDs that don't exist or are inaccessible will have None value.
        """
        ...

    @abstractmethod
    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        """Get the GraphQL node ID for a workflow run.

        This method fetches the node_id from the GitHub API given a workflow run ID.
        The node_id is required for batched GraphQL queries and for updating
        issue metadata synchronously after triggering a workflow.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID (numeric string)

        Returns:
            GraphQL node ID (e.g., "WFR_kwLOPxC3hc8AAAAEnZK8rQ") or None if not found
        """
        ...
