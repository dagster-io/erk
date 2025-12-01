"""Fake GitHub operations for testing.

FakeGitHub is an in-memory implementation that accepts pre-configured state
in its constructor. Construct instances directly with keyword arguments.
"""

from pathlib import Path
from typing import cast

from erk_shared.github.abc import GitHub
from erk_shared.github.types import (
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PRState,
    PullRequestInfo,
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
        prs: dict[str, PullRequestInfo] | None = None,
        pr_statuses: dict[str, tuple[str | None, int | None, str | None]] | None = None,
        pr_bases: dict[int, str] | None = None,
        pr_mergeability: dict[int, PRMergeability | None] | None = None,
        workflow_runs: list[WorkflowRun] | None = None,
        workflow_runs_by_node_id: dict[str, WorkflowRun] | None = None,
        run_logs: dict[str, str] | None = None,
        pr_issue_linkages: dict[int, list[PullRequestInfo]] | None = None,
        polled_run_id: str | None = None,
        pr_checkout_infos: dict[int, PRCheckoutInfo] | None = None,
        authenticated: bool = True,
        auth_username: str | None = "test-user",
        auth_hostname: str | None = "github.com",
    ) -> None:
        """Create FakeGitHub with pre-configured state.

        Args:
            prs: Mapping of branch name -> PullRequestInfo
            pr_statuses: Legacy parameter for backward compatibility.
                        Mapping of branch name -> (state, pr_number, title)
            pr_bases: Mapping of pr_number -> base_branch
            pr_mergeability: Mapping of pr_number -> PRMergeability (None for API errors)
            workflow_runs: List of WorkflowRun objects to return from list_workflow_runs
            workflow_runs_by_node_id: Mapping of GraphQL node_id -> WorkflowRun for
                                     get_workflow_runs_by_node_ids()
            run_logs: Mapping of run_id -> log string
            pr_issue_linkages: Mapping of issue_number -> list[PullRequestInfo]
            polled_run_id: Run ID to return from poll_for_workflow_run (None for timeout)
            pr_checkout_infos: Mapping of pr_number -> PRCheckoutInfo
            authenticated: Whether gh CLI is authenticated (default True for test convenience)
            auth_username: Username returned by check_auth_status() (default "test-user")
            auth_hostname: Hostname returned by check_auth_status() (default "github.com")
        """
        if prs is not None and pr_statuses is not None:
            msg = "Cannot specify both prs and pr_statuses"
            raise ValueError(msg)

        if pr_statuses is not None:
            # Convert legacy pr_statuses format to PullRequestInfo
            self._prs = {}
            for branch, (state, pr_number, title) in pr_statuses.items():
                if pr_number is not None:
                    # Handle None state - default to "OPEN"
                    resolved_state = state if state is not None and state != "NONE" else "OPEN"
                    self._prs[branch] = PullRequestInfo(
                        number=pr_number,
                        state=resolved_state,
                        url=f"https://github.com/owner/repo/pull/{pr_number}",
                        is_draft=False,
                        title=title,
                        checks_passing=None,
                        owner="owner",
                        repo="repo",
                        has_conflicts=None,
                    )
            self._pr_statuses = pr_statuses
        else:
            self._prs = prs or {}
            self._pr_statuses = None

        self._pr_bases = pr_bases or {}
        self._pr_mergeability = pr_mergeability or {}
        self._workflow_runs = workflow_runs or []
        self._workflow_runs_by_node_id = workflow_runs_by_node_id or {}
        self._run_logs = run_logs or {}
        self._pr_issue_linkages = pr_issue_linkages or {}
        self._polled_run_id = polled_run_id
        self._pr_checkout_infos = pr_checkout_infos or {}
        self._authenticated = authenticated
        self._auth_username = auth_username
        self._auth_hostname = auth_hostname
        self._updated_pr_bases: list[tuple[int, str]] = []
        self._updated_pr_bodies: list[tuple[int, str]] = []
        self._merged_prs: list[int] = []
        self._closed_prs: list[int] = []
        self._get_prs_for_repo_calls: list[tuple[Path, bool]] = []
        self._get_pr_status_calls: list[tuple[Path, str]] = []
        self._triggered_workflows: list[tuple[str, dict[str, str]]] = []
        self._poll_attempts: list[tuple[str, str, int, int]] = []
        self._check_auth_status_calls: list[None] = []
        self._created_prs: list[tuple[str, str, str, str | None, bool]] = []

    @property
    def merged_prs(self) -> list[int]:
        """List of PR numbers that were merged."""
        return self._merged_prs

    @property
    def closed_prs(self) -> list[int]:
        """Read-only access to tracked PR closures for test assertions."""
        return self._closed_prs

    @property
    def get_prs_for_repo_calls(self) -> list[tuple[Path, bool]]:
        """Read-only access to tracked get_prs_for_repo() calls for test assertions.

        Returns list of (repo_root, include_checks) tuples.
        """
        return self._get_prs_for_repo_calls

    @property
    def get_pr_status_calls(self) -> list[tuple[Path, str]]:
        """Read-only access to tracked get_pr_status() calls for test assertions.

        Returns list of (repo_root, branch) tuples.
        """
        return self._get_pr_status_calls

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches (returns pre-configured data).

        The include_checks parameter is accepted but ignored - fake returns the
        same pre-configured data regardless of this parameter.
        """
        self._get_prs_for_repo_calls.append((repo_root, include_checks))
        return self._prs

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status from configured PRs.

        Returns PRInfo("NONE", None, None) if branch not found.
        """
        # Support legacy pr_statuses format
        if self._pr_statuses is not None:
            result = self._pr_statuses.get(branch)
            if result is None:
                return PRInfo("NONE", None, None)
            state, pr_number, title = result
            # Convert None state to "NONE" for consistency
            if state is None:
                state = "NONE"
            return PRInfo(cast(PRState, state), pr_number, title)

        pr = self._prs.get(branch)
        if pr is None:
            return PRInfo("NONE", None, None)
        # PullRequestInfo has: number, state, url, is_draft, title, checks_passing
        # Return state, number, and title as expected by PRInfo
        return PRInfo(cast(PRState, pr.state), pr.number, pr.title)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from configured state.

        Returns None if PR number not found.
        """
        return self._pr_bases.get(pr_number)

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Record PR base branch update in mutation tracking list."""
        self._updated_pr_bases.append((pr_number, new_base))

    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        """Record PR body update in mutation tracking list."""
        self._updated_pr_bodies.append((pr_number, body))

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from configured state.

        Returns configured mergeability or defaults to MERGEABLE if not configured.
        """
        if pr_number in self._pr_mergeability:
            return self._pr_mergeability[pr_number]
        # Default to MERGEABLE if not configured
        return PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN")

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Fetch PR titles for all PRs in a single batched query.

        Fake just returns the PRs as-is. We assume PRs already have titles
        if configured. This method is a no-op that returns the input unchanged.
        """
        return prs

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PRs with CI status and mergeability using batched query.

        Fake just returns the PRs as-is. We assume PRs already have CI status
        and mergeability if configured. This method is a no-op that returns
        the input unchanged.
        """
        return prs

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
    ) -> None:
        """Record PR merge in mutation tracking list."""
        self._merged_prs.append(pr_number)

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
    ) -> str:
        """Record workflow trigger in mutation tracking list.

        Note: In production, trigger_workflow() generates a distinct_id internally
        and adds it to the inputs. Tests should verify the workflow was called
        with expected inputs; the distinct_id is an internal implementation detail.

        Returns:
            A fake run ID for testing
        """
        self._triggered_workflows.append((workflow, inputs))
        return "1234567890"

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
        repo_root: Path,
        issue_numbers: list[int],
        owner: str,
        repo: str,
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues via closing keywords (returns pre-configured data).

        Returns only the mappings for issues in issue_numbers that have
        pre-configured PR linkages. Issues without linkages are omitted.

        The owner/repo parameters are accepted but ignored - fake returns
        pre-configured data regardless of these parameters.
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

    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo | None:
        """Get PR checkout info from pre-configured state.

        Returns None if pr_number not found in pr_checkout_infos mapping.
        """
        return self._pr_checkout_infos.get(pr_number)

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

        Args:
            repo_root: Repository root directory (ignored in fake)
            node_ids: List of GraphQL node IDs to lookup

        Returns:
            Mapping of node_id -> WorkflowRun or None if not found
        """
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
