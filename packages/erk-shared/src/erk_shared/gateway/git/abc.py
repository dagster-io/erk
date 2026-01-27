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
    from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
    from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
    from erk_shared.gateway.git.status_ops.abc import GitStatusOps
    from erk_shared.gateway.git.tag_ops.abc import GitTagOps
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

    @property
    @abstractmethod
    def status(self) -> GitStatusOps:
        """Access status operations subgateway."""
        ...

    @property
    @abstractmethod
    def rebase(self) -> GitRebaseOps:
        """Access rebase operations subgateway."""
        ...

    @property
    @abstractmethod
    def tag(self) -> GitTagOps:
        """Access tag operations subgateway."""
        ...

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
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
