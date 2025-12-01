"""Real subprocess-based implementations of GT kit operations interfaces.

This module provides concrete implementations that wrap subprocess.run calls
for git, Graphite (gt), and GitHub (gh) commands. These are the production
implementations used by GT kit CLI commands.

Design:
- Each implementation wraps existing subprocess patterns from CLI commands
- Returns match interface contracts (str | None, bool, tuple)
- Uses check=False to allow LBYL error handling
- RealGtKit composes git, GitHub (unified), and main_graphite implementations
"""

import json
import subprocess
from pathlib import Path

from erk_shared.github.abc import GitHub
from erk_shared.github.parsing import parse_gh_auth_status_output
from erk_shared.github.types import PRMergeability
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.gt.abc import GitGtKit, GitHubGtKit, GtKit


def _run_subprocess_with_timeout(
    cmd: list[str],
    timeout: int,
    **kwargs,
) -> subprocess.CompletedProcess[str] | None:
    """Run subprocess command with timeout handling.

    Returns CompletedProcess on success, None on timeout.
    This encapsulates TimeoutExpired exception handling at the subprocess boundary.

    Args:
        cmd: Command and arguments to execute
        timeout: Timeout in seconds
        **kwargs: Additional arguments passed to subprocess.run

    Returns:
        CompletedProcess if command completes within timeout, None if timeout occurs
    """
    try:
        return subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired:
        return None


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


