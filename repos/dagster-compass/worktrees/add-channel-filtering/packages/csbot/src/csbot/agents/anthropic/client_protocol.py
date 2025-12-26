"""Protocol defining the interface AnthropicAgent expects from an Anthropic client."""

from typing import Protocol, runtime_checkable

from csbot.agents.anthropic.messages_protocol import AsyncMessagesProtocol


@runtime_checkable
class AnthropicClientProtocol(Protocol):
    """Protocol defining the interface AnthropicAgent expects from an Anthropic client."""

    @property
    def messages(self) -> AsyncMessagesProtocol:
        """Access to messages API."""
        ...

    async def close(self) -> None:
        """Clean up client resources."""
        ...
