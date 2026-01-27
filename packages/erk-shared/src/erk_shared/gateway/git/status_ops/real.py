"""Production implementation of Git status operations using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitStatusOps(GitStatusOps):
    """Real implementation of Git status operations using subprocess."""

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
