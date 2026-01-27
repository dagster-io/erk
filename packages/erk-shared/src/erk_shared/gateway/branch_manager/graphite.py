"""Graphite-based BranchManager implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.branch_manager.abc import BranchManager
from erk_shared.gateway.branch_manager.types import PrInfo
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.branch_ops.abc import GraphiteBranchOps


@dataclass(frozen=True)
class GraphiteBranchManager(BranchManager):
    """BranchManager implementation using Graphite.

    Uses Graphite's local cache for fast PR lookups and `gt create`
    for branch creation with parent tracking. Falls back to GitHub API
    when PR info is not in Graphite cache.
    """

    git: Git
    graphite: Graphite
    graphite_branch_ops: GraphiteBranchOps
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

        Creates the branch via git and registers it with Graphite for stack tracking.
        Does NOT checkout the branch - leaves the current branch unchanged.

        Note: Graphite's `gt track` requires the branch to exist and be checked out,
        so we temporarily checkout the new branch to track it, then checkout back.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the new branch
            base_branch: Name of the parent branch (can be local or remote ref like origin/main)
        """
        # Save current branch to restore later
        current_branch = self.git.get_current_branch(repo_root)

        # Create the branch from base_branch
        self.git.branch.create_branch(repo_root, branch_name, base_branch, force=False)

        # Checkout the new branch temporarily to track it with Graphite
        # (gt track requires the branch to be checked out)
        self.git.branch.checkout_branch(repo_root, branch_name)

        # Track it with Graphite - use local branch name for parent
        # (gt track doesn't accept remote refs like origin/branch)
        parent_for_graphite = base_branch.removeprefix("origin/")

        # If base was origin/something, ensure local parent branch matches remote
        # so Graphite's ancestry check passes (local must be ancestor of new branch)
        if base_branch.startswith("origin/"):
            self._ensure_local_matches_remote(repo_root, parent_for_graphite, base_branch)

        # Auto-fix diverged parent before tracking child
        # (gt track fails if parent is diverged from Graphite's tracking)
        if self.graphite.is_branch_diverged_from_tracking(self.git, repo_root, parent_for_graphite):
            # Checkout parent, retrack to update Graphite's cache, restore to new branch
            self.git.branch.checkout_branch(repo_root, parent_for_graphite)
            self.graphite_branch_ops.retrack_branch(repo_root, parent_for_graphite)
            self.git.branch.checkout_branch(repo_root, branch_name)

        self.graphite_branch_ops.track_branch(repo_root, branch_name, parent_for_graphite)

        # Restore original branch so callers can create worktrees with the new branch
        if current_branch is not None:
            self.git.branch.checkout_branch(repo_root, current_branch)

    def _ensure_local_matches_remote(
        self, repo_root: Path, local_branch: str, remote_ref: str
    ) -> None:
        """Ensure local branch matches remote ref for Graphite tracking.

        If the local branch doesn't exist, it is created from the remote ref.
        If the local branch exists but has diverged from remote, it is
        force-updated to match remote. This is safe because by the time this
        method is called, we've already checked out the new branch being
        created, so we're not on the local_branch.

        Args:
            repo_root: Repository root directory
            local_branch: Local branch name (e.g., "feature-branch")
            remote_ref: Remote reference (e.g., "origin/feature-branch")
        """
        local_branches = self.git.list_local_branches(repo_root)

        if local_branch not in local_branches:
            # Local doesn't exist - create it from remote
            self.git.branch.create_branch(repo_root, local_branch, remote_ref, force=False)
            return

        # Check if local differs from remote
        local_sha = self.git.get_branch_head(repo_root, local_branch)
        remote_sha = self.git.get_branch_head(repo_root, remote_ref)

        if local_sha == remote_sha:
            return  # Already in sync

        # Local and remote diverged - force-update local to match remote
        # This is safe because we're on the new branch (not this one)
        self.git.branch.create_branch(repo_root, local_branch, remote_ref, force=True)

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        """Delete a branch with Graphite metadata cleanup.

        Always uses gt delete when tracked (handles diverged branches gracefully).
        Falls back to plain git only if branch is not tracked by Graphite.

        Args:
            repo_root: Repository root directory
            branch: Branch name to delete
            force: If True, use -D (force delete) for non-Graphite branches.
                   Graphite-tracked branches always use gt delete which handles
                   diverged branches gracefully.
        """
        # LBYL: Check if branch is tracked by Graphite
        if not self.graphite.is_branch_tracked(repo_root, branch):
            # Branch not in Graphite - use plain git
            self.git.branch.delete_branch(repo_root, branch, force=force)
            return

        # Branch is tracked - use gt delete which:
        # - Re-parents children to parent branch
        # - Cleans up .graphite_cache_persist metadata
        # - Handles diverged SHAs gracefully
        self.graphite_branch_ops.delete_branch(repo_root, branch)

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
        self.graphite_branch_ops.track_branch(repo_root, branch_name, parent_branch)

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

    def checkout_branch(self, repo_root: Path, branch: str) -> None:
        """Checkout a branch.

        Args:
            repo_root: Repository root directory
            branch: Branch name to checkout
        """
        self.git.branch.checkout_branch(repo_root, branch)

    def checkout_detached(self, repo_root: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref.

        Args:
            repo_root: Repository root directory
            ref: Git ref to checkout
        """
        self.git.branch.checkout_detached(repo_root, ref)

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch.

        Args:
            repo_root: Repository root directory
            branch: Name for the local branch
            remote_ref: Remote reference to track
        """
        self.git.branch.create_tracking_branch(repo_root, branch, remote_ref)

    def is_graphite_managed(self) -> bool:
        """Returns True - this implementation uses Graphite."""
        return True
