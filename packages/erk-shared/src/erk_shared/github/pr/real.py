"""Production implementation of GitHub pull request operations."""

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.parsing import (
    execute_gh_command,
    parse_aggregated_check_counts,
    parse_github_pr_list,
    parse_github_pr_status,
)
from erk_shared.github.pr.abc import GitHubPrGateway
from erk_shared.github.types import (
    GitHubRepoId,
    GitHubRepoLocation,
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
)
from erk_shared.output.output import user_output
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitHubPrGateway(GitHubPrGateway):
    """Production implementation using gh CLI.

    All GitHub pull request operations execute actual gh commands via subprocess.
    """

    # --- PR CRUD operations ---

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

    # --- PR query operations ---

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

    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str:
        """Get current base branch of a PR from GitHub.

        Note: Uses try/except as an acceptable error boundary for handling gh CLI
        availability and authentication. We cannot reliably check gh installation
        and authentication status a priori without duplicating gh's logic.
        """
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

    # --- Batch GraphQL operations ---

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

    # --- Issue-PR linkage operations ---

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

        Args:
            issue_numbers: List of issue numbers to query
            repo_id: GitHub repository identity (owner and repo name)

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
  repository(owner: "{repo_id.owner}", name: "{repo_id.repo}") {{
{chr(10).join(issue_queries)}
  }}
}}"""
        return query

    def _parse_issue_pr_linkages(
        self, response: dict[str, Any], repo_id: GitHubRepoId
    ) -> dict[int, list[PullRequestInfo]]:
        """Parse GraphQL response from issue timeline query.

        Processes CrossReferencedEvent timeline items to extract PRs that
        will close each issue (willCloseTarget=true).

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
                    owner=repo_id.owner,
                    repo=repo_id.repo,
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

    def get_issues_with_pr_linkages(
        self,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Fetch issues and linked PRs in a single GraphQL query.

        Uses repository.issues() connection with inline timelineItems
        to get PR linkages in one API call.
        """
        repo_id = location.repo_id
        query = self._build_issues_with_pr_linkages_query(repo_id, labels, state, limit)
        response = self._execute_batch_pr_query(query, location.root)
        return self._parse_issues_with_pr_linkages(response, repo_id)

    def _build_issues_with_pr_linkages_query(
        self,
        repo_id: GitHubRepoId,
        labels: list[str],
        state: str | None,
        limit: int | None,
    ) -> str:
        """Build GraphQL query to fetch issues with PR linkages.

        Uses repository.issues() connection with timelineItems to get
        cross-referenced PRs in a single query.

        Args:
            repo_id: GitHub repository identity (owner and repo name)
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
  repository(owner: "{repo_id.owner}", name: "{repo_id.repo}") {{
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
        from datetime import datetime

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
        self, event: dict[str, Any], repo_id: GitHubRepoId
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
            owner=repo_id.owner,
            repo=repo_id.repo,
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
        repo_id: GitHubRepoId,
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
                result = self._parse_pr_from_timeline_event(event, repo_id)
                if result is not None:
                    prs_with_timestamps.append(result)

            if prs_with_timestamps:
                prs_with_timestamps.sort(key=lambda x: x[1], reverse=True)
                pr_linkages[issue.number] = [pr for pr, _ in prs_with_timestamps]

        return (issues, pr_linkages)
