"""Caching wrapper for GitHub issues using updated_at for cache validation."""

import json
from datetime import datetime
from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.issues.types import CreateIssueResult, IssueInfo
from erk_shared.subprocess_utils import execute_gh_command


def _parse_github_timestamp(timestamp_str: str) -> datetime:
    """Parse GitHub timestamp string to datetime.

    GitHub timestamps are in ISO 8601 format with Z suffix.
    """
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


class CachingGitHubIssues(GitHubIssues):
    """Caching wrapper using updated_at for cache validation.

    Decorates any GitHubIssues implementation to add caching.
    Read operations check timestamps and only fetch full data when stale.
    Write operations invalidate cache entries.

    Cache Strategy:
    - For get_issue: Fetch lightweight timestamp, compare with cache, fetch full if stale
    - For list_issues: Fetch timestamps for all matching issues, batch-fetch only changed
    - All writes: Delegate to wrapped impl, then invalidate the cache entry

    This wrapper can be composed with DryRunGitHubIssues:
        DryRunGitHubIssues(CachingGitHubIssues(RealGitHubIssues()))
    """

    def __init__(self, wrapped: GitHubIssues) -> None:
        """Initialize caching wrapper with a real implementation.

        Args:
            wrapped: The GitHubIssues implementation to wrap
        """
        self._wrapped = wrapped
        # Cache: (repo_key, issue_number) -> IssueInfo
        self._cache: dict[tuple[str, int], IssueInfo] = {}

    def _get_repo_key(self, repo_root: Path) -> str:
        """Get normalized string key for repository.

        Uses string representation of path as cache key.
        We don't resolve the path to avoid filesystem operations
        in unit tests with sentinel paths.
        """
        return str(repo_root)

    def _invalidate(self, repo_root: Path, number: int) -> None:
        """Invalidate cache for a modified issue."""
        repo_key = self._get_repo_key(repo_root)
        self._cache.pop((repo_key, number), None)

    def _fetch_single_timestamp(self, repo_root: Path, number: int) -> datetime:
        """Fetch only updatedAt for a single issue (minimal payload).

        Args:
            repo_root: Repository root directory
            number: Issue number

        Returns:
            datetime of the issue's updated_at timestamp
        """
        cmd = ["gh", "issue", "view", str(number), "--json", "updatedAt"]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)
        return _parse_github_timestamp(data["updatedAt"])

    def _fetch_timestamps(
        self,
        repo_root: Path,
        labels: list[str] | None,
        state: str | None,
        limit: int | None,
    ) -> dict[int, datetime]:
        """Fetch only number + updatedAt for issues matching filters (minimal payload).

        Args:
            repo_root: Repository root directory
            labels: Filter by labels
            state: Filter by state
            limit: Maximum issues to return

        Returns:
            Mapping of issue number -> updated_at datetime
        """
        cmd = ["gh", "issue", "list", "--json", "number,updatedAt"]

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        if state:
            cmd.extend(["--state", state])

        if limit is not None:
            cmd.extend(["--limit", str(limit)])

        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)

        return {item["number"]: _parse_github_timestamp(item["updatedAt"]) for item in data}

    def _get_repo_info(self, repo_root: Path) -> tuple[str, str]:
        """Get owner and repo name for GraphQL queries.

        Returns:
            Tuple of (owner, repo_name)
        """
        cmd = ["gh", "repo", "view", "--json", "owner,name"]
        stdout = execute_gh_command(cmd, repo_root)
        data = json.loads(stdout)
        return data["owner"]["login"], data["name"]

    def _batch_fetch_issues(self, repo_root: Path, numbers: list[int]) -> list[IssueInfo]:
        """Batch fetch full issue data via GraphQL.

        Uses aliased GraphQL queries to fetch multiple issues in one call.

        Args:
            repo_root: Repository root directory
            numbers: List of issue numbers to fetch

        Returns:
            List of IssueInfo for the requested issues
        """
        if not numbers:
            return []

        owner, repo_name = self._get_repo_info(repo_root)

        # Build aliased GraphQL query
        aliases = []
        for i, num in enumerate(numbers):
            aliases.append(
                f"issue{i}: issue(number: {num}) {{ "
                f"number title body state url "
                f"labels(first: 100) {{ nodes {{ name }} }} "
                f"assignees(first: 100) {{ nodes {{ login }} }} "
                f"createdAt updatedAt }}"
            )

        query = (
            f'query {{ repository(owner: "{owner}", name: "{repo_name}") {{ '
            + " ".join(aliases)
            + " } }"
        )

        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
        stdout = execute_gh_command(cmd, repo_root)
        response = json.loads(stdout)

        # Parse results
        repository = response.get("data", {}).get("repository", {})
        results: list[IssueInfo] = []

        for i, _num in enumerate(numbers):
            issue_data = repository.get(f"issue{i}")
            if issue_data is None:
                continue

            results.append(
                IssueInfo(
                    number=issue_data["number"],
                    title=issue_data["title"],
                    body=issue_data["body"],
                    state=issue_data["state"],
                    url=issue_data["url"],
                    labels=[node["name"] for node in issue_data.get("labels", {}).get("nodes", [])],
                    assignees=[
                        node["login"] for node in issue_data.get("assignees", {}).get("nodes", [])
                    ],
                    created_at=_parse_github_timestamp(issue_data["createdAt"]),
                    updated_at=_parse_github_timestamp(issue_data["updatedAt"]),
                )
            )

        return results

    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """Create issue via wrapped implementation (no caching needed)."""
        return self._wrapped.create_issue(repo_root, title, body, labels)

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Get issue with caching based on updated_at timestamp.

        Strategy:
        1. Fetch lightweight timestamp via gh issue view --json updatedAt
        2. Compare with cached entry (if exists)
        3. Return cached if timestamps match, fetch full otherwise
        """
        repo_key = self._get_repo_key(repo_root)
        cache_key = (repo_key, number)

        # Fetch lightweight timestamp
        remote_updated_at = self._fetch_single_timestamp(repo_root, number)

        # Check cache
        cached = self._cache.get(cache_key)
        if cached is not None and cached.updated_at == remote_updated_at:
            return cached

        # Cache miss or stale - fetch full issue
        issue = self._wrapped.get_issue(repo_root, number)
        self._cache[cache_key] = issue
        return issue

    def add_comment(self, repo_root: Path, number: int, body: str) -> None:
        """Add comment and invalidate cache."""
        self._wrapped.add_comment(repo_root, number, body)
        self._invalidate(repo_root, number)

    def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
        """Update issue body and invalidate cache."""
        self._wrapped.update_issue_body(repo_root, number, body)
        self._invalidate(repo_root, number)

    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """List issues with caching based on updated_at timestamps.

        Strategy:
        1. Always fetch lightweight timestamps via gh issue list --json number,updatedAt
        2. Compare each issue's updated_at against cache
        3. Batch-fetch only changed/missing issues via GraphQL
        4. Return combined results from cache + fresh fetch
        """
        repo_key = self._get_repo_key(repo_root)

        # Phase 1: Fetch lightweight timestamps (with all filters applied)
        timestamps = self._fetch_timestamps(repo_root, labels, state, limit)

        # Determine which issues need full fetch
        to_fetch: list[int] = []
        cached_issues: list[IssueInfo] = []

        for number, updated_at in timestamps.items():
            cache_key = (repo_key, number)
            cached = self._cache.get(cache_key)
            if cached is not None and cached.updated_at == updated_at:
                cached_issues.append(cached)
            else:
                to_fetch.append(number)

        # Phase 2: Batch fetch only changed/missing issues
        if to_fetch:
            fetched = self._batch_fetch_issues(repo_root, to_fetch)
            for issue in fetched:
                self._cache[(repo_key, issue.number)] = issue
                cached_issues.append(issue)

        return cached_issues

    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Delegate to wrapped implementation (comments not cached)."""
        return self._wrapped.get_issue_comments(repo_root, number)

    def get_multiple_issue_comments(
        self, repo_root: Path, issue_numbers: list[int]
    ) -> dict[int, list[str]]:
        """Delegate to wrapped implementation (comments not cached)."""
        return self._wrapped.get_multiple_issue_comments(repo_root, issue_numbers)

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """Delegate to wrapped implementation (labels not issue-specific)."""
        self._wrapped.ensure_label_exists(repo_root, label, description, color)

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Ensure label on issue and invalidate cache."""
        self._wrapped.ensure_label_on_issue(repo_root, issue_number, label)
        self._invalidate(repo_root, issue_number)

    def remove_label_from_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """Remove label from issue and invalidate cache."""
        self._wrapped.remove_label_from_issue(repo_root, issue_number, label)
        self._invalidate(repo_root, issue_number)

    def close_issue(self, repo_root: Path, number: int) -> None:
        """Close issue and invalidate cache."""
        self._wrapped.close_issue(repo_root, number)
        self._invalidate(repo_root, number)

    def get_current_username(self) -> str | None:
        """Delegate to wrapped implementation (not issue-specific)."""
        return self._wrapped.get_current_username()
