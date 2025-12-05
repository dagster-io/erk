"""Printing GitWorktrees wrapper for verbose output."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktrees.abc import GitWorktrees
from erk_shared.printing.base import PrintingBase


class PrintingGitWorktrees(PrintingBase, GitWorktrees):
    """Wrapper that prints operations before delegating."""

    # Read-only: delegate without printing
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        return self._wrapped.list_worktrees(repo_root)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        return self._wrapped.get_git_common_dir(cwd)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    # Write operations: delegate without printing (not used in land-stack)
    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        self._wrapped.add_worktree(
            repo_root, path, branch=branch, ref=ref, create_branch=create_branch
        )

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        self._wrapped.move_worktree(repo_root, old_path, new_path)

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        self._wrapped.remove_worktree(repo_root, path, force=force)

    def prune_worktrees(self, repo_root: Path) -> None:
        self._wrapped.prune_worktrees(repo_root)
