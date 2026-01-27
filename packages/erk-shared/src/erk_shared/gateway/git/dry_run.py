"""No-op Git wrapper for dry-run mode.

This module provides a Git wrapper that prevents execution of destructive
operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.abc import Git, RebaseResult
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.branch_ops.dry_run import DryRunGitBranchOps
from erk_shared.gateway.git.worktree.abc import Worktree
from erk_shared.gateway.git.worktree.dry_run import DryRunWorktree
from erk_shared.output.output import user_output

# ============================================================================
# No-op Wrapper
# ============================================================================


class DryRunGit(Git):
    """No-op wrapper that prevents execution of destructive operations.

    This wrapper intercepts destructive git operations and either returns without
    executing (for land-stack operations) or prints what would happen (for other
    operations). Read-only operations are delegated to the wrapped implementation.

    Worktree operations are handled by the DryRunWorktree subgateway, accessible
    via the worktree property.

    Usage:
        real_ops = RealGit()
        noop_ops = DryRunGit(real_ops)

        # Worktree operations go through subgateway
        noop_ops.worktree.remove_worktree(repo_root, path, force=False)
    """

    def __init__(self, wrapped: Git) -> None:
        """Create a dry-run wrapper around a Git implementation.

        Args:
            wrapped: The Git implementation to wrap (usually RealGit or FakeGit)
        """
        self._wrapped = wrapped

    @property
    def worktree(self) -> Worktree:
        """Access worktree operations subgateway (wrapped with DryRunWorktree)."""
        return DryRunWorktree(self._wrapped.worktree)

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway (wrapped with DryRunGitBranchOps)."""
        return DryRunGitBranchOps(self._wrapped.branch)

    # Read-only operations: delegate to wrapped implementation

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get git common directory (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_common_dir(cwd)

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_uncommitted_changes(cwd)

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get commit message (read-only, delegates to wrapped)."""
        return self._wrapped.get_commit_message(repo_root, commit_sha)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, delegates to wrapped)."""
        return self._wrapped.get_file_status(cwd)

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commits (read-only, delegates to wrapped)."""
        return self._wrapped.get_recent_commits(cwd, limit=limit)

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """No-op for fetching branch in dry-run mode."""
        # Do nothing - prevents actual fetch execution
        pass

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """No-op for pulling branch in dry-run mode."""
        # Do nothing - prevents actual pull execution
        pass

    def fetch_pr_ref(
        self, *, repo_root: Path, remote: str, pr_number: int, local_branch: str
    ) -> None:
        """No-op for fetching PR ref in dry-run mode."""
        # Do nothing - prevents actual fetch execution
        pass

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """No-op for staging files in dry-run mode."""
        # Do nothing - prevents actual file staging
        pass

    def commit(self, cwd: Path, message: str) -> None:
        """No-op for committing in dry-run mode."""
        # Do nothing - prevents actual commit creation
        pass

    def push_to_remote(
        self,
        cwd: Path,
        remote: str,
        branch: str,
        *,
        set_upstream: bool = False,
        force: bool = False,
    ) -> None:
        """No-op for pushing in dry-run mode."""
        # Do nothing - prevents actual push execution
        pass

    def add_all(self, cwd: Path) -> None:
        """No-op for staging all changes in dry-run mode."""
        # Do nothing - prevents actual staging
        pass

    def amend_commit(self, cwd: Path, message: str) -> None:
        """No-op for amending commit in dry-run mode."""
        # Do nothing - prevents actual commit amendment
        pass

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits ahead (read-only, delegates to wrapped)."""
        return self._wrapped.count_commits_ahead(cwd, base_branch)

    def get_repository_root(self, cwd: Path) -> Path:
        """Get repository root (read-only, delegates to wrapped)."""
        return self._wrapped.get_repository_root(cwd)

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff to branch (read-only, delegates to wrapped)."""
        return self._wrapped.get_diff_to_branch(cwd, branch)

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check merge conflicts (read-only, delegates to wrapped)."""
        return self._wrapped.check_merge_conflicts(cwd, base_branch, head_branch)

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get remote URL (read-only, delegates to wrapped)."""
        return self._wrapped.get_remote_url(repo_root, remote)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get conflicted files (read-only, delegates to wrapped)."""
        return self._wrapped.get_conflicted_files(cwd)

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check if rebase in progress (read-only, delegates to wrapped)."""
        return self._wrapped.is_rebase_in_progress(cwd)

    def rebase_continue(self, cwd: Path) -> None:
        """No-op for continuing rebase in dry-run mode."""
        # Do nothing - prevents actual rebase continue
        pass

    def get_commit_messages_since(self, cwd: Path, base_branch: str) -> list[str]:
        """Get commit messages since base branch (read-only, delegates to wrapped)."""
        return self._wrapped.get_commit_messages_since(cwd, base_branch)

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str = "local") -> None:
        """No-op for setting git config in dry-run mode."""
        pass

    def get_head_commit_message_full(self, cwd: Path) -> str:
        """Get full commit message (read-only, delegates to wrapped)."""
        return self._wrapped.get_head_commit_message_full(cwd)

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get git user.name (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_user_name(cwd)

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if tag exists (read-only, delegates to wrapped)."""
        return self._wrapped.tag_exists(repo_root, tag_name)

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Print dry-run message instead of creating tag."""
        user_output(f"[DRY RUN] Would run: git tag -a {tag_name} -m '{message}'")

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Print dry-run message instead of pushing tag."""
        user_output(f"[DRY RUN] Would run: git push {remote} {tag_name}")

    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """No-op for rebase in dry-run mode. Returns success."""
        return RebaseResult(success=True, conflict_files=())

    def rebase_abort(self, cwd: Path) -> None:
        """No-op for rebase abort in dry-run mode."""
        pass

    def pull_rebase(self, cwd: Path, remote: str, branch: str) -> None:
        """No-op for pull --rebase in dry-run mode."""
        pass

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get merge base (read-only, delegates to wrapped)."""
        return self._wrapped.get_merge_base(repo_root, ref1, ref2)
