"""Abstract interface for spawning Claude agents with MCP tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentResult:
    """Result from spawning a Claude agent.

    Attributes:
        session_id: The Claude session ID for conversation resume
        success: Whether the agent completed successfully
        error_message: Error description if agent failed, None otherwise
    """

    session_id: str
    success: bool
    error_message: str | None


class AgentSpawner(ABC):
    """Abstract interface for spawning Claude agents with MCP tools.

    Implementations handle the mechanics of launching a Claude agent
    process with the appropriate MCP server configuration for Slack.
    """

    @abstractmethod
    def spawn(
        self,
        channel: str,
        thread_ts: str,
        message: str,
        repo_path: Path,
        session_id: str | None = None,
    ) -> AgentResult:
        """Spawn an agent to handle a Slack message.

        The agent will use MCP tools to post replies to the Slack thread.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp to reply to
            message: The user's message text
            repo_path: Path to the repository for context
            session_id: Optional session ID to resume conversation

        Returns:
            AgentResult with session_id and success status
        """
        ...
