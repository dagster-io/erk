"""Git-based BranchManager implementation (no Graphite)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.types import PrInfo
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.types import PRNotFound


@dataclass(frozen=True)
class GitBranchManager(BranchManager):
    """BranchManager implementation using plain Git and GitHub.

    Falls back to GitHub REST API for PR lookups when Graphite
    is not available or not configured.
    """

    git: Git
    github: GitHub

    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PrInfo | None:
        """Get PR info from GitHub REST API.

        This is slower than Graphite's local cache but works when
        Graphite is not available.

        Args:
            repo_root: Repository root directory
            branch: Branch name to look up

        Returns:
            PrInfo if a PR exists for the branch, None otherwise.
        """
        result = self.github.get_pr_for_branch(repo_root, branch)
        if isinstance(result, PRNotFound):
            return None

        return PrInfo(
            number=result.number,
            state=result.state,
            is_draft=result.is_draft,
        )

    def create_branch(self, repo_root: Path, branch_name: str, base_branch: str) -> None:
        """Create a new branch using Git.

        Uses plain git commands without Graphite tracking.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the new branch
            base_branch: Name of the base branch
        """
        # First checkout the base branch
        self.git.checkout_branch(repo_root, base_branch)
        # Create the branch using git (from base_branch)
        self.git.create_branch(repo_root, branch_name, base_branch)
        # Checkout the new branch
        self.git.checkout_branch(repo_root, branch_name)

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete a branch using plain Git.

        Args:
            repo_root: Repository root directory
            branch: Branch name to delete
        """
        self.git.delete_branch(repo_root, branch, force=True)

    def is_graphite_managed(self) -> bool:
        """Returns False - this implementation uses plain Git."""
        return False
