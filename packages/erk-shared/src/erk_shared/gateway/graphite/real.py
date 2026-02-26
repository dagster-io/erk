"""Production implementation of Graphite operations."""

import json
import subprocess
import sys
from pathlib import Path
from subprocess import DEVNULL

from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.github.types import GitHubRepoId, PullRequestInfo
from erk_shared.gateway.graphite.abc import Graphite
from erk_shared.gateway.graphite.parsing import (
    parse_graphite_cache,
    parse_graphite_pr_info,
    read_graphite_json_file,
)
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.output.output import user_output
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGraphite(Graphite):
    """Production implementation using gt CLI.

    All Graphite operations execute actual gt commands via subprocess.
    """

    def __init__(self) -> None:
        """Initialize with empty cache for get_all_branches."""
        self._branches_cache: dict[str, BranchMetadata] | None = None
        self._branches_cache_mtime: float | None = None

    def get_graphite_url(self, repo_id: GitHubRepoId, pr_number: int) -> str:
        """Get Graphite PR URL for a pull request.

        Constructs the Graphite URL directly from GitHub repo information.
        No subprocess calls or external dependencies required.

        Args:
            repo_id: GitHub repository identity (owner and repo name)
            pr_number: GitHub PR number

        Returns:
            Graphite PR URL (e.g., "https://app.graphite.com/github/pr/dagster-io/erk/23")
        """
        return f"https://app.graphite.com/github/pr/{repo_id.owner}/{repo_id.repo}/{pr_number}"

    def get_prs_from_graphite(self, git_ops: Git, repo_root: Path) -> dict[str, PullRequestInfo]:
        """Get PR information from Graphite's .git/.graphite_pr_info file."""
        git_dir = git_ops.repo.get_git_common_dir(repo_root)
        if git_dir is None:
            return {}

        pr_info_file = git_dir / ".graphite_pr_info"
        if not pr_info_file.exists():
            return {}

        data = read_graphite_json_file(pr_info_file, "Graphite PR info")

        # parse_graphite_pr_info expects JSON string, so convert back
        return parse_graphite_pr_info(json.dumps(data))

    def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
        """Get all gt-tracked branches with metadata.

        Reads .git/.graphite_cache_persist and enriches with commit SHAs from git.
        Returns empty dict if cache doesn't exist or git operations fail.

        Results are cached based on file mtime - the cache is automatically
        invalidated when the underlying file changes, whether from erk operations
        or external gt commands.
        """
        git_dir = git_ops.repo.get_git_common_dir(repo_root)
        if git_dir is None:
            return {}

        cache_file = git_dir / ".graphite_cache_persist"
        if not cache_file.exists():
            return {}

        # Check if cache is still valid via mtime
        current_mtime = cache_file.stat().st_mtime
        if (
            self._branches_cache is not None
            and self._branches_cache_mtime is not None
            and self._branches_cache_mtime == current_mtime
        ):
            return self._branches_cache

        # Cache miss or stale - recompute
        data = read_graphite_json_file(cache_file, "Graphite cache")

        # Get all branch heads from git in a single call for enrichment
        all_heads = git_ops.branch.get_all_branch_heads(repo_root)
        branches_data = data.get("branches", [])
        git_branch_heads = {
            branch_name: all_heads[branch_name]
            for branch_name, _ in branches_data
            if isinstance(branch_name, str) and branch_name in all_heads
        }

        # parse_graphite_cache expects JSON string, so convert back
        self._branches_cache = parse_graphite_cache(json.dumps(data), git_branch_heads)
        self._branches_cache_mtime = current_mtime
        return self._branches_cache

    def get_branch_stack(self, git_ops: Git, repo_root: Path, branch: str) -> list[str] | None:
        """Get the linear worktree stack for a given branch."""
        # Get all branch metadata
        all_branches = self.get_all_branches(git_ops, repo_root)
        if not all_branches:
            return None

        # Check if the requested branch exists
        if branch not in all_branches:
            return None

        # Build parent-child map for traversal
        branch_info: dict[str, dict[str, str | list[str] | None]] = {}
        for name, metadata in all_branches.items():
            branch_info[name] = {
                "parent": metadata.parent,
                "children": metadata.children,
            }

        # Traverse DOWN to collect ancestors (current → parent → ... → trunk)
        ancestors: list[str] = []
        current = branch
        while current in branch_info:
            ancestors.append(current)
            parent = branch_info[current]["parent"]
            if parent is None or parent not in branch_info:
                break
            current = parent

        # Reverse to get [trunk, ..., parent, current]
        ancestors.reverse()

        # Traverse UP to collect descendants (current → child → ... → leaf)
        descendants: list[str] = []
        current = branch
        while True:
            children = branch_info[current]["children"]
            if not children:
                break
            # Follow the first child for linear stack
            first_child = children[0]
            if first_child not in branch_info:
                break
            descendants.append(first_child)
            current = first_child

        # Combine ancestors and descendants
        # ancestors already contains the current branch
        return ancestors + descendants

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check Graphite authentication status.

        Runs `gt auth` and parses the output to determine authentication status.
        Looks for patterns like:
        - "Authenticated as: USERNAME"
        - "Ready to submit PRs to OWNER/REPO"
        - Success indicator (checkmark)

        Returns:
            Tuple of (is_authenticated, username, repo_info)
        """
        result = subprocess.run(
            ["gt", "auth", "--no-interactive"],
            capture_output=True,
            text=True,
            check=False,
        )

        # If command failed, not authenticated
        if result.returncode != 0:
            return (False, None, None)

        output = result.stdout + result.stderr

        # Look for success indicator (checkmark symbol or "Authenticated as:")
        if "Authenticated as:" not in output and "✓" not in output:
            return (False, None, None)

        # Extract username from "Authenticated as: USERNAME"
        username: str | None = None
        for line in output.split("\n"):
            if "Authenticated as:" in line:
                # Parse "Authenticated as: USERNAME" or similar
                parts = line.split("Authenticated as:")
                if len(parts) >= 2:
                    username = parts[1].strip()
                break

        # Extract repo info from "Ready to submit PRs to OWNER/REPO"
        repo_info: str | None = None
        for line in output.split("\n"):
            if "Ready to submit PRs to" in line:
                parts = line.split("Ready to submit PRs to")
                if len(parts) >= 2:
                    repo_info = parts[1].strip()
                break

        return (True, username, repo_info)

    def squash_branch(self, repo_root: Path, *, quiet: bool) -> None:
        """Squash all commits on the current branch into one."""
        cmd = ["gt", "squash", "--no-edit", "--no-interactive"]

        run_subprocess_with_context(
            cmd=cmd,
            operation_context="squash branch commits with Graphite",
            cwd=repo_root,
            stdout=DEVNULL if quiet else sys.stdout,
            stderr=subprocess.PIPE,
        )

    def submit_stack(
        self,
        repo_root: Path,
        *,
        publish: bool,
        restack: bool,
        quiet: bool,
        force: bool,
    ) -> None:
        """Submit the current stack to create or update PRs."""
        cmd = ["gt", "submit", "--no-edit", "--no-interactive"]

        if publish:
            cmd.append("--publish")
        if restack:
            cmd.append("--restack")
        if force:
            cmd.append("--force")

        # Use 90-second timeout to leave headroom before Bash tool's 120s timeout.
        # Capture stdout so Python controls when output is written to the pipe,
        # preventing loss of all output when the process is killed externally.
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_root,
                timeout=90,
                stdout=DEVNULL if quiet else subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            if not quiet and result.stdout:
                user_output(result.stdout, nl=False)
            if not quiet and result.stderr:
                user_output(result.stderr, nl=False)
        except subprocess.TimeoutExpired as e:
            if not quiet and e.stdout:
                stdout = e.stdout if isinstance(e.stdout, str) else e.stdout.decode()
                user_output(stdout, nl=False)
            raise RuntimeError(
                "gt submit timed out after 90 seconds. Check network connectivity and try again."
            ) from e
        except subprocess.CalledProcessError as e:
            if not quiet and e.stdout:
                user_output(e.stdout, nl=False)
            raise RuntimeError(
                f"gt submit failed (exit code {e.returncode}): {e.stderr or ''}"
            ) from e

        # Invalidate branches cache - gt submit modifies Graphite metadata
        self._branches_cache = None

    def is_branch_tracked(self, repo_root: Path, branch: str) -> bool:
        """Check if a branch is tracked by Graphite.

        Uses `gt branch info` to get authoritative tracking status. Exit code 0
        means the branch is tracked, non-zero means untracked or error.
        """
        result = subprocess.run(
            ["gt", "branch", "info", branch, "--quiet", "--no-interactive"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
