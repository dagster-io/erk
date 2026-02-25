"""Production implementation of GitHub operations.

Error Handling Philosophy:
    gh CLI invocations should let exceptions bubble by default. Callers are
    responsible for handling failures appropriately. Don't swallow exceptions
    and return None/False/default values - this masks real errors and makes
    debugging difficult.

    Legitimate "not found" cases (e.g., no PR exists for a branch) are handled
    by checking the response data, not by catching exceptions.
"""

import json
import logging
import secrets
import string
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from erk_shared.debug import debug_log
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.graphql_queries import (
    ADD_REVIEW_THREAD_REPLY_MUTATION,
    GET_ISSUES_WITH_PR_LINKAGES_QUERY,
    GET_PR_REVIEW_THREADS_QUERY,
    GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY,
    ISSUE_PR_LINKAGE_FRAGMENT,
    RESOLVE_REVIEW_THREAD_MUTATION,
)
from erk_shared.gateway.github.issues.abc import GitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.github.parsing import (
    execute_gh_command_with_retry,
    parse_aggregated_check_counts,
    parse_gh_auth_status_output,
)
from erk_shared.gateway.github.retry import RetriesExhausted, RetryRequested, with_retries
from erk_shared.gateway.github.types import (
    BRANCH_NOT_AVAILABLE,
    DISPLAY_TITLE_NOT_AVAILABLE,
    BodyContent,
    BodyFile,
    BodyText,
    GitHubRepoId,
    GitHubRepoLocation,
    IssueFilterState,
    MergeError,
    MergeResult,
    PRDetails,
    PRListState,
    PRNotFound,
    PRReviewComment,
    PRReviewThread,
    PullRequestInfo,
    RepoInfo,
    WorkflowRun,
    WorkflowRunConclusion,
    WorkflowRunStatus,
)
from erk_shared.gateway.time.abc import Time
from erk_shared.output.output import user_output
from erk_shared.subprocess_utils import _GH_COMMAND_TIMEOUT, run_subprocess_with_context

_logger = logging.getLogger(__name__)


def _elapsed_ms(start: float, end: float) -> float:
    """Convert monotonic clock interval to milliseconds."""
    return (end - start) * 1000


# Feature flag to control whether PR mutations use REST API or gh CLI commands.
# When True: Use REST API (gh api) - uses REST quota, preserves GraphQL quota
# When False: Use gh CLI commands (gh pr) - uses GraphQL quota internally
USE_REST_API_FOR_PR_MUTATIONS = True

# Feature flag for merge operations to use gh pr merge.
# When True: Use gh pr merge (simpler CLI-based merge)
# When False: Use REST API for merge
# This takes precedence over USE_REST_API_FOR_PR_MUTATIONS for merge_pr() only.
#
# Note: We intentionally do NOT use --delete-branch with gh pr merge because
# it attempts local branch operations that fail when running from a git worktree
# (error: "master already used by worktree"). Instead, we delete the remote
# branch separately via REST API after the merge succeeds.
USE_GH_PR_MERGE_FOR_LANDING = True


