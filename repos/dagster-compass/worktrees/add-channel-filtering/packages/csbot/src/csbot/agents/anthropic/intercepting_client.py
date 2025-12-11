"""Intercepting client for capturing raw Anthropic API events during AnthropicAgent recording."""

import asyncio
from collections.abc import AsyncIterator, Iterable
from datetime import UTC, datetime
from typing import Any, Literal, overload

import httpx
from anthropic import AsyncAnthropic
from anthropic._streaming import AsyncStream
from anthropic._types import NOT_GIVEN, Body, Headers, NotGiven, Query
from anthropic.lib.streaming import AsyncMessageStreamManager
from anthropic.resources.messages import AsyncMessages
from anthropic.types import (
    Message,
    MessageCountTokensToolParam,
    MessageParam,
    MessageTokensCount,
    MetadataParam,
    ModelParam,
    RawMessageStreamEvent,
    TextBlockParam,
    ThinkingConfigParam,
    ToolChoiceParam,
    ToolUnionParam,
)

from csbot.agents.anthropic.messages_protocol import AsyncMessagesProtocol


class InterceptingStream(AsyncStream[RawMessageStreamEvent]):
    """Wrapper that makes an async generator behave like an AsyncStream."""

    def __init__(self, async_gen: AsyncIterator[RawMessageStreamEvent]) -> None:
        # We can't call super().__init__() because AsyncStream requires specific parameters
        # Instead, we'll store the generator and implement the required interface
        self._async_gen = async_gen

    def __aiter__(self) -> AsyncIterator[RawMessageStreamEvent]:
        return self._async_gen

    async def __anext__(self) -> RawMessageStreamEvent:
        return await self._async_gen.__anext__()

    async def close(self) -> None:
        """Close the stream."""
        if hasattr(self._async_gen, "aclose"):
            await self._async_gen.aclose()  # type: ignore[attr-defined]


class InterceptingClient:
    """Wrapper that intercepts and records raw Anthropic events while passing them through."""

    def __init__(self, real_client: AsyncAnthropic):
        self.real_client = real_client
        self.raw_events: list[dict[str, Any]] = []
        self._messages = InterceptingMessages(self)

    @property
    def messages(self) -> AsyncMessages:
        """Return the intercepting messages wrapper as AsyncMessages."""
        return self._messages  # type: ignore

    def get_raw_events(self) -> list[dict[str, Any]]:
        """Get the captured raw events."""
        return self.raw_events

    def clear_raw_events(self) -> int:
        """Clear raw events and return the count of events cleared.

        Returns:
            Number of events that were cleared
        """
        count = len(self.raw_events)
        self.raw_events.clear()
        return count

    async def close(self) -> None:
        """Forward close to real client."""
        await self.real_client.close()


