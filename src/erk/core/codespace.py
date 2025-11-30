"""Codespace service for remote and local planning.

This module provides abstraction over GitHub Codespace operations, enabling
dependency injection for testing without mock.patch.
"""

import json
import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import click
from erk_shared.output.output import user_output


@dataclass
class CodespaceInfo:
    """Information about a Codespace.

    Attributes:
        name: The unique name of the Codespace
        state: Current state (Available, Shutdown, etc.)
        repository: Repository in 'owner/repo' format
        branch: The git branch the Codespace is on
    """

    name: str
    state: str
    repository: str
    branch: str


class Codespace(ABC):
    """Abstract interface for Codespace operations.

    This abstraction enables testing without mock.patch by making Codespace
    operations an injectable dependency.
    """

    @abstractmethod
    def get_repo_name(self) -> str:
        """Get the current repository's name with owner.

        Returns:
            Repository name in 'owner/repo' format.

        Raises:
            SystemExit: If gh command fails or repo info cannot be retrieved.
        """
        ...

    @abstractmethod
    def get_current_branch(self) -> str:
        """Get the current git branch name.

        Returns:
            Current branch name.

        Raises:
            SystemExit: If git command fails.
        """
        ...

    @abstractmethod
    def find_existing_codespace(self, repo: str, branch: str) -> str | None:
        """Find an existing available Codespace for the given repo and branch.

        Args:
            repo: Repository name in 'owner/repo' format.
            branch: Branch name to match.

        Returns:
            Codespace name if found, None otherwise.
        """
        ...

    @abstractmethod
    def create_codespace(self, repo: str, branch: str) -> str:
        """Create a new GitHub Codespace.

        Args:
            repo: Repository name in 'owner/repo' format.
            branch: Branch name to create Codespace on.

        Returns:
            Name of the created Codespace.

        Raises:
            SystemExit: If Codespace creation fails.
        """
        ...

    @abstractmethod
    def wait_for_codespace(self, codespace_name: str, timeout_seconds: int = 300) -> None:
        """Wait for Codespace to become available.

        Args:
            codespace_name: Name of the Codespace to wait for.
            timeout_seconds: Maximum time to wait in seconds.

        Raises:
            SystemExit: If Codespace doesn't become available within timeout.
        """
        ...

    @abstractmethod
    def is_claude_available(self) -> bool:
        """Check if Claude CLI is installed and available.

        Returns:
            True if Claude CLI is available, False otherwise.
        """
        ...

    @abstractmethod
    def exec_ssh_with_claude(self, codespace_name: str, slash_cmd: str) -> None:
        """SSH to Codespace and execute Claude with the given command.

        This replaces the current process with SSH.

        Args:
            codespace_name: Name of the Codespace to connect to.
            slash_cmd: The slash command to pass to Claude.
        """
        ...

    @abstractmethod
    def exec_claude_local(self, slash_cmd: str) -> None:
        """Execute Claude locally with the given command.

        This replaces the current process with Claude.

        Args:
            slash_cmd: The slash command to pass to Claude.
        """
        ...

    def get_or_create_codespace(self, repo: str, branch: str) -> str:
        """Get an existing Codespace or create a new one.

        Args:
            repo: Repository name in 'owner/repo' format.
            branch: Branch name.

        Returns:
            Name of the available Codespace.
        """
        user_output(f"Checking for existing Codespace on {branch}...")
        existing = self.find_existing_codespace(repo, branch)

        if existing:
            user_output(click.style("-> ", fg="green") + f"Found existing Codespace: {existing}")
            return existing

        user_output("No existing Codespace found, creating new one...")
        codespace_name = self.create_codespace(repo, branch)
        user_output(f"Codespace '{codespace_name}' created, waiting for ready...")
        self.wait_for_codespace(codespace_name)
        user_output(click.style("-> ", fg="green") + "Codespace ready.")
        return codespace_name

    def run_remote_planning(self, description: str) -> None:
        """Create/reuse Codespace and auto-execute Claude with /erk:craft-plan.

        Args:
            description: Optional description for the planning session.
        """
        repo = self.get_repo_name()
        branch = self.get_current_branch()
        codespace_name = self.get_or_create_codespace(repo, branch)

        # Build slash command
        slash_cmd = "/erk:craft-plan"
        if description:
            slash_cmd = f"/erk:craft-plan {description}"

        user_output("")
        user_output("Connecting to Codespace and starting planning...")
        self.exec_ssh_with_claude(codespace_name, slash_cmd)

    def run_local_planning(self, description: str) -> None:
        """Run Claude with /erk:craft-plan in current directory.

        Args:
            description: Optional description for the planning session.
        """
        if not self.is_claude_available():
            user_output(click.style("Error: ", fg="red") + "Claude CLI not found.")
            raise SystemExit(1)

        slash_cmd = "/erk:craft-plan"
        if description:
            slash_cmd = f"/erk:craft-plan {description}"

        user_output("Starting local planning...")
        self.exec_claude_local(slash_cmd)


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


