"""Production Git tag operations using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitTagOps(GitTagOps):
    """Production implementation of Git tag operations using subprocess."""

    # ============================================================================
    # Query Operations
    # ============================================================================

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

    # ============================================================================
    # Mutation Operations
    # ============================================================================

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
