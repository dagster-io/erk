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

        Falls back to plain git if Graphite can't delete (untracked/diverged).

        Args:
            repo_root: Repository root directory
            branch: Branch name to delete
        """
        # LBYL: Check if Graphite can handle this branch
        if not self._can_graphite_delete(repo_root, branch):
            self.git.delete_branch(repo_root, branch, force=True)
            return

        self.graphite.delete_branch(repo_root, branch)

    def _can_graphite_delete(self, repo_root: Path, branch: str) -> bool:
        """Check if Graphite can delete this branch (tracked and not diverged).

        Args:
            repo_root: Repository root directory
            branch: Branch name to check

        Returns:
            True if Graphite can delete the branch, False if git fallback needed.
        """
        # Check 1: Is branch tracked?
        if not self.graphite.is_branch_tracked(repo_root, branch):
            return False

        # Check 2: Is branch diverged from Graphite's cached SHA?
        branches = self.graphite.get_all_branches(self.git, repo_root)
        if branch in branches:
            graphite_sha = branches[branch].commit_sha
            actual_sha = self.git.get_branch_head(repo_root, branch)
            if graphite_sha is not None and actual_sha is not None and graphite_sha != actual_sha:
                return False

        return True

    def submit_branch(self, repo_root: Path, branch: str) -> None:
        """Submit branch via Graphite.

        Uses `gt submit --force --quiet` to submit the stack.

        Args:
            repo_root: Repository root directory
            branch: Branch name to submit (unused - Graphite submits current stack)
        """
        self.graphite.submit_stack(repo_root, quiet=True, force=True)

    def is_graphite_managed(self) -> bool:
        """Returns True - this implementation uses Graphite."""
        return True
