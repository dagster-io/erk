"""Git status collector."""

from pathlib import Path

from erk.core.context import ErkContext
from erk.status.collectors.base import StatusCollector
from erk.status.models.status_data import CommitInfo, GitStatus


class GitStatusCollector(StatusCollector):
    """Collects git repository status information."""

    @property
    def name(self) -> str:
        """Name identifier for this collector."""
        return "git"

    def is_available(self, ctx: ErkContext, worktree_path: Path) -> bool:
        """Check if git operations are available.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree

        Returns:
            True if worktree exists and has git
        """
        if not worktree_path.exists():
            return False

        return True

    def collect(self, ctx: ErkContext, worktree_path: Path, repo_root: Path) -> GitStatus | None:
        """Collect git status information.

        Args:
            ctx: Erk context
            worktree_path: Path to worktree
            repo_root: Repository root path

        Returns:
            GitStatus with repository information or None if collection fails
        """
        branch = ctx.git.branch.get_current_branch(worktree_path)
        if branch is None:
            return None

        # Get git status
        staged, modified, untracked = ctx.git.get_file_status(worktree_path)
        clean = len(staged) == 0 and len(modified) == 0 and len(untracked) == 0

        # Get ahead/behind counts
        ahead, behind = ctx.git.branch.get_ahead_behind(worktree_path, branch)

        # Get recent commits
        commit_dicts = ctx.git.get_recent_commits(worktree_path, limit=5)
        recent_commits = [
            CommitInfo(
                sha=c["sha"],
                message=c["message"],
                author=c["author"],
                date=c["date"],
            )
            for c in commit_dicts
        ]

        return GitStatus(
            branch=branch,
            clean=clean,
            ahead=ahead,
            behind=behind,
            staged_files=staged,
            modified_files=modified,
            untracked_files=untracked,
            recent_commits=recent_commits,
        )
