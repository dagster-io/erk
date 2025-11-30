"""Production implementation of GitHub operations."""

import json
import secrets
import string
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from erk_shared.github.abc import GitHub
from erk_shared.github.parsing import (
    _determine_checks_status,
    execute_gh_command,
    parse_gh_auth_status_output,
    parse_github_pr_list,
    parse_github_pr_status,
)
from erk_shared.github.types import (
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
    WorkflowRun,
)
from erk_shared.integrations.time.abc import Time
from erk_shared.output.output import user_output
from erk_shared.subprocess_utils import run_subprocess_with_context

from erk.cli.debug import debug_log


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
          contexts(last: 100) {
            nodes {
              ... on StatusContext {
                state
              }
              ... on CheckRun {
                status
                conclusion
              }
            }
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

    def _parse_pr_ci_status(self, pr_data: dict[str, Any] | None) -> bool | None:
        """Parse CI status from GraphQL PR response.

        Args:
            pr_data: GraphQL response data for single PR (may be None)

        Returns:
            True if all checks passing, False if any failing, None if no checks or error
        """
        nodes = self._extract_check_nodes(pr_data)
        if nodes is None:
            return None
        return _determine_checks_status(nodes)

    def _parse_pr_ci_counts(self, pr_data: dict[str, Any] | None) -> tuple[int, int] | None:
        """Parse check counts from GraphQL PR response.

        Args:
            pr_data: GraphQL response data for single PR (may be None)

        Returns:
            (passing, total) tuple or None if no checks
        """
        from erk_shared.github.parsing import _extract_checks_counts

        nodes = self._extract_check_nodes(pr_data)
        if nodes is None:
            return None
        return _extract_checks_counts(nodes)

    def _extract_check_nodes(self, pr_data: dict[str, Any] | None) -> list[dict] | None:
        """Extract check nodes from GraphQL PR response.

        Args:
            pr_data: GraphQL response data for single PR (may be None)

        Returns:
            List of check node dicts or None if not available
        """
        # Check if PR data is missing (not found or error)
        if pr_data is None:
            return None

        # Extract commits
        commits = pr_data.get("commits")
        if commits is None:
            return None

        # Check for empty commits nodes
        nodes = commits.get("nodes", [])
        if not nodes:
            return None

        # Extract statusCheckRollup from first commit
        commit = nodes[0].get("commit")
        if commit is None:
            return None

        status_check_rollup = commit.get("statusCheckRollup")
        if status_check_rollup is None:
            return None

        # Extract contexts connection
        contexts = status_check_rollup.get("contexts")
        if contexts is None:
            return None

        # Validate contexts is a dict (connection object) not a list
        # This handles cases where query structure is wrong or API changes
        if not isinstance(contexts, dict):
            return None

        # Extract nodes array from contexts connection
        return contexts.get("nodes", [])

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
    ) -> None:
        """Merge a pull request on GitHub via gh CLI."""
        cmd = ["gh", "pr", "merge", str(pr_number)]
        if squash:
            cmd.append("--squash")

        result = run_subprocess_with_context(
            cmd,
            operation_context=f"merge PR #{pr_number}",
            cwd=repo_root,
        )

        # Show output in verbose mode
        if verbose and result.stdout:
            user_output(result.stdout)

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

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        try:
            cmd = [
                "gh",
                "run",
                "view",
                run_id,
                "--json",
                "databaseId,status,conclusion,headBranch,headSha,displayTitle,createdAt",
            ]

            result = run_subprocess_with_context(
                cmd,
                operation_context=f"get workflow run details for run {run_id}",
                cwd=repo_root,
            )

            # Parse JSON response
            data = json.loads(result.stdout)

            # Parse created_at timestamp if present
            created_at = None
            created_at_str = data.get("createdAt")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

            return WorkflowRun(
                run_id=str(data["databaseId"]),
                status=data["status"],
                conclusion=data.get("conclusion"),
                branch=data["headBranch"],
                head_sha=data["headSha"],
                display_title=data.get("displayTitle"),
                created_at=created_at,
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
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues via closing keywords.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
        # Early exit for empty input
        if not issue_numbers:
            return {}

        try:
            # Get owner/repo from first PR in repo (needed for GraphQL query)
            # We query for ANY PR to extract owner/repo info
            cmd = ["gh", "pr", "list", "--limit", "1", "--json", "url"]
            stdout = execute_gh_command(cmd, repo_root)
            pr_list = json.loads(stdout)

            # If no PRs exist in repo, return empty dict
            if not pr_list:
                return {}

            # Extract owner/repo from first PR URL
            # Format: https://github.com/owner/repo/pull/123
            pr_url = pr_list[0]["url"]
            parts = pr_url.split("/")
            owner = parts[-4]
            repo = parts[-3]

            # Build and execute GraphQL query to fetch all issues
            query = self._build_issue_pr_linkage_query(issue_numbers, owner, repo)
            response = self._execute_batch_pr_query(query, repo_root)

            # Parse response and build inverse mapping
            return self._parse_issue_pr_linkages(response, owner, repo)

        except (RuntimeError, FileNotFoundError, json.JSONDecodeError, KeyError, IndexError):
            # gh not installed, not authenticated, or parsing failed
            return {}

    def _build_issue_pr_linkage_query(self, issue_numbers: list[int], owner: str, repo: str) -> str:
        """Build GraphQL query to fetch PRs linked to issues via timeline.

        Uses CrossReferencedEvent on issue timelines to find PRs that will close
        each issue. This is O(issues) instead of O(all PRs in repo).

        Args:
            issue_numbers: List of issue numbers to query
            owner: Repository owner
            repo: Repository name

        Returns:
            GraphQL query string
        """
        # Define the fragment once at the top of the query
        # NOTE: Includes detailed contexts for check count extraction
        fragment_definition = """fragment IssuePRLinkageFields on CrossReferencedEvent {
  willCloseTarget
  source {
    ... on PullRequest {
      number
      state
      url
      isDraft
      title
      createdAt
      statusCheckRollup {
        state
        contexts(last: 100) {
          nodes {
            ... on StatusContext {
              state
            }
            ... on CheckRun {
              status
              conclusion
            }
          }
        }
      }
      mergeable
      labels(first: 10) {
        nodes {
          name
        }
      }
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

                # Extract optional fields
                is_draft = source.get("isDraft")
                title = source.get("title")
                created_at = source.get("createdAt")

                # Parse checks status and counts
                checks_passing = None
                checks_counts: tuple[int, int] | None = None
                status_rollup = source.get("statusCheckRollup")
                if status_rollup is not None:
                    rollup_state = status_rollup.get("state")
                    if rollup_state == "SUCCESS":
                        checks_passing = True
                    elif rollup_state in ("FAILURE", "ERROR"):
                        checks_passing = False

                    # Extract check counts from detailed contexts
                    contexts = status_rollup.get("contexts")
                    if contexts is not None and isinstance(contexts, dict):
                        from erk_shared.github.parsing import _extract_checks_counts

                        check_nodes = contexts.get("nodes", [])
                        checks_counts = _extract_checks_counts(check_nodes)

                # Parse conflicts status
                has_conflicts = None
                mergeable = source.get("mergeable")
                if mergeable == "CONFLICTING":
                    has_conflicts = True
                elif mergeable == "MERGEABLE":
                    has_conflicts = False

                # Parse labels
                labels: list[str] = []
                labels_data = source.get("labels")
                if labels_data is not None:
                    label_nodes = labels_data.get("nodes", [])
                    for label_node in label_nodes:
                        if label_node is not None:
                            label_name = label_node.get("name")
                            if label_name:
                                labels.append(label_name)

                pr_info = PullRequestInfo(
                    number=pr_number,
                    state=state,
                    url=url,
                    is_draft=is_draft if is_draft is not None else False,
                    title=title,
                    checks_passing=checks_passing,
                    owner=owner,
                    repo=repo,
                    has_conflicts=has_conflicts,
                    labels=labels,
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

    def get_workflow_runs_batch(
        self,
        repo_root: Path,
        run_ids: list[str],
        *,
        workflow: str | None = None,
        user: str | None = None,
    ) -> dict[str, WorkflowRun | None]:
        """Get details for multiple workflow runs by ID.

        If workflow is provided, uses `gh run list --workflow [--user]` to fetch runs
        efficiently in a single API call and filters by run_id in memory.
        Otherwise falls back to individual `gh run view` calls.
        """
        # Early exit for empty input
        if not run_ids:
            return {}

        # If workflow provided, use efficient batch fetch via gh run list
        if workflow is not None:
            # Fetch recent runs from workflow (single API call)
            all_runs = self.list_workflow_runs(repo_root, workflow, limit=200, user=user)

            # Build lookup by run_id
            runs_by_id = {run.run_id: run for run in all_runs}

            # Return only requested run_ids
            return {run_id: runs_by_id.get(run_id) for run_id in run_ids}

        # Fallback: individual fetch for each run_id (existing behavior)
        result: dict[str, WorkflowRun | None] = {}
        for run_id in run_ids:
            result[run_id] = self.get_workflow_run(repo_root, run_id)
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
