"""Agent launcher abstraction for testing.

This module provides an ABC for agent CLI launches to enable
testing without actually executing Claude or replacing the process.
"""

from abc import ABC, abstractmethod
from typing import NoReturn

from erk_shared.context.types import InteractiveAgentConfig


class AgentLauncher(ABC):
    """Abstract agent launcher for dependency injection."""

    @abstractmethod
    def launch_interactive(self, config: InteractiveAgentConfig, *, command: str) -> NoReturn:
        """Replace current process with agent CLI session.

        Uses os.execvp() to replace the current process, so this
        method never returns.

        Args:
            config: InteractiveAgentConfig with resolved values
            command: The slash command to execute (empty string for no command)

        Note:
            This method never returns - the process is replaced.
        """
        ...
