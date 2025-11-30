"""GitHub Codespace operations for erk.

This module provides functions for managing GitHub Codespaces:
- Finding existing Codespaces for a repo/branch
- Creating new Codespaces with devcontainer
- Waiting for Codespaces to become available
"""

import json
import subprocess
from pathlib import Path

from erk_shared.subprocess_utils import run_subprocess_with_context


class CodespaceError(Exception):
    """Raised when a Codespace operation fails."""


def get_repo_name(cwd: Path) -> str:
    """Get the repository name in 'owner/repo' format.

    Args:
        cwd: Working directory within the repository

    Returns:
        Repository name in 'owner/repo' format (e.g., 'anthropics/erk')

    Raises:
        RuntimeError: If gh repo view fails
    """
    result = run_subprocess_with_context(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        operation_context="get repository name",
        cwd=cwd,
    )
    return result.stdout.strip()


def get_current_branch(cwd: Path) -> str:
    """Get the current git branch name.

    Args:
        cwd: Working directory within the repository

    Returns:
        Current branch name (e.g., 'main', 'feature/my-feature')

    Raises:
        RuntimeError: If git rev-parse fails
    """
    result = run_subprocess_with_context(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        operation_context="get current branch",
        cwd=cwd,
    )
    return result.stdout.strip()


def find_existing_codespace(repo: str, branch: str) -> str | None:
    """Find an existing available Codespace for the given repo and branch.

    Args:
        repo: Repository in 'owner/repo' format
        branch: Branch name to find Codespace for

    Returns:
        Codespace name if found, None if no matching Codespace exists

    Note:
        Only returns Codespaces that are in 'Available' state.
    """
    # LBYL: Use check=False to handle case where no codespaces exist gracefully
    result = subprocess.run(
        ["gh", "codespace", "list", "--repo", repo, "--json", "name,gitStatus,state"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    # Parse JSON output
    codespaces = json.loads(result.stdout)

    # Find a codespace on the target branch that's available
    for cs in codespaces:
        cs_branch = cs.get("gitStatus", {}).get("ref", "")
        cs_state = cs.get("state", "")
        if cs_branch == branch and cs_state == "Available":
            return cs.get("name")

    return None


def create_codespace(repo: str, branch: str, devcontainer_path: str | None = None) -> str:
    """Create a new Codespace for the given repo and branch.

    Args:
        repo: Repository in 'owner/repo' format
        branch: Branch name to create Codespace for
        devcontainer_path: Optional path to devcontainer.json

    Returns:
        Name of the created Codespace

    Raises:
        RuntimeError: If codespace creation fails
    """
    cmd = ["gh", "codespace", "create", "--repo", repo, "--branch", branch]

    if devcontainer_path:
        cmd.extend(["--devcontainer-path", devcontainer_path])

    result = run_subprocess_with_context(
        cmd,
        operation_context=f"create codespace for {repo}@{branch}",
    )

    return result.stdout.strip()


def wait_for_codespace(codespace_name: str, timeout_seconds: int = 300) -> bool:
    """Wait for a Codespace to become available.

    Args:
        codespace_name: Name of the Codespace to wait for
        timeout_seconds: Maximum time to wait (default: 5 minutes)

    Returns:
        True if Codespace is available, False if timeout

    Note:
        Polls every 5 seconds until Codespace state is 'Available'.
    """
    import time

    start_time = time.monotonic()

    while time.monotonic() - start_time < timeout_seconds:
        # Check codespace state
        result = subprocess.run(
            ["gh", "codespace", "view", "--codespace", codespace_name, "--json", "state"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("state") == "Available":
                return True

        time.sleep(5)

    return False


def get_or_create_codespace(
    cwd: Path,
    devcontainer_path: str | None = None,
) -> str:
    """Get an existing Codespace or create a new one.

    This is a convenience wrapper that:
    1. Gets the repo name and current branch
    2. Looks for an existing available Codespace
    3. Creates a new one if none exists
    4. Waits for the Codespace to become available

    Args:
        cwd: Working directory within the repository
        devcontainer_path: Optional path to devcontainer.json

    Returns:
        Name of the available Codespace

    Raises:
        CodespaceError: If Codespace creation fails or times out
        RuntimeError: If underlying git/gh commands fail
    """
    repo = get_repo_name(cwd)
    branch = get_current_branch(cwd)

    # Check for existing codespace
    existing = find_existing_codespace(repo, branch)
    if existing:
        return existing

    # Create new codespace
    codespace_name = create_codespace(repo, branch, devcontainer_path)

    # Wait for it to be available
    if not wait_for_codespace(codespace_name):
        raise CodespaceError(f"Codespace {codespace_name} did not become available within timeout")

    return codespace_name
