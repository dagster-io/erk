"""Printing Git commit operations wrapper for verbose output.

This module provides a wrapper that prints styled output for commit operations
before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.printing.base import PrintingBase


class PrintingGitCommitOps(PrintingBase, GitCommitOps):
    """Wrapper that prints commit operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_ops = PrintingGitCommitOps(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGitCommitOps(real_ops)
        printing_ops = PrintingGitCommitOps(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Mutation Operations (print before delegating)
    # ============================================================================

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Stage files with printed output."""
        self._emit(self._format_command(f"git add {' '.join(paths)}"))
        self._wrapped.stage_files(cwd, paths)

    def commit(self, cwd: Path, message: str) -> None:
        """Commit with printed output."""
        # Truncate message for display
        display_msg = message[:50] + "..." if len(message) > 50 else message
        self._emit(self._format_command(f'git commit --allow-empty -m "{display_msg}"'))
        self._wrapped.commit(cwd, message)

    def add_all(self, cwd: Path) -> None:
        """Stage all changes with printed output."""
        self._emit(self._format_command("git add -A"))
        self._wrapped.add_all(cwd)

    def amend_commit(self, cwd: Path, message: str) -> None:
        """Amend commit with printed output."""
        display_msg = message[:50] + "..." if len(message) > 50 else message
        self._emit(self._format_command(f'git commit --amend -m "{display_msg}"'))
        self._wrapped.amend_commit(cwd, message)

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get commit message (read-only, no printing)."""
        return self._wrapped.get_commit_message(repo_root, commit_sha)

    def get_commit_messages_since(self, cwd: Path, base_branch: str) -> list[str]:
        """Get commit messages since base branch (read-only, no printing)."""
        return self._wrapped.get_commit_messages_since(cwd, base_branch)

    def get_head_commit_message_full(self, cwd: Path) -> str:
        """Get full commit message (read-only, no printing)."""
        return self._wrapped.get_head_commit_message_full(cwd)

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commits (read-only, no printing)."""
        return self._wrapped.get_recent_commits(cwd, limit=limit)
