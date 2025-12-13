"""Protocol defining the interface all agent implementations must follow."""

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
    ) -> AsyncGenerator[AgentBlockEvent]:
        """Stream agent responses with tool support."""
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
