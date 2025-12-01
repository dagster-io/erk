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
import secrets
import string
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from erk_shared.debug import debug_log
from erk_shared.github.abc import GitHub
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.parsing import (
    execute_gh_command,
    parse_aggregated_check_counts,
    parse_gh_auth_status_output,
    parse_github_pr_list,
    parse_github_pr_status,
)
from erk_shared.github.types import (
    BRANCH_NOT_AVAILABLE,
    DISPLAY_TITLE_NOT_AVAILABLE,
    GitHubRepoLocation,
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
    RepoInfo,
    WorkflowRun,
    WorkflowRunConclusion,
    WorkflowRunStatus,
)
from erk_shared.integrations.time.abc import Time
from erk_shared.output.output import user_output
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitHub(GitHub):
    """Production implementation using gh CLI.

    All GitHub operations execute actual gh commands via subprocess.
    """

    def __init__(self, time: Time):
        """Initialize RealGitHub.

        Args:
            time: Time abstraction for sleep operations
        """
        self._time = time

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches in the repository.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            # Build JSON fields list - conditionally include statusCheckRollup for performance
            json_fields = "number,headRefName,url,state,isDraft,title"
            if include_checks:
                json_fields += ",statusCheckRollup"

            cmd = [
                "gh",
                "pr",
                "list",
                "--state",
                "all",
                "--json",
                json_fields,
            ]
            stdout = execute_gh_command(cmd, repo_root)
            return parse_github_pr_list(stdout, include_checks)

        except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
            # gh not installed, not authenticated, or JSON parsing failed
            return {}

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status for a specific branch.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            # Query gh for PR info for this specific branch
            cmd = [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "number,state,title",
                "--limit",
                "1",
            ]

            if debug:
                user_output(f"$ {' '.join(cmd)}")

            stdout = execute_gh_command(cmd, repo_root)
            return parse_github_pr_status(stdout)

        except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
            # gh not installed, not authenticated, or JSON parsing failed
            return PRInfo("NONE", None, None)

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str | None:
        """Get current base branch of a PR from GitHub.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            cmd = [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "baseRefName",
                "--jq",
                ".baseRefName",
            ]
            stdout = execute_gh_command(cmd, repo_root)
            return stdout.strip()

        except (RuntimeError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            return None

    def update_pr_base_branch(self, repo_root: Path, pr_number: int, new_base: str) -> None:
        """Update base branch of a PR on GitHub.

        Gracefully handles gh CLI availability issues (not installed, not authenticated).
        The calling code should validate preconditions (PR exists, is open, new base exists)
        before calling this method.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability. Genuine command failures (invalid PR, invalid base) should be
        caught by precondition checks in the caller.
        """
        try:
            cmd = ["gh", "pr", "edit", str(pr_number), "--base", new_base]
            execute_gh_command(cmd, repo_root)
        except (RuntimeError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            # Graceful degradation - operation skipped
            # Caller is responsible for precondition validation
            pass

    def update_pr_body(self, repo_root: Path, pr_number: int, body: str) -> None:
        """Update body of a PR on GitHub.

        Gracefully handles gh CLI availability issues (not installed, not authenticated).
        The calling code should validate preconditions (PR exists, is open)
        before calling this method.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability. Genuine command failures (invalid PR) should be
        caught by precondition checks in the caller.
        """
        try:
            cmd = ["gh", "pr", "edit", str(pr_number), "--body", body]
            execute_gh_command(cmd, repo_root)
        except (RuntimeError, FileNotFoundError):
            # gh not installed, not authenticated, or command failed
            # Graceful degradation - operation skipped
            # Caller is responsible for precondition validation
            pass

    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from GitHub via gh CLI.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            result = run_subprocess_with_context(
                ["gh", "pr", "view", str(pr_number), "--json", "mergeable,mergeStateStatus"],
                operation_context=f"check PR mergeability for PR #{pr_number}",
                cwd=repo_root,
            )
            data = json.loads(result.stdout)
            return PRMergeability(
                mergeable=data["mergeable"],
                merge_state_status=data["mergeStateStatus"],
            )
        except (
            RuntimeError,
            json.JSONDecodeError,
            KeyError,
            FileNotFoundError,
        ):
            return None

    def _build_batch_pr_query(self, pr_numbers: list[int], owner: str, repo: str) -> str:
        """Build GraphQL query with aliases for multiple PRs using named fragments.

        Args:
            pr_numbers: List of PR numbers to query
            owner: Repository owner
            repo: Repository name

        Returns:
            GraphQL query string
        """
        # Define the fragment once at the top of the query
        # Uses pre-aggregated count fields for ~15-30x smaller payload vs fetching 100 nodes
        fragment_definition = """fragment PRCICheckFields on PullRequest {
  number
  title
  mergeable
  mergeStateStatus
  commits(last: 1) {
    nodes {
      commit {
        statusCheckRollup {
          state
          contexts(last: 1) {
            totalCount
            checkRunCountsByState { state count }
            statusContextCountsByState { state count }
          }
        }
      }
    }
  }
}"""

        # Build aliased PR queries using the fragment spread
        pr_queries = []
        for pr_num in pr_numbers:
            pr_query = f"""    pr_{pr_num}: pullRequest(number: {pr_num}) {{
      ...PRCICheckFields
    }}"""
            pr_queries.append(pr_query)

        # Combine fragment definition and query
        query = f"""{fragment_definition}

