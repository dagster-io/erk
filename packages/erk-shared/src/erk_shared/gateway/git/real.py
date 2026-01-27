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
from erk_shared.gateway.git.lock import wait_for_index_lock
from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
from erk_shared.gateway.git.remote_ops.real import RealGitRemoteOps
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

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check if the repository has staged changes."""
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode in (0, 1):
            return result.returncode == 1
        result.check_returncode()
        return False

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        return bool(result.stdout.strip())

    def get_commit_message(self, repo_root: Path, commit_sha: str) -> str | None:
        """Get the first line of commit message for a given commit SHA."""
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s", commit_sha],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        return result.stdout.strip()

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files."""
        result = run_subprocess_with_context(
            cmd=["git", "status", "--porcelain"],
            operation_context="get file status",
            cwd=cwd,
        )

        staged = []
        modified = []
        untracked = []

        for line in result.stdout.splitlines():
            if not line:
                continue

            status_code = line[:2]
            filename = line[3:]

            # Check if file is staged (first character is not space)
            if status_code[0] != " " and status_code[0] != "?":
                staged.append(filename)

            # Check if file is modified (second character is not space)
            if status_code[1] != " " and status_code[1] != "?":
                modified.append(filename)

            # Check if file is untracked
            if status_code == "??":
                untracked.append(filename)

        return staged, modified, untracked

    def get_recent_commits(self, cwd: Path, *, limit: int = 5) -> list[dict[str, str]]:
        """Get recent commit information."""
        result = run_subprocess_with_context(
            cmd=[
                "git",
                "log",
                f"-{limit}",
                "--format=%H%x00%s%x00%an%x00%ar",
            ],
            operation_context=f"get recent {limit} commits",
            cwd=cwd,
        )

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\x00")
            if len(parts) == 4:
                commits.append(
                    {
                        "sha": parts[0][:7],  # Short SHA
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                    }
                )

        return commits

    def stage_files(self, cwd: Path, paths: list[str]) -> None:
        """Stage specific files for commit."""
        # Wait for index lock if another git operation is in progress
        wait_for_index_lock(cwd, self._time)

        run_subprocess_with_context(
            cmd=["git", "add", *paths],
            operation_context=f"stage files: {', '.join(paths)}",
            cwd=cwd,
        )

    def commit(self, cwd: Path, message: str) -> None:
        """Create a commit with staged changes."""
        # Wait for index lock if another git operation is in progress
        wait_for_index_lock(cwd, self._time)

        run_subprocess_with_context(
            cmd=["git", "commit", "--allow-empty", "-m", message],
            operation_context="create commit",
            cwd=cwd,
        )

    def add_all(self, cwd: Path) -> None:
        """Stage all changes for commit (git add -A)."""
        run_subprocess_with_context(
            cmd=["git", "add", "-A"],
            operation_context="stage all changes",
            cwd=cwd,
        )

    def amend_commit(self, cwd: Path, message: str) -> None:
        """Amend the current commit with a new message."""
        run_subprocess_with_context(
            cmd=["git", "commit", "--amend", "-m", message],
            operation_context="amend commit",
            cwd=cwd,
        )

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

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree."""
        result = subprocess.run(
            ["git", "merge-tree", "--write-tree", base_branch, head_branch],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode != 0

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Parse git status --porcelain for UU/AA/DD/AU/UA/DU/UD status codes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        conflict_codes = {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
        conflicted = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            if status in conflict_codes:
                # File path starts at position 3
                conflicted.append(line[3:])
        return conflicted

    def is_rebase_in_progress(self, cwd: Path) -> bool:
        """Check for .git/rebase-merge or .git/rebase-apply directories."""
        git_common_dir = self.get_git_common_dir(cwd)
        if git_common_dir is None:
            return False
        rebase_merge = git_common_dir / "rebase-merge"
        rebase_apply = git_common_dir / "rebase-apply"
        return rebase_merge.exists() or rebase_apply.exists()

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

    def get_commit_messages_since(self, cwd: Path, base_branch: str) -> list[str]:
        """Get full commit messages for commits in HEAD but not in base_branch."""
        separator = "---COMMIT_SEP---"
        result = subprocess.run(
            ["git", "log", "--reverse", f"--format=%B{separator}", f"{base_branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        return [msg.strip() for msg in result.stdout.split(separator) if msg.strip()]

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str = "local") -> None:
        """Set a git configuration value."""
        run_subprocess_with_context(
            cmd=["git", "config", f"--{scope}", key, value],
            operation_context=f"set git config {key}",
            cwd=cwd,
        )

    def get_head_commit_message_full(self, cwd: Path) -> str:
        """Get the full commit message of HEAD."""
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

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

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists."""
        result = subprocess.run(
            ["git", "tag", "-l", tag_name],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return tag_name in result.stdout.strip().split("\n")

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag."""
        run_subprocess_with_context(
            cmd=["git", "tag", "-a", tag_name, "-m", message],
            operation_context=f"create tag '{tag_name}'",
            cwd=repo_root,
        )

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote."""
        run_subprocess_with_context(
            cmd=["git", "push", remote, tag_name],
            operation_context=f"push tag '{tag_name}' to remote '{remote}'",
            cwd=repo_root,
        )

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
        conflict_files = self.get_conflicted_files(cwd)
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
