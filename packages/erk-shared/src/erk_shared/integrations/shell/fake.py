"""Fake implementation of Shell for testing.

This fake enables testing shell-dependent functionality without
requiring specific shell configurations or installed tools.
"""

import subprocess
from pathlib import Path

from erk_shared.integrations.shell.abc import Shell


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
        claude_extraction_raises: bool = False,
        extraction_plan_url: str | None = None,
    ) -> None:
        """Initialize fake with predetermined shell and tool availability.

        Args:
            detected_shell: Shell to return from detect_shell(), or None if no shell
                should be detected. Format: (shell_name, rc_file_path)
            installed_tools: Mapping of tool name to executable path. Tools not in
                this mapping will return None from get_installed_tool_path()
            claude_extraction_raises: If True, run_claude_extraction_plan will raise
                CalledProcessError
            extraction_plan_url: URL to return from run_claude_extraction_plan on success
        """
        self._detected_shell = detected_shell
        self._installed_tools = installed_tools or {}
        self._extraction_calls: list[Path] = []
        self._claude_extraction_raises = claude_extraction_raises
        self._extraction_plan_url = extraction_plan_url

    def detect_shell(self) -> tuple[str, Path] | None:
        """Return the shell configured at construction time."""
        return self._detected_shell

    def get_installed_tool_path(self, tool_name: str) -> str | None:
        """Return the tool path if configured, None otherwise."""
        return self._installed_tools.get(tool_name)

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
