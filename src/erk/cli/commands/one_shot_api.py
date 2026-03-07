"""API-only implementations for one-shot dispatch without a local repo.

When running `erk one-shot` from outside a git repository (with --repo),
these functions replace local git operations with GitHub REST API calls
via the `gh api` CLI command.
"""

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

from erk_shared.subprocess_utils import run_subprocess_with_context


@dataclass(frozen=True)
class ApiOnlyOneShotOps:
    """API-only implementations for one-shot dispatch without a local repo."""

    nwo: str  # "owner/repo" name-with-owner


def gh_env_for_nwo(nwo: str) -> dict[str, str]:
    """Return env dict with GH_REPO set for out-of-repo gh commands."""
    env = os.environ.copy()
    env["GH_REPO"] = nwo
    return env


def api_get_default_branch(nwo: str) -> str:
    """Get the default branch of a repository via GitHub API.

    Args:
        nwo: Repository in "owner/repo" format

    Returns:
        The default branch name (e.g., "main", "master")
    """
    result = run_subprocess_with_context(
        cmd=[
            "gh",
            "api",
            f"repos/{nwo}",
            "--jq",
            ".default_branch",
        ],
        operation_context=f"get default branch for {nwo}",
        cwd=Path.cwd(),
    )
    return result.stdout.strip()


def api_get_branch_sha(nwo: str, branch: str) -> str:
    """Get the SHA of a branch's HEAD commit via GitHub API.

    Args:
        nwo: Repository in "owner/repo" format
        branch: Branch name to look up

    Returns:
        The SHA of the branch's HEAD commit
    """
    result = run_subprocess_with_context(
        cmd=[
            "gh",
            "api",
            f"repos/{nwo}/git/ref/heads/{branch}",
            "--jq",
            ".object.sha",
        ],
        operation_context=f"get branch SHA for {branch} in {nwo}",
        cwd=Path.cwd(),
    )
    return result.stdout.strip()


def api_create_branch(nwo: str, branch_name: str, from_sha: str) -> None:
    """Create a branch via GitHub API.

    Args:
        nwo: Repository in "owner/repo" format
        branch_name: Name of the new branch
        from_sha: SHA to create the branch from
    """
    payload = json.dumps(
        {
            "ref": f"refs/heads/{branch_name}",
            "sha": from_sha,
        }
    )
    run_subprocess_with_context(
        cmd=[
            "gh",
            "api",
            f"repos/{nwo}/git/refs",
            "-X",
            "POST",
            "--input",
            "-",
        ],
        operation_context=f"create branch {branch_name} in {nwo}",
        cwd=Path.cwd(),
        input=payload,
    )


def api_commit_file(
    nwo: str,
    *,
    branch: str,
    path: str,
    content: str,
    message: str,
) -> None:
    """Commit a file to a branch via GitHub API.

    Uses PUT /repos/{nwo}/contents/{path} which creates the file and
    commits in a single API call.

    Args:
        nwo: Repository in "owner/repo" format
        branch: Branch to commit to
        path: File path within the repository
        content: File content (will be base64-encoded)
        message: Commit message
    """
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
    payload = json.dumps(
        {
            "message": message,
            "content": encoded_content,
            "branch": branch,
        }
    )
    run_subprocess_with_context(
        cmd=[
            "gh",
            "api",
            f"repos/{nwo}/contents/{path}",
            "-X",
            "PUT",
            "--input",
            "-",
        ],
        operation_context=f"commit file {path} to {branch} in {nwo}",
        cwd=Path.cwd(),
        input=payload,
    )
