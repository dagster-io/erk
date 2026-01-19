"""Docker execution for isolated implementation mode.

This module provides utilities for running Claude Code inside a Docker container
with filesystem isolation. The container can only access the mounted worktree,
making --dangerously-skip-permissions safe to use.

Key design:
- Auto-builds the erk-local image if not present
- Mounts worktree to /workspace
- Mounts ~/.claude/ for auth preservation
- Mounts ~/.ssh/ read-only for git push operations
- Uses --user flag to match host UID/GID for file permissions
"""

import os
import shutil
import subprocess
from pathlib import Path

import click

DEFAULT_DOCKER_IMAGE = "erk-local:latest"
DEFAULT_DOCKERFILE_PATH = ".erk/docker/Dockerfile"
CONTAINER_WORKSPACE = "/workspace"
CONTAINER_CLAUDE_DIR = "/home/ci-user/.claude"
CONTAINER_SSH_DIR = "/home/ci-user/.ssh"


def is_docker_available() -> bool:
    """Check if Docker CLI is available in PATH."""
    return shutil.which("docker") is not None


def image_exists(image_name: str) -> bool:
    """Check if a Docker image exists locally.

    Args:
        image_name: Name of the Docker image (e.g., "erk-local:latest")

    Returns:
        True if image exists, False otherwise
    """
    result = subprocess.run(
        ["docker", "image", "inspect", image_name],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def build_docker_image(
    *,
    repo_root: Path,
    image_name: str,
    dockerfile_path: str,
) -> None:
    """Build the Docker image from the Dockerfile.

    Args:
        repo_root: Path to repository root containing Dockerfile
        image_name: Name for the built image (e.g., "erk-local")
        dockerfile_path: Relative path to Dockerfile from repo root

    Raises:
        RuntimeError: If Docker build fails
    """
    dockerfile_full_path = repo_root / dockerfile_path
    if not dockerfile_full_path.exists():
        raise RuntimeError(
            f"Dockerfile not found at {dockerfile_full_path}\n"
            "Expected: .erk/docker/Dockerfile in erk repository"
        )

    click.echo(f"Building Docker image {image_name}...", err=True)

    # Build the image - need context for the COPY instruction
    result = subprocess.run(
        [
            "docker",
            "build",
            "-t",
            image_name.split(":")[0],  # Use base name without tag
            "-f",
            str(dockerfile_full_path),
            str(repo_root),  # Build context at repo root
        ],
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Docker build failed with exit code {result.returncode}\n"
            f"Run 'docker build -t {image_name.split(':')[0]} "
            f"-f {dockerfile_path} .' manually to see full output"
        )

    click.echo("Docker image built successfully", err=True)


def ensure_docker_image(
    *,
    repo_root: Path,
    image_name: str,
) -> None:
    """Ensure the Docker image exists, building it if necessary.

    Args:
        repo_root: Path to repository root
        image_name: Docker image name

    Raises:
        RuntimeError: If Docker is not available or build fails
    """
    if not is_docker_available():
        raise RuntimeError(
            "Docker CLI not found\nInstall Docker from: https://docs.docker.com/get-docker/"
        )

    if not image_exists(image_name):
        build_docker_image(
            repo_root=repo_root,
            image_name=image_name,
            dockerfile_path=DEFAULT_DOCKERFILE_PATH,
        )


def build_docker_run_args(
    *,
    worktree_path: Path,
    image_name: str,
    interactive: bool,
    home_dir: Path | None,
) -> list[str]:
    """Build the docker run command arguments.

    Args:
        worktree_path: Path to the worktree to mount
        image_name: Docker image name
        interactive: Whether to run in interactive mode (TTY)
        home_dir: Home directory for locating .claude/ and .ssh/ dirs.
            If None, uses Path.home(). Pass explicitly for testability.

    Returns:
        List of docker run arguments
    """
    # Get host user UID/GID for permission matching
    uid = os.getuid()
    gid = os.getgid()

    # Get host paths for mounts
    resolved_home = home_dir if home_dir is not None else Path.home()
    claude_dir = resolved_home / ".claude"
    ssh_dir = resolved_home / ".ssh"

    args = ["docker", "run", "--rm"]

    if interactive:
        args.extend(["-it"])

    # User mapping for file permissions
    args.extend(["--user", f"{uid}:{gid}"])

    # Volume mounts
    args.extend(["-v", f"{worktree_path}:{CONTAINER_WORKSPACE}"])

    if claude_dir.exists():
        args.extend(["-v", f"{claude_dir}:{CONTAINER_CLAUDE_DIR}"])

    if ssh_dir.exists():
        args.extend(["-v", f"{ssh_dir}:{CONTAINER_SSH_DIR}:ro"])

    # Working directory
    args.extend(["-w", CONTAINER_WORKSPACE])

    # Image
    args.append(image_name)

    return args


def build_claude_command_args(
    *,
    interactive: bool,
    dangerous: bool,
    model: str | None,
    command: str,
) -> list[str]:
    """Build Claude CLI command arguments for Docker execution.

    Args:
        interactive: Whether running in interactive mode
        dangerous: Whether to skip permission prompts (always True with Docker)
        model: Optional model name (haiku, sonnet, opus)
        command: Slash command to execute

    Returns:
        List of claude command arguments
    """
    # Always use --dangerously-skip-permissions with Docker (isolation provides safety)
    args = ["claude", "--dangerously-skip-permissions"]

    if not interactive:
        args.extend(["--print", "--verbose", "--output-format", "stream-json"])

    if model is not None:
        args.extend(["--model", model])

    args.append(command)

    return args


def execute_docker_interactive(
    *,
    repo_root: Path,
    worktree_path: Path,
    image_name: str,
    model: str | None,
) -> None:
    """Execute Claude in Docker interactively, replacing current process.

    Args:
        repo_root: Repository root for Dockerfile lookup
        worktree_path: Path to worktree to mount
        image_name: Docker image name
        model: Optional model name

    Raises:
        RuntimeError: If Docker is not available or image build fails

    Note:
        This function never returns - process is replaced.
    """
    ensure_docker_image(repo_root=repo_root, image_name=image_name)

    docker_args = build_docker_run_args(
        worktree_path=worktree_path,
        image_name=image_name,
        interactive=True,
        home_dir=None,  # Use real home directory
    )

    claude_args = build_claude_command_args(
        interactive=True,
        dangerous=True,  # Always skip permissions in Docker
        model=model,
        command="/erk:system:impl-execute",
    )

    full_args = docker_args + claude_args

    click.echo("Launching Claude in Docker...", err=True)

    # Replace current process with docker
    os.execvp("docker", full_args)
    # Never returns


def execute_docker_non_interactive(
    *,
    repo_root: Path,
    worktree_path: Path,
    image_name: str,
    model: str | None,
    commands: list[str],
    verbose: bool,
) -> int:
    """Execute Claude commands in Docker non-interactively.

    Args:
        repo_root: Repository root for Dockerfile lookup
        worktree_path: Path to worktree to mount
        image_name: Docker image name
        model: Optional model name
        commands: List of slash commands to execute
        verbose: Whether to show verbose output

    Returns:
        Exit code (0 for success, non-zero for failure)

    Raises:
        RuntimeError: If Docker is not available or image build fails
    """
    ensure_docker_image(repo_root=repo_root, image_name=image_name)

    for command in commands:
        docker_args = build_docker_run_args(
            worktree_path=worktree_path,
            image_name=image_name,
            interactive=False,
            home_dir=None,  # Use real home directory
        )

        claude_args = build_claude_command_args(
            interactive=False,
            dangerous=True,  # Always skip permissions in Docker
            model=model,
            command=command,
        )

        full_args = docker_args + claude_args

        if verbose:
            click.echo(f"Running {command} in Docker...", err=True)
            result = subprocess.run(full_args, check=False)
        else:
            # Stream output for progress
            result = subprocess.run(full_args, check=False)

        if result.returncode != 0:
            click.echo(f"Command {command} failed with exit code {result.returncode}", err=True)
            return result.returncode

    return 0
