"""Real subprocess-based implementations of GT kit operations interfaces.

This module provides concrete implementations that wrap subprocess.run calls
for git and Graphite (gt) commands. These are the production implementations
used by GT kit CLI commands.

Design:
- Each implementation wraps existing subprocess patterns from CLI commands
- Returns match interface contracts (str | None, bool, tuple)
- Uses check=False to allow LBYL error handling
- RealGtKit composes git, main_graphite, and GitHub (from erk_shared.github)
"""

import subprocess
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.real import RealGitHub
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.gt.abc import GitGtKit, GtKit
from erk_shared.integrations.time.real import RealTime


class RealGitGtKit(GitGtKit):
    """Real git operations using subprocess."""

    def get_current_branch(self) -> str | None:
        """Get the name of the current branch using git."""
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes using git status."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False

        return len(result.stdout.strip()) > 0

    def add_all(self) -> bool:
        """Stage all changes using git add."""
        result = subprocess.run(
            ["git", "add", "."],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    def commit(self, message: str) -> bool:
        """Create a commit using git commit."""
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    def amend_commit(self, message: str) -> bool:
        """Amend the current commit using git commit --amend."""
        result = subprocess.run(
            ["git", "commit", "--amend", "-m", message],
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    def count_commits_in_branch(self, parent_branch: str) -> int:
        """Count commits in current branch using git rev-list."""
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{parent_branch}..HEAD"],
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

    def get_trunk_branch(self) -> str:
        """Get the trunk branch name for the repository.

        Detects trunk by checking git's remote HEAD reference. Falls back to
        checking for existence of common trunk branch names if detection fails.
        """
        # 1. Try git symbolic-ref to detect default branch
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            # Parse "refs/remotes/origin/master" -> "master"
            ref = result.stdout.strip()
            if ref.startswith("refs/remotes/origin/"):
                return ref.replace("refs/remotes/origin/", "")

        # 2. Fallback: try 'main' then 'master', use first that exists
        for candidate in ["main", "master"]:
            result = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{candidate}"],
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return candidate

        # 3. Final fallback: 'main'
        return "main"

    def get_repository_root(self) -> str:
        """Get the absolute path to the repository root."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def get_diff_to_parent(self, parent_branch: str) -> str:
        """Get git diff between parent branch and HEAD."""
        result = subprocess.run(
            ["git", "diff", f"{parent_branch}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def check_merge_conflicts(self, base_branch: str, head_branch: str) -> bool:
        """Check for merge conflicts using git merge-tree."""
        # Use modern --write-tree mode which properly reports conflicts
        result = subprocess.run(
            ["git", "merge-tree", "--write-tree", base_branch, head_branch],
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit
        )

        # Modern merge-tree: returns non-zero exit code if conflicts exist
        # Exit code 1 = conflicts, 0 = clean merge
        return result.returncode != 0

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory for a path.

        For regular repos, this is the .git directory.
        For worktrees, this is the shared .git directory.
        """
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        common_dir = result.stdout.strip()
        if not common_dir:
            return None

        # Convert to absolute path if relative
        common_path = Path(common_dir)
        if not common_path.is_absolute():
            common_path = (cwd / common_path).resolve()

        return common_path

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        result = subprocess.run(
            ["git", "rev-parse", branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return None

        sha = result.stdout.strip()
        return sha if sha else None

    def checkout_branch(self, branch: str) -> bool:
        """Switch to a different branch."""
        result = subprocess.run(
            ["git", "checkout", branch],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0


class RealGtKit(GtKit):
    """Real composite operations implementation.

    Combines real git, GitHub, and Graphite operations for production use.
    GitHub operations now use the main RealGitHub from erk_shared.github
    which provides repo_root-based methods.
    """

    def __init__(self) -> None:
        """Initialize real operations instances."""
        self._git = RealGitGtKit()
        self._github = RealGitHub(time=RealTime())
        self._main_graphite = RealGraphite()

    def git(self) -> GitGtKit:
        """Get the git operations interface."""
        return self._git

    def github(self) -> GitHub:
        """Get the GitHub operations interface."""
        return self._github

    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface."""
        return self._main_graphite
