"""Abstract interface for git worktree operations.

This module defines the GitWorktrees ABC, a focused interface for managing
git worktrees. Part of the Git gateway refactoring to improve testability
by splitting the monolithic Git ABC into smaller integrations.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo


class GitWorktrees(ABC):
    """Abstract interface for git worktree operations.

    All implementations (real, fake, dry-run) must implement this interface.
    This interface contains ONLY worktree-related operations.
    """

    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository.

        Args:
            repo_root: Path to the git repository root

        Returns:
            List of WorktreeInfo objects describing each worktree
        """
        ...

    @abstractmethod
    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Add a new git worktree.

        Args:
            repo_root: Path to the git repository root
            path: Path where the worktree should be created
            branch: Branch name (None creates detached HEAD or uses ref)
            ref: Git ref to base worktree on (None defaults to HEAD when creating branches)
            create_branch: True to create new branch, False to checkout existing
        """
        ...

    @abstractmethod
    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move a worktree to a new location.

        Args:
            repo_root: Path to the git repository root
            old_path: Current path of the worktree
            new_path: New path for the worktree
        """
        ...

    @abstractmethod
    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove a worktree.

        Args:
            repo_root: Path to the git repository root
            path: Path to the worktree to remove
            force: True to force removal even if worktree has uncommitted changes
        """
        ...

    @abstractmethod
    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata.

        Removes administrative files for worktrees that no longer exist on disk.

        Args:
            repo_root: Path to the git repository root
        """
        ...

    @abstractmethod
    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree.

        Args:
            repo_root: Path to the git repository root
            branch: Branch name to check

        Returns:
            Path to the worktree where branch is checked out, or None if not checked out.
        """
        ...

    @abstractmethod
    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name.

        Args:
            repo_root: Repository root path
            branch: Branch name to search for

        Returns:
            Path to worktree if branch is checked out, None otherwise
        """
        ...

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory for a worktree.

        The common directory is where shared repository data lives
        (objects, refs, etc.). For a normal repo this is the .git directory.
        For worktrees, this points to the main repository's .git directory.

        Args:
            cwd: Working directory (can be any worktree)

        Returns:
            Path to the common git directory, or None if not in a git repository
        """
        ...
