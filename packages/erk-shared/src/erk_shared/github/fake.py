"""Fake GitHub operations for testing.

FakeGitHub is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import (
    GitHubRepoLocation,
    PRDetails,
    PRListState,
    PRNotFound,
    PRReviewThread,
    PullRequestInfo,
    RepoInfo,
    WorkflowRun,
)


class FakeGitHub(GitHub):
    """In-memory fake implementation of GitHub operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults (empty dicts).
    """

    def __init__(
        self,
        *,
        repo_info: RepoInfo | None = None,
        prs: dict[str, PullRequestInfo] | None = None,
        pr_bases: dict[int, str] | None = None,
        pr_details: dict[int, PRDetails] | None = None,
        workflow_runs: list[WorkflowRun] | None = None,
        workflow_runs_by_node_id: dict[str, WorkflowRun] | None = None,
        run_logs: dict[str, str] | None = None,
        pr_issue_linkages: dict[int, list[PullRequestInfo]] | None = None,
        polled_run_id: str | None = None,
        authenticated: bool = True,
        auth_username: str | None = "test-user",
        auth_hostname: str | None = "github.com",
        issues: list[IssueInfo] | None = None,
        pr_titles: dict[int, str] | None = None,
        pr_bodies_by_number: dict[int, str] | None = None,
        pr_diffs: dict[int, str] | None = None,
        merge_should_succeed: bool = True,
        pr_update_should_succeed: bool = True,
        pr_review_threads: dict[int, list[PRReviewThread]] | None = None,
        review_threads_rate_limited: bool = False,
        pr_diff_error: str | None = None,
        workflow_runs_error: str | None = None,
    ) -> None:
        """Create FakeGitHub with pre-configured state.

        Args:
            repo_info: Repository owner/name info (defaults to test-owner/test-repo)
            prs: Mapping of branch name -> PullRequestInfo
            pr_bases: Mapping of pr_number -> base_branch
            pr_details: Mapping of pr_number -> PRDetails for get_pr() and get_pr_for_branch()
            workflow_runs: List of WorkflowRun objects to return from list_workflow_runs
            workflow_runs_by_node_id: Mapping of GraphQL node_id -> WorkflowRun for
                                     get_workflow_runs_by_node_ids()
            run_logs: Mapping of run_id -> log string
            pr_issue_linkages: Mapping of issue_number -> list[PullRequestInfo]
            polled_run_id: Run ID to return from poll_for_workflow_run (None for timeout)
            authenticated: Whether gh CLI is authenticated (default True for test convenience)
            auth_username: Username returned by check_auth_status() (default "test-user")
            auth_hostname: Hostname returned by check_auth_status() (default "github.com")
            issues: List of IssueInfo objects for get_issues_with_pr_linkages()
            pr_titles: Mapping of pr_number -> title for explicit title storage
            pr_bodies_by_number: Mapping of pr_number -> body for explicit body storage
            pr_diffs: Mapping of pr_number -> diff content
            merge_should_succeed: Whether merge_pr() should succeed (default True)
            pr_update_should_succeed: Whether PR updates should succeed (default True)
            pr_review_threads: Mapping of pr_number -> list[PRReviewThread]
            review_threads_rate_limited: Whether get_pr_review_threads() should raise
                RuntimeError simulating GraphQL rate limit
            pr_diff_error: If set, get_pr_diff() raises RuntimeError with this message.
                Use to simulate HTTP 406 "diff too large" errors.
            workflow_runs_error: If set, get_workflow_runs_by_node_ids() raises
                RuntimeError with this message. Use to simulate API failures.
        """
        # Default to test values if not provided
        self._repo_info = repo_info or RepoInfo(owner="test-owner", name="test-repo")
        self._prs = prs or {}
        self._pr_bases = pr_bases or {}
        self._pr_details = pr_details or {}
        self._workflow_runs = workflow_runs or []
        self._workflow_runs_by_node_id = workflow_runs_by_node_id or {}
        self._run_logs = run_logs or {}
        self._pr_issue_linkages = pr_issue_linkages or {}
        self._polled_run_id = polled_run_id
        self._authenticated = authenticated
        self._auth_username = auth_username
        self._auth_hostname = auth_hostname
        self._issues = issues or []
        self._pr_titles = pr_titles or {}
        self._pr_bodies_by_number = pr_bodies_by_number or {}
        self._pr_diffs = pr_diffs or {}
        self._merge_should_succeed = merge_should_succeed
        self._pr_update_should_succeed = pr_update_should_succeed
        self._pr_review_threads = pr_review_threads or {}
        self._review_threads_rate_limited = review_threads_rate_limited
        self._pr_diff_error = pr_diff_error
        self._workflow_runs_error = workflow_runs_error
        self._updated_pr_bases: list[tuple[int, str]] = []
        self._updated_pr_bodies: list[tuple[int, str]] = []
        self._updated_pr_titles: list[tuple[int, str]] = []
        self._merged_prs: list[int] = []
        self._closed_prs: list[int] = []
        self._triggered_workflows: list[tuple[str, dict[str, str]]] = []
        self._poll_attempts: list[tuple[str, str, int, int]] = []
        self._check_auth_status_calls: list[None] = []
        self._created_prs: list[tuple[str, str, str, str | None, bool]] = []
        self._pr_labels: dict[int, set[str]] = {}
        self._added_labels: list[tuple[int, str]] = []
        self._pr_review_threads = pr_review_threads or {}
        self._resolved_thread_ids: set[str] = set()
        self._thread_replies: list[tuple[str, str]] = []
        self._pr_review_comments: list[tuple[int, str, str, str, int]] = []
        self._pr_comments: list[tuple[int, str]] = []
        self._pr_comment_updates: list[tuple[int, str]] = []
        self._next_comment_id = 1000000
        self._deleted_remote_branches: list[str] = []

    @property
    def merged_prs(self) -> list[int]:
        """List of PR numbers that were merged."""
        return self._merged_prs

    @property
    def closed_prs(self) -> list[int]:
        """Read-only access to tracked PR closures for test assertions."""
        return self._closed_prs

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from configured state.

        Returns None if PR number not found.
        """
        return self._pr_bases.get(pr_number)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Record PR base branch update in mutation tracking list."""
        self._updated_pr_bases.append((pr_number, new_base))

    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        """Record PR body update in mutation tracking list.

        Raises RuntimeError if pr_update_should_succeed is False.
        """
        if not self._pr_update_should_succeed:
            raise RuntimeError("PR update failed (configured to fail)")
        self._updated_pr_bodies.append((pr_number, body))

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
        """Record PR merge in mutation tracking list.

        Returns True on success, error message string on failure.
        """
        if self._merge_should_succeed:
            self._merged_prs.append(pr_number)
            return True
        return "Merge failed (configured to fail in test)"

    def trigger_workflow(
        self, *, repo_root: Path, workflow: str, inputs: dict[str, str], ref: str | None = None
    ) -> str:
        """Record workflow trigger in mutation tracking list.

        Note: In production, trigger_workflow() generates a distinct_id internally
        and adds it to the inputs. Tests should verify the workflow was called
        with expected inputs; the distinct_id is an internal implementation detail.

        Also creates a WorkflowRun entry so get_workflow_run() can find it.
        This simulates the real behavior where triggering a workflow creates a run.

        Returns:
            A fake run ID for testing
        """
        self._triggered_workflows.append((workflow, inputs))
        run_id = "1234567890"
        # Create a WorkflowRun entry so get_workflow_run() can find it
        # Use branch_name from inputs if available
        branch = inputs.get("branch_name", "main")
        triggered_run = WorkflowRun(
            run_id=run_id,
            status="queued",
            conclusion=None,
            branch=branch,
            head_sha="abc123",
            node_id=f"WFR_{run_id}",
        )
        # Prepend to list so it's found first (most recent)
        self._workflow_runs.insert(0, triggered_run)
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
        """Record PR creation in mutation tracking list.

        Returns:
            A fake PR number for testing
        """
        self._created_prs.append((branch, title, body, base, draft))
        # Return a fake PR number
        return 999

    @property
    def created_prs(self) -> list[tuple[str, str, str, str | None, bool]]:
        """Read-only access to tracked PR creations for test assertions.

        Returns list of (branch, title, body, base, draft) tuples.
        """
        return self._created_prs

    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        """Record PR closure in mutation tracking list."""
        self._closed_prs.append(pr_number)

    @property
    def updated_pr_bases(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR base updates for test assertions."""
        return self._updated_pr_bases

    @property
    def updated_pr_bodies(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR body updates for test assertions."""
        return self._updated_pr_bodies

    @property
    def updated_pr_titles(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR title updates for test assertions."""
        return self._updated_pr_titles

    @property
    def triggered_workflows(self) -> list[tuple[str, dict[str, str]]]:
        """Read-only access to tracked workflow triggers for test assertions."""
        return self._triggered_workflows

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow (returns pre-configured data).

        Returns the pre-configured list of workflow runs. The workflow, limit and user
        parameters are accepted but ignored - fake returns all pre-configured runs.
        """
        return self._workflow_runs

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Get details for a specific workflow run by ID (returns pre-configured data).

        Args:
            repo_root: Repository root directory (ignored in fake)
            run_id: GitHub Actions run ID to lookup

        Returns:
            WorkflowRun if found in pre-configured data, None otherwise
        """
        for run in self._workflow_runs:
            if run.run_id == run_id:
                return run
        return None

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Return pre-configured log string for run_id.

        Raises RuntimeError if run_id not found, mimicking gh CLI behavior.
        """
        if run_id not in self._run_logs:
            msg = f"Run {run_id} not found"
            raise RuntimeError(msg)
        return self._run_logs[run_id]

    def get_prs_linked_to_issues(
        self,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues (returns pre-configured data).

        Returns only the mappings for issues in issue_numbers that have
        pre-configured PR linkages. Issues without linkages are omitted.

        The location parameter is accepted but ignored - fake returns
        pre-configured data regardless of the location.
        """
        result = {}
        for issue_num in issue_numbers:
            if issue_num in self._pr_issue_linkages:
                result[issue_num] = self._pr_issue_linkages[issue_num]
        return result

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get the most relevant workflow run for each branch.

        Returns a mapping of branch name -> WorkflowRun for branches that have
        matching workflow runs. Uses priority: in_progress/queued > failed > success > other.

        The workflow parameter is accepted but ignored - fake returns runs from
        all pre-configured workflow runs regardless of workflow name.
        """
        if not branches:
            return {}

        # Group runs by branch
        runs_by_branch: dict[str, list[WorkflowRun]] = {}
        for run in self._workflow_runs:
            if run.branch in branches:
                if run.branch not in runs_by_branch:
                    runs_by_branch[run.branch] = []
                runs_by_branch[run.branch].append(run)

        # Select most relevant run for each branch
        result: dict[str, WorkflowRun | None] = {}
        for branch in branches:
            if branch not in runs_by_branch:
                continue

            branch_runs = runs_by_branch[branch]

            # Priority 1: in_progress or queued (active runs)
            active_runs = [r for r in branch_runs if r.status in ("in_progress", "queued")]
            if active_runs:
                result[branch] = active_runs[0]
                continue

            # Priority 2: failed completed runs
            failed_runs = [
                r for r in branch_runs if r.status == "completed" and r.conclusion == "failure"
            ]
            if failed_runs:
                result[branch] = failed_runs[0]
                continue

            # Priority 3: successful completed runs (most recent = first in list)
            completed_runs = [r for r in branch_runs if r.status == "completed"]
            if completed_runs:
                result[branch] = completed_runs[0]
                continue

            # Priority 4: any other runs (unknown status, etc.)
            if branch_runs:
                result[branch] = branch_runs[0]

        return result

    def poll_for_workflow_run(
        self,
        *,
        repo_root: Path,
        workflow: str,
        branch_name: str,
        timeout: int = 30,
        poll_interval: int = 2,
    ) -> str | None:
        """Return pre-configured run ID without sleeping.

        Tracks poll attempts for test assertions but returns immediately
        without actual polling delays.

        Args:
            repo_root: Repository root directory (ignored)
            workflow: Workflow filename (ignored)
            branch_name: Expected branch name (ignored)
            timeout: Maximum seconds to poll (ignored)
            poll_interval: Seconds between poll attempts (ignored)

        Returns:
            Pre-configured run ID or None for timeout simulation
        """
        self._poll_attempts.append((workflow, branch_name, timeout, poll_interval))
        return self._polled_run_id

    @property
    def poll_attempts(self) -> list[tuple[str, str, int, int]]:
        """Read-only access to tracked poll attempts for test assertions.

        Returns list of (workflow, branch_name, timeout, poll_interval) tuples.
        """
        return self._poll_attempts

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Return pre-configured authentication status.

        Tracks calls for verification.

        Returns:
            Tuple of (is_authenticated, username, hostname)
        """
        self._check_auth_status_calls.append(None)

        if not self._authenticated:
            return (False, None, None)

        return (True, self._auth_username, self._auth_hostname)

    @property
    def check_auth_status_calls(self) -> list[None]:
        """Get the list of check_auth_status() calls that were made.

        Returns list of None values (one per call, no arguments tracked).

        This property is for test assertions only.
        """
        return self._check_auth_status_calls

    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Get workflow runs by GraphQL node IDs (returns pre-configured data).

        Looks up each node_id in the pre-configured workflow_runs_by_node_id mapping.

        Raises RuntimeError if workflow_runs_error is set, simulating API failures.

        Args:
            repo_root: Repository root directory (ignored in fake)
            node_ids: List of GraphQL node IDs to lookup

        Returns:
            Mapping of node_id -> WorkflowRun or None if not found
        """
        if self._workflow_runs_error is not None:
            raise RuntimeError(self._workflow_runs_error)
        return {node_id: self._workflow_runs_by_node_id.get(node_id) for node_id in node_ids}

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        """Get node ID for a workflow run (returns pre-configured fake data).

        Looks up the run_id in the pre-configured workflow_runs_by_node_id mapping
        (reverse lookup) to find the corresponding node_id.

        Args:
            repo_root: Repository root directory (ignored in fake)
            run_id: GitHub Actions run ID

        Returns:
            Node ID if found in pre-configured data, or a generated fake node_id
        """
        # Reverse lookup: find node_id by run_id
        for node_id, run in self._workflow_runs_by_node_id.items():
            if run is not None and run.run_id == run_id:
                return node_id

        # If not in node_id mapping, check regular workflow runs and generate fake node_id
        for run in self._workflow_runs:
            if run.run_id == run_id:
                return f"WFR_fake_node_id_{run_id}"

        # Default: return a fake node_id for any run_id (convenience for tests)
        return f"WFR_fake_node_id_{run_id}"

    def get_issues_with_pr_linkages(
        self,
        *,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
        creator: str | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Get issues and PR linkages from pre-configured data.

        Filters pre-configured issues by labels, state, and creator, then returns
        matching PR linkages from pr_issue_linkages mapping.

        Args:
            location: GitHub repository location (ignored in fake)
            labels: Labels to filter by
            state: Filter by state ("open", "closed", or None for OPEN default)
            limit: Maximum issues to return (default: all)
            creator: Filter by creator username (e.g., "octocat")

        Returns:
            Tuple of (filtered_issues, pr_linkages for those issues)
        """
        # Default to OPEN to match gh CLI behavior (gh issue list defaults to open)
        effective_state = state if state is not None else "open"

        # Filter issues by labels, state, and creator
        filtered_issues = []
        for issue in self._issues:
            # Check if issue has all required labels
            if not all(label in issue.labels for label in labels):
                continue
            # Check state filter
            if issue.state.lower() != effective_state.lower():
                continue
            # Check creator filter
            if creator is not None and issue.author != creator:
                continue
            filtered_issues.append(issue)

        # Apply limit
        effective_limit = limit if limit is not None else len(filtered_issues)
        filtered_issues = filtered_issues[:effective_limit]

        # Build PR linkages for filtered issues
        pr_linkages: dict[int, list[PullRequestInfo]] = {}
        for issue in filtered_issues:
            if issue.number in self._pr_issue_linkages:
                pr_linkages[issue.number] = self._pr_issue_linkages[issue.number]

        return (filtered_issues, pr_linkages)

    def get_pr(self, repo_root: Path, pr_number: int) -> PRDetails | PRNotFound:
        """Get comprehensive PR details from pre-configured state.

        Returns:
            PRDetails if pr_number exists, PRNotFound otherwise
        """
        if pr_number not in self._pr_details:
            return PRNotFound(pr_number=pr_number)
        return self._pr_details[pr_number]

    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PRDetails | PRNotFound:
        """Get comprehensive PR details for a branch from pre-configured state.

        Returns:
            PRDetails if a PR exists for the branch, PRNotFound otherwise
        """
        pr = self._prs.get(branch)
        if pr is None:
            return PRNotFound(branch=branch)
        pr_details = self._pr_details.get(pr.number)
        if pr_details is None:
            return PRNotFound(branch=branch)
        return pr_details

    def list_prs(
        self,
        repo_root: Path,
        *,
        state: PRListState,
    ) -> dict[str, PullRequestInfo]:
        """List PRs from pre-configured state, filtered by state.

        Args:
            repo_root: Repository root directory (ignored in fake)
            state: Filter by state - "open", "closed", or "all"

        Returns:
            Dict mapping head branch name to PullRequestInfo.
        """
        if state == "all":
            return dict(self._prs)

        # Filter by state (normalize to upper case for comparison)
        target_state = state.upper()
        return {branch: pr for branch, pr in self._prs.items() if pr.state == target_state}

    def get_pr_title(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR title by number from configured state.

        First checks explicit pr_titles storage, then searches through
        configured PRs. Returns None if PR not found.
        """
        # Check explicit title storage first
        if pr_number in self._pr_titles:
            return self._pr_titles[pr_number]

        # Fall back to searching through PRs
        for pr in self._prs.values():
            if pr.number == pr_number:
                return pr.title
        return None

    def get_pr_body(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR body by number from configured state.

        Checks explicit pr_bodies_by_number storage.
        Returns None if PR body not configured.
        """
        return self._pr_bodies_by_number.get(pr_number)

    def update_pr_title_and_body(
        self, *, repo_root: Path, pr_number: int, title: str, body: str
    ) -> None:
        """Record PR title and body update in mutation tracking lists.

        Raises RuntimeError if pr_update_should_succeed is False.
        """
        if not self._pr_update_should_succeed:
            raise RuntimeError("PR update failed (configured to fail)")

        self._updated_pr_titles.append((pr_number, title))
        self._updated_pr_bodies.append((pr_number, body))

    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> None:
        """Mark a draft PR as ready for review (fake is a no-op)."""
        pass

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Get the diff for a PR from configured state or return default.

        First checks if pr_diff_error is set and raises RuntimeError.
        Then checks explicit pr_diffs storage. Returns a simple default
        diff if not configured.
        """
        if self._pr_diff_error is not None:
            raise RuntimeError(self._pr_diff_error)

        if pr_number in self._pr_diffs:
            return self._pr_diffs[pr_number]

        return (
            "diff --git a/file.py b/file.py\n"
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-old\n"
            "+new"
        )

    def get_pr_mergeability_status(self, repo_root: Path, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from configured state.

        Returns configured values from pr_details if available,
        otherwise defaults to ("MERGEABLE", "CLEAN").
        """
        if pr_number in self._pr_details:
            details = self._pr_details[pr_number]
            return (details.mergeable, details.merge_state_status)
        return ("MERGEABLE", "CLEAN")

    def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
        """Record label addition in mutation tracking list and update internal state."""
        self._added_labels.append((pr_number, label))
        if pr_number not in self._pr_labels:
            self._pr_labels[pr_number] = set()
        self._pr_labels[pr_number].add(label)

    def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
        """Check if a PR has a specific label from configured state."""
        if pr_number not in self._pr_labels:
            return False
        return label in self._pr_labels[pr_number]

    @property
    def added_labels(self) -> list[tuple[int, str]]:
        """Read-only access to tracked label additions for test assertions.

        Returns list of (pr_number, label) tuples.
        """
        return self._added_labels

    def set_pr_labels(self, pr_number: int, labels: set[str]) -> None:
        """Set labels for a PR (for test setup)."""
        self._pr_labels[pr_number] = labels

    def get_pr_review_threads(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        include_resolved: bool = False,
    ) -> list[PRReviewThread]:
        """Get review threads for a PR from pre-configured data.

        Applies any resolutions that happened during the test, then filters
        and sorts the results.

        Raises RuntimeError if review_threads_rate_limited is True, simulating
        a GraphQL API rate limit error.
        """
        if self._review_threads_rate_limited:
            raise RuntimeError("GraphQL API RATE_LIMIT exceeded")
        threads = self._pr_review_threads.get(pr_number, [])

        # Apply any resolutions that happened during test
        result_threads: list[PRReviewThread] = []
        for t in threads:
            is_resolved = t.is_resolved or t.id in self._resolved_thread_ids
            if is_resolved and not include_resolved:
                continue
            # Create new thread with updated resolution status
            result_threads.append(
                PRReviewThread(
                    id=t.id,
                    path=t.path,
                    line=t.line,
                    is_resolved=is_resolved,
                    is_outdated=t.is_outdated,
                    comments=t.comments,
                )
            )

        # Sort by path, then by line
        result_threads.sort(key=lambda t: (t.path, t.line or 0))
        return result_threads

    def resolve_review_thread(
        self,
        repo_root: Path,
        thread_id: str,
    ) -> bool:
        """Record thread resolution in mutation tracking set.

        Always returns True to simulate successful resolution.
        """
        self._resolved_thread_ids.add(thread_id)
        return True

    @property
    def resolved_thread_ids(self) -> set[str]:
        """Read-only access to tracked thread resolutions for test assertions."""
        return self._resolved_thread_ids

    def add_review_thread_reply(
        self,
        repo_root: Path,
        thread_id: str,
        body: str,
    ) -> bool:
        """Record thread reply in mutation tracking list.

        Always returns True to simulate successful comment addition.
        """
        self._thread_replies.append((thread_id, body))
        return True

    @property
    def thread_replies(self) -> list[tuple[str, str]]:
        """Read-only access to tracked thread replies for test assertions.

        Returns list of (thread_id, body) tuples.
        """
        return self._thread_replies

    def create_pr_review_comment(
        self, *, repo_root: Path, pr_number: int, body: str, commit_sha: str, path: str, line: int
    ) -> int:
        """Record PR review comment in mutation tracking list.

        Returns a generated comment ID.
        """
        self._pr_review_comments.append((pr_number, body, commit_sha, path, line))
        comment_id = self._next_comment_id
        self._next_comment_id += 1
        return comment_id

    @property
    def pr_review_comments(self) -> list[tuple[int, str, str, str, int]]:
        """Read-only access to tracked PR review comments for test assertions.

        Returns list of (pr_number, body, commit_sha, path, line) tuples.
        """
        return self._pr_review_comments

    def find_pr_comment_by_marker(
        self,
        repo_root: Path,
        pr_number: int,
        marker: str,
    ) -> int | None:
        """Find a PR comment by marker in tracked comments.

        Searches _pr_comments for a comment containing the marker.
        Returns None if not found (typical for first run).
        """
        for i, (stored_pr, body) in enumerate(self._pr_comments):
            if stored_pr == pr_number and marker in body:
                return 1000000 + i
        return None

    def update_pr_comment(
        self,
        repo_root: Path,
        comment_id: int,
        body: str,
    ) -> None:
        """Record PR comment update in mutation tracking list."""
        self._pr_comment_updates.append((comment_id, body))

    @property
    def pr_comment_updates(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR comment updates for test assertions.

        Returns list of (comment_id, body) tuples.
        """
        return self._pr_comment_updates

    def create_pr_comment(
        self,
        repo_root: Path,
        pr_number: int,
        body: str,
    ) -> int:
        """Record PR comment creation in mutation tracking list.

        Returns a generated comment ID.
        """
        self._pr_comments.append((pr_number, body))
        comment_id = self._next_comment_id
        self._next_comment_id += 1
        return comment_id

    @property
    def pr_comments(self) -> list[tuple[int, str]]:
        """Read-only access to tracked PR comments for test assertions.

        Returns list of (pr_number, body) tuples.
        """
        return self._pr_comments

    def delete_remote_branch(self, repo_root: Path, branch: str) -> bool:
        """Record remote branch deletion in mutation tracking list.

        Always returns True to simulate successful deletion.
        """
        self._deleted_remote_branches.append(branch)
        return True

    @property
    def deleted_remote_branches(self) -> list[str]:
        """Read-only access to tracked remote branch deletions for test assertions.

        Returns list of branch names that were deleted.
        """
        return self._deleted_remote_branches
