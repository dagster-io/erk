"""Production Git implementation using subprocess.

This module provides the real Git implementation that executes actual git
commands via subprocess. Located in erk-shared so it can be used by both
the main erk package and erk-kits without circular dependencies.
"""

import os
import subprocess
from pathlib import Path

from erk_shared.gateway.git.abc import Git, RebaseResult
from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps
from erk_shared.gateway.git.analysis_ops.real import RealGitAnalysisOps
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.branch_ops.real import RealGitBranchOps
from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.gateway.git.commit_ops.real import RealGitCommitOps
from erk_shared.gateway.git.config_ops.abc import GitConfigOps
from erk_shared.gateway.git.config_ops.real import RealGitConfigOps
from erk_shared.gateway.git.rebase_ops.abc import GitRebaseOps
from erk_shared.gateway.git.rebase_ops.real import RealGitRebaseOps
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.real import RealGitRemoteOps
from erk_shared.gateway.git.repo_ops.abc import GitRepoOps
from erk_shared.gateway.git.repo_ops.real import RealGitRepoOps
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.real import RealGitStatusOps
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.gateway.git.tag_ops.real import RealGitTagOps
from erk_shared.gateway.git.worktree.abc import Worktree
from erk_shared.gateway.git.worktree.real import RealWorktree
from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime


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
        # New subgateways
        self._repo = RealGitRepoOps()
        self._analysis = RealGitAnalysisOps()
        self._config = RealGitConfigOps()
        # Rebase operations subgateway
        self._rebase_gateway = RealGitRebaseOps(
            get_git_common_dir=self._repo.get_git_common_dir,
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

    @property
    def repo(self) -> GitRepoOps:
        """Access repository location operations subgateway."""
        return self._repo

    @property
    def analysis(self) -> GitAnalysisOps:
        """Access branch analysis operations subgateway."""
        return self._analysis

    @property
    def config(self) -> GitConfigOps:
        """Access configuration operations subgateway."""
        return self._config

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
        from erk_shared.subprocess_utils import run_subprocess_with_context

        run_subprocess_with_context(
            cmd=["git", "rebase", "--abort"],
            operation_context="abort rebase",
            cwd=cwd,
        )
