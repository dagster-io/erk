"""Protocol defining the interface all agent implementations must follow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from csbot.agents.messages import AgentBlockEvent, AgentMessage


@dataclass(frozen=True)
class ContextData:
    topic: str
    incorrect_understanding: str
    correct_understanding: str
    search_keywords: str


@dataclass(frozen=True)
class AgentCompressionConfig:
    """Config for mid-execution history compression in stream_messages_with_tools.

    When enabled, this allows the agent loop to compress conversation history
    when it exceeds the threshold, preventing context window exceeded errors.
    """

    compression_agent: AsyncAgent
    """Agent to use for summarization (e.g., a Haiku-based agent for speed/cost)."""

    threshold_tokens: int = 100_000
    """Trigger compression when history exceeds this token count."""

    target_tokens: int = 20_000
    """Target size after compression."""


class AsyncAgent(ABC):
    """Abstract base class defining the interface all agent implementations must follow."""

    @property
    @abstractmethod
    def model(self) -> str:
        """The model name for this agent."""
        ...

    @abstractmethod
    def stream_messages_with_tools(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        tools: dict[str, Callable[..., Awaitable[Any]]],
        max_tokens: int,
        on_history_added: Callable[[AgentMessage], Awaitable[None]] | None = None,
        on_token_usage: Callable[[int, dict[str, Any]], Awaitable[None]] | None = None,
        compression_config: AgentCompressionConfig | None = None,
    ) -> AsyncGenerator[AgentBlockEvent]:
        """Stream agent responses with tool support.

        Args:
            model: Model name to use for this request.
            system: System prompt.
            messages: Initial conversation messages.
            tools: Available tools for the agent to call.
            max_tokens: Maximum tokens for response.
            on_history_added: Callback when history is updated.
            on_token_usage: Callback for token usage tracking.
            compression_config: Optional config for mid-execution history compression.
                When provided, the agent loop will compress history if it exceeds
                the threshold, preventing context window exceeded errors.
        """
        ...

    @abstractmethod
    async def create_completion(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        max_tokens: int = 4000,
    ) -> str:
        """Create a simple text completion."""
        ...

    @abstractmethod
    async def create_completion_with_tokens(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        max_tokens: int = 4000,
    ) -> tuple[str, int]:
        """Create a simple text completion, also returns how many tokens were consumed."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        ...
