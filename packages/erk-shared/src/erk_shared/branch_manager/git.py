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
            from_fallback=False,  # GitBranchManager always uses GitHub directly
        )

    def create_branch(self, repo_root: Path, branch_name: str, base_branch: str) -> None:
        """Create a new branch using Git.

        Uses plain git commands without Graphite tracking.
        Does NOT checkout the branch - leaves the current branch unchanged.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the new branch
            base_branch: Name of the base branch
        """
        # Create the branch from base_branch without checking it out
        # This allows callers to create worktrees with the branch later
        self.git.branch.create_branch(repo_root, branch_name, base_branch, force=False)

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        """Delete a branch using plain Git.

        Args:
            repo_root: Repository root directory
            branch: Branch name to delete
            force: If True, use -D (force delete) instead of -d
        """
        self.git.branch.delete_branch(repo_root, branch, force=force)

    def submit_branch(self, repo_root: Path, branch: str) -> None:
        """Submit branch via git push.

        Uses `git push -u --force origin <branch>` to push with upstream tracking.
        Force push is used for parity with Graphite's submit behavior, which
        always force pushes during quick iterations.

        Args:
            repo_root: Repository root directory
            branch: Branch name to push
        """
        self.git.push_to_remote(repo_root, "origin", branch, set_upstream=True, force=True)

    def commit(self, repo_root: Path, message: str) -> None:
        """Create a commit using git.

        Args:
            repo_root: Repository root directory
            message: Commit message
        """
        self.git.commit(repo_root, message)

    def get_branch_stack(self, repo_root: Path, branch: str) -> list[str] | None:
        """Git-only mode doesn't track stacks.

        Args:
            repo_root: Repository root directory (unused)
            branch: Name of the branch (unused)

        Returns:
            None - stacks are a Graphite-only feature.
        """
        return None

    def track_branch(self, repo_root: Path, branch_name: str, parent_branch: str) -> None:
        """No-op for plain Git - parent relationships not tracked.

        Args:
            repo_root: Repository root directory (unused)
            branch_name: Name of the branch (unused)
            parent_branch: Name of the parent branch (unused)
        """
        # Plain Git doesn't track parent relationships
        pass

    def get_parent_branch(self, repo_root: Path, branch: str) -> str | None:
        """Git-only mode doesn't track parent relationships.

        Args:
            repo_root: Repository root directory (unused)
            branch: Name of the branch (unused)

        Returns:
            None - parent tracking is a Graphite-only feature.
        """
        return None

    def get_child_branches(self, repo_root: Path, branch: str) -> list[str]:
        """Git-only mode doesn't track child relationships.

        Args:
            repo_root: Repository root directory (unused)
            branch: Name of the branch (unused)

        Returns:
            Empty list - child tracking is a Graphite-only feature.
        """
        return []

    def checkout_branch(self, repo_root: Path, branch: str) -> None:
        """Checkout a branch using plain Git.

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
        """Returns False - this implementation uses plain Git."""
        return False
