"""Real implementation of git analysis operations."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps


class RealGitAnalysisOps(GitAnalysisOps):
    """Real implementation of Git analysis operations using subprocess."""

    # ============================================================================
    # Query Operations
    # ============================================================================

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
        return int(result.stdout.strip())

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

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        result = subprocess.run(
            ["git", "diff", f"{branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
