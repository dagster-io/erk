"""Dry-run wrapper for GitHub issues operations."""

from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.issues.types import (
    CreateIssueResult,
    IssueComment,
    IssueInfo,
    PRReference,
)


class DryRunGitHubIssues(GitHubIssues):
    """No-op wrapper for GitHub issue operations.

    Read operations are delegated to the wrapped implementation.
    Write operations return without executing (no-op behavior).

    This wrapper prevents issue mutations from executing in dry-run mode,
    while still allowing read operations for validation.
    """

    def __init__(self, wrapped: GitHubIssues) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real GitHubIssues implementation to wrap
        """
        self._wrapped = wrapped

    def create_issue(
        self, repo_root: Path, title: str, body: str, labels: list[str]
    ) -> CreateIssueResult:
        """No-op for creating issue in dry-run mode.

        Returns a fake CreateIssueResult to allow dry-run workflows to continue.
        """
        return CreateIssueResult(number=1, url="https://github.com/dry-run/dry-run/issues/1")

    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_issue(repo_root, number)

    def add_comment(self, repo_root: Path, number: int, body: str) -> int:
        """No-op for adding comment in dry-run mode.

        Returns a fake comment ID to allow dry-run workflows to continue.
        """
        return 1234567890  # Fake comment ID for dry-run mode

    def update_issue_body(self, repo_root: Path, number: int, body: str) -> None:
        """No-op for updating issue body in dry-run mode."""

    def list_issues(
        self,
        repo_root: Path,
        labels: list[str] | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[IssueInfo]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.list_issues(repo_root, labels=labels, state=state, limit=limit)

    def get_issue_comments(self, repo_root: Path, number: int) -> list[str]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_issue_comments(repo_root, number)

    def get_issue_comments_with_urls(self, repo_root: Path, number: int) -> list[IssueComment]:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_issue_comments_with_urls(repo_root, number)

    def get_comment_by_id(self, repo_root: Path, comment_id: int) -> str:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_comment_by_id(repo_root, comment_id)

    def ensure_label_exists(
        self,
        repo_root: Path,
        label: str,
        description: str,
        color: str,
    ) -> None:
        """No-op for ensuring label exists in dry-run mode."""

    def ensure_label_on_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """No-op for ensuring label in dry-run mode (idempotent)."""

    def remove_label_from_issue(self, repo_root: Path, issue_number: int, label: str) -> None:
        """No-op for removing label in dry-run mode."""

    def close_issue(self, repo_root: Path, number: int) -> None:
        """No-op for closing issue in dry-run mode."""

    def get_current_username(self) -> str | None:
        """Delegate to wrapped implementation (read operation)."""
        return self._wrapped.get_current_username()

    def get_prs_referencing_issue(
        self,
        repo_root: Path,
        issue_number: int,
    ) -> list[PRReference]:
        """Delegate to wrapped implementation (read-only operation)."""
        return self._wrapped.get_prs_referencing_issue(repo_root, issue_number)

    def add_reaction_to_comment(
        self,
        repo_root: Path,
        comment_id: int,
        reaction: str,
    ) -> None:
        """No-op for adding reaction in dry-run mode."""
