"""No-op Git worktree operations wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktree.abc import Worktree
from erk_shared.output.output import user_output


class DryRunWorktree(Worktree):
    """No-op wrapper that prevents execution of worktree operations.

    This wrapper intercepts worktree operations and either returns without
    executing or prints what would happen.

    Usage:
        real_worktree = RealWorktree()
        noop_worktree = DryRunWorktree(real_worktree)

        # Prints message instead of adding worktree
        noop_worktree.add_worktree(repo_root, path, branch="feature", ref=None, create_branch=True)
    """

    def __init__(self, wrapped: Worktree) -> None:
        """Create a dry-run wrapper around a Worktree implementation.

        Args:
            wrapped: The Worktree implementation to wrap (usually RealWorktree)
        """
        self._wrapped = wrapped

    # Read-only operations: delegate to wrapped implementation

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List worktrees (read-only, delegates to wrapped)."""
        return self._wrapped.list_worktrees(repo_root)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree for branch (read-only, delegates to wrapped)."""
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if branch is checked out (read-only, delegates to wrapped)."""
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def is_worktree_clean(self, worktree_path: Path) -> bool:
        """Check if worktree is clean (read-only, delegates to wrapped)."""
        return self._wrapped.is_worktree_clean(worktree_path)

    def path_exists(self, path: Path) -> bool:
        """Check if path exists (read-only, delegates to wrapped)."""
        return self._wrapped.path_exists(path)

    def is_dir(self, path: Path) -> bool:
        """Check if path is directory (read-only, delegates to wrapped)."""
        return self._wrapped.is_dir(path)

    # Write operations: print dry-run message instead of executing

    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Print dry-run message instead of adding worktree."""
        if branch and create_branch:
            base_ref = ref or "HEAD"
            user_output(f"[DRY RUN] Would run: git worktree add -b {branch} {path} {base_ref}")
        elif branch:
            user_output(f"[DRY RUN] Would run: git worktree add {path} {branch}")
        else:
            base_ref = ref or "HEAD"
            user_output(f"[DRY RUN] Would run: git worktree add {path} {base_ref}")

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Print dry-run message instead of moving worktree."""
        user_output(f"[DRY RUN] Would run: git worktree move {old_path} {new_path}")

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Print dry-run message instead of removing worktree."""
        force_flag = "--force " if force else ""
        user_output(f"[DRY RUN] Would run: git worktree remove {force_flag}{path}")

    def prune_worktrees(self, repo_root: Path) -> None:
        """Print dry-run message instead of pruning worktrees."""
        user_output("[DRY RUN] Would run: git worktree prune")

    def safe_chdir(self, path: Path) -> bool:
        """Print dry-run message instead of changing directory."""
        would_succeed = self.path_exists(path)
        if would_succeed:
            user_output(f"[DRY RUN] Would run: cd {path}")
        return False  # Never actually change directory in dry-run
