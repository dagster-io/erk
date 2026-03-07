"""Real Codespace implementation using gh codespace ssh.

RealCodespace provides SSH execution to GitHub Codespaces using
the gh CLI tool.
"""

import json
import os
import subprocess
from typing import NoReturn

from erk_shared.gateway.codespace.abc import Codespace
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealCodespace(Codespace):
    """Production implementation using gh codespace ssh for remote execution."""

    def start_codespace(self, gh_name: str) -> None:
        """Start a stopped codespace.

        Uses GitHub REST API POST /user/codespaces/{name}/start to ensure
        the codespace is running.

        Args:
            gh_name: GitHub codespace name (from gh codespace list)
        """
        # GH-API-AUDIT: REST - codespace start
        run_subprocess_with_context(
            cmd=["gh", "api", "--method", "POST", f"/user/codespaces/{gh_name}/start"],
            operation_context=f"start codespace '{gh_name}'",
        )

    def exec_ssh_interactive(self, gh_name: str, remote_command: str) -> NoReturn:
        """Replace current process with SSH session to codespace.

        Uses os.execvp() to replace the current process with gh codespace ssh.

        Args:
            gh_name: GitHub codespace name (from gh codespace list)
            remote_command: Command to execute in the codespace

        Note:
            This method never returns - the process is replaced.
        """
        # GH-API-AUDIT: REST - codespace SSH connection
        # -t: Force pseudo-terminal allocation (required for interactive TUI)
        os.execvp(
            "gh",
            [
                "gh",
                "codespace",
                "ssh",
                "-c",
                gh_name,
                "--",
                "-t",
                remote_command,
            ],
        )

    def run_ssh_command(self, gh_name: str, remote_command: str) -> int:
        """Run SSH command in codespace and return exit code.

        Uses subprocess.run() to execute the command and wait for completion.

        Args:
            gh_name: GitHub codespace name (from gh codespace list)
            remote_command: Command to execute in the codespace

        Returns:
            Exit code from the remote command (0 for success)
        """
        # GH-API-AUDIT: REST - codespace SSH connection
        # Note: No -t flag for non-interactive (no TTY allocation)
        result = subprocess.run(
            [
                "gh",
                "codespace",
                "ssh",
                "-c",
                gh_name,
                "--",
                remote_command,
            ],
            check=False,
        )
        return result.returncode

    def get_repo_id(self, owner_repo: str) -> int:
        """Get GitHub repository database ID via REST API.

        Args:
            owner_repo: Repository in "owner/repo" format.

        Returns:
            The numeric repository ID.

        Raises:
            RuntimeError: If the API call fails.
        """
        # GH-API-AUDIT: REST - get repository ID
        result = run_subprocess_with_context(
            cmd=["gh", "api", f"repos/{owner_repo}", "--jq", ".id"],
            operation_context=f"get repository ID for '{owner_repo}'",
        )
        return int(result.stdout.strip())

    def create_codespace(
        self,
        *,
        repo_id: int,
        machine: str,
        display_name: str,
        branch: str | None,
    ) -> str:
        """Create a codespace via REST API.

        Args:
            repo_id: GitHub repository database ID.
            machine: Machine type for the codespace.
            display_name: Human-readable display name.
            branch: Branch to create codespace from, or None for default.

        Returns:
            The gh_name of the created codespace.

        Raises:
            RuntimeError: If the API call fails or response is malformed.
        """
        # GH-API-AUDIT: REST - POST user/codespaces
        cmd = [
            "gh",
            "api",
            "--method",
            "POST",
            "/user/codespaces",
            "-F",
            f"repository_id={repo_id}",
            "-f",
            f"machine={machine}",
            "-f",
            f"display_name={display_name}",
            "-f",
            "devcontainer_path=.devcontainer/devcontainer.json",
        ]

        if branch is not None:
            cmd.extend(["-f", f"ref={branch}"])

        result = run_subprocess_with_context(
            cmd=cmd,
            operation_context="create codespace",
        )

        response = json.loads(result.stdout)
        if "name" not in response:
            raise RuntimeError(
                f"API response missing 'name' field. Response: {result.stdout.strip()}"
            )
        return response["name"]
