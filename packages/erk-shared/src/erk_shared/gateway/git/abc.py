"""High-level git operations interface.

This module provides a clean abstraction over git subprocess calls, making the
codebase more testable and maintainable.

Architecture:
- Git: Abstract base class defining the interface
- RealGit: Production implementation using subprocess
- Standalone functions: Convenience wrappers delegating to module singleton
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
    from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
    from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
    from erk_shared.gateway.git.worktree.abc import Worktree


class BranchDivergence(NamedTuple):
    """Result of checking if a branch has diverged from its remote tracking branch.

    Attributes:
        is_diverged: True if the branch has commits both ahead and behind the remote.
            A branch is diverged when it cannot be fast-forwarded in either direction.
        ahead: Number of commits on local branch not present on remote.
        behind: Number of commits on remote branch not present locally.
    """

    is_diverged: bool
    ahead: int
    behind: int


@dataclass(frozen=True)
class WorktreeInfo:
    """Information about a single git worktree."""

    path: Path
    branch: str | None
    is_root: bool = False


@dataclass(frozen=True)
class BranchSyncInfo:
    """Sync status for a branch relative to its upstream."""

    branch: str
    upstream: str | None  # None if no tracking branch
    ahead: int
    behind: int


@dataclass(frozen=True)
class RebaseResult:
    """Result of a git rebase operation.

    Attributes:
        success: True if rebase completed without conflicts
        conflict_files: Tuple of file paths with conflicts (empty if success=True)
    """

    success: bool
    conflict_files: tuple[str, ...]


def find_worktree_for_branch(worktrees: list[WorktreeInfo], branch: str) -> Path | None:
    """Find the path of the worktree that has the given branch checked out.

    Args:
        worktrees: List of worktrees to search
        branch: Branch name to find

    Returns:
        Path to the worktree with the branch checked out, or None if not found
    """
    for wt in worktrees:
        if wt.branch == branch:
            return wt.path
    return None


# ============================================================================
# Abstract Interface
# ============================================================================


class Git(ABC):
    """Abstract interface for git operations.

    All implementations (real and fake) must implement this interface.
    This interface contains ONLY runtime operations - no test setup methods.
    """

    @property
    @abstractmethod
    def worktree(self) -> Worktree:
        """Access worktree operations subgateway."""
        ...

    @property
    @abstractmethod
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway."""
        ...

    @property
    @abstractmethod
    def remote(self) -> GitRemoteOps:
        """Access remote operations subgateway."""
        ...

    @property
    @abstractmethod
    def commit(self) -> GitCommitOps:
        """Access commit operations subgateway."""
        ...

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        ...

    @abstractmethod
    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check if the repository has staged changes."""
        ...

    @abstractmethod
    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes.

        Uses git status --porcelain to detect any uncommitted changes.
        Returns False if git command fails (worktree might be in invalid state).

        Args:
            cwd: Working directory to check

        Returns:
            True if there are any uncommitted changes (staged, modified, or untracked)
        """
        ...

    @abstractmethod
    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files.

        Args:
            cwd: Working directory

        Returns:
            Tuple of (staged, modified, untracked) file lists
        """
        ...

    @abstractmethod
    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        ...

    @abstractmethod
    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        ...

    @abstractmethod
    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        ...

    @abstractmethod
    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree."""
        ...

    @abstractmethod
    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get list of files with merge conflicts from git status --porcelain.

        Returns file paths with conflict status codes (UU, AA, DD, AU, UA, DU, UD).

        Args:
            cwd: Working directory

        Returns:
            List of file paths with conflicts
        """
        ...

    @abstractmethod
    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check if rebase in progress (.git/rebase-merge or .git/rebase-apply).

        Handles worktrees by checking git common dir.

        Args:
            cwd: Working directory

        Returns:
            True if a rebase is in progress
        """
        ...

    @abstractmethod
    def rebase_continue(self, cwd: Path) -> None:
        """Continue an in-progress rebase (git rebase --continue).

        Args:
            cwd: Working directory

        Raises:
            subprocess.CalledProcessError: If continue fails (e.g., unresolved conflicts)
        """
        ...

    @abstractmethod
    def config_set(self, cwd: Path, key: str, value: str, *, scope: str = "local") -> None:
        """Set a git configuration value.

        Args:
            cwd: Working directory
            key: Configuration key (e.g., "user.name", "user.email")
            value: Configuration value
            scope: Configuration scope ("local", "global", or "system")

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name.

        Args:
            cwd: Working directory

        Returns:
            The configured user.name, or None if not set
        """
        ...

    @abstractmethod
    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists.

        Args:
            repo_root: Path to the repository root
            tag_name: Tag name to check (e.g., 'v1.0.0')

        Returns:
            True if the tag exists, False otherwise
        """
        ...

    @abstractmethod
    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag.

        Args:
            repo_root: Path to the repository root
            tag_name: Tag name to create (e.g., 'v1.0.0')
            message: Tag message

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote.

        Args:
            repo_root: Path to the repository root
            remote: Remote name (e.g., 'origin')
            tag_name: Tag name to push

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """Rebase the current branch onto a target ref.

        Runs `git rebase <target_ref>` to replay current branch commits on top
        of the target ref.

        Args:
            cwd: Working directory (must be in a git repository)
            target_ref: The ref to rebase onto (e.g., "origin/main", branch name)

        Returns:
            RebaseResult with success flag and any conflict files.
            If conflicts occur, the rebase will be left in progress.
        """
        ...

    @abstractmethod
    def rebase_abort(self, cwd: Path) -> None:
        """Abort an in-progress rebase operation.

        Runs `git rebase --abort` to cancel a rebase that has conflicts
        and restore the branch to its original state.

        Args:
            cwd: Working directory (must have a rebase in progress)

        Raises:
            subprocess.CalledProcessError: If no rebase is in progress
        """
        ...

    @abstractmethod
    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs.

        The merge base is the best common ancestor of two commits, which is
        useful for determining how branches have diverged.

        Args:
            repo_root: Path to the git repository root
            ref1: First ref (branch name, commit SHA, or remote ref like origin/main)
            ref2: Second ref (branch name, commit SHA, or remote ref like origin/main)

        Returns:
            Commit SHA of the merge base, or None if refs have no common ancestor
        """
        ...
