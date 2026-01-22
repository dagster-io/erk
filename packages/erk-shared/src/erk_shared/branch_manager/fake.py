"""Fake BranchManager implementation for testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.types import PrInfo


@dataclass(frozen=True)
class FakeBranchManager(BranchManager):
    """Test implementation of BranchManager.

    Provides in-memory storage for PR info and branch creation tracking.
    All state is provided at construction time (frozen dataclass pattern).
    """

    # Mapping of branch name -> PrInfo
    pr_info: dict[str, PrInfo] = field(default_factory=dict)
    # Whether to simulate Graphite mode
    graphite_mode: bool = False
    # Mapping of branch name -> stack (list of branches from trunk to leaf)
    stacks: dict[str, list[str]] = field(default_factory=dict)
    # Mapping of branch name -> parent branch name
    parent_branches: dict[str, str] = field(default_factory=dict)
    # Mapping of branch name -> list of child branch names
    child_branches: dict[str, list[str]] = field(default_factory=dict)
    # Track created branches for assertions: list of (branch_name, base_branch) tuples
    _created_branches: list[tuple[str, str]] = field(default_factory=list)
    # Track deleted branches for assertions
    _deleted_branches: list[str] = field(default_factory=list)
    # Track submitted branches for assertions
    _submitted_branches: list[str] = field(default_factory=list)
    # Track tracked branches for assertions: list of (branch_name, parent_branch) tuples
    _tracked_branches: list[tuple[str, str]] = field(default_factory=list)
    # Track commits for assertions: list of commit messages
    _commits: list[str] = field(default_factory=list)
    # Track checked out branches for assertions: list of branch names
    _checked_out_branches: list[str] = field(default_factory=list)
    # Track detached checkouts for assertions: list of refs
    _detached_checkouts: list[str] = field(default_factory=list)
    # Track created tracking branches: list of (branch, remote_ref) tuples
    _created_tracking_branches: list[tuple[str, str]] = field(default_factory=list)

    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PrInfo | None:
        """Get PR info from in-memory storage.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Branch name to look up

        Returns:
            PrInfo if configured for the branch, None otherwise.
        """
        return self.pr_info.get(branch)

    def create_branch(self, repo_root: Path, branch_name: str, base_branch: str) -> None:
        """Record branch creation in tracked list.

        Note: This mutates internal state despite the frozen dataclass.
        The list reference is frozen, but the list contents can change.
        This is intentional for test observability.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch_name: Name of the new branch
            base_branch: Name of the base branch
        """
        self._created_branches.append((branch_name, base_branch))

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Record branch deletion in tracked list.

        Note: This mutates internal state despite the frozen dataclass.
        The list reference is frozen, but the list contents can change.
        This is intentional for test observability.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Branch name to delete
        """
        self._deleted_branches.append(branch)

    def submit_branch(self, repo_root: Path, branch: str) -> None:
        """Record branch submission in tracked list.

        Note: This mutates internal state despite the frozen dataclass.
        The list reference is frozen, but the list contents can change.
        This is intentional for test observability.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Branch name to submit
        """
        self._submitted_branches.append(branch)

    def commit(self, repo_root: Path, message: str) -> None:
        """Record commit in tracked list.

        Note: This mutates internal state despite the frozen dataclass.
        The list reference is frozen, but the list contents can change.
        This is intentional for test observability.

        Args:
            repo_root: Repository root directory (unused in fake)
            message: Commit message
        """
        self._commits.append(message)

    def get_branch_stack(self, repo_root: Path, branch: str) -> list[str] | None:
        """Get stack from configured test data.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Branch name to look up

        Returns:
            List of branch names in the stack if configured, None otherwise.
        """
        return self.stacks.get(branch)

    def track_branch(self, repo_root: Path, branch_name: str, parent_branch: str) -> None:
        """Record branch tracking in tracked list.

        Note: This mutates internal state despite the frozen dataclass.
        The list reference is frozen, but the list contents can change.
        This is intentional for test observability.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch_name: Name of the branch to track
            parent_branch: Name of the parent branch
        """
        self._tracked_branches.append((branch_name, parent_branch))

    def get_parent_branch(self, repo_root: Path, branch: str) -> str | None:
        """Get parent branch from configured test data.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Name of the branch to get the parent for

        Returns:
            Parent branch name if configured, None otherwise.
        """
        return self.parent_branches.get(branch)

    def get_child_branches(self, repo_root: Path, branch: str) -> list[str]:
        """Get child branches from configured test data.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Name of the branch to get children for

        Returns:
            List of child branch names if configured, empty list otherwise.
        """
        return self.child_branches.get(branch, [])

    def checkout_branch(self, repo_root: Path, branch: str) -> None:
        """Record branch checkout in tracked list.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Branch name to checkout
        """
        self._checked_out_branches.append(branch)

    def checkout_detached(self, repo_root: Path, ref: str) -> None:
        """Record detached HEAD checkout in tracked list.

        Args:
            repo_root: Repository root directory (unused in fake)
            ref: Git ref to checkout
        """
        self._detached_checkouts.append(ref)

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Record tracking branch creation in tracked list.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Name for the local branch
            remote_ref: Remote reference to track
        """
        self._created_tracking_branches.append((branch, remote_ref))

    def is_graphite_managed(self) -> bool:
        """Returns the configured graphite_mode value."""
        return self.graphite_mode

    @property
    def created_branches(self) -> list[tuple[str, str]]:
        """Get list of created branches for test assertions.

        Returns:
            List of (branch_name, base_branch) tuples.
        """
        return list(self._created_branches)

    @property
    def deleted_branches(self) -> list[str]:
        """Get list of deleted branches for test assertions.

        Returns:
            List of branch names that were deleted.
        """
        return list(self._deleted_branches)

    @property
    def submitted_branches(self) -> list[str]:
        """Get list of submitted branches for test assertions.

        Returns:
            List of branch names that were submitted.
        """
        return list(self._submitted_branches)

    @property
    def tracked_branches(self) -> list[tuple[str, str]]:
        """Get list of tracked branches for test assertions.

        Returns:
            List of (branch_name, parent_branch) tuples.
        """
        return list(self._tracked_branches)

    @property
    def commits(self) -> list[str]:
        """Get list of commit messages for test assertions.

        Returns:
            List of commit messages.
        """
        return list(self._commits)

    @property
    def checked_out_branches(self) -> list[str]:
        """Get list of checked out branches for test assertions.

        Returns:
            List of branch names that were checked out.
        """
        return list(self._checked_out_branches)

    @property
    def detached_checkouts(self) -> list[str]:
        """Get list of detached HEAD checkouts for test assertions.

        Returns:
            List of refs that were checked out with detached HEAD.
        """
        return list(self._detached_checkouts)

    @property
    def created_tracking_branches(self) -> list[tuple[str, str]]:
        """Get list of created tracking branches for test assertions.

        Returns:
            List of (branch, remote_ref) tuples.
        """
        return list(self._created_tracking_branches)
