"""Recording agent that captures AgentBlockEvents using composition over inheritance."""

from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Literal, NotRequired, TypedDict

from csbot.agents.messages import AgentBlockEvent, AgentMessage
from csbot.agents.protocol import AgentCompressionConfig, AsyncAgent


class ContentBlockDict(TypedDict, total=False):
    """TypedDict for content block serialization."""

    type: str
    text: NotRequired[str]
    id: NotRequired[str]
    name: NotRequired[str]
    data: NotRequired[str]  # For unknown types


class DeltaDict(TypedDict, total=False):
    """TypedDict for delta serialization."""

    type: str
    text: NotRequired[str]
    partial_json: NotRequired[str]
    data: NotRequired[str]  # For unknown types


class AgentBlockEventDict(TypedDict, total=False):
    """TypedDict for agent block event serialization."""

    type: str
    index: int
    content_block: NotRequired[ContentBlockDict]
    delta: NotRequired[DeltaDict]


class RecordedEventDict(TypedDict):
    """TypedDict for recorded event entries."""

    type: Literal["agent_block_event"]
    event: AgentBlockEventDict
    timestamp: str


class RecordingAnthropicAgent(AsyncAgent):
    """Agent wrapper that records AgentBlockEvents during streaming using composition."""

    def __init__(self, wrapped_agent: AsyncAgent):
        """Initialize with any AsyncAgent implementation to wrap.

        Args:
            wrapped_agent: The AsyncAgent implementation to wrap with recording functionality
        """
        self.agent = wrapped_agent
        self.recorded_events: list[RecordedEventDict] = []

    @property
    def model(self) -> str:
        """Get the model name from the wrapped agent."""
        return self.agent.model

    async def stream_messages_with_tools(
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
        """Stream messages and capture AgentBlockEvents for recording."""
        async for event in self.agent.stream_messages_with_tools(
            model=model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            on_history_added=on_history_added,
            on_token_usage=on_token_usage,
            compression_config=compression_config,
        ):
            # Record the event with timestamp
            self.recorded_events.append(
                {
                    "type": "agent_block_event",
                    "event": self._agent_block_event_to_dict(event),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            yield event

    async def create_completion(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        max_tokens: int = 4000,
    ) -> str:
        """Delegate completion creation to wrapped agent."""
        return await self.agent.create_completion(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )

    async def create_completion_with_tokens(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        max_tokens: int = 4000,
    ) -> tuple[str, int]:
        """Delegate completion creation to wrapped agent."""
        return await self.agent.create_completion_with_tokens(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )

    async def close(self) -> None:
        """Clean up resources and delegate close to wrapped agent."""
        # Clear recorded events to prevent memory leaks
        self.recorded_events.clear()
        await self.agent.close()

    def get_recorded_events(self) -> list[RecordedEventDict]:
        """Get the captured agent block events."""
        return self.recorded_events

    def clear_recorded_events(self) -> int:
        """Clear recorded events and return the count of events cleared.

        Returns:
            Number of events that were cleared
        """
        count = len(self.recorded_events)
        self.recorded_events.clear()
        return count

    def _agent_block_event_to_dict(self, event: AgentBlockEvent) -> AgentBlockEventDict:
        """Convert AgentBlockEvent to serializable dictionary."""
        result: AgentBlockEventDict = {
            "type": event.type,
            "index": event.index,
        }

        if event.type == "start":
            result["content_block"] = self._content_block_to_dict(event.content_block)
        elif event.type == "delta":
            result["delta"] = self._delta_to_dict(event.delta)
        elif event.type == "stop":
            result["index"] = event.index

        return result

    def _content_block_to_dict(self, block) -> ContentBlockDict:
        """Convert content block to dict."""
        if hasattr(block, "type"):
            result: ContentBlockDict = {"type": block.type}
            if hasattr(block, "text"):
                result["text"] = block.text
            if hasattr(block, "id"):
                result["id"] = block.id
            if hasattr(block, "name"):
                result["name"] = block.name
            return result
        return {"type": "unknown", "data": str(block)}

    def _delta_to_dict(self, delta) -> DeltaDict:
        """Convert delta to dict."""
        if hasattr(delta, "type"):
            result: DeltaDict = {"type": delta.type}
            if hasattr(delta, "text"):
                result["text"] = delta.text
            if hasattr(delta, "partial_json"):
                result["partial_json"] = delta.partial_json
            return result
        return {"type": "unknown", "data": str(delta)}
