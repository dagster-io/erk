"""Fake implementation of ScriptWriter for testing."""

import os
import uuid
from datetime import datetime
from pathlib import Path

from erk.core.script_writer import ScriptResult, ScriptWriter


class FakeScriptWriter(ScriptWriter):
    """In-memory fake for script writing operations.

    Stores scripts in memory using sentinel paths instead of creating
    actual temp files. This allows tests to verify script content
    without filesystem I/O.
    """

    def __init__(self) -> None:
        """Initialize empty script storage."""
        self._scripts: dict[Path, str] = {}
        self.last_script: ScriptResult | None = None

    def write_activation_script(
        self,
        content: str,
        *,
        command_name: str,
        comment: str,
    ) -> ScriptResult:
        """Write script to in-memory storage with sentinel path.

        Args:
            content: The shell script content
            command_name: Command generating the script
            comment: Description for the script header

        Returns:
            ScriptResult with sentinel path and full content including headers
        """
        # Generate unique ID (same pattern as real implementation)
        unique_id = uuid.uuid4().hex[:8]

        # Use sentinel path instead of real temp file
        script_path = Path(f"/test/script/erk-{command_name}-{unique_id}.sh")

        # Build header (same structure as real implementation)
        header = [
            "#!/bin/bash",
            f"# erk {command_name}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# UUID: {unique_id}",
            f"# User: {os.getenv('USER', 'unknown')}",
            f"# Working dir: {Path.cwd()}",
            f"# {comment}",
            "",  # Blank line before script
        ]

        full_content = "\n".join(header) + "\n" + content

        # Store in memory
        self._scripts[script_path] = full_content

        # Track last script for test assertions
        result = ScriptResult(path=script_path, content=full_content)
        self.last_script = result

        return result

    def write_worktree_script(
        self,
        content: str,
        *,
        worktree_path: Path,
        script_name: str,
        command_name: str,
        comment: str,
    ) -> "ScriptResult":
        """Write script to worktree location with sentinel path.

        For testing, we use a sentinel path that matches the expected real path
        pattern but don't actually write to the filesystem.

        Args:
            content: The shell script content
            worktree_path: Path to the worktree directory
            script_name: Name of the script file (e.g., 'land')
            command_name: Command generating the script
            comment: Description for the script header

        Returns:
            ScriptResult with sentinel path and full content including headers
        """
        # Generate unique ID (same pattern as real implementation)
        unique_id = uuid.uuid4().hex[:8]

        # Use the real target path as sentinel (tests can check this)
        script_path = worktree_path / ".erk" / "bin" / f"{script_name}.sh"

        # Build header (same structure as real implementation)
        header = [
            "#!/bin/bash",
            f"# erk {command_name}",
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# UUID: {unique_id}",
            f"# User: {os.getenv('USER', 'unknown')}",
            f"# Working dir: {Path.cwd()}",
            f"# {comment}",
            "",  # Blank line before script
        ]

        full_content = "\n".join(header) + "\n" + content

        # Store in memory
        self._scripts[script_path] = full_content

        # Track last script for test assertions
        result = ScriptResult(path=script_path, content=full_content)
        self.last_script = result

        return result

    def get_script_content(self, path: Path) -> str | None:
        """Get stored script content for test assertions.

        Args:
            path: Sentinel path returned by write_activation_script()

        Returns:
            Script content if found, None otherwise
        """
        return self._scripts.get(path)

    @property
    def written_scripts(self) -> dict[Path, str]:
        """Read-only view of all written scripts.

        Returns:
            Mapping of sentinel paths to script content
        """
        return dict(self._scripts)
