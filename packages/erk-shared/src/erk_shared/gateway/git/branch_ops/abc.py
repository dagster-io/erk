"""Abstract base class for Git branch operations.

This sub-gateway extracts branch operations from the main Git gateway,
including both mutation and query operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk_shared.gateway.git.abc import BranchDivergence, BranchSyncInfo


class GitBranchOps(ABC):
    """Abstract interface for Git branch operations.

    This interface contains both mutation and query operations for branches.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    @abstractmethod
    def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> None:
        """Create a new branch without checking it out.

        Args:
            cwd: Working directory to run command in
            branch_name: Name of the branch to create
            start_point: Commit/branch to base the new branch on
            force: Use -f flag to move existing branch to the start_point
        """
        ...

    @abstractmethod
    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch.

        Args:
            cwd: Working directory to run command in
            branch_name: Name of the branch to delete
            force: Use -D (force delete) instead of -d
        """
        ...

    @abstractmethod
    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory.

        Args:
            cwd: Working directory to run command in
            branch: Branch name to checkout
        """
        ...

    @abstractmethod
    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref.

        Args:
            cwd: Working directory to run command in
            ref: Git ref to checkout (commit SHA, branch name, etc.)
        """
        ...

    @abstractmethod
    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch.

        Args:
            repo_root: Path to the repository root
            branch: Name for the local branch (e.g., 'feature-remote')
            remote_ref: Remote reference to track (e.g., 'origin/feature-remote')

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch.

        Args:
            cwd: Working directory to query

        Returns:
            Branch name, or None if in detached HEAD state
        """
        ...

    @abstractmethod
    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository.

        Args:
            repo_root: Path to the repository root

        Returns:
            List of local branch names
        """
        ...

    @abstractmethod
    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository.

        Returns branch names in format 'origin/branch-name', 'upstream/feature', etc.
        Only includes refs from configured remotes, not local branches.

        Args:
            repo_root: Path to the repository root

        Returns:
            List of remote branch names with remote prefix (e.g., 'origin/main')
        """
        ...

    @abstractmethod
    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch.

        Args:
            repo_root: Path to the git repository root
            branch: Branch name to query

        Returns:
            Commit SHA as a string, or None if branch doesn't exist.
        """
        ...

    @abstractmethod
    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name.

        Checks git's remote HEAD reference, then falls back to checking for
        existence of 'main' then 'master'. Returns 'main' as final fallback
        if neither branch exists.

        Args:
            repo_root: Path to the repository root

        Returns:
            Trunk branch name (e.g., 'main', 'master')
        """
        ...

    @abstractmethod
    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists.

        Args:
            repo_root: Path to the repository root
            name: Trunk branch name to validate

        Returns:
            The validated trunk branch name

        Raises:
            RuntimeError: If the specified branch doesn't exist
        """
        ...

    @abstractmethod
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote.

        Args:
            repo_root: Path to the git repository root
            remote: Remote name (e.g., "origin")
            branch: Branch name to check

        Returns:
            True if branch exists on remote, False otherwise
        """
        ...

    @abstractmethod
    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch.

        Args:
            cwd: Working directory
            branch: Current branch name

        Returns:
            Tuple of (ahead, behind) counts
        """
        ...

    @abstractmethod
    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get sync status for all local branches in a single git call.

        Uses git for-each-ref to batch-fetch upstream tracking information.

        Args:
            repo_root: Path to the git repository root

        Returns:
            Dict mapping branch name to BranchSyncInfo.
        """
        ...

    @abstractmethod
    def is_branch_diverged_from_remote(
        self, cwd: Path, branch: str, remote: str
    ) -> BranchDivergence:
        """Check if a local branch has diverged from its remote tracking branch.

        A branch is considered diverged when it has commits both ahead and behind
        the remote tracking branch.

        Args:
            cwd: Working directory
            branch: Local branch name to check
            remote: Remote name (e.g., "origin")

        Returns:
            BranchDivergence with is_diverged flag and ahead/behind counts.
        """
        ...

    @abstractmethod
    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Extract GitHub issue number from branch name.

        Branch names follow the pattern: {issue_number}-{slug}-{timestamp}
        Examples: "2382-convert-erk-create-raw-ext-12-05-2359"

        Args:
            repo_root: Path to the git repository root (unused, kept for interface compat)
            branch: Branch name to parse

        Returns:
            Issue number if branch starts with digits followed by hyphen, None otherwise
        """
        ...

    @abstractmethod
    def get_behind_commit_authors(self, cwd: Path, branch: str) -> list[str]:
        """Get authors of commits on remote that are not in local branch.

        Used to detect server-side commits (e.g., autofix from CI).

        Args:
            cwd: Working directory
            branch: Local branch name

        Returns:
            List of author names for commits on origin/branch but not locally.
            Empty list if no tracking branch or no behind commits.
        """
        ...

    @abstractmethod
    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get the author date of the most recent commit unique to a branch.

        Returns ISO 8601 timestamp of the latest commit on `branch` but not on `trunk`,
        or None if branch has no unique commits or doesn't exist.

        Args:
            repo_root: Path to the repository root
            branch: Branch name to check
            trunk: Trunk branch name to compare against

        Returns:
            ISO 8601 timestamp string, or None if no unique commits
        """
        ...

    @abstractmethod
    def get_branch_commits_with_authors(
        self, repo_root: Path, branch: str, trunk: str, *, limit: int
    ) -> list[dict[str, str]]:
        """Get commits on branch not on trunk, with author and timestamp.

        Returns commits unique to the branch (not present on trunk),
        ordered from newest to oldest.

        Args:
            repo_root: Path to the repository root
            branch: Branch name to get commits from
            trunk: Trunk branch name to compare against
            limit: Maximum number of commits to retrieve

        Returns:
            List of commit info dicts with keys:
            - sha: Commit SHA (full)
            - author: Author name
            - timestamp: ISO 8601 timestamp (author date)
        """
        ...
