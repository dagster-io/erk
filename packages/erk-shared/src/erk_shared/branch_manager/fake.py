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
    # Track created branches for assertions: list of (branch_name, base_branch) tuples
    _created_branches: list[tuple[str, str]] = field(default_factory=list)
    # Track deleted branches for assertions
    _deleted_branches: list[str] = field(default_factory=list)
    # Track submitted branches for assertions
    _submitted_branches: list[str] = field(default_factory=list)

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

    def get_branch_stack(self, repo_root: Path, branch: str) -> list[str] | None:
        """Get stack from configured test data.

        Args:
            repo_root: Repository root directory (unused in fake)
            branch: Branch name to look up

        Returns:
            List of branch names in the stack if configured, None otherwise.
        """
        return self.stacks.get(branch)

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
