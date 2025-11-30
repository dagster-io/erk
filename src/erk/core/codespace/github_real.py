"""Production implementation of CodespaceGitHub using gh CLI."""

import json
import os
import subprocess
from datetime import datetime

from erk_shared.integrations.time.abc import Time

from erk.core.codespace.github_abc import CodespaceGitHub
from erk.core.codespace.types import GitHubCodespaceInfo


class RealCodespaceGitHub(CodespaceGitHub):
    """Production implementation using gh CLI."""

    def __init__(self, time: Time) -> None:
        """Initialize with time dependency for polling.

        Args:
            time: Time implementation for sleep during polling
        """
        self._time = time

    def list_codespaces(self) -> list[GitHubCodespaceInfo]:
        """List all codespaces for the authenticated user."""
        result = subprocess.run(
            [
                "gh",
                "codespace",
                "list",
                "--json",
                "name,state,repository,gitStatus,machineName,createdAt",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to list codespaces: {result.stderr}")

        data = json.loads(result.stdout)
        codespaces = []
        for cs in data:
            # Extract branch from gitStatus
            git_status = cs.get("gitStatus", {})
            branch = git_status.get("ref", "unknown")

            # Parse created_at - handle both formats
            created_at_str = cs.get("createdAt", "")
            if created_at_str:
                # Handle ISO format with Z suffix
                created_at_str = created_at_str.rstrip("Z")
                # Handle microseconds (truncate if too long)
                if "." in created_at_str:
                    base, frac = created_at_str.split(".")
                    frac = frac[:6]  # Truncate to microseconds
                    created_at_str = f"{base}.{frac}"
                created_at = datetime.fromisoformat(created_at_str)
            else:
                created_at = datetime.now()

            codespaces.append(
                GitHubCodespaceInfo(
                    name=cs["name"],
                    state=cs["state"],
                    repository=cs["repository"],
                    branch=branch,
                    machine_type=cs.get("machineName", "unknown"),
                    created_at=created_at,
                )
            )

        return codespaces

    def get_codespace(self, gh_name: str) -> GitHubCodespaceInfo | None:
        """Get codespace by exact name match."""
        codespaces = self.list_codespaces()
        for cs in codespaces:
            if cs.name == gh_name:
                return cs
        return None

    def create_codespace(
        self,
        repo: str,
        branch: str,
        machine_type: str = "standardLinux32gb",
    ) -> GitHubCodespaceInfo:
        """Create a new codespace."""
        result = subprocess.run(
            [
                "gh",
                "codespace",
                "create",
                "--repo",
                repo,
                "--branch",
                branch,
                "--machine",
                machine_type,
                "--devcontainer-path",
                ".devcontainer/devcontainer.json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create codespace: {result.stderr}")

        # The output contains the codespace name
        codespace_name = result.stdout.strip()

        # Fetch full info
        info = self.get_codespace(codespace_name)
        if info is None:
            # Return minimal info if we can't fetch full details
            return GitHubCodespaceInfo(
                name=codespace_name,
                state="Pending",
                repository=repo,
                branch=branch,
                machine_type=machine_type,
                created_at=datetime.now(),
            )

        return info

    def wait_for_available(
        self,
        gh_name: str,
        timeout_seconds: int = 300,
    ) -> bool:
        """Wait for codespace to become available."""
        poll_interval = 5  # seconds
        elapsed = 0

        while elapsed < timeout_seconds:
            info = self.get_codespace(gh_name)
            if info and info.state == "Available":
                return True

            self._time.sleep(poll_interval)
            elapsed += poll_interval

        return False

    def ssh_interactive(self, gh_name: str) -> int:
        """Open interactive SSH session, return exit code."""
        result = subprocess.run(
            ["gh", "codespace", "ssh", "-c", gh_name],
            check=False,
        )
        return result.returncode

    def ssh_replace(self, gh_name: str) -> None:
        """Replace process with SSH (never returns on success)."""
        os.execvp("gh", ["gh", "codespace", "ssh", "-c", gh_name])
