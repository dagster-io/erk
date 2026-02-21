"""Production implementation of Git commit operations using subprocess."""

import os
import subprocess
import tempfile
from pathlib import Path

from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
from erk_shared.gateway.git.lock import wait_for_index_lock
from erk_shared.gateway.time.abc import Time
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitCommitOps(GitCommitOps):
    """Real implementation of Git commit operations using subprocess."""

    def __init__(self, time: Time) -> None:
        """Initialize RealGitCommitOps with Time provider.

        Args:
            time: Time provider for lock waiting
        """
        self._time = time

    # ============================================================================
    # Mutation Operations
    # ============================================================================

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

    def commit_files_to_branch(
        self,
        cwd: Path,
        *,
        branch: str,
        files: dict[str, str],
        message: str,
    ) -> None:
        """Create a commit on a branch using git plumbing (no checkout)."""
        # Get parent commit SHA
        parent_sha = run_subprocess_with_context(
            cmd=["git", "rev-parse", branch],
            operation_context=f"resolve branch {branch}",
            cwd=cwd,
        ).stdout.strip()

        # Create temporary index file to avoid touching the real index
        tmp_fd, tmp_index = tempfile.mkstemp(suffix=".idx", prefix="erk-plan-")
        os.close(tmp_fd)
        try:
            env = os.environ.copy()
            env["GIT_INDEX_FILE"] = tmp_index

            # Read parent tree into temp index
            run_subprocess_with_context(
                cmd=["git", "read-tree", parent_sha],
                operation_context="read parent tree into temp index",
                cwd=cwd,
                env=env,
            )

            # Hash each file and add to temp index
            for path, content in files.items():
                blob_sha = run_subprocess_with_context(
                    cmd=["git", "hash-object", "-w", "--stdin"],
                    operation_context=f"hash content for {path}",
                    cwd=cwd,
                    input=content,
                ).stdout.strip()

                cacheinfo = f"100644,{blob_sha},{path}"
                run_subprocess_with_context(
                    cmd=["git", "update-index", "--add", "--cacheinfo", cacheinfo],
                    operation_context=f"add {path} to temp index",
                    cwd=cwd,
                    env=env,
                )

            # Write tree from temp index
            tree_sha = run_subprocess_with_context(
                cmd=["git", "write-tree"],
                operation_context="write tree from temp index",
                cwd=cwd,
                env=env,
            ).stdout.strip()

            # Create commit object
            commit_sha = run_subprocess_with_context(
                cmd=["git", "commit-tree", tree_sha, "-p", parent_sha, "-m", message],
                operation_context="create commit on branch",
                cwd=cwd,
            ).stdout.strip()

            # Update branch ref
            run_subprocess_with_context(
                cmd=["git", "update-ref", f"refs/heads/{branch}", commit_sha],
                operation_context=f"update ref for {branch}",
                cwd=cwd,
            )
        finally:
            Path(tmp_index).unlink(missing_ok=True)

    # ============================================================================
    # Query Operations
    # ============================================================================

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
