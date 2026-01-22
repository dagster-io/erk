"""Graphite-based BranchManager implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.branch_manager.abc import BranchManager
from erk_shared.branch_manager.types import PrInfo
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.git.abc import Git
from erk_shared.github.abc import GitHub
from erk_shared.github.types import PRNotFound


@dataclass(frozen=True)
class GraphiteBranchManager(BranchManager):
    """BranchManager implementation using Graphite.

    Uses Graphite's local cache for fast PR lookups and `gt create`
    for branch creation with parent tracking. Falls back to GitHub API
    when PR info is not in Graphite cache.
    """

    git: Git
    graphite: Graphite
    github: GitHub

    def get_pr_for_branch(self, repo_root: Path, branch: str) -> PrInfo | None:
        """Get PR info from Graphite's local cache, falling back to GitHub API.

        First checks Graphite's .graphite_pr_info cache file for fast lookup
        without network calls. If the branch is not in the cache (e.g., after
        `gt track` without `gt sync`), falls back to GitHub API.

        Args:
            repo_root: Repository root directory
            branch: Branch name to look up

        Returns:
            PrInfo if a PR exists for the branch, None otherwise.
            The from_fallback field indicates whether GitHub API was used.
        """
        # Try Graphite cache first (fast, local file read)
        prs = self.graphite.get_prs_from_graphite(self.git, repo_root)
        if branch in prs:
            pr_info = prs[branch]
            return PrInfo(
                number=pr_info.number,
                state=pr_info.state,
                is_draft=pr_info.is_draft,
                from_fallback=False,
            )

        # Fall back to GitHub API for branches not in Graphite cache
        pr_details = self.github.get_pr_for_branch(repo_root, branch)
        if isinstance(pr_details, PRNotFound):
            return None
        return PrInfo(
            number=pr_details.number,
            state=pr_details.state,
            is_draft=pr_details.is_draft,
            from_fallback=True,  # Mark as fallback
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
            base_branch: Name of the parent branch (can be local or remote ref like origin/main)
        """
        # First checkout the base branch (may result in detached HEAD if remote ref)
        self.git.checkout_branch(repo_root, base_branch)
        # Create the branch using git (from base_branch)
        self.git.create_branch(repo_root, branch_name, base_branch)
        # Checkout the new branch
        self.git.checkout_branch(repo_root, branch_name)
        # Track it with Graphite - use local branch name for parent
        # (gt track doesn't accept remote refs like origin/branch)
        parent_for_graphite = base_branch
        if base_branch.startswith("origin/"):
            parent_for_graphite = base_branch.removeprefix("origin/")
        self.graphite.track_branch(repo_root, branch_name, parent_for_graphite)

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete a branch with Graphite metadata cleanup.

        Always uses gt delete when tracked (handles diverged branches gracefully).
        Falls back to plain git only if branch is not tracked by Graphite.

        Args:
            repo_root: Repository root directory
            branch: Branch name to delete
        """
        # LBYL: Check if branch is tracked by Graphite
        if not self.graphite.is_branch_tracked(repo_root, branch):
            # Branch not in Graphite - use plain git
            self.git.delete_branch(repo_root, branch, force=True)
            return

        # Branch is tracked - use gt delete which:
        # - Re-parents children to parent branch
        # - Cleans up .graphite_cache_persist metadata
        # - Handles diverged SHAs gracefully
        self.graphite.delete_branch(repo_root, branch)

    def submit_branch(self, repo_root: Path, branch: str) -> None:
        """Submit branch via Graphite.

        Uses `gt submit --force --quiet` to submit the stack.

        Args:
            repo_root: Repository root directory
            branch: Branch name to submit (unused - Graphite submits current stack)
        """
        self.graphite.submit_stack(repo_root, quiet=True, force=True)

    def commit(self, repo_root: Path, message: str) -> None:
        """Create a commit using git.

        Commits are not Graphite-specific, so we delegate to git.

        Args:
            repo_root: Repository root directory
            message: Commit message
        """
        self.git.commit(repo_root, message)

    def get_branch_stack(self, repo_root: Path, branch: str) -> list[str] | None:
        """Get stack from Graphite's local cache.

        Args:
            repo_root: Repository root directory
            branch: Name of the branch to get the stack for

        Returns:
            List of branch names in the stack (ordered trunk to leaf),
            or None if branch is not tracked by Graphite.
        """
        return self.graphite.get_branch_stack(self.git, repo_root, branch)

    def track_branch(self, repo_root: Path, branch_name: str, parent_branch: str) -> None:
        """Track an existing branch with Graphite.

        Registers the branch with Graphite for stack tracking.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the branch to track
            parent_branch: Name of the parent branch
        """
        self.graphite.track_branch(repo_root, branch_name, parent_branch)

    def get_parent_branch(self, repo_root: Path, branch: str) -> str | None:
        """Get parent branch from Graphite's cache.

        Args:
            repo_root: Repository root directory
            branch: Name of the branch to get the parent for

        Returns:
            Parent branch name, or None if branch is not tracked or is trunk.
        """
        return self.graphite.get_parent_branch(self.git, repo_root, branch)

    def get_child_branches(self, repo_root: Path, branch: str) -> list[str]:
        """Get child branches from Graphite's cache.

        Args:
            repo_root: Repository root directory
            branch: Name of the branch to get children for

        Returns:
            List of child branch names, or empty list if none.
        """
        return self.graphite.get_child_branches(self.git, repo_root, branch)

    def is_graphite_managed(self) -> bool:
        """Returns True - this implementation uses Graphite."""
        return True
