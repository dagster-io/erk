"""Graphite-based BranchManager implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.types import PrInfo
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.git.abc import Git


@dataclass(frozen=True)
class GraphiteBranchManager(BranchManager):
    """BranchManager implementation using Graphite.

    Uses Graphite's local cache for fast PR lookups and `gt create`
    for branch creation with parent tracking.
    """

    git: Git
    graphite: Graphite

    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PrInfo | None:
        """Get PR info from Graphite's local cache.

        Reads from .graphite_pr_info cache file for fast lookup
        without network calls.

        Args:
            repo_root: Repository root directory
            branch: Branch name to look up

        Returns:
            PrInfo if a PR exists for the branch, None otherwise.
        """
        prs = self.graphite.get_prs_from_graphite(self.git, repo_root)
        if branch not in prs:
            return None

        pr_info = prs[branch]
        return PrInfo(
            number=pr_info.number,
            state=pr_info.state,
            is_draft=pr_info.is_draft,
        )

    def create_branch(self, repo_root: Path, branch_name: str, base_branch: str) -> None:
        """Create a new branch using Graphite.

        Uses `gt create` via the Graphite gateway. This creates the branch
        and registers it with Graphite for stack tracking.

        Note: This currently uses track_branch after git branch creation
        since there's no direct `gt create` method in the gateway yet.
        Future work may add a direct create method.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the new branch
            base_branch: Name of the parent branch
        """
        # First checkout the base branch
        self.git.checkout_branch(repo_root, base_branch)
        # Create the branch using git (from base_branch)
        self.git.create_branch(repo_root, branch_name, base_branch)
        # Checkout the new branch
        self.git.checkout_branch(repo_root, branch_name)
        # Track it with Graphite
        self.graphite.track_branch(repo_root, branch_name, base_branch)

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete a branch with Graphite metadata cleanup.

        Args:
            repo_root: Repository root directory
            branch: Branch name to delete
        """
        self.git.delete_branch_with_graphite(repo_root, branch, force=True)

    def is_graphite_managed(self) -> bool:
        """Returns True - this implementation uses Graphite."""
        return True
