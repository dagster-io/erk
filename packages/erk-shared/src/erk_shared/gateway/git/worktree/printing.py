"""Printing Git worktree operations wrapper for verbose output."""

from pathlib import Path

from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.worktree.abc import Worktree
from erk_shared.printing.base import PrintingBase


class PrintingWorktree(PrintingBase, Worktree):
    """Wrapper that prints operations before delegating to inner implementation.

    This wrapper prints styled output for worktree operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_wt = PrintingWorktree(real_wt, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunWorktree(real_wt)
        printing_wt = PrintingWorktree(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # Read-only operations: delegate without printing

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List worktrees (read-only, no printing)."""
        return self._wrapped.list_worktrees(repo_root)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree for branch (read-only, no printing)."""
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if branch is checked out (read-only, no printing)."""
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree is clean (read-only, no printing)."""
        return self._wrapped.is_worktree_clean(worktree_path)

    def path_exists(self, path: Path) -> bool:
        """Check if path exists (read-only, no printing)."""
        return self._wrapped.path_exists(path)

    def is_dir(self, path: Path) -> bool:
        """Check if path is directory (read-only, no printing)."""
        return self._wrapped.is_dir(path)

    # Write operations: print, then delegate

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Add worktree with printed output."""
        if branch and create_branch:
            base_ref = ref or "HEAD"
            self._emit(self._format_command(f"git worktree add -b {branch} {path} {base_ref}"))
        elif branch:
            self._emit(self._format_command(f"git worktree add {path} {branch}"))
        else:
            base_ref = ref or "HEAD"
            self._emit(self._format_command(f"git worktree add {path} {base_ref}"))
        self._wrapped.add_worktree(
            repo_root, path, branch=branch, ref=ref, create_branch=create_branch
        )

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move worktree with printed output."""
        self._emit(self._format_command(f"git worktree move {old_path} {new_path}"))
        self._wrapped.move_worktree(repo_root, old_path, new_path)

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove worktree with printed output."""
        force_flag = "--force " if force else ""
        self._emit(self._format_command(f"git worktree remove {force_flag}{path}"))
        self._wrapped.remove_worktree(repo_root, path, force=force)

    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune worktrees with printed output."""
        self._emit(self._format_command("git worktree prune"))
        self._wrapped.prune_worktrees(repo_root)

    def safe_chdir(self, path: Path) -> bool:
        """Change directory with printed output."""
        self._emit(self._format_command(f"cd {path}"))
        return self._wrapped.safe_chdir(path)
