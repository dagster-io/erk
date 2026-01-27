"""Printing Git tag operations wrapper for verbose output.

This module provides a wrapper that prints styled output for tag operations
before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.printing.base import PrintingBase


class PrintingGitTagOps(PrintingBase, GitTagOps):
    """Wrapper that prints tag operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_ops = PrintingGitTagOps(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGitTagOps(real_ops)
        printing_ops = PrintingGitTagOps(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if tag exists (read-only, no printing)."""
        return self._wrapped.tag_exists(repo_root, tag_name)

    # ============================================================================
    # Mutation Operations (print before delegating)
    # ============================================================================

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create tag with printed output."""
        self._emit(self._format_command(f"git tag -a {tag_name} -m '{message}'"))
        self._wrapped.create_tag(repo_root, tag_name, message)

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push tag with printed output."""
        self._emit(self._format_command(f"git push {remote} {tag_name}"))
        self._wrapped.push_tag(repo_root, remote, tag_name)
