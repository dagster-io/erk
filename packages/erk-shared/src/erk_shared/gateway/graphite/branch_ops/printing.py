"""Printing Graphite branch operations wrapper for verbose output."""

from pathlib import Path

from erk_shared.gateway.graphite.branch_ops.abc import GraphiteBranchOps
from erk_shared.printing.base import PrintingBase


class PrintingGraphiteBranchOps(PrintingBase, GraphiteBranchOps):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for branch operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_ops = PrintingGraphiteBranchOps(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGraphiteBranchOps(real_ops)
        printing_ops = PrintingGraphiteBranchOps(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Track branch with printed output."""
        self._emit(
            self._format_command(f"gt track --branch {branch_name} --parent {parent_branch}")
        )
        self._wrapped.track_branch(cwd, branch_name, parent_branch)

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete branch with printed output."""
        self._emit(self._format_command(f"gt delete -f {branch}"))
        self._wrapped.delete_branch(repo_root, branch)

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Submit branch with printed output."""
        self._emit(self._format_command(f"gt submit --branch {branch_name} --no-edit"))
        self._wrapped.submit_branch(repo_root, branch_name, quiet=quiet)