class RealCodespace(Codespace):
    """Production implementation using gh CLI and subprocess."""

    def get_repo_name(self) -> str:
        """Get the current repository's name with owner."""
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
                click.style("Error: ", fg="red")
                + "Could not determine repository name from gh output."
            )
            raise SystemExit(1)

        return repo_name

    def get_current_branch(self) -> str:
        """Get the current git branch name."""
        result = _run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])

        if result.returncode != 0:
            user_output(
                click.style("Error: ", fg="red")
                + "Failed to get current branch.\n\n"
                + "Make sure you're in a git repository."
            )
            raise SystemExit(1)

        return result.stdout.strip()

    def find_existing_codespace(self, repo: str, branch: str) -> str | None:
        """Find an existing available Codespace for the given repo and branch."""
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

    def create_codespace(self, repo: str, branch: str) -> str:
        """Create a new GitHub Codespace."""
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
            user_output(
                click.style("Error: ", fg="red") + "Codespace creation returned empty name."
            )
            raise SystemExit(1)

        return codespace_name

    def wait_for_codespace(self, codespace_name: str, timeout_seconds: int = 300) -> None:
        """Wait for Codespace to become available."""
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

    def is_claude_available(self) -> bool:
        """Check if Claude CLI is installed and available."""
        return shutil.which("claude") is not None

    def exec_ssh_with_claude(self, codespace_name: str, slash_cmd: str) -> None:
        """SSH to Codespace and execute Claude with the given command."""
        ssh_cmd = [
            "gh",
            "codespace",
            "ssh",
            "-c",
            codespace_name,
            "--",
            "claude",
            "--permission-mode",
            "acceptEdits",
            slash_cmd,
        ]
        _print_command(ssh_cmd)
        os.execvp("gh", ssh_cmd)

    def exec_claude_local(self, slash_cmd: str) -> None:
        """Execute Claude locally with the given command."""
        cmd = ["claude", "--permission-mode", "acceptEdits", slash_cmd]
        _print_command(cmd)
        os.execvp("claude", cmd)


@dataclass
class FakeCodespace(Codespace):
    """Fake implementation for testing.

    All state is provided via constructor. No real subprocess calls are made.
    """

    repo_name: str = "owner/repo"
    current_branch: str = "main"
    existing_codespaces: list[CodespaceInfo] = field(default_factory=list)
    created_codespace_name: str = "fake-codespace"
    claude_available: bool = True

    # Mutation tracking
    created_codespaces: list[tuple[str, str]] = field(default_factory=list)
    waited_for: list[str] = field(default_factory=list)
    ssh_commands: list[tuple[str, str]] = field(default_factory=list)
    local_commands: list[str] = field(default_factory=list)

    def get_repo_name(self) -> str:
        """Return pre-configured repo name."""
        return self.repo_name

    def get_current_branch(self) -> str:
        """Return pre-configured branch name."""
        return self.current_branch

    def find_existing_codespace(self, repo: str, branch: str) -> str | None:
        """Find matching codespace from pre-configured list."""
        for cs in self.existing_codespaces:
            if cs.repository == repo and cs.state == "Available" and cs.branch == branch:
                return cs.name
        return None

    def create_codespace(self, repo: str, branch: str) -> str:
        """Record codespace creation and return pre-configured name."""
        self.created_codespaces.append((repo, branch))
        return self.created_codespace_name

    def wait_for_codespace(self, codespace_name: str, timeout_seconds: int = 300) -> None:
        """Record wait call (no actual waiting in fake)."""
        self.waited_for.append(codespace_name)

    def is_claude_available(self) -> bool:
        """Return pre-configured availability."""
        return self.claude_available

    def exec_ssh_with_claude(self, codespace_name: str, slash_cmd: str) -> None:
        """Record SSH command (no actual execution in fake)."""
        self.ssh_commands.append((codespace_name, slash_cmd))

    def exec_claude_local(self, slash_cmd: str) -> None:
        """Record local command (no actual execution in fake)."""
        self.local_commands.append(slash_cmd)


# Module-level convenience functions using RealCodespace
# These maintain backward compatibility with the previous API


def get_repo_name() -> str:
    """Get the current repository's name with owner."""
    return RealCodespace().get_repo_name()


def get_current_branch() -> str:
    """Get the current git branch name."""
    return RealCodespace().get_current_branch()


def find_existing_codespace(repo: str, branch: str) -> str | None:
    """Find an existing available Codespace for the given repo and branch."""
    return RealCodespace().find_existing_codespace(repo, branch)


def create_codespace(repo: str, branch: str) -> str:
    """Create a new GitHub Codespace."""
    return RealCodespace().create_codespace(repo, branch)


def wait_for_codespace(codespace_name: str, timeout_seconds: int = 300) -> None:
    """Wait for Codespace to become available."""
    return RealCodespace().wait_for_codespace(codespace_name, timeout_seconds)


def get_or_create_codespace(repo: str, branch: str) -> str:
    """Get an existing Codespace or create a new one."""
    return RealCodespace().get_or_create_codespace(repo, branch)


def run_remote_planning(description: str) -> None:
    """Create/reuse Codespace and auto-execute Claude with /erk:craft-plan."""
    return RealCodespace().run_remote_planning(description)


def run_local_planning(description: str) -> None:
    """Run Claude with /erk:craft-plan in current directory."""
    return RealCodespace().run_local_planning(description)
