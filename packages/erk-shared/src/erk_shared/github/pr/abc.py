"""Abstract base class for GitHub pull request operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.types import (
    GitHubRepoLocation,
    PRCheckoutInfo,
    PRInfo,
    PRMergeability,
    PullRequestInfo,
)


class GitHubPrGateway(ABC):
    """Abstract interface for GitHub pull request operations.

    All implementations (real and fake) must implement this interface.
    """

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
            True on success, False on failure
        """
        ...

    @abstractmethod
    def get_pr_status(self, repo_root: Path, branch: str, *, debug: bool) -> PRInfo:
        """Get PR status for a specific branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name to check
            debug: If True, print debug information

        Returns:
            PRInfo with state, pr_number, and title
            - state: "OPEN", "MERGED", "CLOSED", or "NONE" if no PR exists
            - pr_number: PR number or None if no PR exists
            - title: PR title or None if no PR exists
        """
        ...

    @abstractmethod
    def get_pr_base_branch(self, repo_root: Path, pr_number: int) -> str:
        """Get current base branch of a PR from GitHub.

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            Name of the base branch
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
    def get_pr_mergeability(self, repo_root: Path, pr_number: int) -> PRMergeability | None:
        """Get PR mergeability status from GitHub.

        Returns None if PR not found or API error.
        """
        ...

    @abstractmethod
    def fetch_pr_titles_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Fetch PR titles for all PRs in a single batched GraphQL query.

        This is a lighter-weight alternative to enrich_prs_with_ci_status_batch
        that only fetches titles, not CI status or mergeability.

        Args:
            prs: Mapping of branch name to PullRequestInfo (without titles)
            repo_root: Repository root directory

        Returns:
            Mapping of branch name to PullRequestInfo (with titles enriched)
        """
        ...

    @abstractmethod
    def enrich_prs_with_ci_status_batch(
        self, prs: dict[str, PullRequestInfo], repo_root: Path
    ) -> dict[str, PullRequestInfo]:
        """Enrich PR information with CI check status and mergeability using batched GraphQL query.

        Fetches both CI status and mergeability for all PRs in a single GraphQL API call,
        dramatically improving performance over serial fetching.

        Args:
            prs: Mapping of branch name to PullRequestInfo (without CI status or mergeability)
            repo_root: Repository root directory

        Returns:
            Mapping of branch name to PullRequestInfo (with CI status and has_conflicts enriched)
        """
        ...

    @abstractmethod
    def get_prs_for_repo(
        self, repo_root: Path, *, include_checks: bool
    ) -> dict[str, PullRequestInfo]:
        """Get PR information for all branches in the repository.

        Args:
            repo_root: Repository root directory
            include_checks: If True, fetch CI check status (slower). If False, skip check status

        Returns:
            Mapping of branch name -> PullRequestInfo
            - checks_passing is None when include_checks=False
            Empty dict if gh CLI is not available or not authenticated
        """
        ...

    @abstractmethod
    def get_pr_checkout_info(self, repo_root: Path, pr_number: int) -> PRCheckoutInfo | None:
        """Get PR details needed for checkout.

        Fetches the minimal information required to checkout a PR into a worktree:
        - head_ref_name: The branch name in the source repository
        - is_cross_repository: Whether this PR is from a fork
        - state: The PR state (OPEN, CLOSED, MERGED)

        Args:
            repo_root: Repository root directory
            pr_number: PR number to query

        Returns:
            PRCheckoutInfo with checkout details, or None if PR not found
        """
        ...

    @abstractmethod
    def get_pr_info_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        """Get PR number and URL for a specific branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name to check

        Returns:
            Tuple of (pr_number, pr_url) or None if no PR exists for this branch
        """
        ...

    @abstractmethod
    def get_pr_state_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        """Get PR number and state for a specific branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name to check

        Returns:
            Tuple of (pr_number, state) where state is "OPEN", "MERGED", or "CLOSED"
            None if no PR exists for this branch
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
        self, repo_root: Path, pr_number: int, title: str, body: str
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
    def get_prs_linked_to_issues(
        self,
        location: GitHubRepoLocation,
        issue_numbers: list[int],
    ) -> dict[int, list[PullRequestInfo]]:
        """Get PRs linked to issues via GitHub's native branch linking.

        Queries GitHub for PRs associated with branches created via
        `gh issue develop`. Returns a mapping of issue numbers to PRs.

        Args:
            location: GitHub repository location (local path + owner/repo identity)
            issue_numbers: List of issue numbers to query

        Returns:
            Mapping of issue_number -> list of PRs linked to that issue.
            Returns empty dict if no PRs link to any of the issues.
        """
        ...

    @abstractmethod
    def get_issues_with_pr_linkages(
        self,
        location: GitHubRepoLocation,
        labels: list[str],
        state: str | None = None,
        limit: int | None = None,
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

        Returns:
            Tuple of (issues, pr_linkages) where:
            - issues: List of IssueInfo objects
            - pr_linkages: Mapping of issue_number -> list of linked PRs
        """
        ...
