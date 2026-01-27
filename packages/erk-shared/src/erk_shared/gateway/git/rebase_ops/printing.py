"""Printing Git rebase operations wrapper for verbose output.

This module provides a wrapper that prints styled output for rebase operations
before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.abc import RebaseResult
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.printing.base import PrintingBase


class PrintingGitRebaseOps(PrintingBase, GitRebaseOps):
    """Wrapper that prints rebase operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Mutation Operations (print before delegating)
    # ============================================================================

    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """Rebase onto target ref with printed output."""
        self._emit(self._format_command(f"git rebase {target_ref}"))
        return self._wrapped.rebase_onto(cwd, target_ref)

    def rebase_continue(self, cwd: Path) -> None:
        """Continue rebase with printed output."""
        self._emit(self._format_command("git rebase --continue"))
        self._wrapped.rebase_continue(cwd)

    def rebase_abort(self, cwd: Path) -> None:
        """Abort rebase with printed output."""
        self._emit(self._format_command("git rebase --abort"))
        self._wrapped.rebase_abort(cwd)

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check if rebase in progress (read-only, no printing)."""
        return self._wrapped.is_rebase_in_progress(cwd)
