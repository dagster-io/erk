"""Fake implementation of Git commit operations for testing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.git.commit_ops.abc import GitCommitOps


@dataclass(frozen=True)
class CommitRecord:
    """Record of a commit operation.

    Attributes:
        cwd: Working directory where commit was made
        message: Commit message
        staged_files: Files that were staged at time of commit
    """

    cwd: Path
    message: str
    staged_files: tuple[str, ...]


class FakeGitCommitOps(GitCommitOps):
    """In-memory fake implementation of Git commit operations.

    This fake accepts pre-configured state in its constructor and tracks
    mutations for test assertions.

    Constructor Injection:
    ---------------------
    - commit_messages: Mapping of commit SHA -> commit message
    - recent_commits: Mapping of cwd -> list of commit info dicts
    - commit_messages_since: Mapping of (cwd, base_branch) -> list of messages
    - head_commit_messages_full: Mapping of cwd -> full HEAD commit message
    - commits_ahead: Mapping of (cwd, base_branch) -> commit count (for updating)
    - add_all_raises: Exception to raise when add_all() is called

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - staged_files: List of file paths staged via stage_files()
    - commits: List of CommitRecord from commit()
    """

    def __init__(
        self,
        *,
        commit_messages: dict[str, str] | None = None,
        recent_commits: dict[Path, list[dict[str, str]]] | None = None,
        commit_messages_since: dict[tuple[Path, str], list[str]] | None = None,
        head_commit_messages_full: dict[Path, str] | None = None,
        commits_ahead: dict[tuple[Path, str], int] | None = None,
        add_all_raises: Exception | None = None,
        dirty_worktrees: set[Path] | None = None,
    ) -> None:
        """Create FakeGitCommitOps with pre-configured state.

        Args:
            commit_messages: Mapping of commit SHA -> commit message
            recent_commits: Mapping of cwd -> list of commit info dicts
            commit_messages_since: Mapping of (cwd, base_branch) -> list of messages
            head_commit_messages_full: Mapping of cwd -> full HEAD commit message
            commits_ahead: Mapping of (cwd, base_branch) -> commit count
            add_all_raises: Exception to raise when add_all() is called
            dirty_worktrees: Set of worktree paths with uncommitted changes
        """
        self._commit_messages = commit_messages if commit_messages is not None else {}
        self._recent_commits = recent_commits if recent_commits is not None else {}
        self._commit_messages_since = (
            commit_messages_since if commit_messages_since is not None else {}
        )
        self._head_commit_messages_full = (
            head_commit_messages_full if head_commit_messages_full is not None else {}
        )
        self._commits_ahead = commits_ahead if commits_ahead is not None else {}
        self._add_all_raises = add_all_raises
        self._dirty_worktrees = dirty_worktrees if dirty_worktrees is not None else set()

        # Mutation tracking
        self._staged_files: list[str] = []
        self._commits: list[CommitRecord] = []

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Record staged files for commit."""
        self._staged_files.extend(paths)

    def commit(self, cwd: Path, message: str) -> None:
        """Record commit with staged changes.

        Also updates commits_ahead for the parent branch if state is tracked.
        """
        self._commits.append(
            CommitRecord(cwd=cwd, message=message, staged_files=tuple(self._staged_files))
        )
        self._staged_files = []  # Clear staged files after commit

        # Update commits_ahead for all tracked parent branches at this cwd
        for (path, base_branch), count in list(self._commits_ahead.items()):
            if path == cwd:
                self._commits_ahead[(cwd, base_branch)] = count + 1

    def add_all(self, cwd: Path) -> None:
        """Stage all changes for commit (git add -A).

        Also clears dirty worktree state since changes are now staged.
        Raises configured exception if add_all_raises was set.
        """
        if self._add_all_raises is not None:
            raise self._add_all_raises
        # Clear dirty state - changes are staged for commit
        self._dirty_worktrees.discard(cwd)

    def amend_commit(self, cwd: Path, message: str) -> None:
        """Amend the current commit with a new message."""
        # In the fake, replace last commit message if commits exist
        if self._commits:
            last_commit = self._commits[-1]
            self._commits[-1] = CommitRecord(
                cwd=last_commit.cwd, message=message, staged_files=last_commit.staged_files
            )
        else:
            # If no commits tracked yet, create one to track the amend
            self._commits.append(CommitRecord(cwd=cwd, message=message, staged_files=()))

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get the commit message for a given commit SHA."""
        return self._commit_messages.get(commit_sha)

    def get_commit_messages_since(self, cwd: Path, base_branch: str) -> list[str]:
        """Get full commit messages for commits in HEAD but not in base_branch."""
        return self._commit_messages_since.get((cwd, base_branch), [])

    def get_head_commit_message_full(self, cwd: Path) -> str:
        """Get the full commit message (subject + body) of HEAD.

        Returns:
            Full commit message from head_commit_messages_full if configured,
            or the message from the most recent commit if commits were created,
            or empty string as fallback.
        """
        # Check configured messages first
        if cwd in self._head_commit_messages_full:
            return self._head_commit_messages_full[cwd]

        # Fallback: return message from most recent commit at this cwd
        for commit_record in reversed(self._commits):
            if commit_record.cwd == cwd:
                return commit_record.message

        return ""

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commit information."""
        commits = self._recent_commits.get(cwd, [])
        return commits[:limit]

    # ============================================================================
    # Mutation Tracking Properties
    # ============================================================================

    @property
    def staged_files(self) -> list[str]:
        """Read-only access to currently staged files for test assertions."""
        return list(self._staged_files)

    @property
    def commits(self) -> list[CommitRecord]:
        """Read-only access to commits for test assertions."""
        return list(self._commits)

    # ============================================================================
    # Link Mutation Tracking (for integration with FakeGit)
    # ============================================================================

    def link_mutation_tracking(
        self,
        *,
        staged_files: list[str],
        commits: list[CommitRecord],
    ) -> None:
        """Link this fake's mutation tracking to FakeGit's tracking lists.

        This allows FakeGit to expose commit operations mutations through its
        own properties while delegating to this subgateway.

        Args:
            staged_files: FakeGit's _staged_files list
            commits: FakeGit's _commits list
        """
        self._staged_files = staged_files
        self._commits = commits

    def link_state(
        self,
        *,
        commits_ahead: dict[tuple[Path, str], int],
        dirty_worktrees: set[Path],
    ) -> None:
        """Link this fake's state to FakeGit's mutable state.

        This allows FakeGit's state to be updated when commit operations
        mutate shared state (like commits_ahead counters).

        Args:
            commits_ahead: FakeGit's _commits_ahead mapping
            dirty_worktrees: FakeGit's _dirty_worktrees set
        """
        self._commits_ahead = commits_ahead
        self._dirty_worktrees = dirty_worktrees
