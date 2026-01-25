"""Abstract base class for Graphite branch operations.

This sub-gateway extracts branch mutation operations from the main Graphite gateway,
making BranchManager the enforced abstraction for branch mutations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GraphiteBranchOps(ABC):
    """Abstract interface for Graphite branch mutation operations.

    This interface contains ONLY mutation operations that modify branch state.
    Query operations (get_all_branches, get_branch_stack, etc.) remain on the
    main Graphite ABC for convenience.

    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    @abstractmethod
    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Track a branch with Graphite.

        Uses `gt track` to register a branch in Graphite's cache. This is needed
        when branches are created with direct git operations (git branch) instead
        of gt create.

        Args:
            cwd: Working directory where gt track should run
            branch_name: Name of the branch to track
            parent_branch: Name of the parent branch in the stack
        """
        ...

    @abstractmethod
    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete a branch using Graphite's gt delete command.

        Uses `gt delete -f <branch>` to delete a branch and clean up Graphite
        metadata. The -f flag is always used to force deletion without prompts.

        Args:
            repo_root: Repository root directory
            branch: Name of the branch to delete

        Raises:
            RuntimeError: If gt delete fails
        """
        ...

    @abstractmethod
    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Submit (force-push) a branch to GitHub.

        Uses `gt submit` to push a branch that was rebased by `gt sync -f`.
        This ensures GitHub PRs show the rebased commits rather than stale
        versions with duplicate commits.

        Args:
            repo_root: Repository root directory
            branch_name: Name of the branch to submit
            quiet: If True, pass --quiet flag to gt submit for minimal output
        """
        ...

    @abstractmethod
    def retrack_branch(self, cwd: Path, branch_name: str) -> None:
        """Re-track an existing branch to fix Graphite tracking divergence.

        After rebase/restack operations, Graphite's internal SHA tracking
        (in .graphite_cache_persist) may become stale. This method runs
        `gt track` on an already-tracked branch to refresh the SHA.

        Args:
            cwd: Working directory where gt track should run
            branch_name: Name of the branch to re-track
        """
        ...
