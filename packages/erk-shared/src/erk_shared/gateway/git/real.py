"""Production Git implementation using subprocess.

This module provides the real Git implementation that executes actual git
commands via subprocess. Located in erk-shared so it can be used by both
the main erk package and erk-kits without circular dependencies.
"""

import os
import subprocess
from pathlib import Path

from erk_shared.gateway.git.abc import Git, RebaseResult
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.branch_ops.real import RealGitBranchOps
from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.gateway.git.commit_ops.real import RealGitCommitOps
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.gateway.git.rebase_ops.real import RealGitRebaseOps
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.real import RealGitRemoteOps
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.real import RealGitStatusOps
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.gateway.git.tag_ops.real import RealGitTagOps
from erk_shared.gateway.git.worktree.abc import Worktree
from erk_shared.gateway.git.worktree.real import RealWorktree
from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGit(Git):
    """Production implementation using subprocess.

    All git operations execute actual git commands via subprocess.
    """

    def __init__(self, time: Time | None = None) -> None:
        """Initialize RealGit with optional Time provider.

        Args:
            time: Time provider for lock waiting. Defaults to RealTime().
        """
        self._time = time if time is not None else RealTime()
        self._worktree = RealWorktree()
        self._branch = RealGitBranchOps(time=self._time)
        self._remote = RealGitRemoteOps(time=self._time)
        self._commit = RealGitCommitOps(time=self._time)
        self._status = RealGitStatusOps()
        # Rebase operations subgateway
        self._rebase_gateway = RealGitRebaseOps(
            get_git_common_dir=self.get_git_common_dir,
            get_conflicted_files=self._status.get_conflicted_files,
        )
        self._tag = RealGitTagOps()

    @property
    def worktree(self) -> Worktree:
        """Access worktree operations subgateway."""
        return self._worktree

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway."""
        return self._branch

    @property
    def remote(self) -> GitRemoteOps:
        """Access remote operations subgateway."""
        return self._remote

    @property
    def commit(self) -> GitCommitOps:
        """Access commit operations subgateway."""
        return self._commit

    @property
    def status(self) -> GitStatusOps:
        """Access status operations subgateway."""
        return self._status

    @property
    def rebase(self) -> GitRebaseOps:
        """Access rebase operations subgateway."""
        return self._rebase_gateway

    @property
    def tag(self) -> GitTagOps:
        """Access tag operations subgateway."""
        return self._tag

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        git_dir = Path(result.stdout.strip())
        if not git_dir.is_absolute():
            git_dir = cwd / git_dir

        return git_dir.resolve()

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{base_branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return 0
        count_str = result.stdout.strip()
        if not count_str:
            return 0
        return int(count_str)

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        result = run_subprocess_with_context(
            cmd=["git", "rev-parse", "--show-toplevel"],
            operation_context="get repository root",
            cwd=cwd,
        )
        return Path(result.stdout.strip())

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD.

        Uses two-dot syntax (branch..HEAD) to compare the actual tree states,
        not the merge-base. This is correct for PR diffs because it shows
        "what will change when merged" rather than "all changes since the
        merge-base" which can include rebased commits with different SHAs.
        """
        result = run_subprocess_with_context(
            cmd=["git", "diff", f"{branch}..HEAD"],
            operation_context=f"get diff to branch '{branch}'",
            cwd=cwd,
        )
        return result.stdout

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str = "local") -> None:
        """Set a git configuration value."""
        run_subprocess_with_context(
            cmd=["git", "config", f"--{scope}", key, value],
            operation_context=f"set git config {key}",
            cwd=cwd,
        )

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name."""
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        name = result.stdout.strip()
        return name if name else None

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
        conflict_files = self.status.get_conflicted_files(cwd)
        return RebaseResult(success=False, conflict_files=tuple(conflict_files))

    def rebase_abort(self, cwd: Path) -> None:
        """Abort an in-progress rebase operation."""
        run_subprocess_with_context(
            cmd=["git", "rebase", "--abort"],
            operation_context="abort rebase",
            cwd=cwd,
        )

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs."""
        result = subprocess.run(
            ["git", "merge-base", ref1, ref2],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
