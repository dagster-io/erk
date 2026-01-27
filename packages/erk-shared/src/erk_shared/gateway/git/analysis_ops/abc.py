"""Abstract interface for git analysis operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitAnalysisOps(ABC):
    """Abstract interface for Git branch analysis operations.

    This interface contains query operations for comparing branches and commits.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch.

        Uses `git rev-list --count {base_branch}..HEAD`.

        Args:
            cwd: Working directory
            base_branch: Branch to compare against

        Returns:
            Number of commits ahead, or 0 on error
        """
        ...

    @abstractmethod
    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs.

        The merge base is the best common ancestor of two commits, useful
        for determining how branches have diverged.

        Args:
            repo_root: Path to the git repository root
            ref1: First ref (branch name, commit SHA, or remote ref)
            ref2: Second ref (branch name, commit SHA, or remote ref)

        Returns:
            Commit SHA of the merge base, or None if refs have no common ancestor
        """
        ...

    @abstractmethod
    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD.

        Uses two-dot syntax `git diff {branch}..HEAD` to show what will
        change when merged.

        Args:
            cwd: Working directory
            branch: Branch to diff against

        Returns:
            Full diff as string
        """
        ...
