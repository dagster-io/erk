"""No-op GitWorktrees wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktrees.abc import GitWorktrees
from erk_shared.output.output import user_output


class DryRunGitWorktrees(GitWorktrees):
    """No-op wrapper that prevents execution of destructive operations."""

    def __init__(self, wrapped: GitWorktrees) -> None:
        self._wrapped = wrapped

    # Read-only: delegate
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        return self._wrapped.list_worktrees(repo_root)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        return self._wrapped.get_git_common_dir(cwd)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    # Write operations: print dry-run message
    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        if branch and create_branch:
            base_ref = ref or "HEAD"
            user_output(f"[DRY RUN] Would run: git worktree add -b {branch} {path} {base_ref}")
        elif branch:
            user_output(f"[DRY RUN] Would run: git worktree add {path} {branch}")
        else:
            base_ref = ref or "HEAD"
            user_output(f"[DRY RUN] Would run: git worktree add {path} {base_ref}")

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        user_output(f"[DRY RUN] Would run: git worktree move {old_path} {new_path}")

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        force_flag = "--force " if force else ""
        user_output(f"[DRY RUN] Would run: git worktree remove {force_flag}{path}")

    def prune_worktrees(self, repo_root: Path) -> None:
        user_output("[DRY RUN] Would run: git worktree prune")
