"""Printing Git status operations wrapper for verbose output.

Since all status operations are read-only queries, this wrapper
simply delegates all calls without printing (read-only ops don't print).
"""

from pathlib import Path

from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.printing.base import PrintingBase


class PrintingGitStatusOps(PrintingBase, GitStatusOps):
    """Pass-through wrapper for status operations with printing support.

    All status operations are read-only queries, so they are delegated
    to the wrapped implementation without printing output.

    Usage:
        printing_ops = PrintingGitStatusOps(real_ops, script_mode=False, dry_run=False)

        # All operations delegate without printing (read-only)
        has_staged = printing_ops.has_staged_changes(repo_root)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # All operations are read-only - delegate without printing
    # ============================================================================

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, no printing)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, no printing)."""
        return self._wrapped.has_uncommitted_changes(cwd)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, no printing)."""
        return self._wrapped.get_file_status(cwd)

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check merge conflicts (read-only, no printing)."""
        return self._wrapped.check_merge_conflicts(cwd, base_branch, head_branch)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get conflicted files (read-only, no printing)."""
        return self._wrapped.get_conflicted_files(cwd)