class RealGitHub(GitHub):
    """Production implementation using gh CLI.

    All GitHub operations execute actual gh commands via subprocess.
    """

    def __init__(
        self,
        time: Time,
        repo_info: RepoInfo | None,
        *,
        issues: GitHubIssues,
    ):
        """Initialize RealGitHub.

        Args:
            time: Time abstraction for sleep operations
            repo_info: Repository owner/name info (None if not in a GitHub repo)
            issues: GitHubIssues gateway for issue operations
        """
        self._time = time
        self._repo_info = repo_info
        self._issues = issues
        self._default_branch_cache: dict[Path, str] = {}

    @classmethod
    def for_test(
        cls,
        time: Time | None = None,
        repo_info: RepoInfo | None = None,
    ) -> "RealGitHub":
        """Create RealGitHub with test defaults.

        Convenience factory for tests that need RealGitHub but don't care
        about the issues gateway configuration.

        Args:
            time: Time implementation (defaults to FakeTime)
            repo_info: Repository info (defaults to None)

        Returns:
            RealGitHub configured with FakeGitHubIssues
        """
        from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
        from erk_shared.gateway.time.fake import FakeTime

        return cls(
            time=time if time is not None else FakeTime(),
            repo_info=repo_info,
            issues=FakeGitHubIssues(),
        )

    @property
    def issues(self) -> GitHubIssues:
        """Access to issue operations."""
        return self._issues

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update base branch of a PR on GitHub.

        Uses REST API to preserve GraphQL quota.

        Gracefully handles gh CLI availability issues (not installed, not authenticated).
        The calling code should validate preconditions (PR exists, is open, new base exists)
        before calling this method.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability. Genuine command failures (invalid PR, invalid base) should be
        caught by precondition checks in the caller.
        """
        try:
            # GH-API-AUDIT: REST - PATCH pulls/{number}
            cmd = [
                "gh",
                "api",
                "--method",
                "PATCH",
                f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
                "-f",
                f"base={new_base}",
            ]
            execute_gh_command_with_retry(cmd, repo_root, self._time)
        except (RuntimeError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            # Graceful degradation - operation skipped
            # Caller is responsible for precondition validation
            pass

    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        """Update body of a PR on GitHub.

        Uses REST API to preserve GraphQL quota.

        Gracefully handles gh CLI availability issues (not installed, not authenticated).
        The calling code should validate preconditions (PR exists, is open)
        before calling this method.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability. Genuine command failures (invalid PR) should be
        caught by precondition checks in the caller.
        """
        try:
            # GH-API-AUDIT: REST - PATCH pulls/{number}
            cmd = [
                "gh",
                "api",
                "--method",
                "PATCH",
                f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
                "-f",
                f"body={body}",
            ]
            execute_gh_command_with_retry(cmd, repo_root, self._time)
        except (RuntimeError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            # Graceful degradation - operation skipped
            # Caller is responsible for precondition validation
            pass

    def _execute_batch_pr_query(self, query: str, repo_root: Path) -> dict[str, Any]:
        """Execute batched GraphQL query via gh CLI.

        Args:
            query: GraphQL query string
            repo_root: Repository root directory

        Returns:
            Parsed JSON response
        """
        # GH-API-AUDIT: GraphQL - explicit graphql query
        # WHY GRAPHQL: Used by get_prs_linked_to_issues for erk dash batch queries
        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        return json.loads(stdout)

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

        When USE_GH_PR_MERGE_FOR_LANDING is True, uses gh pr merge.
        Note: Does NOT use --delete-branch because it attempts local branch
        operations that fail from git worktrees. Callers should use
        delete_remote_branch() separately after merge succeeds.

        When USE_REST_API_FOR_PR_MUTATIONS is True, uses REST API to preserve
        GraphQL quota. Otherwise uses gh pr merge (GraphQL internally).
        """
        if USE_GH_PR_MERGE_FOR_LANDING:
            # Build gh pr merge command WITHOUT --delete-branch
            # (--delete-branch fails from worktrees with "master already used by worktree")
            cmd = ["gh", "pr", "merge", str(pr_number)]
            if squash:
                cmd.append("--squash")
            if subject is not None:
                cmd.extend(["--subject", subject])
            if body is not None:
                cmd.extend(["--body", body])
        else:
            # Build REST API command
            # GH-API-AUDIT: REST - PUT pulls/{number}/merge
            cmd = [
                "gh",
                "api",
                "--method",
                "PUT",
                f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/merge",
            ]

            # Add merge method
            if squash:
                cmd.extend(["-f", "merge_method=squash"])

            # Add commit title (corresponds to --subject)
            if subject is not None:
                cmd.extend(["-f", f"commit_title={subject}"])

            # Add commit message (corresponds to --body)
            if body is not None:
                cmd.extend(["-f", f"commit_message={body}"])

        try:
            result = run_subprocess_with_context(
                cmd=cmd,
                operation_context=f"merge PR #{pr_number}",
                cwd=repo_root,
            )

            # Show output in verbose mode
            if verbose and result.stdout:
                user_output(result.stdout)
            return MergeResult(pr_number=pr_number)
        except RuntimeError as e:
            return MergeError(pr_number=pr_number, message=str(e))

    def _generate_distinct_id(self) -> str:
        """Generate a random base36 ID for workflow dispatch correlation.

        Returns:
            6-character base36 string (e.g., 'a1b2c3')
        """
        # Base36 alphabet: 0-9 and a-z
        base36_chars = string.digits + string.ascii_lowercase
        # Generate 6 random characters (~2.2 billion possibilities)
        return "".join(secrets.choice(base36_chars) for _ in range(6))

    def _get_default_branch(self, repo_root: Path) -> str:
        """Get the repository's default branch via REST API.

        Uses REST quota instead of the implicit GraphQL call that
        gh workflow run makes when ref is not specified.
        Results are cached per repo_root since the default branch
        does not change within a session.
        """
        if repo_root in self._default_branch_cache:
            return self._default_branch_cache[repo_root]
        # GH-API-AUDIT: REST - GET repos/{owner}/{repo} (.default_branch)
        cmd = ["gh", "api", "repos/{owner}/{repo}", "--jq", ".default_branch"]
        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        branch = stdout.strip()
        self._default_branch_cache[repo_root] = branch
        return branch

    def _dispatch_workflow_impl(
        self, *, repo_root: Path, workflow: str, inputs: dict[str, str], ref: str | None
    ) -> str:
        """Dispatch a GitHub Actions workflow and return the distinct_id.

        Internal implementation used by trigger_workflow().
        Generates a unique distinct_id, passes it to the workflow, and returns
        the distinct_id for polling.

        Args:
            repo_root: Repository root path
            workflow: Workflow file name (e.g., "implement-plan.yml")
            inputs: Workflow inputs as key-value pairs
            ref: Branch or tag to run workflow from (default: repository default branch)

        Returns:
            The distinct_id used for correlation
        """
        distinct_id = self._generate_distinct_id()
        debug_log(
            f"_dispatch_workflow_impl: workflow={workflow}, distinct_id={distinct_id}, ref={ref}"
        )

        ref_value = ref if ref is not None else self._get_default_branch(repo_root)
        payload = json.dumps({"ref": ref_value, "inputs": {"distinct_id": distinct_id, **inputs}})

        # GH-API-AUDIT: REST - POST workflows/{id}/dispatches
        cmd = [
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/dispatches",
            "--input",
            "-",
        ]

        debug_log(f"_dispatch_workflow_impl: executing command: {' '.join(cmd)}")
        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"trigger workflow '{workflow}'",
            cwd=repo_root,
            input=payload,
        )
        debug_log("_dispatch_workflow_impl: workflow dispatched successfully")
        return distinct_id

    def trigger_workflow(
        self, *, repo_root: Path, workflow: str, inputs: dict[str, str], ref: str | None
    ) -> str:
        """Trigger GitHub Actions workflow via gh CLI.

        Generates a unique distinct_id internally, passes it to the workflow,
        and uses it to reliably find the triggered run via displayTitle matching.

        Args:
            repo_root: Repository root path
            workflow: Workflow file name (e.g., "implement-plan.yml")
            inputs: Workflow inputs as key-value pairs
            ref: Branch or tag to run workflow from (default: repository default branch)

        Returns:
            The GitHub Actions run ID as a string
        """
        distinct_id = self._dispatch_workflow_impl(
            repo_root=repo_root, workflow=workflow, inputs=inputs, ref=ref
        )

        # Poll for the run by matching displayTitle containing the distinct ID
        # The workflow uses run-name: "<issue_number>:<distinct_id>"
        # GitHub API eventual consistency: exponential backoff 1,2,4,8,...,8s (~62s, 11 attempts)
        max_attempts = 11
        runs_data: list[dict[str, Any]] = []
        for attempt in range(max_attempts):
            user_output(f"  Waiting for workflow run... (attempt {attempt + 1}/{max_attempts})")
            debug_log(f"trigger_workflow: polling attempt {attempt + 1}/{max_attempts}")

            # GH-API-AUDIT: REST - GET actions/workflows/{id}/runs
            runs_cmd = [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/runs?per_page=10",
                "--jq",
                ".workflow_runs",
            ]

            runs_result = run_subprocess_with_context(
                cmd=runs_cmd,
                operation_context=f"get run ID for workflow '{workflow}'",
                cwd=repo_root,
            )

            runs_data = json.loads(runs_result.stdout)
            debug_log(f"trigger_workflow: found {len(runs_data)} runs")

            # Validate response structure (must be a list)
            if not isinstance(runs_data, list):
                msg = (
                    f"GitHub workflow '{workflow}' triggered but received invalid response format. "
                    f"Expected JSON array, got: {type(runs_data).__name__}. "
                    f"Raw output: {runs_result.stdout[:200]}"
                )
                raise RuntimeError(msg)

            # Empty list is valid - workflow hasn't appeared yet, continue polling
            if not runs_data:
                # Continue to retry logic below
                pass

            # Find run by matching distinct_id in display_title
            for run in runs_data:
                display_title = run.get("display_title", "")
                # Check for match pattern: :<distinct_id> (new format: issue_number:distinct_id)
                if f":{distinct_id}" not in display_title:
                    continue

                conclusion = run.get("conclusion")
                if conclusion in ("skipped", "cancelled"):
                    # Matched run was skipped/cancelled — no point polling further
                    raise RuntimeError(
                        f"Workflow '{workflow}' run was {conclusion}.\n"
                        f"Run ID: {run['id']}, title: '{display_title}'\n"
                        f"This usually means a job-level condition was not met "
                        f"(e.g., vars.CLAUDE_ENABLED is 'false')."
                    )

                run_id = run["id"]
                debug_log(f"trigger_workflow: found run {run_id}, title='{display_title}'")
                return str(run_id)

            # No matching run found, retry if attempts remaining
            # Exponential backoff: 2^attempt seconds, capped at 8s
            if attempt < max_attempts - 1:
                delay = min(2**attempt, 8)
                self._time.sleep(delay)

        # All attempts exhausted without finding matching run
        msg_parts = [
            f"GitHub workflow triggered but could not find run ID after {max_attempts} attempts.",
            "",
            f"Workflow file: {workflow}",
            f"Correlation ID: {distinct_id}",
            "",
        ]

        if runs_data:
            msg_parts.append(f"Found {len(runs_data)} recent runs, but none matched.")
            msg_parts.append("Recent run titles:")
            for run in runs_data[:5]:
                title = run.get("display_title", "N/A")
                status = run.get("status", "N/A")
                msg_parts.append(f"  • {title} ({status})")
            msg_parts.append("")
        else:
            msg_parts.append("No workflow runs found at all.")
            msg_parts.append("")

        msg_parts.extend(
            [
                "Possible causes:",
                "  • GitHub API eventual consistency delay (rare but possible)",
                "  • Workflow file doesn't use 'run-name' with distinct_id",
                "  • All recent runs were cancelled/skipped",
                "",
                "Debug commands:",
                f"  gh api repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/runs?per_page=10",
            ]
        )

        msg = "\n".join(msg_parts)
        debug_log(f"trigger_workflow: exhausted all attempts, error: {msg}")
        raise RuntimeError(msg)

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
        """Create a pull request on GitHub.

        Uses REST API to preserve GraphQL quota.

        Args:
            repo_root: Repository root directory
            branch: Source branch for the PR
            title: PR title
            body: PR body (markdown)
            base: Target base branch (defaults to repository default branch if None)
            draft: If True, create as draft PR

        Returns:
            PR number
        """
        # GH-API-AUDIT: REST - POST pulls
        cmd = [
            "gh",
            "api",
            "--method",
            "POST",
            "repos/{owner}/{repo}/pulls",
            "-f",
            f"head={branch}",
            "-f",
            f"title={title}",
            "-f",
            f"body={body}",
        ]

        # Add draft flag if specified
        if draft:
            cmd.extend(["-F", "draft=true"])

        # Add base branch if specified
        if base is not None:
            cmd.extend(["-f", f"base={base}"])

        result = run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"create pull request for branch '{branch}'",
            cwd=repo_root,
        )

        # Extract PR number from REST API JSON response
        data = json.loads(result.stdout)
        return data["number"]

    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        """Close a pull request without deleting its branch.

        Uses REST API to preserve GraphQL quota.
        """
        # GH-API-AUDIT: REST - PATCH pulls/{number} state=closed
        cmd = [
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
            "-f",
            "state=closed",
        ]
        execute_gh_command_with_retry(cmd, repo_root, self._time)

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow."""
        # GH-API-AUDIT: REST - GET actions/workflows/{id}/runs
        query_params = f"per_page={limit}"
        if user is not None:
            query_params += f"&actor={user}"

        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/runs?{query_params}",
            "--jq",
            ".workflow_runs",
        ]

        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)

        # Parse JSON response
        data = json.loads(stdout)

        # Map to WorkflowRun dataclasses
        runs = []
        for run in data:
            # Parse created_at timestamp if present
            created_at = None
            created_at_str = run.get("created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            workflow_run = WorkflowRun(
                run_id=str(run["id"]),
                status=run["status"],
                conclusion=run.get("conclusion"),
                branch=run["head_branch"],
                head_sha=run["head_sha"],
                display_title=run.get("display_title"),
                created_at=created_at,
            )
            runs.append(workflow_run)

        return runs

    def get_workflow_run(self, repo_root: Path, run_id: str) -> WorkflowRun | None:
        """Get details for a specific workflow run by ID.

        Uses the REST API to get workflow run details including node_id.
        The gh CLI's `gh run view --json` does not support the nodeId field,
        but the REST API does.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            # GH-API-AUDIT: REST - GET actions/runs/{id}
            cmd = [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}",
            ]

            stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
            data = json.loads(stdout)

            # Parse created_at timestamp if present
            created_at = None
            created_at_str = data.get("created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            return WorkflowRun(
                run_id=str(data["id"]),
                status=data["status"],
                conclusion=data.get("conclusion"),
                branch=data["head_branch"],
                head_sha=data["head_sha"],
                display_title=data.get("display_title"),
                created_at=created_at,
                node_id=data.get("node_id"),
            )

        except (RuntimeError, json.JSONDecodeError, KeyError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed (e.g., 404)
            return None

    def get_run_logs(self, repo_root: Path, run_id: str) -> str:
        """Get logs for a workflow run using gh CLI."""
        # GH-API-AUDIT: REST - gh run view uses REST
        result = run_subprocess_with_context(
            cmd=["gh", "run", "view", run_id, "--log"],
            operation_context=f"fetch logs for run {run_id}",
            cwd=repo_root,
        )
        return result.stdout

    def get_prs_linked_to_issues(
        self,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues via CrossReferencedEvent timeline.

        Uses GraphQL CrossReferencedEvent to find all PRs that reference each issue,
        regardless of whether they will close the issue when merged. Includes open,
        closed, and draft PRs. Used by erk dash for batch queries with full PR data
        (CI status, mergeability).

        For simpler single-issue queries, see GitHubIssues.get_prs_referencing_issue().

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        if not issue_numbers:
            return {}

        try:
            # Build and execute GraphQL query to fetch all issues
            query = self._build_issue_pr_linkage_query(issue_numbers, location.repo_id)
            response = self._execute_batch_pr_query(query, location.root)

            # Parse response and build inverse mapping
            return self._parse_issue_pr_linkages(response, location.repo_id)
        except (RuntimeError, FileNotFoundError, json.JSONDecodeError, KeyError, IndexError):
            # gh not installed, not authenticated, or parsing failed
            return {}

    def _build_issue_pr_linkage_query(self, issue_numbers: list[int], repo_id: GitHubRepoId) -> str:
        """Build GraphQL query to fetch PRs linked to issues via timeline.

        Uses CrossReferencedEvent on issue timelines to find PRs that will close
        each issue. This is O(issues) instead of O(all PRs in repo).

        Uses pre-aggregated count fields for efficiency (~15-30x smaller payload):
        - contexts(last: 1) with totalCount, checkRunCountsByState, statusContextCountsByState
        - Removes title and labels fields (not needed for dash)

        Note: This method still builds dynamic alias queries because GraphQL doesn't
        support variable alias names. The fragment is reused from graphql_queries.py.

        Args:
            issue_numbers: List of issue numbers to query
            repo_id: GitHub repository identity (owner and repo name)

        Returns:
            GraphQL query string
        """
        # Build aliased issue queries using the fragment spread
        issue_queries = []
        for issue_num in issue_numbers:
            issue_query = f"""    issue_{issue_num}: issue(number: {issue_num}) {{
      timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 20) {{
        nodes {{
          ... on CrossReferencedEvent {{
            ...IssuePRLinkageFields
          }}
        }}
      }}
    }}"""
            issue_queries.append(issue_query)

        # Combine fragment definition (from constant) and query
        query = f"""{ISSUE_PR_LINKAGE_FRAGMENT}

query {{
  repository(owner: "{repo_id.owner}", name: "{repo_id.repo}") {{
{chr(10).join(issue_queries)}
  }}
}}"""
        return query

    def _parse_issue_pr_linkages(
        self, response: dict[str, Any], repo_id: GitHubRepoId
    ) -> dict[int, list[PullRequestInfo]]:
        """Parse GraphQL response from issue timeline query.

        Processes CrossReferencedEvent timeline items to extract all PRs that
        reference each issue.

        Args:
            response: GraphQL response data
            repo_id: GitHub repository identity (owner and repo name)

        Returns:
            Mapping of issue_number -> list of PRs sorted by created_at descending
        """
        result: dict[int, list[PullRequestInfo]] = {}
        repo_data = response.get("data", {}).get("repository", {})

        # Iterate over aliased issue results
        for key, issue_data in repo_data.items():
            # Skip non-issue aliases or missing issues
            if not key.startswith("issue_") or issue_data is None:
                continue

            # Extract issue number from alias
            issue_number = int(key.removeprefix("issue_"))

            # Collect PRs with timestamps for sorting
            prs_with_timestamps: list[tuple[PullRequestInfo, str]] = []

            timeline_items = issue_data.get("timelineItems", {})
            nodes = timeline_items.get("nodes", [])

            for node in nodes:
                if node is None:
                    continue

                source = node.get("source")
                if source is None:
                    continue

                # Extract required PR fields
                pr_number = source.get("number")
                state = source.get("state")
                url = source.get("url")

                # Skip if essential fields are missing (source may be Issue, not PR)
                if pr_number is None or state is None or url is None:
                    continue

                # Extract optional fields (title no longer fetched for efficiency)
                is_draft = source.get("isDraft")
                created_at = source.get("createdAt")

                # Parse checks status and counts using aggregated fields
                checks_passing = None
                checks_counts: tuple[int, int] | None = None
                status_rollup = source.get("statusCheckRollup")
                if status_rollup is not None:
                    rollup_state = status_rollup.get("state")
                    if rollup_state == "SUCCESS":
                        checks_passing = True
                    elif rollup_state in ("FAILURE", "ERROR"):
                        checks_passing = False

                    # Extract check counts from aggregated fields
                    contexts = status_rollup.get("contexts")
                    if contexts is not None and isinstance(contexts, dict):
                        total = contexts.get("totalCount", 0)
                        if total > 0:
                            checks_counts = parse_aggregated_check_counts(
                                contexts.get("checkRunCountsByState", []),
                                contexts.get("statusContextCountsByState", []),
                                total,
                            )

                # Parse conflicts status
                has_conflicts = None
                mergeable = source.get("mergeable")
                if mergeable == "CONFLICTING":
                    has_conflicts = True
                elif mergeable == "MERGEABLE":
                    has_conflicts = False

                # Extract head branch (source branch) for landing
                head_ref_name = source.get("headRefName")

                # Note: title and labels not fetched (not needed for dash)
                pr_info = PullRequestInfo(
                    number=pr_number,
                    state=state,
                    url=url,
                    is_draft=is_draft if is_draft is not None else False,
                    title=None,  # Not fetched for efficiency
                    checks_passing=checks_passing,
                    owner=repo_id.owner,
                    repo=repo_id.repo,
                    has_conflicts=has_conflicts,
                    checks_counts=checks_counts,
                    head_branch=head_ref_name,
                )

                # Store with timestamp for sorting
                if created_at:
                    prs_with_timestamps.append((pr_info, created_at))

            # Sort by created_at descending and store
            if prs_with_timestamps:
                prs_with_timestamps.sort(key=lambda x: x[1], reverse=True)
                result[issue_number] = [pr for pr, _ in prs_with_timestamps]

        return result

    def get_workflow_runs_by_branches(
        self, repo_root: Path, workflow: str, branches: list[str]
    ) -> dict[str, WorkflowRun | None]:
        """Get the most relevant workflow run for each branch.

        Queries GitHub Actions for workflow runs and returns the most relevant
        run for each requested branch. Priority order:
        1. In-progress or queued runs (active runs take precedence)
        2. Failed completed runs (failures are more actionable than successes)
        3. Successful completed runs (most recent)

        Note: Uses list_workflow_runs internally, which already handles gh CLI
        errors gracefully.
        """
        if not branches:
            return {}

        # Get all workflow runs
        all_runs = self.list_workflow_runs(repo_root, workflow, limit=100)

        # Filter to requested branches
        branch_set = set(branches)
        runs_by_branch: dict[str, list[WorkflowRun]] = {}
        for run in all_runs:
            if run.branch in branch_set:
                if run.branch not in runs_by_branch:
                    runs_by_branch[run.branch] = []
                runs_by_branch[run.branch].append(run)

        # Select most relevant run for each branch using priority rules
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
        """Poll for a workflow run matching branch name within timeout.

        Uses multi-factor matching (creation time + event type + branch validation)
        to reliably find the correct workflow run even under high throughput.

        Args:
            repo_root: Repository root directory
            workflow: Workflow filename (e.g., "dispatch-erk-queue.yml")
            branch_name: Expected branch name to match
            timeout: Maximum seconds to poll (default: 30)
            poll_interval: Seconds between poll attempts (default: 2)

        Returns:
            Run ID as string if found within timeout, None otherwise
        """
        start_time = datetime.now(UTC)
        max_attempts = timeout // poll_interval

        def _fetch_and_find_run() -> str | RetryRequested:
            """Fetch runs and find matching run, or return RetryRequested if not found."""
            # GH-API-AUDIT: REST - GET actions/workflows/{id}/runs
            runs_cmd = [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/runs?per_page=20",
                "--jq",
                ".workflow_runs",
            ]

            try:
                runs_stdout = execute_gh_command_with_retry(runs_cmd, repo_root, self._time)
                runs_data = json.loads(runs_stdout)
            except (RuntimeError, FileNotFoundError, json.JSONDecodeError) as e:
                # Transient API error - retry
                return RetryRequested(reason=f"API error: {e}")

            if not runs_data or not isinstance(runs_data, list):
                # Data not available yet - keep polling
                return RetryRequested(reason="No runs data yet")

            # Find run matching our criteria
            for run in runs_data:
                # Skip skipped/cancelled runs
                conclusion = run.get("conclusion")
                if conclusion in ("skipped", "cancelled"):
                    continue

                # Match by branch name
                head_branch = run.get("head_branch")
                if head_branch != branch_name:
                    continue

                # Verify run was created after we started polling (within tolerance)
                created_at_str = run.get("created_at")
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    # Allow 5-second tolerance for runs created just before polling started
                    if created_at >= start_time - timedelta(seconds=5):
                        run_id = run["id"]
                        return str(run_id)

            # Run not found in results yet - keep polling
            return RetryRequested(reason="Run not found in results")

        result = with_retries(
            self._time,
            f"poll for workflow run ({workflow}, {branch_name})",
            _fetch_and_find_run,
            retry_delays=[float(poll_interval)] * max_attempts,
        )
        if isinstance(result, RetriesExhausted):
            # Timeout - run never appeared
            return None
        # with_retries never returns RetryRequested (consumed internally).
        # Assert narrows type to str for both runtime safety and static analysis.
        assert isinstance(result, str)
        return result

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status.

        Runs `gh auth status` and parses the output to determine authentication status.
        Looks for patterns like:
        - "Logged in to github.com as USERNAME"
        - Success indicator (checkmark)

        Returns:
            Tuple of (is_authenticated, username, hostname)
        """
        # GH-API-AUDIT: REST - auth validation
        result = run_subprocess_with_context(
            cmd=["gh", "auth", "status"],
            operation_context="check GitHub authentication status",
            capture_output=True,
            check=False,
            timeout=_GH_COMMAND_TIMEOUT,
        )

        # gh auth status returns non-zero if not authenticated
        if result.returncode != 0:
            return (False, None, None)

        output = result.stdout + result.stderr
        return parse_gh_auth_status_output(output)

    def get_workflow_runs_by_node_ids(
        self,
        repo_root: Path,
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Batch query workflow runs by GraphQL node IDs.

        Uses GraphQL nodes(ids: [...]) query to efficiently fetch multiple
        workflow runs in a single API call. This is dramatically faster than
        individual REST API calls for each run.
        """
        # Early exit for empty input
        if not node_ids:
            return {}

        # GH-API-AUDIT: GraphQL - nodes query by IDs
        # WHY GRAPHQL: Batch fetch O(1) vs REST O(N) individual calls
        # CRITICAL: gh api graphql requires arrays to be passed as -f key[]=val1 -f key[]=val2
        # Using -f key=json.dumps([...]) passes the array as a literal string, not an array
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={GET_WORKFLOW_RUNS_BY_NODE_IDS_QUERY}",
        ]
        for node_id in node_ids:
            cmd.extend(["-f", f"nodeIds[]={node_id}"])
        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        response = json.loads(stdout)

        # Parse response into WorkflowRun objects
        return self._parse_workflow_runs_nodes_response(response, node_ids)

    def _parse_workflow_runs_nodes_response(
        self,
        response: dict[str, Any],
        node_ids: list[str],
    ) -> dict[str, WorkflowRun | None]:
        """Parse GraphQL nodes response into WorkflowRun objects.

        Maps the GraphQL checkSuite status/conclusion to WorkflowRun fields.

        Args:
            response: GraphQL response data
            node_ids: Original list of node IDs (for result ordering)

        Returns:
            Mapping of node_id -> WorkflowRun or None
        """
        result: dict[str, WorkflowRun | None] = {}
        nodes = response.get("data", {}).get("nodes", [])

        # Build mapping from id to parsed WorkflowRun
        for node in nodes:
            if node is None:
                continue

            node_id = node.get("id")
            if node_id is None:
                continue

            # Extract checkSuite data
            check_suite = node.get("checkSuite")
            status: WorkflowRunStatus | None = None
            conclusion: WorkflowRunConclusion | None = None
            head_sha: str | None = None

            if check_suite is not None:
                # Map GitHub checkSuite status to workflow run status
                cs_status = check_suite.get("status")
                cs_conclusion = check_suite.get("conclusion")

                # Map checkSuite.status to workflow run status
                if cs_status == "COMPLETED":
                    status = "completed"
                elif cs_status == "IN_PROGRESS":
                    status = "in_progress"
                elif cs_status == "QUEUED":
                    status = "queued"

                # Map checkSuite.conclusion to workflow run conclusion
                if cs_conclusion == "SUCCESS":
                    conclusion = "success"
                elif cs_conclusion == "FAILURE":
                    conclusion = "failure"
                elif cs_conclusion == "SKIPPED":
                    conclusion = "skipped"
                elif cs_conclusion == "CANCELLED":
                    conclusion = "cancelled"

                # Extract commit SHA
                commit = check_suite.get("commit")
                if commit is not None:
                    head_sha = commit.get("oid")

            # Parse created_at timestamp
            created_at = None
            created_at_str = node.get("createdAt")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            workflow_run = WorkflowRun(
                run_id=str(node.get("databaseId", "")),
                status=status or "unknown",  # Default for missing status
                conclusion=conclusion,
                branch=BRANCH_NOT_AVAILABLE,
                head_sha=head_sha or "",  # Default for missing SHA
                display_title=DISPLAY_TITLE_NOT_AVAILABLE,
                created_at=created_at,
            )
            result[node_id] = workflow_run

        # Ensure all requested node_ids are in result (with None for missing)
        for node_id in node_ids:
            if node_id not in result:
                result[node_id] = None

        return result

    def get_workflow_run_node_id(self, repo_root: Path, run_id: str) -> str | None:
        """Get the GraphQL node ID for a workflow run via gh API.

        Uses the REST API endpoint to get workflow run details including node_id.
        """
        # GH-API-AUDIT: REST - GET actions/runs/{id}
        cmd = [
            "gh",
            "api",
            f"/repos/{{owner}}/{{repo}}/actions/runs/{run_id}",
            "--jq",
            ".node_id",
        ]
        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        node_id = stdout.strip()
        return node_id if node_id else None

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
        to get PR linkages in one API call.
        """
        repo_id = location.repo_id

        states = [state.upper()]
        effective_limit = limit if limit is not None else 30

        # GH-API-AUDIT: GraphQL - issues with timeline
        # WHY GRAPHQL: Complex nested query (issues + timeline + PR status) for erk dash
        # IMPORTANT: gh api graphql requires special syntax for arrays and objects:
        # - Arrays: use key[]=value1 -f key[]=value2 (NOT -F key=["value1"])
        # - Objects: use key[subkey]=value (NOT -F key={"subkey": "value"})
        # - Strings: use -f key=value
        # - Integers: use -F key=123
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={GET_ISSUES_WITH_PR_LINKAGES_QUERY}",
            "-f",
            f"owner={repo_id.owner}",
            "-f",
            f"repo={repo_id.repo}",
            "-F",
            f"first={effective_limit}",
        ]

        # Add labels array using gh's array syntax: labels[]=value
        for label in labels:
            cmd.extend(["-f", f"labels[]={label}"])

        # Add states array using gh's array syntax: states[]=value
        for state_val in states:
            cmd.extend(["-f", f"states[]={state_val}"])

        # Add filterBy if creator specified using gh's object syntax: filterBy[createdBy]=value
        if creator is not None:
            cmd.extend(["-f", f"filterBy[createdBy]={creator}"])

        stdout = execute_gh_command_with_retry(cmd, location.root, self._time)
        response = json.loads(stdout)
        return self._parse_issues_with_pr_linkages(response, repo_id)

    def _parse_issue_node(self, node: dict[str, Any]) -> IssueInfo | None:
        """Parse a single issue node from GraphQL response.

        Returns None if node is invalid or missing required fields.
        """
        issue_number = node.get("number")
        if issue_number is None:
            return None

        created_at_str = node.get("createdAt", "")
        updated_at_str = node.get("updatedAt", "")
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))

        labels_data = node.get("labels", {}).get("nodes", [])
        labels = [label.get("name", "") for label in labels_data if label]

        assignees_data = node.get("assignees", {}).get("nodes", [])
        assignees = [assignee.get("login", "") for assignee in assignees_data if assignee]

        # Extract author login
        author_data = node.get("author")
        author = author_data.get("login", "") if author_data else ""

        return IssueInfo(
            number=issue_number,
            title=node.get("title", ""),
            body=node.get("body", ""),
            state=node.get("state", "OPEN"),
            url=node.get("url", ""),
            labels=labels,
            assignees=assignees,
            created_at=created_at,
            updated_at=updated_at,
            author=author,
        )

    def _parse_pr_from_timeline_event(
        self, event: dict[str, Any], repo_id: GitHubRepoId
    ) -> tuple[PullRequestInfo, str] | None:
        """Parse PR info from a timeline CrossReferencedEvent.

        Returns tuple of (PullRequestInfo, created_at_timestamp) or None if invalid.
        The willCloseTarget field from the event indicates whether the PR will
        close this issue when merged. PRs with willCloseTarget=False are still
        included (they reference the issue but won't close it on merge).
        """
        source = event.get("source")
        if source is None:
            return None

        pr_number = source.get("number")
        pr_state = source.get("state")
        pr_url = source.get("url")
        created_at_pr = source.get("createdAt")

        # Skip if essential fields are missing (source may be Issue, not PR)
        if pr_number is None or pr_state is None or pr_url is None or created_at_pr is None:
            return None

        checks_passing, checks_counts = self._parse_status_rollup(source.get("statusCheckRollup"))
        has_conflicts = self._parse_mergeable_status(source.get("mergeable"))
        will_close_target = event.get("willCloseTarget", False)
        review_thread_counts = self._parse_review_thread_counts(source.get("reviewThreads"))
        head_ref_name = source.get("headRefName")
        review_decision = source.get("reviewDecision")

        pr_info = PullRequestInfo(
            number=pr_number,
            state=pr_state,
            url=pr_url,
            is_draft=source.get("isDraft", False),
            title=None,
            checks_passing=checks_passing,
            owner=repo_id.owner,
            repo=repo_id.repo,
            has_conflicts=has_conflicts,
            checks_counts=checks_counts,
            will_close_target=will_close_target,
            review_thread_counts=review_thread_counts,
            head_branch=head_ref_name,
            review_decision=review_decision,
            base_ref_name=source.get("baseRefName"),
        )
        return (pr_info, created_at_pr)

    def _parse_status_rollup(
        self, status_rollup: dict[str, Any] | None
    ) -> tuple[bool | None, tuple[int, int] | None]:
        """Parse checks status and counts from statusCheckRollup.

        Returns (checks_passing, checks_counts).
        """
        if status_rollup is None:
            return (None, None)

        rollup_state = status_rollup.get("state")
        checks_passing = None
        if rollup_state == "SUCCESS":
            checks_passing = True
        elif rollup_state in ("FAILURE", "ERROR"):
            checks_passing = False

        checks_counts = None
        contexts = status_rollup.get("contexts")
        if contexts is not None and isinstance(contexts, dict):
            total = contexts.get("totalCount", 0)
            if total > 0:
                checks_counts = parse_aggregated_check_counts(
                    contexts.get("checkRunCountsByState", []),
                    contexts.get("statusContextCountsByState", []),
                    total,
                )

        return (checks_passing, checks_counts)

    def _parse_mergeable_status(self, mergeable: str | None) -> bool | None:
        """Parse has_conflicts from mergeable field."""
        if mergeable == "CONFLICTING":
            return True
        if mergeable == "MERGEABLE":
            return False
        return None

    def _parse_review_thread_counts(
        self, review_threads: dict[str, Any] | None
    ) -> tuple[int, int] | None:
        """Parse review thread counts from reviewThreads field.

        Returns (resolved_count, total_count) or None if not available.
        """
        if review_threads is None:
            return None

        total_count = review_threads.get("totalCount", 0)
        if total_count == 0:
            return (0, 0)

        # Count resolved threads from the nodes
        nodes = review_threads.get("nodes", [])
        resolved_count = sum(1 for node in nodes if node and node.get("isResolved", False))

        return (resolved_count, total_count)

    def _parse_issues_with_pr_linkages(
        self,
        response: dict[str, Any],
        repo_id: GitHubRepoId,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Parse GraphQL response to extract issues and PR linkages.

        Uses CrossReferencedEvent timeline items to build the issue -> PR mapping.
        This captures ALL PRs that reference each issue, with willCloseTarget
        indicating whether the PR will close the issue when merged.
        """
        issues: list[IssueInfo] = []
        pr_linkages: dict[int, list[PullRequestInfo]] = {}

        repo_data = response.get("data", {}).get("repository", {})
        issue_nodes = repo_data.get("issues", {}).get("nodes", [])

        for node in issue_nodes:
            if node is None:
                continue

            issue = self._parse_issue_node(node)
            if issue is None:
                continue
            issues.append(issue)

            # Parse PR linkages from timelineItems
            timeline_nodes = node.get("timelineItems", {}).get("nodes", [])
            prs_with_timestamps: list[tuple[PullRequestInfo, str]] = []

            for event in timeline_nodes:
                if event is None:
                    continue
                result = self._parse_pr_from_timeline_event(event, repo_id)
                if result is not None:
                    prs_with_timestamps.append(result)

            if prs_with_timestamps:
                prs_with_timestamps.sort(key=lambda x: x[1], reverse=True)
                pr_linkages[issue.number] = [pr for pr, _ in prs_with_timestamps]

        return (issues, pr_linkages)

    def get_pr(self, repo_root: Path, pr_number: int) -> PRDetails | PRNotFound:
        """Get comprehensive PR details via GitHub REST API.

        Uses gh api to call GET /repos/{owner}/{repo}/pulls/{pr_number}
        which returns all PR fields in a single request.

        Returns:
            PRDetails with all PR fields, or PRNotFound if PR doesn't exist
        """
        assert self._repo_info is not None, "repo_info required for get_pr"
        endpoint = f"/repos/{self._repo_info.owner}/{self._repo_info.name}/pulls/{pr_number}"

        # GH-API-AUDIT: REST - GET pulls/{number}
        cmd = ["gh", "api", endpoint]
        try:
            stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        except RuntimeError:
            # API call failed - PR not found or other error
            return PRNotFound(pr_number=pr_number)

        data = json.loads(stdout)
        return self._parse_pr_details_from_rest_api(data, self._repo_info)

    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PRDetails | PRNotFound:
        """Get comprehensive PR details for a branch via GitHub REST API.

        Uses gh api to call GET /repos/{owner}/{repo}/pulls?head={owner}:{branch}&state=all
        which returns PRs for the branch in a single request.

        Returns:
            PRDetails if a PR exists for the branch, PRNotFound otherwise
        """
        assert self._repo_info is not None, "repo_info required for get_pr_for_branch"
        endpoint = (
            f"/repos/{self._repo_info.owner}/{self._repo_info.name}/pulls"
            f"?head={self._repo_info.owner}:{branch}&state=all"
        )

        # GH-API-AUDIT: REST - GET pulls (filtered by head)
        cmd = ["gh", "api", endpoint]
        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        data = json.loads(stdout)

        if not data:
            return PRNotFound(branch=branch)

        pr = data[0]
        return self._parse_pr_details_from_rest_api(pr, self._repo_info)

    def _parse_pr_details_from_rest_api(
        self, data: dict[str, Any], repo_info: RepoInfo
    ) -> PRDetails:
        """Parse PRDetails from REST API response data.

        Args:
            data: PR data from REST API response
            repo_info: Repository owner and name

        Returns:
            PRDetails with all PR fields
        """
        # Derive state (REST API uses "open"/"closed" + merged boolean)
        if data.get("merged"):
            state = "MERGED"
        elif data["state"] == "closed":
            state = "CLOSED"
        else:
            state = "OPEN"

        # Map mergeable (true/false/null) to MERGEABLE/CONFLICTING/UNKNOWN
        mergeable_raw = data.get("mergeable")
        if mergeable_raw is True:
            mergeable = "MERGEABLE"
        elif mergeable_raw is False:
            mergeable = "CONFLICTING"
        else:
            mergeable = "UNKNOWN"

        # Map mergeable_state to upper case
        merge_state_status = (data.get("mergeable_state") or "UNKNOWN").upper()

        # Extract labels
        labels = tuple(lbl.get("name", "") for lbl in data.get("labels", []))

        # Parse timestamps
        created_at_str = data.get("created_at", "")
        updated_at_str = data.get("updated_at", "")
        created_at = (
            datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if created_at_str
            else datetime(2000, 1, 1, tzinfo=UTC)
        )
        updated_at = (
            datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            if updated_at_str
            else datetime(2000, 1, 1, tzinfo=UTC)
        )

        # Extract author login
        author = ""
        if "user" in data and data["user"] and "login" in data["user"]:
            author = data["user"]["login"]

        # Check if head repo exists (can be None for deleted forks)
        head_repo = data["head"].get("repo")
        is_cross_repository = head_repo["fork"] if head_repo else False

        return PRDetails(
            number=data["number"],
            url=data["html_url"],
            title=data.get("title") or "",
            body=data.get("body") or "",
            state=state,
            is_draft=data.get("draft", False),
            base_ref_name=data["base"]["ref"],
            head_ref_name=data["head"]["ref"],
            is_cross_repository=is_cross_repository,
            mergeable=mergeable,
            merge_state_status=merge_state_status,
            owner=repo_info.owner,
            repo=repo_info.name,
            labels=labels,
            created_at=created_at,
            updated_at=updated_at,
            author=author,
        )

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

        Uses REST API to fetch PRs in a single call. Filters by labels, author,
        and draft status are applied client-side on the REST response data
        (the REST pulls endpoint does not support these filters natively).

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
        assert self._repo_info is not None, "repo_info required for list_prs"

        # GH-API-AUDIT: REST - GET pulls (list)
        endpoint = (
            f"/repos/{self._repo_info.owner}/{self._repo_info.name}/pulls"
            f"?state={state}&per_page=100"
        )
        cmd = ["gh", "api", endpoint]

        try:
            stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        except RuntimeError:
            # API call failed - return empty dict for graceful degradation
            # This allows callers to proceed without PR data rather than crashing
            return {}

        data = json.loads(stdout)
        result: dict[str, PullRequestInfo] = {}

        for pr_data in data:
            # Apply draft filter
            pr_is_draft = pr_data.get("draft", False)
            if draft is not None and pr_is_draft != draft:
                continue

            # Apply author filter (REST returns user.login)
            if author is not None:
                pr_author = pr_data.get("user", {}).get("login")
                if pr_author != author:
                    continue

            # Apply label filter (REST returns labels[].name)
            if labels is not None:
                pr_label_names = {label["name"] for label in pr_data.get("labels", [])}
                if not all(label in pr_label_names for label in labels):
                    continue

            # Derive state (REST API uses "open"/"closed" + merged boolean)
            if pr_data.get("merged"):
                pr_state = "MERGED"
            elif pr_data["state"] == "closed":
                pr_state = "CLOSED"
            else:
                pr_state = "OPEN"

            branch = pr_data["head"]["ref"]
            result[branch] = PullRequestInfo(
                number=pr_data["number"],
                state=pr_state,
                url=pr_data["html_url"],
                is_draft=pr_is_draft,
                title=pr_data.get("title"),
                checks_passing=None,  # Not fetched in batch API
                owner=self._repo_info.owner,
                repo=self._repo_info.name,
                has_conflicts=None,  # Not fetched in batch API
                checks_counts=None,
                will_close_target=False,
                base_ref_name=pr_data.get("base", {}).get("ref"),
            )

        return result

    def list_plan_prs_with_details(
        self,
        location: GitHubRepoLocation,
        *,
        labels: list[str],
        state: IssueFilterState,
        limit: int | None,
        author: str | None,
        exclude_labels: list[str] | None = None,
    ) -> tuple[list[PRDetails], dict[int, list[PullRequestInfo]]]:
        """List plan PRs with rich details via REST+GraphQL two-step approach.

        Step 1: REST issues endpoint for server-side author/label filtering.
        Step 2: Batched GraphQL enrichment for rich PR fields.

        This is faster than the single GraphQL pullRequests query because:
        - REST supports server-side creator filtering (GraphQL pullRequests doesn't)
        - Only enriches the filtered set, not all PRs with the label
        """
        repo_id = location.repo_id

        # Step 1: REST issues list with server-side filtering
        rest_state = state.lower()
        effective_limit = limit if limit is not None else 30

        endpoint = f"repos/{repo_id.owner}/{repo_id.repo}/issues"
        params = [
            f"labels={','.join(labels)}",
            f"state={rest_state}",
            f"per_page={effective_limit}",
            "sort=updated",
            "direction=desc",
        ]
        if author is not None:
            params.append(f"creator={author}")

        endpoint += "?" + "&".join(params)

        # GH-API-AUDIT: REST - GET issues (with creator + label filtering)
        cmd = ["gh", "api", endpoint]

        t_rest_start = time.monotonic()
        try:
            stdout = execute_gh_command_with_retry(cmd, location.root, self._time)
        except RuntimeError:
            return ([], {})
        t_rest_end = time.monotonic()

        issues_data = json.loads(stdout)

        # Filter to PRs only (items with pull_request key)
        pr_items = [item for item in issues_data if "pull_request" in item]

        # Client-side exclude_labels filtering (cheap — labels are in REST response)
        if exclude_labels:
            exclude_set = set(exclude_labels)
            pr_items = [
                item
                for item in pr_items
                if not any(label["name"] in exclude_set for label in item.get("labels", []))
            ]

        if not pr_items:
            rest_ms = _elapsed_ms(t_rest_start, t_rest_end)
            _logger.info("list_plan_prs_with_details: REST=%.0fms (0 PRs after filter)", rest_ms)
            return ([], {})

        # Step 2: Batched GraphQL enrichment for rich PR fields
        pr_numbers = [item["number"] for item in pr_items]
        t_gql_start = time.monotonic()
        enrichment_data = self._enrich_prs_via_graphql(location, pr_numbers)
        t_gql_end = time.monotonic()

        rest_ms = _elapsed_ms(t_rest_start, t_rest_end)
        gql_ms = _elapsed_ms(t_gql_start, t_gql_end)
        merge_ms = _elapsed_ms(t_gql_end, time.monotonic())
        _logger.info(
            "list_plan_prs_with_details: REST=%.0fms GraphQL=%.0fms merge=%.0fms (%d PRs)",
            rest_ms,
            gql_ms,
            merge_ms,
            len(pr_numbers),
        )

        # Merge REST + GraphQL data into PRDetails and PullRequestInfo
        return self._merge_rest_graphql_pr_data(pr_items, enrichment_data, repo_id)

    def _parse_plan_prs_with_details(
        self,
        response: dict[str, Any],
        repo_id: GitHubRepoId,
        *,
        author: str | None,
    ) -> tuple[list[PRDetails], dict[int, list[PullRequestInfo]]]:
        """Parse GraphQL response for plan PRs into PRDetails and PullRequestInfo."""
        pr_details_list: list[PRDetails] = []
        pr_linkages: dict[int, list[PullRequestInfo]] = {}

        repo_data = response.get("data", {}).get("repository")
        if repo_data is None:
            return ([], {})

        nodes = repo_data.get("pullRequests", {}).get("nodes", [])
        for node in nodes:
            if node is None:
                continue

            pr_number = node.get("number")
            if pr_number is None:
                continue

            # Client-side author filter
            author_data = node.get("author")
            pr_author = author_data.get("login", "") if author_data else ""
            if author is not None and pr_author != author:
                continue

            # Parse timestamps
            created_at_str = node.get("createdAt", "")
            updated_at_str = node.get("updatedAt", "")
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))

            # Parse labels
            labels_data = node.get("labels", {}).get("nodes", [])
            label_names = tuple(label.get("name", "") for label in labels_data if label)

            # Build PRDetails
            pr_state = node.get("state", "OPEN")
            mergeable_raw = node.get("mergeable", "UNKNOWN")
            pr_details = PRDetails(
                number=pr_number,
                url=node.get("url", ""),
                title=node.get("title", ""),
                body=node.get("body", ""),
                state=pr_state,
                is_draft=node.get("isDraft", False),
                base_ref_name=node.get("baseRefName", ""),
                head_ref_name=node.get("headRefName", ""),
                is_cross_repository=node.get("isCrossRepository", False),
                mergeable=mergeable_raw,
                merge_state_status=node.get("mergeStateStatus", "UNKNOWN"),
                owner=repo_id.owner,
                repo=repo_id.repo,
                labels=label_names,
                created_at=created_at,
                updated_at=updated_at,
                author=pr_author,
            )
            pr_details_list.append(pr_details)

            # Build PullRequestInfo with rich data
            checks_passing, checks_counts = self._parse_status_rollup(node.get("statusCheckRollup"))
            has_conflicts = self._parse_mergeable_status(node.get("mergeable"))
            review_thread_counts = self._parse_review_thread_counts(node.get("reviewThreads"))
            review_decision = node.get("reviewDecision")

            pr_info = PullRequestInfo(
                number=pr_number,
                state=pr_state,
                url=node.get("url", ""),
                is_draft=node.get("isDraft", False),
                title=node.get("title"),
                checks_passing=checks_passing,
                owner=repo_id.owner,
                repo=repo_id.repo,
                has_conflicts=has_conflicts,
                checks_counts=checks_counts,
                review_thread_counts=review_thread_counts,
                head_branch=node.get("headRefName"),
                review_decision=review_decision,
                base_ref_name=node.get("baseRefName"),
            )
            pr_linkages[pr_number] = [pr_info]

        return (pr_details_list, pr_linkages)

    def _enrich_prs_via_graphql(
        self,
        location: GitHubRepoLocation,
        pr_numbers: list[int],
    ) -> dict[int, dict[str, Any]]:
        """Batch-fetch rich PR fields via a single aliased GraphQL query.

        Builds a dynamic query with aliased pullRequest(number: N) fields
        to fetch checks, review threads, merge status, etc. in one API call.

        Args:
            location: GitHub repository location
            pr_numbers: List of PR numbers to enrich

        Returns:
            Mapping of pr_number -> GraphQL node data dict
        """
        repo_id = location.repo_id

        # Build aliased pull request fields
        pr_fields = """
            isDraft
            mergeable
            mergeStateStatus
            isCrossRepository
            baseRefName
            headRefName
            statusCheckRollup {
                state
                contexts(last: 1) {
                    totalCount
                    checkRunCountsByState { state count }
                    statusContextCountsByState { state count }
                }
            }
            reviewThreads(first: 100) {
                totalCount
                nodes { isResolved }
            }
            reviewDecision
        """

        aliases = []
        for pr_num in pr_numbers:
            aliases.append(f"pr_{pr_num}: pullRequest(number: {pr_num}) {{ {pr_fields} }}")

        query = (
            "query($owner: String!, $repo: String!) {"
            f"  repository(owner: $owner, name: $repo) {{ {' '.join(aliases)} }}"
            "}"
        )

        # GH-API-AUDIT: GraphQL - batched pullRequest enrichment
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"owner={repo_id.owner}",
            "-f",
            f"repo={repo_id.repo}",
        ]

        try:
            stdout = execute_gh_command_with_retry(cmd, location.root, self._time)
        except RuntimeError:
            return {}

        response = json.loads(stdout)
        repo_data = response.get("data", {}).get("repository", {})

        result: dict[int, dict[str, Any]] = {}
        for pr_num in pr_numbers:
            alias = f"pr_{pr_num}"
            node = repo_data.get(alias)
            if node is not None:
                result[pr_num] = node

        return result

    def _merge_rest_graphql_pr_data(
        self,
        rest_items: list[dict[str, Any]],
        enrichment: dict[int, dict[str, Any]],
        repo_id: GitHubRepoId,
    ) -> tuple[list[PRDetails], dict[int, list[PullRequestInfo]]]:
        """Merge REST issue data with GraphQL PR enrichment into PRDetails and PullRequestInfo.

        Args:
            rest_items: Raw REST API issue/PR items
            enrichment: GraphQL enrichment data keyed by PR number
            repo_id: GitHub repository identity

        Returns:
            Tuple of (pr_details_list, pr_linkages_by_pr_number)
        """
        pr_details_list: list[PRDetails] = []
        pr_linkages: dict[int, list[PullRequestInfo]] = {}

        for item in rest_items:
            pr_number = item["number"]
            gql = enrichment.get(pr_number, {})

            # Parse timestamps from REST
            created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))

            # Parse labels from REST
            label_names = tuple(label["name"] for label in item.get("labels", []))

            # Author from REST
            pr_author = item.get("user", {}).get("login", "")

            # Draft and merge info from GraphQL enrichment
            is_draft = gql.get("isDraft", False)
            mergeable_raw = gql.get("mergeable", "UNKNOWN")
            merge_state_status = gql.get("mergeStateStatus", "UNKNOWN")
            is_cross_repository = gql.get("isCrossRepository", False)
            base_ref_name = gql.get("baseRefName", "")
            rest_head_ref = item.get("pull_request", {}).get("head", {}).get("ref", "")
            head_ref_name = gql.get("headRefName", rest_head_ref)

            # State from REST (normalize to upper)
            pr_state = item.get("state", "open").upper()

            pr_details = PRDetails(
                number=pr_number,
                url=item.get("html_url", ""),
                title=item.get("title", ""),
                body=item.get("body", "") or "",
                state=pr_state,
                is_draft=is_draft,
                base_ref_name=base_ref_name,
                head_ref_name=head_ref_name,
                is_cross_repository=is_cross_repository,
                mergeable=mergeable_raw,
                merge_state_status=merge_state_status,
                owner=repo_id.owner,
                repo=repo_id.repo,
                labels=label_names,
                created_at=created_at,
                updated_at=updated_at,
                author=pr_author,
            )
            pr_details_list.append(pr_details)

            # Build PullRequestInfo with rich GraphQL data
            checks_passing, checks_counts = self._parse_status_rollup(gql.get("statusCheckRollup"))
            has_conflicts = self._parse_mergeable_status(gql.get("mergeable"))
            review_thread_counts = self._parse_review_thread_counts(gql.get("reviewThreads"))
            review_decision = gql.get("reviewDecision")

            pr_info = PullRequestInfo(
                number=pr_number,
                state=pr_state,
                url=item.get("html_url", ""),
                is_draft=is_draft,
                title=item.get("title"),
                checks_passing=checks_passing,
                owner=repo_id.owner,
                repo=repo_id.repo,
                has_conflicts=has_conflicts,
                checks_counts=checks_counts,
                review_thread_counts=review_thread_counts,
                head_branch=head_ref_name,
                review_decision=review_decision,
                base_ref_name=base_ref_name,
            )
            pr_linkages[pr_number] = [pr_info]

        return (pr_details_list, pr_linkages)

    def update_pr_title_and_body(
        self, *, repo_root: Path, pr_number: int, title: str, body: BodyContent
    ) -> None:
        """Update PR title and body on GitHub.

        Uses REST API to preserve GraphQL quota.

        When body is BodyFile, uses gh api's -F body=@{path} syntax to read
        from file, avoiding shell argument length limits for large bodies.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        # GH-API-AUDIT: REST - PATCH pulls/{number}
        cmd = [
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
            "-f",
            f"title={title}",
        ]

        # Use -F body=@file for BodyFile, -f body=value for BodyText
        if isinstance(body, BodyFile):
            cmd.extend(["-F", f"body=@{body.path}"])
        elif isinstance(body, BodyText):
            cmd.extend(["-f", f"body={body.content}"])

        execute_gh_command_with_retry(cmd, repo_root, self._time)

    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> None:
        """Mark a draft PR as ready for review.

        Uses REST API to preserve GraphQL quota.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        # GH-API-AUDIT: REST - PATCH pulls/{number} draft=false
        cmd = [
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
            "-F",
            "draft=false",
        ]
        execute_gh_command_with_retry(cmd, repo_root, self._time)

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Get the diff for a PR using gh CLI.

        Raises:
            RuntimeError: If gh command fails
        """
        # GH-API-AUDIT: REST - gh pr diff uses REST Accept header
        result = run_subprocess_with_context(
            cmd=["gh", "pr", "diff", str(pr_number)],
            operation_context=f"get diff for PR #{pr_number}",
            cwd=repo_root,
        )
        return result.stdout

    def get_pr_changed_files(self, repo_root: Path, pr_number: int) -> list[str]:
        """Get list of files changed in a pull request.

        Uses GitHub REST API with pagination to handle large PRs.
        """
        # GH-API-AUDIT: REST - GET pulls/{number}/files
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/files",
            "--paginate",
            "-q",
            ".[].filename",
        ]
        result = run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"get changed files for PR #{pr_number}",
            cwd=repo_root,
        )
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

    def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
        """Add a label to a pull request.

        Uses REST API to preserve GraphQL quota.
        (PRs share the same labels endpoint as issues.)

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        # GH-API-AUDIT: REST - POST issues/{number}/labels
        cmd = [
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{{owner}}/{{repo}}/issues/{pr_number}/labels",
            "-f",
            f"labels[]={label}",
        ]
        execute_gh_command_with_retry(cmd, repo_root, self._time)

    def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
        """Check if a PR has a specific label using gh CLI.

        Uses REST API (separate quota from GraphQL) via gh api command.

        Returns:
            True if the PR has the label, False otherwise.
        """
        # GH-API-AUDIT: REST - GET pulls/{number} (.labels)
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
            "--jq",
            ".labels[].name",
        ]
        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        labels = stdout.strip().split("\n") if stdout.strip() else []
        return label in labels

    def get_pr_review_threads(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        include_resolved: bool = False,
    ) -> list[PRReviewThread]:
        """Get review threads for a pull request via GraphQL.

        Uses the reviewThreads connection which provides resolution status
        that the REST API doesn't expose.
        """
        assert self._repo_info is not None, "repo_info required for get_pr_review_threads"

        # GH-API-AUDIT: GraphQL - reviewThreads query
        # WHY GRAPHQL: REST API does not expose isResolved field
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={GET_PR_REVIEW_THREADS_QUERY}",
            "-f",
            f"owner={self._repo_info.owner}",
            "-f",
            f"repo={self._repo_info.name}",
            "-F",
            f"number={pr_number}",
        ]
        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        response = json.loads(stdout)

        return self._parse_review_threads_response(response, include_resolved)

    def _parse_review_threads_response(
        self, response: dict[str, Any], include_resolved: bool
    ) -> list[PRReviewThread]:
        """Parse GraphQL response into PRReviewThread objects.

        Args:
            response: GraphQL response data
            include_resolved: Whether to include resolved threads

        Returns:
            List of PRReviewThread sorted by (path, line)
        """
        threads: list[PRReviewThread] = []

        pr_data = response.get("data", {}).get("repository", {}).get("pullRequest")
        if pr_data is None:
            return threads

        thread_nodes = pr_data.get("reviewThreads", {}).get("nodes", [])

        for node in thread_nodes:
            if node is None:
                continue

            is_resolved = node.get("isResolved", False)
            if is_resolved and not include_resolved:
                continue

            # Parse comments
            comments: list[PRReviewComment] = []
            comment_nodes = node.get("comments", {}).get("nodes", [])
            for comment_node in comment_nodes:
                if comment_node is None:
                    continue

                author = comment_node.get("author")
                author_login = author.get("login") if author else "unknown"

                comment = PRReviewComment(
                    id=comment_node.get("databaseId", 0),
                    body=comment_node.get("body", ""),
                    author=author_login,
                    path=comment_node.get("path", ""),
                    line=comment_node.get("line"),
                    created_at=comment_node.get("createdAt", ""),
                )
                comments.append(comment)

            thread = PRReviewThread(
                id=node.get("id", ""),
                path=node.get("path", ""),
                line=node.get("line"),
                is_resolved=is_resolved,
                is_outdated=node.get("isOutdated", False),
                comments=tuple(comments),
            )
            threads.append(thread)

        # Sort by path, then by line (None sorts first)
        threads.sort(key=lambda t: (t.path, t.line or 0))
        return threads

    def resolve_review_thread(
        self,
        repo_root: Path,
        thread_id: str,
    ) -> bool:
        """Resolve a PR review thread via GraphQL mutation.

        Args:
            repo_root: Repository root (for gh CLI context)
            thread_id: GraphQL node ID of the thread

        Returns:
            True if resolved successfully
        """
        # GH-API-AUDIT: GraphQL - resolveReviewThread mutation
        # WHY GRAPHQL: No REST endpoint exists for resolving review threads
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={RESOLVE_REVIEW_THREAD_MUTATION}",
            "-f",
            f"threadId={thread_id}",
        ]

        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        response = json.loads(stdout)

        # Check if the thread was resolved
        thread_data = response.get("data", {}).get("resolveReviewThread", {}).get("thread")
        if thread_data is None:
            return False

        return thread_data.get("isResolved", False)

    def add_review_thread_reply(
        self,
        repo_root: Path,
        thread_id: str,
        body: str,
    ) -> bool:
        """Add a reply comment to a PR review thread via GraphQL mutation.

        Args:
            repo_root: Repository root (for gh CLI context)
            thread_id: GraphQL node ID of the thread
            body: Comment body text

        Returns:
            True if comment added successfully
        """
        # GH-API-AUDIT: GraphQL - addPullRequestReviewThreadReply mutation
        # WHY GRAPHQL: REST requires interface change (PR number + comment ID vs thread node ID)
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={ADD_REVIEW_THREAD_REPLY_MUTATION}",
            "-f",
            f"threadId={thread_id}",
            "-f",
            f"body={body}",
        ]

        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        response = json.loads(stdout)

        # Check if the comment was added
        comment_data = (
            response.get("data", {}).get("addPullRequestReviewThreadReply", {}).get("comment")
        )
        return comment_data is not None

    def create_pr_review_comment(
        self, *, repo_root: Path, pr_number: int, body: str, commit_sha: str, path: str, line: int
    ) -> int:
        """Create an inline review comment on a specific line of a PR.

        Uses GitHub REST API to create a pull request review comment.
        """
        # GH-API-AUDIT: REST - POST pulls/{number}/comments
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/comments",
            "-f",
            f"body={body}",
            "-f",
            f"commit_id={commit_sha}",
            "-f",
            f"path={path}",
            "-F",
            f"line={line}",
            "-f",
            "side=RIGHT",
        ]

        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        response = json.loads(stdout)
        return response["id"]

    def find_pr_comment_by_marker(
        self,
        repo_root: Path,
        pr_number: int,
        marker: str,
    ) -> int | None:
        """Find a PR/issue comment containing a specific HTML marker.

        Uses REST API to list issue comments (PRs are issues in GitHub's model).
        Returns the numeric database ID needed for update operations.
        Fetches all comments as JSON and searches in Python to avoid
        shell escaping issues with special characters in markers.
        """
        # GH-API-AUDIT: REST - GET issues/{number}/comments
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{pr_number}/comments",
            "--paginate",
        ]

        try:
            stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
            comments = json.loads(stdout)
            for comment in comments:
                body = comment.get("body", "")
                if marker in body:
                    comment_id = comment.get("id")
                    if comment_id is not None:
                        return int(comment_id)
            return None
        except RuntimeError as e:
            # Command failed - log for diagnostics but return None
            # (marker not found is expected on first run)
            debug_log(f"find_pr_comment_by_marker failed: {e}")
            return None

    def update_pr_comment(
        self,
        repo_root: Path,
        comment_id: int,
        body: str,
    ) -> None:
        """Update an existing PR/issue comment.

        Uses GitHub REST API via gh api command.
        """
        # GH-API-AUDIT: REST - PATCH issues/comments/{id}
        cmd = [
            "gh",
            "api",
            "--method",
            "PATCH",
            f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}",
            "-f",
            f"body={body}",
        ]
        execute_gh_command_with_retry(cmd, repo_root, self._time)

    def create_pr_comment(
        self,
        repo_root: Path,
        pr_number: int,
        body: str,
    ) -> int:
        """Create a new comment on a PR.

        Uses GitHub REST API to create the comment and returns the ID.
        PRs are issues in GitHub's data model, so we use the issues endpoint.
        """
        # GH-API-AUDIT: REST - POST issues/{number}/comments
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/issues/{pr_number}/comments",
            "-f",
            f"body={body}",
        ]
        stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        response = json.loads(stdout)
        return response["id"]

    def delete_remote_branch(self, repo_root: Path, branch: str) -> bool:
        """Delete a remote branch via REST API.

        Uses DELETE /repos/{owner}/{repo}/git/refs/heads/{branch} endpoint.

        Returns True if the branch was deleted or didn't exist.
        Returns False if deletion failed (e.g., protected branch).
        """
        # GH-API-AUDIT: REST - DELETE git/refs/heads/{branch}
        cmd = [
            "gh",
            "api",
            "--method",
            "DELETE",
            f"repos/{{owner}}/{{repo}}/git/refs/heads/{branch}",
        ]

        try:
            run_subprocess_with_context(
                cmd=cmd,
                operation_context=f"delete remote branch '{branch}'",
                cwd=repo_root,
            )
            return True
        except RuntimeError as e:
            # Check if it's a 404 (branch doesn't exist) - that's fine
            error_str = str(e)
            if "404" in error_str or "Reference does not exist" in error_str:
                return True
            # Log other errors but don't fail - best effort deletion
            debug_log(f"delete_remote_branch failed: {e}")
            return False

    def get_open_prs_with_base_branch(
        self, repo_root: Path, base_branch: str
    ) -> list[PullRequestInfo]:
        """Get all open PRs that have the given branch as their base.

        Uses REST API to fetch PRs filtered by base branch and state=open.
        """
        assert self._repo_info is not None, "repo_info required for get_open_prs_with_base_branch"

        # GH-API-AUDIT: REST - GET pulls (filtered by base and state)
        endpoint = (
            f"/repos/{self._repo_info.owner}/{self._repo_info.name}/pulls"
            f"?base={base_branch}&state=open&per_page=100"
        )
        cmd = ["gh", "api", endpoint]

        try:
            stdout = execute_gh_command_with_retry(cmd, repo_root, self._time)
        except RuntimeError:
            # API call failed - return empty list for graceful degradation
            return []

        data = json.loads(stdout)
        result: list[PullRequestInfo] = []

        for pr_data in data:
            branch = pr_data["head"]["ref"]
            result.append(
                PullRequestInfo(
                    number=pr_data["number"],
                    state="OPEN",  # We filtered by state=open
                    url=pr_data["html_url"],
                    is_draft=pr_data.get("draft", False),
                    title=pr_data.get("title"),
                    checks_passing=None,  # Not fetched in this API call
                    owner=self._repo_info.owner,
                    repo=self._repo_info.name,
                    has_conflicts=None,  # Not fetched in this API call
                    checks_counts=None,
                    will_close_target=False,
                    head_branch=branch,
                )
            )

        return result

    def download_run_artifact(
        self,
        repo_root: Path,
        run_id: str,
        artifact_name: str,
        destination: Path,
    ) -> bool:
        """Download an artifact from a GitHub Actions workflow run.

        Uses gh run download to fetch the artifact.
        """
        cmd = [
            "gh",
            "run",
            "download",
            run_id,
            "--name",
            artifact_name,
            "--dir",
            str(destination),
        ]

        try:
            run_subprocess_with_context(
                cmd=cmd,
                operation_context=f"download artifact '{artifact_name}' from run {run_id}",
                cwd=repo_root,
            )
            return True
        except RuntimeError:
            return False

    def get_issues_by_numbers_with_pr_linkages(
        self,
        *,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Fetch specific issues by number with full PR linkage data.

        Uses issueOrPullRequest to handle both issues and merged PRs.
        """
        if not issue_numbers:
            return ([], {})

        repo_id = location.repo_id
        query = self._build_issues_by_numbers_query(issue_numbers, repo_id)
        response = self._execute_batch_pr_query(query, location.root)
        return self._parse_issues_by_numbers_response(response, repo_id)

    def _build_issues_by_numbers_query(
        self, issue_numbers: list[int], repo_id: GitHubRepoId
    ) -> str:
        """Build GraphQL query to fetch specific issues by number.

        Uses issueOrPullRequest(number: N) aliases to handle both issues
        and merged PRs. Includes full issue fields and PR linkage timeline.

        Args:
            issue_numbers: List of issue/PR numbers to query
            repo_id: GitHub repository identity

        Returns:
            GraphQL query string
        """
        issue_queries = []
        for issue_num in issue_numbers:
            issue_query = f"""    issue_{issue_num}: issueOrPullRequest(number: {issue_num}) {{
      ... on Issue {{
        number
        title
        body
        state
        url
        author {{ login }}
        labels(first: 100) {{ nodes {{ name }} }}
        assignees(first: 100) {{ nodes {{ login }} }}
        createdAt
        updatedAt
        timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 20) {{
          nodes {{
            ... on CrossReferencedEvent {{
              ...IssuePRLinkageFields
            }}
          }}
        }}
      }}
      ... on PullRequest {{
        number
        title
        body
        state
        url
        author {{ login }}
        labels(first: 100) {{ nodes {{ name }} }}
        assignees(first: 100) {{ nodes {{ login }} }}
        createdAt
        updatedAt
      }}
    }}"""
            issue_queries.append(issue_query)

        joined_queries = "\n".join(issue_queries)
        query = f"""{ISSUE_PR_LINKAGE_FRAGMENT}

