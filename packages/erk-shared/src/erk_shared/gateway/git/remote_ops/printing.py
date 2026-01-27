"""Printing Git remote operations wrapper for verbose output.

This module provides a wrapper that prints styled output for remote operations
before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.printing.base import PrintingBase


class PrintingGitRemoteOps(PrintingBase, GitRemoteOps):
    """Wrapper that prints remote operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_ops = PrintingGitRemoteOps(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGitRemoteOps(real_ops)
        printing_ops = PrintingGitRemoteOps(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Mutation Operations (print before delegating)
    # ============================================================================

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch branch with printed output."""
        self._emit(self._format_command(f"git fetch {remote} {branch}"))
        self._wrapped.fetch_branch(repo_root, remote, branch)

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull branch with printed output."""
        ff_flag = " --ff-only" if ff_only else ""
        self._emit(self._format_command(f"git pull{ff_flag} {remote} {branch}"))
        self._wrapped.pull_branch(repo_root, remote, branch, ff_only=ff_only)

    def fetch_pr_ref(
        self, *, repo_root: Path, remote: str, pr_number: int, local_branch: str
    ) -> None:
        """Fetch PR ref with printed output."""
        self._emit(self._format_command(f"git fetch {remote} pull/{pr_number}/head:{local_branch}"))
        self._wrapped.fetch_pr_ref(
            repo_root=repo_root, remote=remote, pr_number=pr_number, local_branch=local_branch
        )

    def push_to_remote(
        self,
        cwd: Path,
        remote: str,
        branch: str,
        *,
        set_upstream: bool,
        force: bool,
    ) -> None:
        """Push to remote with printed output."""
        upstream_flag = "-u " if set_upstream else ""
        force_flag = "--force " if force else ""
        self._emit(self._format_command(f"git push {upstream_flag}{force_flag}{remote} {branch}"))
        self._wrapped.push_to_remote(cwd, remote, branch, set_upstream=set_upstream, force=force)

    def pull_rebase(self, cwd: Path, remote: str, branch: str) -> None:
        """Pull with rebase with printed output."""
        self._emit(self._format_command(f"git pull --rebase {remote} {branch}"))
        self._wrapped.pull_rebase(cwd, remote, branch)

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def get_remote_url(self, repo_root: Path, remote: str) -> str:
        """Get remote URL (read-only, no printing)."""
        return self._wrapped.get_remote_url(repo_root, remote)
