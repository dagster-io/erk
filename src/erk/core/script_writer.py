"""Activation script writing operations.

This module provides the RealScriptWriter implementation.
ABC and types are imported from erk_shared.core.
"""

from pathlib import Path

from erk.cli.shell_utils import write_script_to_path, write_script_to_temp
from erk_shared.core.script_writer import ScriptResult as ScriptResult
from erk_shared.core.script_writer import ScriptWriter as ScriptWriter


class RealScriptWriter(ScriptWriter):
    """Production implementation that writes real temp files."""

    def write_activation_script(
        self,
        content: str,
        *,
        command_name: str,
        comment: str,
    ) -> ScriptResult:
        """Write activation script to temp file.

        Args:
            content: The shell script content
            command_name: Command generating the script
            comment: Description for the script header

        Returns:
            ScriptResult with path to created temp file and full content
        """
        script_path = write_script_to_temp(
            content,
            command_name=command_name,
            comment=comment,
        )

        # Read back the full content that was written (includes headers)
        full_content = script_path.read_text(encoding="utf-8")

        return ScriptResult(path=script_path, content=full_content)

    def write_worktree_script(
        self,
        content: str,
        *,
        worktree_path: Path,
        script_name: str,
        command_name: str,
        comment: str,
    ) -> ScriptResult:
        """Write script to a worktree's .erk/bin/ directory.

        Args:
            content: The shell script content
            worktree_path: Path to the worktree directory
            script_name: Name of the script file (e.g., 'land' -> land.sh)
            command_name: Command generating the script
            comment: Description for the script header

        Returns:
            ScriptResult with path to script and full content
        """
        bin_dir = worktree_path / ".erk" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        script_path = bin_dir / f"{script_name}.sh"

        write_script_to_path(
            content,
            script_path,
            command_name=command_name,
            comment=comment,
        )

        # Read back the full content that was written (includes headers)
        full_content = script_path.read_text(encoding="utf-8")

        return ScriptResult(path=script_path, content=full_content)
