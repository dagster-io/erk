"""Abstract base class for GitHub operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.types import (
    BodyContent,
    GitHubRepoLocation,
    IssueFilterState,
    MergeError,
    MergeResult,
    PRCheckRun,
    PRDetails,
    PRListState,
    PRNotFound,
    PRReviewThread,
    PullRequestInfo,
    WorkflowRun,
)

if TYPE_CHECKING:
    from erk_shared.gateway.github.issues.abc import GitHubIssues


class LocalGitHub(ABC):
    """Abstract interface for GitHub operations.

    All implementations (real and fake) must implement this interface.
    """

    @property
    @abstractmethod
    def issues(self) -> GitHubIssues:
        """Access to issue operations.

        Returns the composed GitHubIssues gateway for issue-related operations.
        All issue operations should be accessed via ctx.github.issues.
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
        squash: bool,
        verbose: bool,
        subject: str | None = None,
        body: str | None = None,
    ) -> MergeResult | MergeError:
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
            MergeResult on success, MergeError on failure
        """
        ...

    @abstractmethod
    def trigger_workflow(
        self, *, repo_root: Path, workflow: str, inputs: dict[str, str], ref: str | None
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
    def list_all_workflow_runs(
        self, repo_root: Path, *, limit: int, actor: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs across all workflows in the repository.

        Uses a single REST API call to fetch runs from all workflows,
        instead of one call per workflow. Each returned WorkflowRun has
        workflow_path populated for caller-side workflow name mapping.

        Args:
            repo_root: Repository root directory
            limit: Maximum number of runs to return (default: 100)
            actor: Optional GitHub username to filter runs by (maps to actor query param)

        Returns:
            List of workflow runs with workflow_path populated,
            ordered by creation time (newest first)
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
    def get_ci_summary_logs(self, repo_root: Path, run_id: str) -> str | None:
        """Fetch logs from the ci-summarize job in a workflow run.

        Looks for a job named "ci-summarize" in the given run and returns
        its raw log text containing ERK-CI-SUMMARY markers.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID

        Returns:
            Raw log text from the ci-summarize job, or None if the job
            doesn't exist or hasn't completed yet
        """
        ...

    @abstractmethod
    def get_pr_comment(self, repo_root: Path, comment_id: int) -> str | None:
        """Fetch a single PR/issue comment by its ID.

        Uses the GitHub REST API to retrieve the comment body.

        Args:
            repo_root: Repository root directory
            comment_id: GitHub comment ID

        Returns:
            Comment body text, or None if the comment doesn't exist
        """
        ...

    @abstractmethod
    def get_prs_by_numbers(
        self, location: GitHubRepoLocation, pr_numbers: list[int]
    ) -> dict[int, PullRequestInfo]:
        """Batch fetch PR info for specific PR numbers.

        Uses a single GraphQL query to fetch PR details for the given
        numbers. More efficient than list_prs(state="all") when only
        a handful of specific PRs are needed.

        Args:
            location: GitHub repository location (local path + owner/repo identity)
            pr_numbers: List of PR numbers to fetch

        Returns:
            Mapping of pr_number -> PullRequestInfo for found PRs.
            PRs that don't exist are omitted from the result.
        """
        ...

    @abstractmethod
    def get_pr_head_branches(
        self, location: GitHubRepoLocation, pr_numbers: list[int]
    ) -> dict[int, str]:
        """Get head branch names for a list of PR numbers.

        Batch-fetches the headRefName for each PR in a single GraphQL query.
        Used to resolve the actual target branch for workflow_dispatch runs,
        where head_branch from the GitHub API is always the default branch.

        Args:
            location: GitHub repository location (local path + owner/repo identity)
            pr_numbers: List of PR numbers to query

        Returns:
            Mapping of pr_number -> head branch name.
            PRs that don't exist or can't be fetched are omitted.
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
        state: IssueFilterState = "open",
        limit: int | None = None,
        creator: str | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Fetch issues and linked PRs in a single GraphQL query.

        Uses repository.issues() connection with inline timelineItems
        to get PR linkages in one API call. This is significantly faster
        than separate calls for issues and PR linkages.

        Args:
            location: GitHub repository location (local root + repo identity)
            labels: Labels to filter by (e.g., ["erk-pr"])
            state: Filter by state ("open" or "closed")
            limit: Maximum issues to return (default: 100)
            creator: Filter by creator username (e.g., "octocat"). If provided,
                only issues created by this user are returned.

        Returns:
            Tuple of (issues, pr_linkages) where:
            - issues: List of IssueInfo objects
            - pr_linkages: Mapping of plan_number -> list of linked PRs
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
        labels: list[str] | None = None,
        author: str | None = None,
        draft: bool | None = None,
    ) -> dict[str, PullRequestInfo]:
        """List PRs for the repository, keyed by head branch name.

        Fetches PRs from GitHub API in a single REST API call.
        This is used as a fallback when Graphite cache is unavailable.

        Args:
            repo_root: Repository root directory
            state: Filter by state - "open", "closed", or "all"
            labels: Filter to PRs with ALL specified labels. None means no label filter.
            author: Filter to PRs by this author username. None means no author filter.
            draft: Filter by draft status. True=only drafts, False=only non-drafts,
                None=no draft filter.

        Returns:
            Dict mapping head branch name to PullRequestInfo.
            Empty dict if no PRs match or on API failure.
        """
        ...

    @abstractmethod
    def list_plan_prs_with_details(
        self,
        location: GitHubRepoLocation,
        *,
        labels: list[str],
        state: IssueFilterState,
        limit: int | None,
        author: str | None,
        exclude_labels: list[str] | None = None,
    ) -> tuple[list[PRDetails], dict[int, list[PullRequestInfo]], int]:
        """List plan PRs with rich details.

        Uses a two-step approach: REST issues endpoint for server-side
        author/label filtering, then batched GraphQL enrichment for rich
        PR fields (checks, review threads, merge status).

        Args:
            location: GitHub repository location
            labels: Labels to filter by (e.g., ["erk-pr"])
            state: Filter by state ("open" or "closed")
            limit: Maximum number of results (None for no limit)
            author: Filter by PR author username (server-side via REST creator param)
            exclude_labels: Labels to exclude from results (client-side filtering
                applied before expensive GraphQL enrichment). None means no exclusion.

        Returns:
            Tuple of (pr_details_list, pr_linkages_by_pr_number, unenriched_count).
            unenriched_count indicates how many PRs lacked GraphQL enrichment data.
        """
        ...

    @abstractmethod
    def update_pr_title_and_body(
        self, *, repo_root: Path, pr_number: int, title: str, body: BodyContent
    ) -> None:
        """Update PR title and body.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to update
            title: New PR title
            body: New PR body - either BodyText with inline content, or
                BodyFile with a path to read from. When BodyFile is provided,
                the gh CLI reads from the file using -F body=@{path} syntax,
                which avoids shell argument length limits for large bodies.

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
    def get_pr_changed_files(self, repo_root: Path, pr_number: int) -> list[str]:
        """Get list of files changed in a pull request.

        Uses GitHub REST API with pagination to handle large PRs that may
        have hundreds of changed files.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            List of file paths changed in the PR.

        Raises:
            RuntimeError: If gh command fails
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
    def get_pr_check_runs(
        self,
        repo_root: Path,
        pr_number: int,
    ) -> list[PRCheckRun]:
        """Get failing check runs for a pull request.

        Queries the PR's statusCheckRollup via GraphQL and returns only
        failing checks (non-success conclusion), sorted by name.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            List of PRCheckRun for failing checks, sorted by name
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
    def fetch_pr_comments(
        self,
        repo_root: Path,
        pr_number: int,
    ) -> list[dict[str, Any]]:
        """Fetch all issue/PR comments as a list of dicts.

        Returns raw comment data from the GitHub API. Each dict contains
        at minimum "id" and "body" keys.

        Args:
            repo_root: Repository root (for gh CLI context)
            pr_number: PR number to fetch comments for

        Returns:
            List of comment dicts, or empty list on failure
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

    @abstractmethod
    def get_open_prs_with_base_branch(
        self, repo_root: Path, base_branch: str
    ) -> list[PullRequestInfo]:
        """Get all open PRs that have the given branch as their base.

        Used to find child PRs that need their base updated before
        landing a parent PR (prevents GitHub auto-close on base deletion).

        Args:
            repo_root: Repository root directory
            base_branch: The base branch name to filter by

        Returns:
            List of PullRequestInfo for open PRs targeting the given base branch.
            Empty list if no PRs match or on API failure.
        """
        ...

    @abstractmethod
    def download_run_artifact(
        self,
        repo_root: Path,
        run_id: str,
        artifact_name: str,
        destination: Path,
    ) -> bool:
        """Download an artifact from a GitHub Actions workflow run.

        Downloads the named artifact from the specified workflow run
        to the given destination directory.

        Args:
            repo_root: Repository root directory (for gh CLI context)
            run_id: GitHub Actions run ID
            artifact_name: Name of the artifact to download
            destination: Directory path to download artifact to

        Returns:
            True if the artifact was downloaded successfully, False otherwise
        """
        ...

    @abstractmethod
    def get_issues_by_numbers_with_pr_linkages(
        self,
        *,
        location: GitHubRepoLocation,
        plan_numbers: list[int],
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Fetch specific issues by number with full PR linkage data.

        Uses issueOrPullRequest(number: N) to handle both issues and merged PRs.
        Returns issue data and PR linkages in the same format as
        get_issues_with_pr_linkages for compatibility.

        Args:
            location: GitHub repository location (local root + repo identity)
            plan_numbers: List of plan/PR numbers to fetch

        Returns:
            Tuple of (issues, pr_linkages) where:
            - issues: List of IssueInfo objects for found issues
            - pr_linkages: Mapping of plan_number -> list of linked PRs
        """
        ...

    @abstractmethod
    def cancel_workflow_run(self, repo_root: Path, run_id: str) -> None:
        """Cancel an in-progress or queued workflow run.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID to cancel
        """
        ...

    @abstractmethod
    def rerun_workflow_run(self, repo_root: Path, run_id: str, *, failed_only: bool) -> None:
        """Re-run a completed workflow run.

        Args:
            repo_root: Repository root directory
            run_id: GitHub Actions run ID to re-run
            failed_only: If True, only re-run failed jobs
        """
        ...

    @abstractmethod
    def create_commit_status(
        self,
        *,
        repo: str,
        sha: str,
        state: str,
        context: str,
        description: str,
    ) -> bool:
        """Create a commit status on GitHub.

        Sets a commit status (check) for CI verification purposes.

        Args:
            repo: GitHub repository (owner/repo format)
            sha: Commit SHA to set status for
            state: Status state - one of "success", "failure", "pending", "error"
            context: Context name for the status (e.g., "ci / lint (autofix-verified)")
            description: Description of the status

        Returns:
            True on success, False on failure
        """
        ...
