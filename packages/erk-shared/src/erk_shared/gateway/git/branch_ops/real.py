"""Production implementation of Git branch operations using subprocess."""

import re
import subprocess
from pathlib import Path

from erk_shared.gateway.git.abc import BranchDivergence, BranchSyncInfo
from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
from erk_shared.gateway.git.lock import wait_for_index_lock
from erk_shared.gateway.time.abc import Time
from erk_shared.gateway.time.real import RealTime
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitBranchOps(GitBranchOps):
    """Production implementation of branch operations using subprocess.

    All git operations execute actual git commands via subprocess.
    """

    def __init__(self, time: Time | None = None) -> None:
        """Initialize RealGitBranchOps with optional Time provider.

        Args:
            time: Time provider for lock waiting. Defaults to RealTime().
        """
        self._time = time if time is not None else RealTime()

    def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> None:
        """Create a new branch without checking it out."""
        cmd = ["git", "branch"]
        if force:
            cmd.append("-f")
        cmd.extend([branch_name, start_point])
        run_subprocess_with_context(
            cmd=cmd,
            operation_context=f"create branch '{branch_name}' from '{start_point}'",
            cwd=cwd,
        )

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch.

        Idempotent: if branch doesn't exist, returns successfully.
        """
        # LBYL: Check if branch exists before attempting delete
        check_result = run_subprocess_with_context(
            cmd=["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
            operation_context=f"check if branch '{branch_name}' exists",
            cwd=cwd,
            check=False,
        )
        if check_result.returncode != 0:
            # Branch doesn't exist - goal achieved
            return

        flag = "-D" if force else "-d"
        run_subprocess_with_context(
            cmd=["git", "branch", flag, branch_name],
            operation_context=f"delete branch '{branch_name}'",
            cwd=cwd,
        )

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        # Wait for index lock if another git operation is in progress
        wait_for_index_lock(cwd, self._time)

        run_subprocess_with_context(
            cmd=["git", "checkout", branch],
            operation_context=f"checkout branch '{branch}'",
            cwd=cwd,
        )

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref."""
        run_subprocess_with_context(
            cmd=["git", "checkout", "--detach", ref],
            operation_context=f"checkout detached HEAD at '{ref}'",
            cwd=cwd,
        )

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch."""
        run_subprocess_with_context(
            cmd=["git", "branch", "--track", branch, remote_ref],
            operation_context=f"create tracking branch '{branch}' from '{remote_ref}'",
            cwd=repo_root,
        )

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        branch = result.stdout.strip()
        if branch == "HEAD":
            return None

        return branch

    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names in the repository."""
        result = run_subprocess_with_context(
            cmd=["git", "branch", "--format=%(refname:short)"],
            operation_context="list local branches",
            cwd=repo_root,
        )
        branches = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return branches

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names in the repository."""
        result = run_subprocess_with_context(
            cmd=["git", "branch", "-r", "--format=%(refname:short)"],
            operation_context="list remote branches",
            cwd=repo_root,
        )
        return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

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

        return result.stdout.strip()

    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name.

        Checks git's remote HEAD reference, then falls back to checking for
        existence of 'main' then 'master'. Returns 'main' as final fallback
        if neither branch exists.
        """
        # 1. Try git symbolic-ref to detect default branch
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_root,
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
                cwd=repo_root,
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return candidate

        # 3. Final fallback: 'main'
        return "main"

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists.

        Args:
            repo_root: Path to the repository root
            name: Trunk branch name to validate

        Returns:
            The validated trunk branch name

        Raises:
            RuntimeError: If the specified branch doesn't exist
        """
        result = subprocess.run(
            ["git", "rev-parse", "--verify", name],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return name
        error_msg = (
            f"Error: Configured trunk branch '{name}' does not exist in repository.\n"
            f"Update your configuration in pyproject.toml or create the branch."
        )
        raise RuntimeError(error_msg)

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote."""
        result = subprocess.run(
            ["git", "ls-remote", remote, branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())

    def get_ahead_behind(self, cwd: Path, branch: str) -> tuple[int, int]:
        """Get number of commits ahead and behind tracking branch."""
        # Check if branch has upstream
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # No upstream branch
            return 0, 0

        upstream = result.stdout.strip()

        # Get ahead/behind counts
        result = run_subprocess_with_context(
            cmd=["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"],
            operation_context=f"get ahead/behind counts for branch '{branch}'",
            cwd=cwd,
        )

        parts = result.stdout.strip().split()
        if len(parts) == 2:
            behind = int(parts[0])
            ahead = int(parts[1])
            return ahead, behind

        return 0, 0

    def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
        """Get sync status for all local branches via git for-each-ref."""
        result = subprocess.run(
            [
                "git",
                "for-each-ref",
                "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)",
                "refs/heads/",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return {}

        sync_info: dict[str, BranchSyncInfo] = {}
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            branch = parts[0]
            upstream = parts[1] if len(parts) > 1 and parts[1] else None
            track = parts[2] if len(parts) > 2 else ""

            ahead, behind = 0, 0
            if track:
                # Parse "[ahead N, behind M]" or "[ahead N]" or "[behind M]"
                ahead_match = re.search(r"ahead (\d+)", track)
                behind_match = re.search(r"behind (\d+)", track)
                if ahead_match:
                    ahead = int(ahead_match.group(1))
                if behind_match:
                    behind = int(behind_match.group(1))

            sync_info[branch] = BranchSyncInfo(
                branch=branch,
                upstream=upstream,
                ahead=ahead,
                behind=behind,
            )

        return sync_info

    def is_branch_diverged_from_remote(
        self, cwd: Path, branch: str, remote: str
    ) -> BranchDivergence:
        """Check if a local branch has diverged from its remote tracking branch."""
        remote_branch = f"{remote}/{branch}"

        # Check if remote branch exists
        result = subprocess.run(
            ["git", "rev-parse", "--verify", remote_branch],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return BranchDivergence(is_diverged=False, ahead=0, behind=0)

        # Get ahead/behind counts
        ahead_result = subprocess.run(
            ["git", "rev-list", "--count", f"{remote_branch}..{branch}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        behind_result = subprocess.run(
            ["git", "rev-list", "--count", f"{branch}..{remote_branch}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        ahead = int(ahead_result.stdout.strip()) if ahead_result.returncode == 0 else 0
        behind = int(behind_result.stdout.strip()) if behind_result.returncode == 0 else 0

        is_diverged = ahead > 0 and behind > 0
        return BranchDivergence(is_diverged=is_diverged, ahead=ahead, behind=behind)

    def get_branch_issue(self, repo_root: Path, branch: str) -> int | None:
        """Extract GitHub issue number from branch name.

        Branch names follow the pattern: P{issue_number}-{slug}-{timestamp}
        """
        from erk_shared.naming import extract_leading_issue_number

        return extract_leading_issue_number(branch)

    def get_behind_commit_authors(self, cwd: Path, branch: str) -> list[str]:
        """Get authors of commits on remote that are not in local branch."""
        # Check if branch has upstream
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # No upstream branch
            return []

        upstream = result.stdout.strip()

        # Get authors of commits on upstream but not locally
        result = subprocess.run(
            ["git", "log", "--format=%an", f"HEAD..{upstream}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return []

        authors = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return authors

    def get_branch_last_commit_time(self, repo_root: Path, branch: str, trunk: str) -> str | None:
        """Get the author date of the most recent commit unique to a branch."""
        result = subprocess.run(
            ["git", "log", f"{trunk}..{branch}", "-1", "--format=%aI"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        timestamp = result.stdout.strip()
        return timestamp if timestamp else None

    def get_branch_commits_with_authors(
        self, repo_root: Path, branch: str, trunk: str, *, limit: int
    ) -> list[dict[str, str]]:
        """Get commits on branch not on trunk, with author and timestamp.

        Returns commits unique to the branch (not present on trunk),
        ordered from newest to oldest.
        """
        result = subprocess.run(
            [
                "git",
                "log",
                f"{trunk}..{branch}",
                f"-{limit}",
                "--format=%H%x00%an%x00%aI",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\x00")
            if len(parts) == 3:
                commits.append(
                    {
                        "sha": parts[0],
                        "author": parts[1],
                        "timestamp": parts[2],
                    }
                )
        return commits
