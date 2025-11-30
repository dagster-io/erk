"""No-op wrapper for issue development operations."""

from pathlib import Path

from erk_shared.github.issue_link_branches import DevelopmentBranch, IssueLinkBranches


class DryRunIssueLinkBranches(IssueLinkBranches):
    """No-op wrapper for issue-linked branch operations.

    Read operations are delegated to the wrapped implementation.
    Write operations return without executing (no-op behavior).

    This wrapper prevents destructive issue-linked branch operations from
    executing in dry-run mode, while still allowing read operations for validation.
    """

    def __init__(self, wrapped: IssueLinkBranches) -> None:
        """Initialize dry-run wrapper with a real implementation.

        Args:
            wrapped: The real IssueLinkBranches implementation to wrap
        """
        self._wrapped = wrapped

    def create_development_branch(
        self,
        repo_root: Path,
        issue_number: int,
        *,
        branch_name: str,
        base_branch: str | None = None,
    ) -> DevelopmentBranch:
        """No-op for creating development branch in dry-run mode.

        Returns a fake branch result without actually creating anything.
        Uses the provided branch_name to match real behavior.
        """
        # Return fake result using the provided branch name
        return DevelopmentBranch(
            branch_name=branch_name,
            issue_number=issue_number,
            already_existed=False,
        )

    def get_linked_branch(
        self,
        repo_root: Path,
        issue_number: int,
    ) -> str | None:
        """Delegate read operation to wrapped implementation."""
        return self._wrapped.get_linked_branch(repo_root, issue_number)
