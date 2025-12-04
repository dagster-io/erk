"""Fake GitHub pull request operations for testing."""

from pathlib import Path
from typing import cast

from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.pr.abc import GitHubPrGateway
from erk_shared.github.types import (
    GitHubRepoLocation,
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PRState,
    PullRequestInfo,
)


class FakeGitHubPrGateway(GitHubPrGateway):
    """In-memory fake implementation of GitHub pull request operations.

    This class has NO public setup methods. All state is provided via constructor
    using keyword arguments with sensible defaults.
    """

    def __init__(
        self,
        *,
        prs: dict[str, PullRequestInfo] | None = None,
        pr_statuses: dict[str, tuple[str | None, int | None, str | None]] | None = None,
        pr_bases: dict[int, str] | None = None,
        pr_mergeability: dict[int, PRMergeability | None] | None = None,
        pr_issue_linkages: dict[int, list[PullRequestInfo]] | None = None,
        pr_checkout_infos: dict[int, PRCheckoutInfo] | None = None,
        issues: list[IssueInfo] | None = None,
        pr_titles: dict[int, str] | None = None,
        pr_bodies_by_number: dict[int, str] | None = None,
        pr_diffs: dict[int, str] | None = None,
        merge_should_succeed: bool = True,
        pr_update_should_succeed: bool = True,
    ) -> None:
        """Create FakeGitHubPrGateway with pre-configured state.

        Args:
            prs: Mapping of branch name -> PullRequestInfo
            pr_statuses: Legacy parameter for backward compatibility.
                        Mapping of branch name -> (state, pr_number, title)
            pr_bases: Mapping of pr_number -> base_branch
            pr_mergeability: Mapping of pr_number -> PRMergeability (None for API errors)
            pr_issue_linkages: Mapping of issue_number -> list[PullRequestInfo]
            pr_checkout_infos: Mapping of pr_number -> PRCheckoutInfo
            issues: List of IssueInfo objects for get_issues_with_pr_linkages()
            pr_titles: Mapping of pr_number -> title for explicit title storage
            pr_bodies_by_number: Mapping of pr_number -> body for explicit body storage
            pr_diffs: Mapping of pr_number -> diff content
            merge_should_succeed: Whether merge_pr() should succeed (default True)
            pr_update_should_succeed: Whether PR updates should succeed (default True)
        """
        if prs is not None and pr_statuses is not None:
            msg = "Cannot specify both prs and pr_statuses"
            raise ValueError(msg)

        if pr_statuses is not None:
            # Convert legacy pr_statuses format to PullRequestInfo
            self._prs: dict[str, PullRequestInfo] = {}
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
        self._pr_issue_linkages = pr_issue_linkages or {}
        self._pr_checkout_infos = pr_checkout_infos or {}
        self._issues = issues or []
        self._pr_titles = pr_titles or {}
        self._pr_bodies_by_number = pr_bodies_by_number or {}
        self._pr_diffs = pr_diffs or {}
        self._merge_should_succeed = merge_should_succeed
        self._pr_update_should_succeed = pr_update_should_succeed

        # Mutation tracking
        self._updated_pr_bases: list[tuple[int, str]] = []
        self._updated_pr_bodies: list[tuple[int, str]] = []
        self._updated_pr_titles: list[tuple[int, str]] = []
        self._merged_prs: list[int] = []
        self._closed_prs: list[int] = []
        self._get_prs_for_repo_calls: list[tuple[Path, bool]] = []
        self._get_pr_status_calls: list[tuple[Path, str]] = []
        self._created_prs: list[tuple[str, str, str, str | None, bool]] = []
        self._marked_ready_prs: list[int] = []

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
        """Record PR creation in mutation tracking list.

        Returns:
            A fake PR number for testing
        """
        self._created_prs.append((branch, title, body, base, draft))
        # Return a fake PR number
        return 999

    def close_pr(self, repo_root: Path, pr_number: int) -> None:
        """Record PR closure in mutation tracking list."""
        self._closed_prs.append(pr_number)

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
        """Record PR merge in mutation tracking list.

        Returns value of merge_should_succeed flag (default True).
        """
        if self._merge_should_succeed:
            self._merged_prs.append(pr_number)
        return self._merge_should_succeed

    # --- PR query operations ---

    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status from configured PRs.

        Returns PRInfo("NONE", None, None) if branch not found.
        """
        self._get_pr_status_calls.append((repo_root, branch))

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

    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches (returns pre-configured data).

        The include_checks parameter is accepted but ignored - fake returns the
        same pre-configured data regardless of this parameter.
        """
        self._get_prs_for_repo_calls.append((repo_root, include_checks))
        return self._prs

    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo | None:
        """Get PR checkout info from pre-configured state.

        Returns None if pr_number not found in pr_checkout_infos mapping.
        """
        return self._pr_checkout_infos.get(pr_number)

    def get_pr_info_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        """Get PR number and URL for a specific branch from configured state.

        Returns None if branch not found in configured PRs.
        """
        pr = self._prs.get(branch)
        if pr is None:
            return None
        return (pr.number, pr.url)

    def get_pr_state_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        """Get PR number and state for a specific branch from configured state.

        Returns None if branch not found in configured PRs.
        """
        pr = self._prs.get(branch)
        if pr is None:
            return None
        return (pr.number, pr.state)

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
        self, repo_root: Path, pr_number: int, title: str, body: str
    ) -> None:
        """Record PR title and body update in mutation tracking lists.

        Raises RuntimeError if pr_update_should_succeed is False.
        """
        if not self._pr_update_should_succeed:
            raise RuntimeError("PR update failed (configured to fail)")

        self._updated_pr_titles.append((pr_number, title))
        self._updated_pr_bodies.append((pr_number, body))

    def mark_pr_ready(self, repo_root: Path, pr_number: int) -> None:
        """Mark a draft PR as ready for review (tracks in mutation list)."""
        self._marked_ready_prs.append(pr_number)

    def get_pr_diff(self, repo_root: Path, pr_number: int) -> str:
        """Get the diff for a PR from configured state or return default.

        First checks explicit pr_diffs storage. Returns a simple default
        diff if not configured.
        """
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

        Returns configured mergeability or defaults to ("MERGEABLE", "CLEAN").
        """
        if pr_number in self._pr_mergeability:
            mergeability = self._pr_mergeability[pr_number]
            if mergeability is None:
                return ("UNKNOWN", "UNKNOWN")
            return (mergeability.mergeable, mergeability.merge_state_status)
        return ("MERGEABLE", "CLEAN")

    # --- Issue-PR linkage operations ---

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

    def get_issues_with_pr_linkages(
        self,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[IssueInfo], dict[int, list[PullRequestInfo]]]:
        """Get issues and PR linkages from pre-configured data.

        Filters pre-configured issues by labels and state, then returns
        matching PR linkages from pr_issue_linkages mapping.

        Args:
            location: GitHub repository location (ignored in fake)
            labels: Labels to filter by
            state: Filter by state ("open", "closed", or None for OPEN default)
            limit: Maximum issues to return (default: all)

        Returns:
            Tuple of (filtered_issues, pr_linkages for those issues)
        """
        # Default to OPEN to match gh CLI behavior (gh issue list defaults to open)
        effective_state = state if state is not None else "open"

        # Filter issues by labels
        filtered_issues = []
        for issue in self._issues:
            # Check if issue has all required labels
            if not all(label in issue.labels for label in labels):
                continue
            # Check state filter
            if issue.state.lower() != effective_state.lower():
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

    # --- Mutation tracking properties ---

    @property
    def created_prs(self) -> list[tuple[str, str, str, str | None, bool]]:
        """Read-only access to tracked PR creations for test assertions.

        Returns list of (branch, title, body, base, draft) tuples.
        """
        return self._created_prs

    @property
    def closed_prs(self) -> list[int]:
        """Read-only access to tracked PR closures for test assertions."""
        return self._closed_prs

    @property
    def merged_prs(self) -> list[int]:
        """List of PR numbers that were merged."""
        return self._merged_prs

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
    def marked_ready_prs(self) -> list[int]:
        """Read-only access to tracked mark_pr_ready calls for test assertions."""
        return self._marked_ready_prs

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
