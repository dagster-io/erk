"""High-level git operations interface.

This module provides a clean abstraction over git subprocess calls, making the
codebase more testable and maintainable.

Architecture:
- Git: Abstract base class defining the interface
- RealGit: Production implementation using subprocess
- Standalone functions: Convenience wrappers delegating to module singleton
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


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

    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository."""
        ...

    @abstractmethod
    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        ...

    @abstractmethod
    def detect_default_branch(self, repo_root: Path, configured: str | None = None) -> str:
        """Detect the default branch (main or master).

        Args:
            repo_root: Path to the repository root
            configured: Optional configured trunk branch name. If provided, validates
                       that this branch exists. If None, uses auto-detection.

        Returns:
            The trunk branch name

        Raises:
            SystemExit: If configured branch doesn't exist or no trunk can be detected
        """
        ...

    @abstractmethod
    def get_trunk_branch(self, repo_root: Path) -> str:
        """Get the trunk branch name for the repository.

        Detects trunk by checking git's remote HEAD reference. Falls back to
        checking for existence of common trunk branch names if detection fails.

        Args:
            repo_root: Path to the repository root

        Returns:
            Trunk branch name (e.g., 'main', 'master')
        """
        ...

    @abstractmethod
    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository.

        Args:
            repo_root: Path to the repository root

        Returns:
            List of local branch names
        """
        ...

    @abstractmethod
    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository.

        Returns branch names in format 'origin/branch-name', 'upstream/feature', etc.
        Only includes refs from configured remotes, not local branches.

        Args:
            repo_root: Path to the repository root

        Returns:
            List of remote branch names with remote prefix (e.g., 'origin/main')
        """
        ...

    @abstractmethod
    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch.

        Args:
            repo_root: Path to the repository root
            branch: Name for the local branch (e.g., 'feature-remote')
            remote_ref: Remote reference to track (e.g., 'origin/feature-remote')

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
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
    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree has no uncommitted changes, staged changes, or untracked files.

        Args:
            worktree_path: Path to the worktree to check

        Returns:
            True if worktree is clean (no uncommitted, staged, or untracked files)
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
    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        ...

    @abstractmethod
    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref (commit SHA, branch, etc)."""
        ...

    @abstractmethod
    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create a new branch without checking it out.

        Args:
            cwd: Working directory to run command in
            branch_name: Name of the branch to create
            start_point: Commit/branch to base the new branch on
        """
        ...

    @abstractmethod
    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch.

        Args:
            cwd: Working directory to run command in
            branch_name: Name of the branch to delete
            force: Use -D (force delete) instead of -d
        """
        ...

    @abstractmethod
    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Delete a branch using Graphite's gt delete command."""
        ...

    @abstractmethod
    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata."""
        ...

    @abstractmethod
    def path_exists(self, path: Path) -> bool:
        """Check if a path exists on the filesystem.

        This is primarily used for checking if worktree directories still exist,
        particularly after cleanup operations. In production (RealGit), this
        delegates to Path.exists(). In tests (FakeGit), this checks an in-memory
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
        and .git files (worktrees with gitdir pointers). In production (RealGit),
        this delegates to Path.is_dir(). In tests (FakeGit), this checks an
        in-memory set of directory paths to avoid filesystem I/O.

        Args:
            path: Path to check

        Returns:
            True if path is a directory, False otherwise
        """
        ...

    @abstractmethod
    def safe_chdir(self, path: Path) -> bool:
        """Change current directory if path exists on real filesystem.

        Used when removing worktrees or switching contexts to prevent shell from
        being in a deleted directory. In production (RealGit), checks if path
        exists then changes directory. In tests (FakeGit), handles sentinel
        paths by returning False without changing directory.

        Args:
            path: Directory to change to

        Returns:
            True if directory change succeeded, False otherwise
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
    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch.

        Args:
            repo_root: Path to the git repository root
            branch: Branch name to query

        Returns:
            Commit SHA as a string, or None if branch doesn't exist.
        """
        ...

    @abstractmethod
    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get the commit message for a given commit SHA.

        Args:
            repo_root: Path to the git repository root
            commit_sha: Commit SHA to query

        Returns:
            First line of commit message, or None if commit doesn't exist.
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
    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch.

        Args:
            cwd: Working directory
            branch: Current branch name

        Returns:
            Tuple of (ahead, behind) counts
        """
        ...

    @abstractmethod
    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get sync status for all local branches in a single git call.

        Uses git for-each-ref to batch-fetch upstream tracking information.

        Args:
            repo_root: Path to the git repository root

        Returns:
            Dict mapping branch name to BranchSyncInfo.
        """
        ...

    @abstractmethod
    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commit information.

        Args:
            cwd: Working directory
            limit: Maximum number of commits to retrieve

        Returns:
            List of commit info dicts with keys: sha, message, author, date
        """
        ...

    @abstractmethod
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote.

        Args:
            repo_root: Path to the git repository root
            remote: Remote name (e.g., "origin")
            branch: Branch name to fetch
        """
        ...

    @abstractmethod
    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote.

        Args:
            repo_root: Path to the git repository root
            remote: Remote name (e.g., "origin")
            branch: Branch name to pull
            ff_only: If True, use --ff-only to prevent merge commits
        """
        ...

    @abstractmethod
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote.

        Args:
            repo_root: Path to the git repository root
            remote: Remote name (e.g., "origin")
            branch: Branch name to check

        Returns:
            True if branch exists on remote, False otherwise
        """
        ...

    @abstractmethod
    def set_branch_issue(self, repo_root: Path, branch: str, issue_number: int) -> None:
        """Associate a GitHub issue number with a branch via git config.

        Stores the issue number in git config at branch.<branch>.issue.
        This association persists even if worktree is removed and recreated.

        Args:
            repo_root: Path to the git repository root
            branch: Branch name to associate with issue
            issue_number: GitHub issue number
        """
        ...

    @abstractmethod
    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Get GitHub issue number associated with a branch from git config.

        Reads the issue number from git config at branch.<branch>.issue.

        Args:
            repo_root: Path to the git repository root
            branch: Branch name to lookup

        Returns:
            Issue number if set, None otherwise
        """
        ...

    @abstractmethod
    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """Fetch a PR ref into a local branch.

        Uses GitHub's special refs/pull/<number>/head reference to fetch
        the PR head commit and create a local branch tracking it.

        Command: git fetch <remote> pull/<number>/head:<local_branch>

        Args:
            repo_root: Path to the git repository root
            remote: Remote name (e.g., "origin")
            pr_number: GitHub PR number
            local_branch: Name for the local branch to create

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Stage specific files for commit.

        Args:
            cwd: Working directory
            paths: List of file paths to stage (relative to cwd)

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def commit(self, cwd: Path, message: str, *, allow_empty: bool = False) -> None:
        """Create a commit with staged changes.

        Args:
            cwd: Working directory
            message: Commit message
            allow_empty: If True, allow creating a commit with no changes (--allow-empty)

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """Push a branch to a remote.

        Args:
            cwd: Working directory
            remote: Remote name (e.g., "origin")
            branch: Branch name to push
            set_upstream: If True, set upstream tracking (-u flag)

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...