class InterceptingMessages(AsyncMessagesProtocol):
    """Intercepts messages.create calls and records events."""

    def __init__(self, parent: InterceptingClient):
        self.parent = parent
        self.real_messages = parent.real_client.messages

    @property
    def batches(self) -> Any:
        """Delegate to real messages batches."""
        return self.real_messages.batches

    @property
    def with_raw_response(self) -> Any:
        """Delegate to real messages with_raw_response."""
        return self.real_messages.with_raw_response

    @property
    def with_streaming_response(self) -> Any:
        """Delegate to real messages with_streaming_response."""
        return self.real_messages.with_streaming_response

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        service_tier: Literal["auto", "standard_only"] | NotGiven = NOT_GIVEN,
        stop_sequences: list[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        system: str | Iterable[TextBlockParam] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        thinking: ThinkingConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message: ...

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        stream: Literal[True],
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        service_tier: Literal["auto", "standard_only"] | NotGiven = NOT_GIVEN,
        stop_sequences: list[str] | NotGiven = NOT_GIVEN,
        system: str | Iterable[TextBlockParam] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        thinking: ThinkingConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[RawMessageStreamEvent]: ...

    async def create(self, **kwargs) -> Message | AsyncStream[RawMessageStreamEvent]:
        """Intercept create call and record events as they stream."""
        # Get the real response
        response = await self.real_messages.create(**kwargs)

        # If it's not streaming, just return the Message directly
        if isinstance(response, Message):
            return response

        # If it's streaming, wrap it with interception and back-pressure control
        async def intercepting_stream():
            event_count = 0
            max_events = 10000  # Prevent memory issues with very large streams

            async for event in response:
                event_count += 1

                # Back-pressure control: yield control periodically to prevent blocking
                if event_count % 100 == 0:
                    await asyncio.sleep(0)  # Allow other tasks to run

                # Memory protection: stop recording if too many events
                if event_count > max_events:
                    print(
                        f"  ⚠️  Stream event limit reached ({max_events}), stopping event recording"
                    )
                    # Continue yielding events but stop recording them
                    yield event
                    continue

                # Record the raw event with size limit protection
                try:
                    event_data = {
                        "type": event.type,
                        "timestamp": datetime.now(UTC).isoformat(),
                        **event.model_dump(),
                    }
                    self.parent.raw_events.append(event_data)
                except Exception as e:
                    print(f"  ⚠️  Failed to record event: {e}")
                    # Continue streaming even if recording fails

                # Print raw event with relevant metadata
                if event.type == "content_block_delta" and hasattr(event, "delta"):
                    if event.delta.type == "text_delta":
                        print(
                            f'  📡 Raw Anthropic event: {event.type} - text: "{event.delta.text}"'
                        )
                    elif event.delta.type == "input_json_delta":
                        print(
                            f"  📡 Raw Anthropic event: {event.type} - tool input: {event.delta.partial_json}"
                        )
                elif event.type == "content_block_start" and hasattr(event, "content_block"):
                    if event.content_block.type == "tool_use":
                        print(
                            f"  📡 Raw Anthropic event: {event.type} - tool: {event.content_block.name} (id: {event.content_block.id})"
                        )
                    else:
                        print(
                            f"  📡 Raw Anthropic event: {event.type} - type: {event.content_block.type}"
                        )
                elif event.type == "message_delta" and hasattr(event, "delta"):
                    if event.delta.stop_reason:
                        print(
                            f"  📡 Raw Anthropic event: {event.type} - stop_reason: {event.delta.stop_reason}"
                        )
                elif event.type == "message_start" and hasattr(event, "message"):
                    if hasattr(event.message, "usage"):
                        print(
                            f"  📡 Raw Anthropic event: {event.type} - input_tokens: {event.message.usage.input_tokens}"
                        )
                    else:
                        print(f"  📡 Raw Anthropic event: {event.type}")
                else:
                    print(f"  📡 Raw Anthropic event: {event.type}")

                # Pass through the original event
                yield event

        # Return the intercepting stream wrapped properly
        # We need to return the same interface as the real stream
        return InterceptingStream(intercepting_stream())

    def stream(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        container: str | None | NotGiven = NOT_GIVEN,
        service_tier: Literal["auto", "standard_only"] | NotGiven = NOT_GIVEN,
        stop_sequences: list[str] | NotGiven = NOT_GIVEN,
        system: str | Iterable[TextBlockParam] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        thinking: ThinkingConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolUnionParam] | NotGiven = NOT_GIVEN,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncMessageStreamManager:
        """Delegate stream to real messages."""
        return self.real_messages.stream(
            max_tokens=max_tokens,
            messages=messages,
            model=model,
            metadata=metadata,
            container=container,
            service_tier=service_tier,
            stop_sequences=stop_sequences,
            system=system,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            thinking=thinking,
            tool_choice=tool_choice,
            tools=tools,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )

    async def count_tokens(
        self,
        *,
        messages: Iterable[MessageParam],
        model: ModelParam,
        system: str | Iterable[TextBlockParam] | NotGiven = NOT_GIVEN,
        thinking: ThinkingConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[MessageCountTokensToolParam] | NotGiven = NOT_GIVEN,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> MessageTokensCount:
        """Delegate count_tokens to real messages."""
        return await self.real_messages.count_tokens(
            messages=messages,
            model=model,
            system=system,
            thinking=thinking,
            tool_choice=tool_choice,
            tools=tools,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
        )
