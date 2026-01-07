"""Fake implementation of Shell for testing.

This fake enables testing shell-dependent functionality without
requiring specific shell configurations or installed tools.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.shell.abc import Shell


@dataclass(frozen=True)
class SpawnSubshellCall:
    """Record of a spawn_subshell call for test assertions."""

    cwd: Path
    shell_path: str
    command: str
    env: dict[str, str]


class FakeShell(Shell):
    """In-memory fake implementation of shell operations.

    Constructor Injection:
    - All state is provided via constructor parameters
    - No mutations occur (immutable after construction)

    When to Use:
    - Testing shell-dependent commands (e.g., init, shell setup)
    - Simulating different shell environments (bash, zsh, fish)
    - Testing behavior when tools are/aren't installed

    Examples:
        # Test with bash shell detected
        >>> shell_ops = FakeShell(
        ...     detected_shell=("bash", Path.home() / ".bashrc")
        ... )
        >>> result = shell_ops.detect_shell()
        >>> assert result == ("bash", Path.home() / ".bashrc")

        # Test with tool installed
        >>> shell_ops = FakeShell(
        ...     installed_tools={"gt": "/usr/local/bin/gt"}
        ... )
        >>> gt_path = shell_ops.get_installed_tool_path("gt")
        >>> assert gt_path == "/usr/local/bin/gt"

        # Test with no shell detected
        >>> shell_ops = FakeShell(detected_shell=None)
        >>> result = shell_ops.detect_shell()
        >>> assert result is None
    """

    def __init__(
        self,
        *,
        detected_shell: tuple[str, Path] | None = None,
        installed_tools: dict[str, str] | None = None,
        tool_versions: dict[str, str] | None = None,
        claude_extraction_raises: bool = False,
        extraction_plan_url: str | None = None,
        subshell_exit_code: int = 0,
    ) -> None:
        """Initialize fake with predetermined shell and tool availability.

        Args:
            detected_shell: Shell to return from detect_shell(), or None if no shell
                should be detected. Format: (shell_name, rc_file_path)
            installed_tools: Mapping of tool name to executable path. Tools not in
                this mapping will return None from get_installed_tool_path()
            tool_versions: Mapping of tool name to version string. Tools not in
                this mapping will return None from get_tool_version()
            claude_extraction_raises: If True, run_claude_extraction_plan will raise
                CalledProcessError
            extraction_plan_url: URL to return from run_claude_extraction_plan on success
            subshell_exit_code: Exit code to return from spawn_subshell()
        """
        self._detected_shell = detected_shell
        self._installed_tools = installed_tools or {}
        self._tool_versions = tool_versions or {}
        self._extraction_calls: list[Path] = []
        self._claude_extraction_raises = claude_extraction_raises
        self._extraction_plan_url = extraction_plan_url
        self._subshell_exit_code = subshell_exit_code
        self._subshell_calls: list[SpawnSubshellCall] = []

    def detect_shell(self) -> tuple[str, Path] | None:
        """Return the shell configured at construction time."""
        return self._detected_shell

    def get_installed_tool_path(self, tool_name: str) -> str | None:
        """Return the tool path if configured, None otherwise."""
        return self._installed_tools.get(tool_name)

    def get_tool_version(self, tool_name: str) -> str | None:
        """Return the tool version if configured, None otherwise."""
        return self._tool_versions.get(tool_name)

    def run_claude_extraction_plan(self, cwd: Path) -> str | None:
        """Track call to run_claude_extraction_plan without executing anything.

        This method records the call parameters for test assertions.
        Raises subprocess.CalledProcessError if configured to do so.
        Returns the configured extraction_plan_url on success.
        """
        self._extraction_calls.append(cwd)
        if self._claude_extraction_raises:
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=["erk", "plan", "extraction", "raw"],
                stderr="Simulated extraction failure",
            )
        return self._extraction_plan_url

    @property
    def extraction_calls(self) -> list[Path]:
        """Get the list of run_claude_extraction_plan() calls that were made.

        Returns list of cwd paths where extraction was invoked.

        This property is for test assertions only.
        """
        return self._extraction_calls.copy()

    def spawn_subshell(
        self,
        *,
        cwd: Path,
        shell_path: str,
        command: str,
        env: dict[str, str],
    ) -> int:
        """Record spawn_subshell call and return configured exit code.

        This method records the call parameters for test assertions.
        Returns the exit code configured at construction time.
        """
        self._subshell_calls.append(
            SpawnSubshellCall(
                cwd=cwd,
                shell_path=shell_path,
                command=command,
                env=env.copy(),
            )
        )
        return self._subshell_exit_code

    @property
    def subshell_calls(self) -> list[SpawnSubshellCall]:
        """Get the list of spawn_subshell() calls that were made.

        Returns list of SpawnSubshellCall records with call parameters.

        This property is for test assertions only.
        """
        return self._subshell_calls.copy()
