"""Real implementation of git configuration operations."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.config_ops.abc import GitConfigOps
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitConfigOps(GitConfigOps):
    """Real implementation of Git configuration operations using subprocess."""

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Set a git configuration value."""
        run_subprocess_with_context(
            cmd=["git", "config", f"--{scope}", key, value],
            operation_context=f"set git config {key}",
            cwd=cwd,
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
        name = result.stdout.strip()
        return name if name else None