class RealGitHubGtKit(GitHubGtKit):
    """Real GitHub operations using subprocess."""

    def get_pr_info(self) -> tuple[int, str] | None:
        """Get PR number and URL using gh pr view."""
        result = _run_subprocess_with_timeout(
            ["gh", "pr", "view", "--json", "number,url"],
            timeout=10,
            capture_output=True,
            text=True,
            check=False,
        )

        if result is None or result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        return (data["number"], data["url"])

    def get_pr_state(self) -> tuple[int, str] | None:
        """Get PR number and state using gh pr view."""
        result = _run_subprocess_with_timeout(
            ["gh", "pr", "view", "--json", "state,number"],
            timeout=10,
            capture_output=True,
            text=True,
            check=False,
        )

        if result is None or result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        return (data["number"], data["state"])

    def update_pr_metadata(self, title: str, body: str) -> bool:
        """Update PR title and body using gh pr edit."""
        result = _run_subprocess_with_timeout(
            ["gh", "pr", "edit", "--title", title, "--body", body],
            timeout=30,
            capture_output=True,
            text=True,
            check=False,
        )

        if result is None:
            return False

        return result.returncode == 0

    def mark_pr_ready(  # type: ignore[override]
        self, repo_root: Path | None = None, pr_number: int | None = None
    ) -> bool:
        """Mark PR as ready for review using gh pr ready.

        Supports both interfaces:
        - Old: mark_pr_ready() - uses current branch context
        - New: mark_pr_ready(repo_root, pr_number) - explicit PR number
        """
        if pr_number is not None:
            # Unified GitHub interface
            cmd = ["gh", "pr", "ready", str(pr_number)]
            cwd = repo_root
        else:
            # Legacy GitHubGtKit interface
            cmd = ["gh", "pr", "ready"]
            cwd = None
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        return result.returncode == 0

    def get_pr_title(  # type: ignore[override]
        self, repo_root: Path | None = None, pr_number: int | None = None
    ) -> str | None:
        """Get the title of a PR.

        Supports both interfaces:
        - Old: get_pr_title() - uses current branch context
        - New: get_pr_title(repo_root, pr_number) - explicit PR number
        """
        if pr_number is not None:
            # Unified GitHub interface
            cmd = ["gh", "pr", "view", str(pr_number), "--json", "title", "-q", ".title"]
            cwd = repo_root
        else:
            # Legacy GitHubGtKit interface
            cmd = ["gh", "pr", "view", "--json", "title", "-q", ".title"]
            cwd = None
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        if result.returncode != 0:
            return None
        title = result.stdout.strip()
        if not title:
            return None
        return title

    def get_pr_body(  # type: ignore[override]
        self, repo_root: Path | None = None, pr_number: int | None = None
    ) -> str | None:
        """Get the body of a PR.

        Supports both interfaces:
        - Old: get_pr_body() - uses current branch context
        - New: get_pr_body(repo_root, pr_number) - explicit PR number
        """
        if pr_number is not None:
            # Unified GitHub interface
            cmd = ["gh", "pr", "view", str(pr_number), "--json", "body", "-q", ".body"]
            cwd = repo_root
        else:
            # Legacy GitHubGtKit interface
            cmd = ["gh", "pr", "view", "--json", "body", "-q", ".body"]
            cwd = None
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
        if result.returncode != 0:
            return None
        body = result.stdout.strip()
        if not body:
            return None
        return body

    def merge_pr(self, *, subject: str | None = None, body: str | None = None) -> bool:
        """Merge the PR using squash merge with gh pr merge."""
        cmd = ["gh", "pr", "merge", "-s"]
        if subject is not None:
            cmd.extend(["--subject", subject])
        if body is not None:
            cmd.extend(["--body", body])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def get_graphite_pr_url(  # type: ignore[override]
        self, repo_root_or_pr_number: Path | int, pr_number: int | None = None
    ) -> str | None:
        """Get Graphite PR URL using gh repo view.

        Supports both interfaces:
        - Old: get_graphite_pr_url(pr_number) - uses current directory context
        - New: get_graphite_pr_url(repo_root, pr_number) - explicit repo root
        """
        if pr_number is not None:
            # Unified GitHub interface
            actual_pr_number = pr_number
            cwd = repo_root_or_pr_number
        else:
            # Legacy GitHubGtKit interface
            actual_pr_number = int(repo_root_or_pr_number)  # type: ignore[arg-type]
            cwd = None

        result = _run_subprocess_with_timeout(
            ["gh", "repo", "view", "--json", "owner,name"],
            timeout=10,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )

        if result is None or result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        owner = data["owner"]["login"]
        repo = data["name"]

        return f"https://app.graphite.com/github/pr/{owner}/{repo}/{actual_pr_number}"

    def check_auth_status(self) -> tuple[bool, str | None, str | None]:
        """Check GitHub CLI authentication status.

        Runs `gh auth status` and parses the output to determine authentication status.
        """
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            check=False,
        )

        # gh auth status returns non-zero if not authenticated
        if result.returncode != 0:
            return (False, None, None)

        output = result.stdout + result.stderr
        return parse_gh_auth_status_output(output)

    def get_pr_diff(  # type: ignore[override]
        self, repo_root_or_pr_number: Path | int, pr_number: int | None = None
    ) -> str:
        """Get the diff for a PR using gh pr diff.

        Supports both interfaces:
        - Old: get_pr_diff(pr_number) - uses current directory context
        - New: get_pr_diff(repo_root, pr_number) - explicit repo root
        """
        if pr_number is not None:
            # Unified GitHub interface
            actual_pr_number = pr_number
            cwd = repo_root_or_pr_number
        else:
            # Legacy GitHubGtKit interface
            actual_pr_number = int(repo_root_or_pr_number)  # type: ignore[arg-type]
            cwd = None

        result = subprocess.run(
            ["gh", "pr", "diff", str(actual_pr_number)],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )
        return result.stdout

    def get_pr_status(self, branch: str) -> tuple[int | None, str | None]:
        """Get PR number and URL using gh CLI."""
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--json", "number,url"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return (None, None)

        data = json.loads(result.stdout)
        if not data:
            return (None, None)

        pr = data[0]
        return (pr["number"], pr["url"])

    def get_pr_mergeability(  # type: ignore[override]
        self, repo_root_or_pr_number: Path | int, pr_number: int | None = None
    ) -> tuple[str, str] | PRMergeability:
        """Get PR mergeability using gh API.

        Supports both interfaces:
        - Old: get_pr_mergeability(pr_number) - returns tuple[str, str]
        - New: get_pr_mergeability(repo_root, pr_number) - returns PRMergeability
        """
        # Determine which interface is being used
        if pr_number is not None:
            # Unified GitHub interface
            actual_pr_number = pr_number
            repo_root = repo_root_or_pr_number
            return_prmergeability = True
        else:
            # Legacy GitHubGtKit interface - first arg is pr_number
            actual_pr_number = int(repo_root_or_pr_number)  # type: ignore[arg-type]
            repo_root = None
            return_prmergeability = False

        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/pulls/{actual_pr_number}",
                "--jq",
                ".mergeable,.mergeable_state",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
        )
        if result.returncode != 0:
            if return_prmergeability:
                return PRMergeability(mergeable="UNKNOWN", merge_state_status="UNKNOWN")
            return ("UNKNOWN", "UNKNOWN")

        lines = result.stdout.strip().split("\n")
        mergeable_raw = lines[0] if len(lines) > 0 else "null"
        merge_state_raw = lines[1] if len(lines) > 1 else "unknown"

        # Convert to GitHub GraphQL enum format
        if mergeable_raw == "true":
            mergeable_enum = "MERGEABLE"
            merge_state_enum = merge_state_raw.upper()
        elif mergeable_raw == "false":
            mergeable_enum = "CONFLICTING"
            merge_state_enum = merge_state_raw.upper()
        else:
            mergeable_enum = "UNKNOWN"
            merge_state_enum = "UNKNOWN"

        if return_prmergeability:
            return PRMergeability(mergeable=mergeable_enum, merge_state_status=merge_state_enum)
        return (mergeable_enum, merge_state_enum)

    # Unified GitHub interface methods (for duck typing compatibility with GitHub ABC)

    def get_pr_info_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        """Get PR number and URL for a branch using gh pr list."""
        result = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--json", "number,url", "--limit", "1"],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        if not data:
            return None

        pr = data[0]
        return (pr["number"], pr["url"])

    def get_pr_state_for_branch(self, repo_root: Path, branch: str) -> tuple[int, str] | None:
        """Get PR number and state for a branch using gh pr list."""
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "number,state",
                "--limit",
                "1",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        if not data:
            return None

        pr = data[0]
        return (pr["number"], pr["state"])

    def update_pr_title_and_body(
        self, repo_root: Path, pr_number: int, title: str, body: str
    ) -> bool:
        """Update PR title and body using gh pr edit."""
        result = subprocess.run(
            ["gh", "pr", "edit", str(pr_number), "--title", title, "--body", body],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
        )
        return result.returncode == 0

    def merge_pr_with_message(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        subject: str | None = None,
        body: str | None = None,
    ) -> bool:
        """Merge a PR using squash merge with gh pr merge."""
        cmd = ["gh", "pr", "merge", str(pr_number), "-s"]
        if subject is not None:
            cmd.extend(["--subject", subject])
        if body is not None:
            cmd.extend(["--body", body])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root,
        )
        return result.returncode == 0


class RealGtKit(GtKit):
    """Real composite operations implementation.

    Combines real git, GitHub (unified), and Graphite operations for production use.
    """

    def __init__(self, github: GitHub | None = None) -> None:
        """Initialize real operations instances.

        Args:
            github: Optional unified GitHub implementation. If not provided,
                   falls back to RealGitHubGtKit for backwards compatibility.
                   Once all callers migrate, this will become required.
        """
        self._git = RealGitGtKit()
        # Use unified GitHub if provided, else fallback to legacy RealGitHubGtKit
        self._github: GitHub | GitHubGtKit = github if github is not None else RealGitHubGtKit()
        self._main_graphite = RealGraphite()

    def git(self) -> GitGtKit:
        """Get the git operations interface."""
        return self._git

    def github(self) -> GitHub:
        """Get the unified GitHub operations interface.

        Note: During migration, this may return GitHubGtKit for callers that
        don't provide a unified GitHub implementation. The return type is
        GitHub (unified) but the implementation respects duck typing.
        """
        # Type assertion for mypy - the actual implementation handles both types
        return self._github  # type: ignore[return-value]

    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface."""
        return self._main_graphite
