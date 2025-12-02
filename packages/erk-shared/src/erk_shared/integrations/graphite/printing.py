"""Printing wrapper for Graphite operations."""

from pathlib import Path

from erk_shared.git.abc import Git
from erk_shared.github.types import GitHubRepoId, PullRequestInfo
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.types import BranchMetadata
from erk_shared.printing.base import PrintingBase


class PrintingGraphite(PrintingBase, Graphite):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or Noop).

    Usage:
        # For production
        printing_ops = PrintingGraphite(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGraphite(real_ops)
        printing_ops = PrintingGraphite(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # Read-only operations: delegate without printing

    def get_graphite_url(self, repo_id: GitHubRepoId, pr_number: int) -> str:
        """Get Graphite URL (read-only, no printing)."""
        return self._wrapped.get_graphite_url(repo_id, pr_number)

    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Get PRs from Graphite (read-only, no printing)."""
        return self._wrapped.get_prs_from_graphite(git_ops, repo_root)

    def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all branches (read-only, no printing)."""
        return self._wrapped.get_all_branches(git_ops, repo_root)

    def get_branch_stack(self, git_ops: Git, repo_root: Path, branch: str) -> list[str] | None:
        """Get branch stack (read-only, no printing)."""
        return self._wrapped.get_branch_stack(git_ops, repo_root, branch)

    def get_parent_branch(self, git_ops: Git, repo_root: Path, branch: str) -> str | None:
        """Get parent branch (read-only, no printing)."""
        return self._wrapped.get_parent_branch(git_ops, repo_root, branch)

    # Operations that need printing

    def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
        """Sync with printed output."""
        cmd = "gt sync -f" if force else "gt sync"
        self._emit(self._format_command(cmd))
        self._wrapped.sync(repo_root, force=force, quiet=quiet)

    def restack(self, repo_root: Path, *, no_interactive: bool, quiet: bool) -> None:
        """Restack with printed output."""
        cmd = "gt restack --no-interactive" if no_interactive else "gt restack"
        self._emit(self._format_command(cmd))
        self._wrapped.restack(repo_root, no_interactive=no_interactive, quiet=quiet)

    def track_branch(self, cwd: Path, branch_name: str, parent_branch: str) -> None:
        """Track branch with printed output."""
        self._emit(
            self._format_command(f"gt track --branch {branch_name} --parent {parent_branch}")
        )
        self._wrapped.track_branch(cwd, branch_name, parent_branch)

    def submit_branch(self, repo_root: Path, branch_name: str, *, quiet: bool) -> None:
        """Submit branch with printed output."""
        self._emit(self._format_command(f"gt submit --branch {branch_name} --no-edit"))
        self._wrapped.submit_branch(repo_root, branch_name, quiet=quiet)
