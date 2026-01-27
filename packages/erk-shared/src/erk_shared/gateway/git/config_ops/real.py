"""Real implementation of git configuration operations."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.config_ops.abc import GitConfigOps


class RealGitConfigOps(GitConfigOps):
    """Real implementation of Git configuration operations using subprocess."""

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Set a git configuration value."""
        subprocess.run(
            ["git", "config", f"--{scope}", key, value],
            cwd=cwd,
            check=True,
        )

    # ============================================================================
    # Query Operations
    # ============================================================================

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
        return result.stdout.strip()
