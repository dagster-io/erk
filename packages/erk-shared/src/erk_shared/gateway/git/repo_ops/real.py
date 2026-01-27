"""Real implementation of git repository operations."""

from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitRepoOps(GitRepoOps):
    """Real implementation of Git repository operations using subprocess."""

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        result = run_subprocess_with_context(
            cmd=["git", "rev-parse", "--show-toplevel"],
            operation_context="get repository root",
            cwd=cwd,
        )
        return Path(result.stdout.strip())

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        import subprocess

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
