"""Real implementation of git repository operations."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps


class RealGitRepoOps(GitRepoOps):
    """Real implementation of Git repository operations using subprocess."""

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())

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
        git_common_dir = result.stdout.strip()
        # Handle relative paths returned by git
        if not Path(git_common_dir).is_absolute():
            return (cwd / git_common_dir).resolve()
        return Path(git_common_dir)
