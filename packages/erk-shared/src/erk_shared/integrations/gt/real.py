"""Real subprocess-based implementations of GT kit operations interfaces.

This module provides concrete implementations that wrap subprocess.run calls
for git, Graphite (gt), and GitHub (gh) commands. These are the production
implementations used by GT kit CLI commands.

Design:
- Each implementation wraps existing subprocess patterns from CLI commands
- Returns match interface contracts (str | None, bool, tuple)
- Uses check=False to allow LBYL error handling
- RealGtKit composes git, GitHub, and main_graphite implementations
"""

import json
import subprocess

from erk_shared.git.abc import Git
from erk_shared.git.real import RealGit
from erk_shared.github.parsing import parse_gh_auth_status_output
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.graphite.real import RealGraphite
from erk_shared.integrations.gt.abc import GitHubGtKit, GtKit


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

    def mark_pr_ready(self) -> bool:
        """Mark PR as ready for review using gh pr ready."""
        result = subprocess.run(
            ["gh", "pr", "ready"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def get_pr_title(self) -> str | None:
        """Get the title of the PR for the current branch."""
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "title", "-q", ".title"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        title = result.stdout.strip()
        if not title:
            return None
        return title

    def get_pr_body(self) -> str | None:
        """Get the body of the PR for the current branch."""
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "body", "-q", ".body"],
            capture_output=True,
            text=True,
            check=False,
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

    def get_graphite_pr_url(self, pr_number: int) -> str | None:
        """Get Graphite PR URL using gh repo view."""
        result = _run_subprocess_with_timeout(
            ["gh", "repo", "view", "--json", "owner,name"],
            timeout=10,
            capture_output=True,
            text=True,
            check=False,
        )

        if result is None or result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        owner = data["owner"]["login"]
        repo = data["name"]

        return f"https://app.graphite.com/github/pr/{owner}/{repo}/{pr_number}"

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

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the diff for a PR using gh pr diff."""
        result = subprocess.run(
            ["gh", "pr", "diff", str(pr_number)],
            capture_output=True,
            text=True,
            check=True,
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

    def get_pr_mergeability(self, pr_number: int) -> tuple[str, str]:
        """Get PR mergeability using gh API."""
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/pulls/{pr_number}",
                "--jq",
                ".mergeable,.mergeable_state",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return ("UNKNOWN", "UNKNOWN")

        lines = result.stdout.strip().split("\n")
        mergeable = lines[0] if len(lines) > 0 else "null"
        merge_state = lines[1] if len(lines) > 1 else "unknown"

        # Convert to GitHub GraphQL enum format
        if mergeable == "true":
            return ("MERGEABLE", merge_state.upper())
        if mergeable == "false":
            return ("CONFLICTING", merge_state.upper())
        return ("UNKNOWN", "UNKNOWN")


class RealGtKit(GtKit):
    """Real composite operations implementation.

    Combines real git, GitHub, and Graphite operations for production use.
    """

    def __init__(self) -> None:
        """Initialize real operations instances."""
        self._git = RealGit()
        self._github = RealGitHubGtKit()
        self._main_graphite = RealGraphite()

    def git(self) -> Git:
        """Get the git operations interface."""
        return self._git

    def github(self) -> GitHubGtKit:
        """Get the GitHub operations interface."""
        return self._github

    def main_graphite(self) -> Graphite:
        """Get the main Graphite operations interface."""
        return self._main_graphite
