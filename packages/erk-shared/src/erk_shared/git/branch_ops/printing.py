"""Printing Git branch operations wrapper for verbose output."""

from pathlib import Path

from erk_shared.git.branch_ops.abc import GitBranchOps
from erk_shared.printing.base import PrintingBase


class PrintingGitBranchOps(PrintingBase, GitBranchOps):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for branch operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_ops = PrintingGitBranchOps(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGitBranchOps(real_ops)
        printing_ops = PrintingGitBranchOps(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create branch (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.create_branch(cwd, branch_name, start_point)

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete branch (delegates without printing for now)."""
        # Not used in land-stack
        self._wrapped.delete_branch(cwd, branch_name, force=force)

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout branch with printed output."""
        self._emit(self._format_command(f"git checkout {branch}"))
        self._wrapped.checkout_branch(cwd, branch)

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout detached HEAD (delegates without printing for now)."""
        # No printing for detached HEAD in land-stack
        self._wrapped.checkout_detached(cwd, ref)

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create tracking branch (delegates without printing for now)."""
        self._wrapped.create_tracking_branch(repo_root, branch, remote_ref)
