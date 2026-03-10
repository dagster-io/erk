"""Fake AgentLauncher implementation for testing.

FakeAgentLauncher is an in-memory implementation that tracks launch calls
without actually executing Claude or replacing the process, enabling fast
and deterministic tests.
"""

from dataclasses import dataclass
from typing import NoReturn

from erk_shared.context.types import InteractiveAgentConfig
from erk_shared.gateway.agent_launcher.abc import AgentLauncher


@dataclass(frozen=True)
class AgentLaunchCall:
    """Record of an agent launch call for test assertions.

    Attributes:
        config: InteractiveAgentConfig that was used
        command: Command that was passed to Claude
    """

    config: InteractiveAgentConfig
    command: str


class FakeAgentLauncher(AgentLauncher):
    """In-memory fake implementation that tracks agent launch calls.

    This class has NO public setup methods. All state is captured during execution.
    """

    def __init__(self, *, launch_error: str | None = None) -> None:
        """Create FakeAgentLauncher.

        Args:
            launch_error: If set, launch_interactive raises RuntimeError with this message.
                Use to simulate Claude CLI not being installed.
        """
        self._launch_calls: list[AgentLaunchCall] = []
        self._launch_called = False
        self._launch_error = launch_error

    @property
    def launch_calls(self) -> list[AgentLaunchCall]:
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
    def last_call(self) -> AgentLaunchCall | None:
        """Get the last launch call, or None if no calls were made.

        This property is for test assertions only.
        """
        if not self._launch_calls:
            return None
        return self._launch_calls[-1]

    def launch_interactive(self, config: InteractiveAgentConfig, *, command: str) -> NoReturn:
        """Track agent launch call.

        In production, this replaces the process. In tests, we record the call
        and raise SystemExit to simulate the process ending.

        Args:
            config: InteractiveAgentConfig with resolved values
            command: The slash command to execute (empty string for no command)

        Raises:
            SystemExit: Always raised to simulate process replacement
        """
        if self._launch_error is not None:
            raise RuntimeError(self._launch_error)
        self._launch_called = True
        self._launch_calls.append(AgentLaunchCall(config=config, command=command))
        # Simulate process replacement by exiting
        raise SystemExit(0)