query {{
  repository(owner: "{repo_id.owner}", name: "{repo_id.repo}") {{
{joined_queries}
  }}
}}"""
        return query

    def _parse_issues_by_numbers_response(
        self,
        response: dict[str, Any],
        repo_id: GitHubRepoId,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Parse GraphQL response from issues-by-numbers query.

        Iterates over aliased keys (issue_8070, etc.) and parses each node.

        Args:
            response: GraphQL response data
            repo_id: GitHub repository identity

        Returns:
            Tuple of (issues, pr_linkages)
        """
        issues: list[IssueInfo] = []
        pr_linkages: dict[int, list[PullRequestInfo]] = {}

        repo_data = response.get("data", {}).get("repository", {})

        for key, node in repo_data.items():
            if not key.startswith("issue_") or node is None:
                continue

            issue = self._parse_issue_node(node)
            if issue is None:
                continue
            issues.append(issue)

            # Parse PR linkages from timelineItems (only present on Issue type)
            timeline_items = node.get("timelineItems")
            if timeline_items is not None:
                timeline_nodes = timeline_items.get("nodes", [])
                prs_with_timestamps: list[tuple[PullRequestInfo, str]] = []

                for event in timeline_nodes:
                    if event is None:
                        continue
                    result = self._parse_pr_from_timeline_event(event, repo_id)
                    if result is not None:
                        prs_with_timestamps.append(result)

                if prs_with_timestamps:
                    prs_with_timestamps.sort(key=lambda x: x[1], reverse=True)
                    pr_linkages[issue.number] = [pr for pr, _ in prs_with_timestamps]

        return (issues, pr_linkages)

    def create_commit_status(
        self,
        *,
        repo: str,
        sha: str,
        state: str,
        context: str,
        description: str,
    ) -> bool:
        """Create a commit status on GitHub via REST API.

        Uses the statuses API endpoint to create a commit status.
        """
        # GH-API-AUDIT: REST - POST statuses/{sha}
        cmd = [
            "gh",
            "api",
            f"repos/{repo}/statuses/{sha}",
            "-f",
            f"state={state}",
            "-f",
            f"context={context}",
            "-f",
            f"description={description}",
        ]

        try:
            run_subprocess_with_context(
                cmd=cmd,
                operation_context=f"create commit status for {sha[:8]}",
            )
            return True
        except RuntimeError:
            return False
