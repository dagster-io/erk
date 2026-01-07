"""Abstract base class for GitHub operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import (
    GitHubRepoLocation,
    PRDetails,
    PRListState,
    PRNotFound,
    PRReviewThread,
    PullRequestInfo,
    WorkflowRun,
)


class GitHub(ABC):
    """Abstract interface for GitHub operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            Name of the base branch, or None if PR not found
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
    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
        subject: str | None = None,
        body: str | None = None,
    ) -> bool | str:
        """Merge a pull request on GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to merge
            squash: If True, use squash merge strategy (default: True)
            verbose: If True, show detailed output
            subject: Optional commit message subject for squash merge.
                     If provided, overrides GitHub's default behavior.
            body: Optional commit message body for squash merge.
                  If provided, included as the commit body text.

        Returns:
            True on success, error message string on failure
        """
        ...

    @abstractmethod
    def trigger_workflow(
        self, *, repo_root: Path, workflow: str, inputs: dict[str, str], ref: str | None = None
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
    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Get details for a specific workflow run by ID.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID

        Returns:
            WorkflowRun with status and conclusion, or None if not found
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
        """Get PRs linked to issues via GitHub's development references.

        Queries GitHub for PRs that reference issues in their description
        or via GitHub's "Closes #N" linking. Returns a mapping of issue
        numbers to PRs.

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
        *,
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

    @abstractmethod
    def get_issues_with_pr_linkages(
        self,
        *,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
        creator: str | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Fetch issues and linked PRs in a single GraphQL query.

        Uses repository.issues() connection with inline timelineItems
        to get PR linkages in one API call. This is significantly faster
        than separate calls for issues and PR linkages.

        Args:
            location: GitHub repository location (local root + repo identity)
            labels: Labels to filter by (e.g., ["erk-plan"])
            state: Filter by state ("open", "closed", or None for all)
            limit: Maximum issues to return (default: 100)
            creator: Filter by creator username (e.g., "octocat"). If provided,
                only issues created by this user are returned.

        Returns:
            Tuple of (issues, pr_linkages) where:
            - issues: List of IssueInfo objects
            - pr_linkages: Mapping of issue_number -> list of linked PRs
        """
        ...

    @abstractmethod
    def get_pr(self, repo_root: Path, pr_number: int) -> PRDetails | PRNotFound:
        """Get comprehensive PR details in a single API call.

        This is the preferred method for fetching PR information. It returns
        all commonly-needed fields in one API call, avoiding multiple separate
        calls for title, body, base branch, etc.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            PRDetails with all PR fields, or PRNotFound if PR doesn't exist
        """
        ...

    @abstractmethod
    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PRDetails | PRNotFound:
        """Get comprehensive PR details for a branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name to look up

        Returns:
            PRDetails if a PR exists for the branch, PRNotFound otherwise
        """
        ...

    @abstractmethod
    def list_prs(
        self,
        repo_root: Path,
        *,
        state: PRListState,
    ) -> dict[str, PullRequestInfo]:
        """List PRs for the repository, keyed by head branch name.

        Fetches PRs from GitHub API in a single REST API call.
        This is used as a fallback when Graphite cache is unavailable.

        Args:
            repo_root: Repository root directory
            state: Filter by state - "open", "closed", or "all"

        Returns:
            Dict mapping head branch name to PullRequestInfo.
            Empty dict if no PRs match or on API failure.
        """
        ...

    @abstractmethod
    def get_pr_title(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR title by number.

        Args:
            repo_root: Repository root directory
            pr_number: PR number

        Returns:
            PR title string, or None if PR not found
        """
        ...

    @abstractmethod
    def get_pr_body(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR body by number.

        Args:
            repo_root: Repository root directory
            pr_number: PR number

        Returns:
            PR body string, or None if PR not found
        """
        ...

    @abstractmethod
    def update_pr_title_and_body(
        self, *, repo_root: Path, pr_number: int, title: str, body: str
    ) -> None:
        """Update PR title and body.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to update
            title: New PR title
            body: New PR body

        Raises:
            RuntimeError: If gh command fails
        """
        ...

    @abstractmethod
    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> None:
        """Mark a draft PR as ready for review.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to mark as ready

        Raises:
            RuntimeError: If gh command fails
        """
        ...

    @abstractmethod
    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Get the diff for a PR.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to get diff for

        Returns:
            Diff content as string

        Raises:
            RuntimeError: If gh command fails
        """
        ...

    @abstractmethod
    def get_pr_mergeability_status(self, repo_root: Path, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from GitHub API.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to check

        Returns:
            Tuple of (mergeable, merge_state_status):
            - mergeable: "MERGEABLE", "CONFLICTING", or "UNKNOWN"
            - merge_state_status: "CLEAN", "DIRTY", "UNSTABLE", etc.
        """
        ...

    @abstractmethod
    def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
        """Add a label to a pull request.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to add label to
            label: Label name to add

        Raises:
            RuntimeError: If gh command fails
        """
        ...

    @abstractmethod
    def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
        """Check if a PR has a specific label.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to check
            label: Label name to check for

        Returns:
            True if the PR has the label, False otherwise
        """
        ...

    @abstractmethod
    def get_pr_review_threads(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        include_resolved: bool = False,
    ) -> list[PRReviewThread]:
        """Get review threads for a pull request.

        Uses GraphQL API (reviewThreads connection) since REST API
        doesn't expose resolution status.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query
            include_resolved: If True, include resolved threads (default: False)

        Returns:
            List of PRReviewThread sorted by (path, line)
        """
        ...

    @abstractmethod
    def resolve_review_thread(
        self,
        repo_root: Path,
        thread_id: str,
    ) -> bool:
        """Resolve a PR review thread.

        Args:
            repo_root: Repository root (for owner/repo context)
            thread_id: GraphQL node ID of the thread

        Returns:
            True if resolved successfully
        """
        ...

    @abstractmethod
    def add_review_thread_reply(
        self,
        repo_root: Path,
        thread_id: str,
        body: str,
    ) -> bool:
        """Add a reply comment to a PR review thread.

        Args:
            repo_root: Repository root (for owner/repo context)
            thread_id: GraphQL node ID of the thread
            body: Comment body text

        Returns:
            True if comment added successfully
        """
        ...

    @abstractmethod
    def create_pr_review_comment(
        self, *, repo_root: Path, pr_number: int, body: str, commit_sha: str, path: str, line: int
    ) -> int:
        """Create an inline review comment on a specific line of a PR.

        Uses GitHub REST API to create a pull request review comment
        attached to a specific line of a file in the PR diff.

        Args:
            repo_root: Repository root (for gh CLI context)
            pr_number: PR number to comment on
            body: Comment body text (markdown supported)
            commit_sha: The SHA of the commit to comment on (PR head commit)
            path: Relative path to the file being commented on
            line: Line number in the diff to attach the comment to

        Returns:
            Comment ID of the created comment
        """
        ...

    @abstractmethod
    def find_pr_comment_by_marker(
        self,
        repo_root: Path,
        pr_number: int,
        marker: str,
    ) -> int | None:
        """Find a PR/issue comment containing a specific HTML marker.

        Searches PR comments for one containing the marker string
        (typically an HTML comment like <!-- marker-name -->).

        Args:
            repo_root: Repository root (for gh CLI context)
            pr_number: PR number to search comments in
            marker: String to search for in comment body

        Returns:
            Comment database ID if found, None otherwise
        """
        ...

    @abstractmethod
    def update_pr_comment(
        self,
        repo_root: Path,
        comment_id: int,
        body: str,
    ) -> None:
        """Update an existing PR/issue comment.

        Args:
            repo_root: Repository root (for gh CLI context)
            comment_id: Database ID of the comment to update
            body: New comment body text

        Raises:
            RuntimeError: If update fails
        """
        ...

    @abstractmethod
    def create_pr_comment(
        self,
        repo_root: Path,
        pr_number: int,
        body: str,
    ) -> int:
        """Create a new comment on a PR.

        This creates a general PR discussion comment, not an inline
        review comment on a specific line.

        Args:
            repo_root: Repository root (for gh CLI context)
            pr_number: PR number to comment on
            body: Comment body text

        Returns:
            Database ID of the created comment
        """
        ...

    @abstractmethod
    def delete_remote_branch(self, repo_root: Path, branch: str) -> bool:
        """Delete a remote branch via REST API.

        This method is used to delete the remote branch after a PR merge,
        avoiding the use of `gh pr merge --delete-branch` which attempts
        local branch operations that fail from git worktrees.

        Args:
            repo_root: Repository root directory (for gh CLI context)
            branch: Name of the branch to delete (without 'refs/heads/' prefix)

        Returns:
            True if the branch was deleted or didn't exist,
            False if deletion failed (e.g., protected branch)
        """
        ...
