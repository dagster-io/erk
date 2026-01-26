"""Abstract interface for git worktree operations.

This module provides a clean abstraction over git worktree subprocess calls,
making the codebase more testable and maintainable.

Architecture:
- Worktree: Abstract base class defining the interface
- RealWorktree: Production implementation using subprocess
- FakeWorktree: In-memory implementation for testing
"""

from abc import ABC, abstractmethod
from pathlib import Path

# Re-export WorktreeInfo from the main git.abc module for backwards compatibility
from erk_shared.gateway.git.abc import WorktreeInfo


class Worktree(ABC):
    """Abstract interface for git worktree operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository."""
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
        """Move a worktree to a new location."""
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
        """Prune stale worktree metadata."""
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
    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree has no uncommitted changes, staged changes, or untracked files.

        Args:
            worktree_path: Path to the worktree to check

        Returns:
            True if worktree is clean (no uncommitted, staged, or untracked files)
        """
        ...

    @abstractmethod
    def safe_chdir(self, path: Path) -> bool:
        """Change current directory if path exists on real filesystem.

        Used when removing worktrees or switching contexts to prevent shell from
        being in a deleted directory. In production (RealWorktree), checks if path
        exists then changes directory. In tests (FakeWorktree), handles sentinel
        paths by returning False without changing directory.

        Args:
            path: Directory to change to

        Returns:
            True if directory change succeeded, False otherwise
        """
        ...

    @abstractmethod
    def path_exists(self, path: Path) -> bool:
        """Check if a path exists on the filesystem.

        This is primarily used for checking if worktree directories still exist,
        particularly after cleanup operations. In production (RealWorktree), this
        delegates to Path.exists(). In tests (FakeWorktree), this checks an in-memory
        set of existing paths to avoid filesystem I/O.

        Args:
            path: Path to check

        Returns:
            True if path exists, False otherwise
        """
        ...

    @abstractmethod
    def is_dir(self, path: Path) -> bool:
        """Check if a path is a directory.

        This is used for distinguishing between .git directories (normal repos)
        and .git files (worktrees with gitdir pointers). In production (RealWorktree),
        this delegates to Path.is_dir(). In tests (FakeWorktree), this checks an
        in-memory set of directory paths to avoid filesystem I/O.

        Args:
            path: Path to check

        Returns:
            True if path is a directory, False otherwise
        """
        ...
