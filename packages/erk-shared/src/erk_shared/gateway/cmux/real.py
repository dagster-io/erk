"""Real cmux implementation using subprocess calls."""

import subprocess

from erk_shared.gateway.cmux.abc import Cmux


class RealCmux(Cmux):
    """Production cmux implementation that shells out to the cmux CLI."""

    def create_workspace(self, *, command: str) -> str:
        """Create a new cmux workspace by running cmux new-workspace.

        Parses the workspace reference from stdout (second whitespace-delimited
        field, matching the ``awk '{print $2}'`` pattern).

        Args:
            command: Shell command to execute in the new workspace.

        Returns:
            Workspace reference string.

        Raises:
            RuntimeError: If cmux new-workspace fails.
        """
        try:
            result = subprocess.run(
                ["cmux", "new-workspace", "--command", command],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip() if e.stderr else e.stdout.strip()
            raise RuntimeError(
                f"cmux new-workspace failed: {error_output}"
            ) from e

        # Parse workspace ref from output (awk '{print $2}' equivalent)
        stdout = result.stdout.strip()
        parts = stdout.split()
        if len(parts) >= 2:
            return parts[1]
        return stdout

    def rename_workspace(self, *, workspace_ref: str, new_name: str) -> None:
        """Rename a cmux workspace by running cmux rename-workspace.

        Args:
            workspace_ref: Reference to the workspace to rename.
            new_name: New name for the workspace.

        Raises:
            RuntimeError: If cmux rename-workspace fails.
        """
        try:
            subprocess.run(
                ["cmux", "rename-workspace", "--workspace", workspace_ref, new_name],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip() if e.stderr else e.stdout.strip()
            raise RuntimeError(
                f"cmux rename-workspace failed: {error_output}"
            ) from e
