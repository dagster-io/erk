"""Create a Codespace and open SSH session for remote planning."""

import json
import os
import subprocess
import time

import click
from erk_shared.output.output import user_output


def _print_command(cmd: list[str]) -> None:
    """Print a command with nice formatting."""
    formatted = " ".join(cmd)
    user_output(click.style("$ ", fg="cyan") + click.style(formatted, fg="white", bold=True))


def _run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, printing it first with nice formatting."""
    _print_command(cmd)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )


def _get_repo_name() -> str:
    """Get the current repository's name with owner.

    Returns:
        Repository name in 'owner/repo' format.

    Raises:
        SystemExit: If gh command fails or repo info cannot be retrieved.
    """
    result = _run_command(["gh", "repo", "view", "--json", "nameWithOwner"])

    if result.returncode != 0:
        user_output(
            click.style("Error: ", fg="red")
            + "Failed to get repository info.\n\n"
            + "Make sure you're in a GitHub repository and authenticated:\n"
            + "  gh auth status"
        )
        raise SystemExit(1)

    data = json.loads(result.stdout)
    repo_name = data.get("nameWithOwner")
    if not repo_name:
        user_output(
            click.style("Error: ", fg="red") + "Could not determine repository name from gh output."
        )
        raise SystemExit(1)

    return repo_name


def _get_current_branch() -> str:
    """Get the current git branch name.

    Returns:
        Current branch name.

    Raises:
        SystemExit: If git command fails.
    """
    result = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    if result.returncode != 0:
        user_output(
            click.style("Error: ", fg="red")
            + "Failed to get current branch.\n\n"
            + "Make sure you're in a git repository."
        )
        raise SystemExit(1)

    return result.stdout.strip()


def _find_existing_codespace(repo: str, branch: str) -> str | None:
    """Find an existing available Codespace for the given repo and branch.

    Args:
        repo: Repository name in 'owner/repo' format.
        branch: Branch name to match.

    Returns:
        Codespace name if found, None otherwise.
    """
    result = subprocess.run(
        ["gh", "codespace", "list", "--json", "name,state,repository,gitStatus"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    codespaces = json.loads(result.stdout)
    for cs in codespaces:
        if (
            cs.get("repository") == repo
            and cs.get("state") == "Available"
            and cs.get("gitStatus", {}).get("ref") == branch
        ):
            return cs.get("name")

    return None


def _create_codespace(repo: str) -> str:
    """Create a new GitHub Codespace.

    Args:
        repo: Repository name in 'owner/repo' format.

    Returns:
        Name of the created Codespace.

    Raises:
        SystemExit: If Codespace creation fails.
    """
    branch = _get_current_branch()

    cmd = [
        "gh",
        "codespace",
        "create",
        "--devcontainer-path",
        ".devcontainer/devcontainer.json",
        "-R",
        repo,
        "-m",
        "standardLinux32gb",
        "-b",
        branch,
    ]
    result = _run_command(cmd)

    if result.returncode != 0:
        user_output(
            click.style("Error: ", fg="red")
            + "Failed to create Codespace.\n\n"
            + f"Details: {result.stderr}\n\n"
            + "Make sure GitHub Codespaces is enabled for your account:\n"
            + "  https://github.com/settings/codespaces"
        )
        raise SystemExit(1)

    codespace_name = result.stdout.strip()
    if not codespace_name:
        user_output(click.style("Error: ", fg="red") + "Codespace creation returned empty name.")
        raise SystemExit(1)

    return codespace_name


def _wait_for_codespace(codespace_name: str, timeout_seconds: int = 300) -> None:
    """Wait for Codespace to become available.

    Args:
        codespace_name: Name of the Codespace to wait for.
        timeout_seconds: Maximum time to wait in seconds.

    Raises:
        SystemExit: If Codespace doesn't become available within timeout.
    """
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            user_output(
                click.style("Error: ", fg="red")
                + f"Codespace did not become available within {timeout_seconds} seconds."
            )
            raise SystemExit(1)

        result = _run_command(["gh", "codespace", "list", "--json", "name,state"])

        if result.returncode != 0:
            # Retry on transient errors
            time.sleep(2)
            continue

        codespaces = json.loads(result.stdout)
        for cs in codespaces:
            if cs.get("name") == codespace_name:
                state = cs.get("state", "")
                if state == "Available":
                    return
                # Still waiting
                break

        time.sleep(3)


@click.command("plan")
@click.argument("description", required=False, default="")
def plan_codespace(description: str) -> None:
    """Create a Codespace and open SSH session for remote planning.

    Creates a new GitHub Codespace for the current repository, waits for
    it to become available, then opens an SSH connection. If an existing
    available Codespace is found for the same repo and branch, it will
    be reused instead of creating a new one.

    Once connected, run:
      claude "/erk:craft-plan <description>"

    DESCRIPTION is an optional description for what you're planning.
    """
    # Get repository info
    repo = _get_repo_name()
    branch = _get_current_branch()

    # Check for existing codespace first
    user_output(f"Checking for existing Codespace on {branch}...")
    existing = _find_existing_codespace(repo, branch)

    if existing:
        codespace_name = existing
        user_output(click.style("✓ ", fg="green") + f"Found existing Codespace: {codespace_name}")
    else:
        user_output("No existing Codespace found, creating new one...")
        codespace_name = _create_codespace(repo)
        user_output(f"Codespace '{codespace_name}' created, waiting for ready...")
        _wait_for_codespace(codespace_name)
        user_output(click.style("✓ ", fg="green") + "Codespace ready.")
    user_output("")
    user_output("Once connected, run:")
    if description:
        user_output(f'  claude "/erk:craft-plan {description}"')
    else:
        user_output('  claude "/erk:craft-plan <description>"')
    user_output("")
    user_output("Connecting via SSH...")

    # Replace current process with SSH to Codespace
    ssh_cmd = ["gh", "codespace", "ssh", "-c", codespace_name]
    _print_command(ssh_cmd)
    os.execvp("gh", ssh_cmd)
    # Never returns - process is replaced
