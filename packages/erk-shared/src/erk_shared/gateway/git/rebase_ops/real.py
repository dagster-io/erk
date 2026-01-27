"""Production implementation of Git rebase operations using subprocess."""

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from erk_shared.gateway.git.abc import RebaseResult
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitRebaseOps(GitRebaseOps):
    """Real implementation of Git rebase operations using subprocess."""

    def __init__(self, get_git_common_dir: Callable, get_conflicted_files: Callable) -> None:
        """Initialize RealGitRebaseOps with helper functions.

        Args:
            get_git_common_dir: Function to get git common directory for worktree support
            get_conflicted_files: Function to get list of conflicted files
        """
        self._get_git_common_dir = get_git_common_dir
        self._get_conflicted_files = get_conflicted_files

    def rebase_onto(self, cwd: Path, target_ref: str) -> RebaseResult:
        """Rebase the current branch onto a target ref."""
        result = subprocess.run(
            ["git", "rebase", target_ref],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GIT_EDITOR": "true"},  # Auto-accept commit messages
        )

        if result.returncode == 0:
            return RebaseResult(success=True, conflict_files=())

        # Rebase failed - get conflict files
        conflict_files = self._get_conflicted_files(cwd)
        return RebaseResult(success=False, conflict_files=tuple(conflict_files))

    def rebase_continue(self, cwd: Path) -> None:
        """Run git rebase --continue."""
        subprocess.run(
            ["git", "rebase", "--continue"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_EDITOR": "true"},  # Auto-accept commit messages
        )

    def rebase_abort(self, cwd: Path) -> None:
        """Abort an in-progress rebase operation."""
        run_subprocess_with_context(
            cmd=["git", "rebase", "--abort"],
            operation_context="abort rebase",
            cwd=cwd,
        )

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check for .git/rebase-merge or .git/rebase-apply directories."""
        git_common_dir = self._get_git_common_dir(cwd)
        if git_common_dir is None:
            return False
        rebase_merge = git_common_dir / "rebase-merge"
        rebase_apply = git_common_dir / "rebase-apply"
        return rebase_merge.exists() or rebase_apply.exists()