query {{
  repository(owner: "{owner}", name: "{repo}") {{
{chr(10).join(pr_queries)}
  }}
}}"""
        return query

    def _execute_batch_pr_query(self, query: str, repo_root: Path) -> dict[str, Any]:
        """Execute batched GraphQL query via gh CLI.

        Args:
            query: GraphQL query string
            repo_root: Repository root directory

        Returns:
            Parsed JSON response
        """
        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
        stdout = execute_gh_command(cmd, repo_root)
        return json.loads(stdout)

    def _extract_aggregated_check_data(
        self, pr_data: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Extract aggregated check count data from GraphQL PR response.

        Returns dict with keys: totalCount, checkRunCountsByState, statusContextCountsByState
        or None if not available.
        """
        if pr_data is None:
            return None
        commits = pr_data.get("commits")
        if commits is None:
            return None
        nodes = commits.get("nodes", [])
        if not nodes:
            return None
        commit = nodes[0].get("commit")
        if commit is None:
            return None
        status_check_rollup = commit.get("statusCheckRollup")
        if status_check_rollup is None:
            return None
        contexts = status_check_rollup.get("contexts")
        if contexts is None or not isinstance(contexts, dict):
            return None
        return contexts

    def _parse_pr_ci_counts(self, pr_data: dict[str, Any] | None) -> tuple[int, int] | None:
        """Parse check counts from GraphQL PR response using aggregated fields."""
        contexts = self._extract_aggregated_check_data(pr_data)
        if contexts is None:
            return None

        total = contexts.get("totalCount", 0)
        if total == 0:
            return None

        check_run_counts = contexts.get("checkRunCountsByState", [])
        status_context_counts = contexts.get("statusContextCountsByState", [])

        return parse_aggregated_check_counts(check_run_counts, status_context_counts, total)

    def _parse_pr_ci_status(self, pr_data: dict[str, Any] | None) -> bool | None:
        """Parse CI status from GraphQL PR response.

        Args:
            pr_data: GraphQL response data for single PR (may be None)

        Returns:
            True if all checks passing, False if any failing, None if no checks or error
        """
        counts = self._parse_pr_ci_counts(pr_data)
        if counts is None:
            return None
        passing, total = counts
        return passing == total

    def _parse_pr_mergeability(self, pr_data: dict[str, Any] | None) -> bool | None:
        """Parse mergeability status from GraphQL PR data.

        Args:
            pr_data: PR data from GraphQL response (may be None for missing PRs)

        Returns:
            True if PR has conflicts, False if mergeable, None if unknown/unavailable
        """
        if pr_data is None:
            return None

        if "mergeable" not in pr_data:
            return None

        mergeable = pr_data["mergeable"]

        # Convert GitHub's mergeable status to has_conflicts boolean
        if mergeable == "CONFLICTING":
            return True
        if mergeable == "MERGEABLE":
            return False

        # UNKNOWN or other states
        return None

    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PR information with CI check status and mergeability using batched GraphQL query.

        Fetches both CI status and mergeability for all PRs in a single GraphQL API call,
        dramatically improving performance over serial fetching.
        """
        # Early exit for empty input
        if not prs:
            return {}

        # Extract PR numbers and owner/repo from first PR
        pr_numbers = [pr.number for pr in prs.values()]
        first_pr = next(iter(prs.values()))
        owner = first_pr.owner
        repo = first_pr.repo

        # Build and execute batched GraphQL query
        query = self._build_batch_pr_query(pr_numbers, owner, repo)
        response = self._execute_batch_pr_query(query, repo_root)

        # Extract repository data from response
        repo_data = response["data"]["repository"]

        # Enrich each PR with CI status and mergeability
        enriched_prs = {}
        for branch, pr in prs.items():
            # Get PR data from GraphQL response using alias
            alias = f"pr_{pr.number}"
            pr_data = repo_data.get(alias)

            # Parse CI status (handles None/missing data gracefully)
            ci_status = self._parse_pr_ci_status(pr_data)

            # Parse check counts
            checks_counts = self._parse_pr_ci_counts(pr_data)

            # Parse mergeability status
            has_conflicts = self._parse_pr_mergeability(pr_data)

            # Extract title from PR data
            title = pr_data.get("title") if pr_data else None

            # Create enriched PR with updated CI status, mergeability, counts, and title
            enriched_pr = replace(
                pr,
                checks_passing=ci_status,
                has_conflicts=has_conflicts,
                title=title,
                checks_counts=checks_counts,
            )
            enriched_prs[branch] = enriched_pr

        return enriched_prs

    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Fetch PR titles for all PRs in a single batched GraphQL query.

        This is a lighter-weight alternative to enrich_prs_with_ci_status_batch
        that only fetches titles, not CI status or mergeability.

        Args:
            prs: Dictionary mapping branch names to PullRequestInfo objects
            repo_root: Repository root path

        Returns:
            Dictionary with same keys, but PullRequestInfo objects enriched with titles
        """
        # Early exit for empty input
        if not prs:
            return {}

        # Extract PR numbers and owner/repo from first PR
        pr_numbers = [pr.number for pr in prs.values()]
        first_pr = next(iter(prs.values()))
        owner = first_pr.owner
        repo = first_pr.repo

        # Build simplified GraphQL query for just titles
        query = self._build_title_batch_query(pr_numbers, owner, repo)
        response = self._execute_batch_pr_query(query, repo_root)

        # Extract repository data from response
        repo_data = response["data"]["repository"]

        # Enrich each PR with title
        enriched_prs = {}
        for branch, pr in prs.items():
            # Get PR data from GraphQL response using alias
            alias = f"pr_{pr.number}"
            pr_data = repo_data.get(alias)

            # Extract title from PR data
            title = pr_data.get("title") if pr_data else None

            # Create enriched PR with title
            enriched_pr = replace(pr, title=title)
            enriched_prs[branch] = enriched_pr

        return enriched_prs

    def _build_title_batch_query(self, pr_numbers: list[int], owner: str, repo: str) -> str:
        """Build GraphQL query to fetch just titles for multiple PRs.

        Args:
            pr_numbers: List of PR numbers to query
            owner: Repository owner
            repo: Repository name

        Returns:
            GraphQL query string
        """
        # Build aliased PR queries for titles only
        pr_queries = []
        for pr_num in pr_numbers:
            pr_query = f"""    pr_{pr_num}: pullRequest(number: {pr_num}) {{
      number
      title
    }}"""
            pr_queries.append(pr_query)

        # Combine into single query
        query = f"""query {{
  repository(owner: "{owner}", name: "{repo}") {{
{chr(10).join(pr_queries)}
  }}
}}"""
        return query

    def merge_pr(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        squash: bool = True,
        verbose: bool = False,
        subject: str | None = None,
        body: str | None = None,
    ) -> bool:
        """Merge a pull request on GitHub via gh CLI."""
        cmd = ["gh", "pr", "merge", str(pr_number)]
        if squash:
            cmd.append("--squash")
        if subject is not None:
            cmd.extend(["--subject", subject])
        if body is not None:
            cmd.extend(["--body", body])

        try:
            result = run_subprocess_with_context(
                cmd,
                operation_context=f"merge PR #{pr_number}",
                cwd=repo_root,
            )

            # Show output in verbose mode
            if verbose and result.stdout:
                user_output(result.stdout)
            return True
        except RuntimeError:
            return False

    def _generate_distinct_id(self) -> str:
        """Generate a random base36 ID for workflow dispatch correlation.

        Returns:
            6-character base36 string (e.g., 'a1b2c3')
        """
        # Base36 alphabet: 0-9 and a-z
        base36_chars = string.digits + string.ascii_lowercase
        # Generate 6 random characters (~2.2 billion possibilities)
        return "".join(secrets.choice(base36_chars) for _ in range(6))

    def trigger_workflow(
        self,
        repo_root: Path,
        workflow: str,
        inputs: dict[str, str],
        ref: str | None = None,
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
        # Generate distinct ID for reliable run matching
        distinct_id = self._generate_distinct_id()
        debug_log(f"trigger_workflow: workflow={workflow}, distinct_id={distinct_id}, ref={ref}")

        cmd = ["gh", "workflow", "run", workflow]

        # Add --ref flag if specified
        if ref:
            cmd.extend(["--ref", ref])

        # Add distinct_id to workflow inputs automatically
        cmd.extend(["-f", f"distinct_id={distinct_id}"])

        # Add caller-provided workflow inputs
        for key, value in inputs.items():
            cmd.extend(["-f", f"{key}={value}"])

        debug_log(f"trigger_workflow: executing command: {' '.join(cmd)}")
        run_subprocess_with_context(
            cmd,
            operation_context=f"trigger workflow '{workflow}'",
            cwd=repo_root,
        )
        debug_log("trigger_workflow: workflow triggered successfully")

        # Poll for the run by matching displayTitle containing the distinct ID
        # The workflow uses run-name: "<issue_number>:<distinct_id>"
        # GitHub API eventual consistency: fast path (5×1s) then slow path (10×2s)
        max_attempts = 15
        runs_data: list[dict[str, Any]] = []
        for attempt in range(max_attempts):
            debug_log(f"trigger_workflow: polling attempt {attempt + 1}/{max_attempts}")

            runs_cmd = [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow,
                "--json",
                "databaseId,status,conclusion,displayTitle",
                "--limit",
                "10",
            ]

            runs_result = run_subprocess_with_context(
                runs_cmd,
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

            # Find run by matching distinct_id in displayTitle
            for run in runs_data:
                conclusion = run.get("conclusion")
                if conclusion in ("skipped", "cancelled"):
                    continue

                display_title = run.get("displayTitle", "")
                # Check for match pattern: :<distinct_id> (new format: issue_number:distinct_id)
                if f":{distinct_id}" in display_title:
                    run_id = run["databaseId"]
                    debug_log(f"trigger_workflow: found run {run_id}, title='{display_title}'")
                    return str(run_id)

            # No matching run found, retry if attempts remaining
            # Fast path: 1s delay for first 5 attempts, then 2s delay for remaining
            if attempt < max_attempts - 1:
                delay = 1 if attempt < 5 else 2
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
                title = run.get("displayTitle", "N/A")
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
                f"  gh run list --workflow {workflow} --limit 10",
                f"  gh workflow view {workflow}",
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
        """Create a pull request using gh CLI.

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
        cmd = [
            "gh",
            "pr",
            "create",
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ]

        # Add --draft flag if specified
        if draft:
            cmd.append("--draft")

        # Add --base flag if specified
        if base is not None:
            cmd.extend(["--base", base])

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"create pull request for branch '{branch}'",
            cwd=repo_root,
        )

        # Extract PR number from gh output
        # Format: https://github.com/owner/repo/pull/123
        pr_url = result.stdout.strip()
        pr_number = int(pr_url.split("/")[-1])

        return pr_number

    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        """Close a pull request without deleting its branch."""
        cmd = ["gh", "pr", "close", str(pr_number)]
        execute_gh_command(cmd, repo_root)

    def list_workflow_runs(
        self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
    ) -> list[WorkflowRun]:
        """List workflow runs for a specific workflow."""
        cmd = [
            "gh",
            "run",
            "list",
            "--workflow",
            workflow,
            "--json",
            "databaseId,status,conclusion,headBranch,headSha,displayTitle,createdAt",
            "--limit",
            str(limit),
        ]
        if user is not None:
            cmd.extend(["--user", user])

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"list workflow runs for '{workflow}'",
            cwd=repo_root,
        )

        # Parse JSON response
        data = json.loads(result.stdout)

        # Map to WorkflowRun dataclasses
        runs = []
        for run in data:
            # Parse created_at timestamp if present
            created_at = None
            created_at_str = run.get("createdAt")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            workflow_run = WorkflowRun(
                run_id=str(run["databaseId"]),
                status=run["status"],
                conclusion=run.get("conclusion"),
                branch=run["headBranch"],
                head_sha=run["headSha"],
                display_title=run.get("displayTitle"),
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
            # Use REST API - {owner}/{repo} placeholders are auto-filled by gh
            cmd = [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}",
            ]

            stdout = execute_gh_command(cmd, repo_root)
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
        result = run_subprocess_with_context(
            ["gh", "run", "view", run_id, "--log"],
            operation_context=f"fetch logs for run {run_id}",
            cwd=repo_root,
        )
        return result.stdout

    def get_prs_linked_to_issues(
        self,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues via GitHub's native branch linking.

        Uses linkedBranches GraphQL field to find branches created via
        `gh issue develop`, then looks up PRs for those branches.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        if not issue_numbers:
            return {}

        try:
            # Build and execute GraphQL query to fetch all issues
            query = self._build_issue_pr_linkage_query(issue_numbers, location.owner, location.repo)
            response = self._execute_batch_pr_query(query, location.root)

            # Parse response and build inverse mapping
            return self._parse_issue_pr_linkages(response, location.owner, location.repo)
        except (RuntimeError, FileNotFoundError, json.JSONDecodeError, KeyError, IndexError):
            # gh not installed, not authenticated, or parsing failed
            return {}

    def _build_issue_pr_linkage_query(self, issue_numbers: list[int], owner: str, repo: str) -> str:
        """Build GraphQL query to fetch PRs linked to issues via timeline.

        Uses CrossReferencedEvent on issue timelines to find PRs that will close
        each issue. This is O(issues) instead of O(all PRs in repo).

        Uses pre-aggregated count fields for efficiency (~15-30x smaller payload):
        - contexts(last: 1) with totalCount, checkRunCountsByState, statusContextCountsByState
        - Removes title and labels fields (not needed for dash)

        Args:
            issue_numbers: List of issue numbers to query
            owner: Repository owner
            repo: Repository name

        Returns:
            GraphQL query string
        """
        # Define the fragment once at the top of the query
        # Uses pre-aggregated count fields for ~15-30x smaller payload vs fetching 100 nodes
        fragment_definition = """fragment IssuePRLinkageFields on CrossReferencedEvent {
  willCloseTarget
  source {
    ... on PullRequest {
      number
      state
      url
      isDraft
      createdAt
      statusCheckRollup {
        state
        contexts(last: 1) {
          totalCount
          checkRunCountsByState { state count }
          statusContextCountsByState { state count }
        }
      }
      mergeable
    }
  }
}"""

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

        # Combine fragment definition and query
        query = f"""{fragment_definition}

query {{
  repository(owner: "{owner}", name: "{repo}") {{
{chr(10).join(issue_queries)}
  }}
}}"""
        return query

    def _parse_issue_pr_linkages(
        self, response: dict[str, Any], owner: str, repo: str
    ) -> dict[int, list[PullRequestInfo]]:
        """Parse GraphQL response from issue timeline query.

        Processes CrossReferencedEvent timeline items to extract PRs that
        will close each issue (willCloseTarget=true).

        Args:
            response: GraphQL response data
            owner: Repository owner
            repo: Repository name

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

                # Filter to only closing PRs
                if not node.get("willCloseTarget"):
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

                # Note: title and labels not fetched (not needed for dash)
                pr_info = PullRequestInfo(
                    number=pr_number,
                    state=state,
                    url=url,
                    is_draft=is_draft if is_draft is not None else False,
                    title=None,  # Not fetched for efficiency
                    checks_passing=checks_passing,
                    owner=owner,
                    repo=repo,
                    has_conflicts=has_conflicts,
                    checks_counts=checks_counts,
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

        for attempt in range(max_attempts):
            # Query for recent runs with branch info
            runs_cmd = [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow,
                "--json",
                "databaseId,status,conclusion,createdAt,event,headBranch",
                "--limit",
                "20",
            ]

            try:
                runs_result = run_subprocess_with_context(
                    runs_cmd,
                    operation_context=(
                        f"poll for workflow run (workflow: {workflow}, branch: {branch_name})"
                    ),
                    cwd=repo_root,
                )

                # Parse JSON output
                runs_data = json.loads(runs_result.stdout)
                if not runs_data or not isinstance(runs_data, list):
                    # No runs found, retry
                    if attempt < max_attempts - 1:
                        self._time.sleep(poll_interval)
                        continue
                    return None

                # Find run matching our criteria
                for run in runs_data:
                    # Skip skipped/cancelled runs
                    conclusion = run.get("conclusion")
                    if conclusion in ("skipped", "cancelled"):
                        continue

                    # Match by branch name
                    head_branch = run.get("headBranch")
                    if head_branch != branch_name:
                        continue

                    # Verify run was created after we started polling (within tolerance)
                    created_at_str = run.get("createdAt")
                    if created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        # Allow 5-second tolerance for runs created just before polling started
                        if created_at >= start_time - timedelta(seconds=5):
                            run_id = run["databaseId"]
                            return str(run_id)

                # No matching run found, retry if attempts remaining
                if attempt < max_attempts - 1:
                    self._time.sleep(poll_interval)

            except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
                # Command failed, retry if attempts remaining
                if attempt < max_attempts - 1:
                    self._time.sleep(poll_interval)
                    continue
                return None

        # Timeout reached without finding matching run
        return None

    def _execute_gh_json_command(self, cmd: list[str], repo_root: Path) -> dict[str, Any] | None:
        """Execute gh CLI command and parse JSON response.

        Encapsulates the third-party error boundary for gh CLI operations.
        We cannot reliably check gh installation and authentication status
        a priori without duplicating gh's logic.

        Args:
            cmd: gh CLI command as list of arguments
            repo_root: Repository root directory

        Returns:
            Parsed JSON data as dict, or None if command failed
        """
        try:
            stdout = execute_gh_command(cmd, repo_root)
            return json.loads(stdout)
        except (RuntimeError, FileNotFoundError, json.JSONDecodeError):
            # gh not installed, not authenticated, command failed, or JSON parsing failed
            return None

    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo | None:
        """Get PR details needed for checkout via gh CLI."""
        cmd = [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "number,headRefName,isCrossRepository,state",
        ]
        data = self._execute_gh_json_command(cmd, repo_root)
        if data is None:
            return None

        # LBYL: Validate required keys before accessing
        required_keys = ("number", "headRefName", "isCrossRepository", "state")
        if not all(key in data for key in required_keys):
            return None

        return PRCheckoutInfo(
            number=data["number"],
            head_ref_name=data["headRefName"],
            is_cross_repository=data["isCrossRepository"],
            state=data["state"],
        )

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status.

        Runs `gh auth status` and parses the output to determine authentication status.
        Looks for patterns like:
        - "Logged in to github.com as USERNAME"
        - Success indicator (checkmark)

        Returns:
            Tuple of (is_authenticated, username, hostname)
        """
        result = run_subprocess_with_context(
            ["gh", "auth", "status"],
            operation_context="check GitHub authentication status",
            capture_output=True,
            check=False,
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

        # Build GraphQL query using nodes() interface
        query = self._build_workflow_runs_nodes_query(node_ids)
        response = self._execute_batch_pr_query(query, repo_root)

        # Parse response into WorkflowRun objects
        return self._parse_workflow_runs_nodes_response(response, node_ids)

    def _build_workflow_runs_nodes_query(self, node_ids: list[str]) -> str:
        """Build GraphQL query to fetch workflow runs by node IDs.

        Uses the nodes(ids: [...]) interface which efficiently fetches
        multiple objects in a single API call. WorkflowRun implements Node.

        Args:
            node_ids: List of GraphQL node IDs

        Returns:
            GraphQL query string
        """
        # Escape node IDs for use in JSON array
        node_ids_json = json.dumps(node_ids)

        query = f"""query {{
  nodes(ids: {node_ids_json}) {{
    ... on WorkflowRun {{
      id
      databaseId
      url
      createdAt
      checkSuite {{
        status
        conclusion
        commit {{
          oid
        }}
      }}
    }}
  }}
}}"""
        return query

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
        cmd = [
            "gh",
            "api",
            f"/repos/{{owner}}/{{repo}}/actions/runs/{run_id}",
            "--jq",
            ".node_id",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        node_id = stdout.strip()
        return node_id if node_id else None

    def get_issues_with_pr_linkages(
        self,
        repo_root: Path,
        owner: str,
        repo: str,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Fetch issues and linked PRs in a single GraphQL query.

        Uses repository.issues() connection with inline timelineItems
        to get PR linkages in one API call.
        """
        query = self._build_issues_with_pr_linkages_query(owner, repo, labels, state, limit)
        response = self._execute_batch_pr_query(query, repo_root)
        return self._parse_issues_with_pr_linkages(response, owner, repo)

    def _build_issues_with_pr_linkages_query(
        self,
        owner: str,
        repo: str,
        labels: list[str],
        state: str | None,
        limit: int | None,
    ) -> str:
        """Build GraphQL query to fetch issues with PR linkages.

        Uses repository.issues() connection with timelineItems to get
        cross-referenced PRs in a single query.

        Args:
            owner: Repository owner
            repo: Repository name
            labels: Labels to filter by
            state: Filter by state ("open", "closed", or None for all)
            limit: Maximum issues to return (default: 100)

        Returns:
            GraphQL query string
        """
        # Build labels array for query
        labels_json = json.dumps(labels)

        # Build states filter
        # Default to OPEN to match gh CLI behavior (gh issue list defaults to open)
        if state is not None:
            states_filter = f"states: [{state.upper()}]"
        else:
            states_filter = "states: [OPEN]"

        # Build limit (default 30 matches gh CLI behavior)
        effective_limit = limit if limit is not None else 30

        # Define the fragment for PR linkage data
        # Uses pre-aggregated count fields for ~15-30x smaller payload
        fragment_definition = """fragment IssuePRLinkageFields on CrossReferencedEvent {
  willCloseTarget
  source {
    ... on PullRequest {
      number
      state
      url
      isDraft
      createdAt
      statusCheckRollup {
        state
        contexts(last: 1) {
          totalCount
          checkRunCountsByState { state count }
          statusContextCountsByState { state count }
        }
      }
      mergeable
    }
  }
}"""

        # Build the query - construct issues args separately for line length
        issues_args = f"labels: {labels_json}, {states_filter} first: {effective_limit}"
        order_by = "orderBy: {field: UPDATED_AT, direction: DESC}"
        query = f"""{fragment_definition}

query {{
  repository(owner: "{owner}", name: "{repo}") {{
    issues({issues_args}, {order_by}) {{
      nodes {{
        number
        title
        body
        state
        url
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
    }}
  }}
}}"""
        return query

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
        )

    def _parse_pr_from_timeline_event(
        self, event: dict[str, Any], owner: str, repo: str
    ) -> tuple[PullRequestInfo, str] | None:
        """Parse PR info from a timeline CrossReferencedEvent.

        Returns tuple of (PullRequestInfo, created_at_timestamp) or None if invalid.
        """
        if not event.get("willCloseTarget"):
            return None

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

        pr_info = PullRequestInfo(
            number=pr_number,
            state=pr_state,
            url=pr_url,
            is_draft=source.get("isDraft", False),
            title=None,
            checks_passing=checks_passing,
            owner=owner,
            repo=repo,
            has_conflicts=has_conflicts,
            checks_counts=checks_counts,
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

    def _parse_issues_with_pr_linkages(
        self,
        response: dict[str, Any],
        owner: str,
        repo: str,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Parse GraphQL response to extract issues and PR linkages."""
        issues: list[IssueInfo] = []
        pr_linkages: dict[int, list[PullRequestInfo]] = {}

        nodes = response.get("data", {}).get("repository", {}).get("issues", {}).get("nodes", [])

        for node in nodes:
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
                result = self._parse_pr_from_timeline_event(event, owner, repo)
                if result is not None:
                    prs_with_timestamps.append(result)

            if prs_with_timestamps:
                prs_with_timestamps.sort(key=lambda x: x[1], reverse=True)
                pr_linkages[issue.number] = [pr for pr, _ in prs_with_timestamps]

        return (issues, pr_linkages)

    def get_pr_info_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        """Get PR number and URL for a specific branch using gh CLI.

        Returns:
            Tuple of (pr_number, pr_url) or None if no PR exists for this branch.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--json",
            "number,url",
            "--limit",
            "1",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)
        if not data:
            return None
        pr = data[0]
        return (pr["number"], pr["url"])

    def get_pr_state_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        """Get PR number and state for a specific branch using gh CLI.

        Returns:
            Tuple of (pr_number, state) or None if no PR exists for this branch.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "all",
            "--json",
            "number,state",
            "--limit",
            "1",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)
        if not data:
            return None
        pr = data[0]
        return (pr["number"], pr["state"])

    def get_pr_title(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR title by number using gh CLI.

        Returns:
            PR title string, or None if empty.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "title",
            "-q",
            ".title",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        title = stdout.strip()
        return title if title else None

    def get_pr_body(self, repo_root: Path, pr_number: int) -> str | None:
        """Get PR body by number using gh CLI.

        Returns:
            PR body string, or None if empty.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "body",
            "-q",
            ".body",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        body = stdout.strip()
        return body if body else None

    def update_pr_title_and_body(
        self, repo_root: Path, pr_number: int, title: str, body: str
    ) -> None:
        """Update PR title and body using gh CLI.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = [
            "gh",
            "pr",
            "edit",
            str(pr_number),
            "--title",
            title,
            "--body",
            body,
        ]
        execute_gh_command(cmd, repo_root)

    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> None:
        """Mark a draft PR as ready for review using gh CLI.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = ["gh", "pr", "ready", str(pr_number)]
        execute_gh_command(cmd, repo_root)

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Get the diff for a PR using gh CLI.

        Raises:
            RuntimeError: If gh command fails
        """
        result = run_subprocess_with_context(
            ["gh", "pr", "diff", str(pr_number)],
            operation_context=f"get diff for PR #{pr_number}",
            cwd=repo_root,
        )
        return result.stdout

    def get_pr_mergeability_status(self, repo_root: Path, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability status from GitHub API.

        Uses REST API to get mergeable state. Returns ("UNKNOWN", "UNKNOWN") when
        GitHub hasn't computed mergeability yet (null response).

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
            "--jq",
            ".mergeable,.mergeable_state",
        ]
        stdout = execute_gh_command(cmd, repo_root)
        lines = stdout.strip().split("\n")
        mergeable = lines[0] if len(lines) > 0 else "null"
        merge_state = lines[1] if len(lines) > 1 else "unknown"

        # Convert to GitHub GraphQL enum format
        if mergeable == "true":
            return ("MERGEABLE", merge_state.upper())
        if mergeable == "false":
            return ("CONFLICTING", merge_state.upper())
        return ("UNKNOWN", "UNKNOWN")

    def get_repo_info(self, repo_root: Path) -> RepoInfo:
        """Get repository owner and name from GitHub CLI.

        Uses `gh repo view --json owner,name` to get repo info.

        Raises:
            RuntimeError: If gh command fails (auth issues, network errors, etc.)
        """
        cmd = ["gh", "repo", "view", "--json", "owner,name"]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)
        owner = data["owner"]["login"]
        name = data["name"]
        return RepoInfo(owner=owner, name=name)
