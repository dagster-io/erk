"""Fake ClaudeLauncher implementation for testing.

FakeClaudeLauncher is an in-memory implementation that tracks launch calls
without actually executing Claude or replacing the process, enabling fast
and deterministic tests.
"""

from dataclasses import dataclass
from typing import NoReturn

from erk_shared.context.types import InteractiveClaudeConfig
from erk_shared.gateway.claude_launcher.abc import ClaudeLauncher


@dataclass(frozen=True)
class ClaudeLaunchCall:
    """Record of a Claude launch call for test assertions.

    Attributes:
        config: InteractiveClaudeConfig that was used
        command: Command that was passed to Claude
    """

    config: InteractiveClaudeConfig
    command: str


class FakeClaudeLauncher(ClaudeLauncher):
    """In-memory fake implementation that tracks Claude launch calls.

    This class has NO public setup methods. All state is captured during execution.
    """

    def __init__(self) -> None:
        """Create FakeClaudeLauncher."""
        self._launch_calls: list[ClaudeLaunchCall] = []
        self._launch_called = False

    @property
    def launch_calls(self) -> list[ClaudeLaunchCall]:
        """Get the list of launch calls that were made.

        Returns a copy of the list to prevent external mutation.

        This property is for test assertions only.
        """
        return list(self._launch_calls)

    @property
    def launch_called(self) -> bool:
        """Check if launch_interactive was called.

        This property is for test assertions only.
        """
        return self._launch_called

    @property
    def last_call(self) -> ClaudeLaunchCall | None:
        """Get the last launch call, or None if no calls were made.

        This property is for test assertions only.
        """
        if not self._launch_calls:
            return None
        return self._launch_calls[-1]

    def launch_interactive(self, config: InteractiveClaudeConfig, *, command: str) -> NoReturn:
        """Track Claude launch call.

        In production, this replaces the process. In tests, we record the call
        and raise SystemExit to simulate the process ending.

        Args:
            config: InteractiveClaudeConfig with resolved values
            command: The slash command to execute (empty string for no command)

        Raises:
            SystemExit: Always raised to simulate process replacement
        """
        self._launch_called = True
        self._launch_calls.append(ClaudeLaunchCall(config=config, command=command))
        # Simulate process replacement by exiting
        raise SystemExit(0)
