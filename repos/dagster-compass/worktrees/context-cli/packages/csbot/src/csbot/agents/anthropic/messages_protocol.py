"""Protocol defining the interface that AsyncMessages implements."""

from collections.abc import Iterable
from typing import Any, Literal, Protocol, overload, runtime_checkable

import httpx
from anthropic._streaming import AsyncStream
from anthropic._types import Body, Headers, NotGiven, Query
from anthropic.lib.streaming import AsyncMessageStreamManager
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


@runtime_checkable
class AsyncMessagesProtocol(Protocol):
    """Protocol that AsyncMessages implements - defines the interface InterceptingMessages needs."""

    @property
    def batches(self) -> Any:
        """Access to batches API."""
        ...

    @property
    def with_raw_response(self) -> Any:
        """Access to raw response wrapper."""
        ...

    @property
    def with_streaming_response(self) -> Any:
        """Access to streaming response wrapper."""
        ...

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = ...,
        service_tier: Literal["auto", "standard_only"] | NotGiven = ...,
        stop_sequences: list[str] | NotGiven = ...,
        stream: Literal[False] | NotGiven = ...,
        system: str | Iterable[TextBlockParam] | NotGiven = ...,
        temperature: float | NotGiven = ...,
        thinking: ThinkingConfigParam | NotGiven = ...,
        tool_choice: ToolChoiceParam | NotGiven = ...,
        tools: Iterable[ToolUnionParam] | NotGiven = ...,
        top_k: int | NotGiven = ...,
        top_p: float | NotGiven = ...,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = ...,
    ) -> Message:
        """Create a message (non-streaming)."""
        ...

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        stream: Literal[True],
        metadata: MetadataParam | NotGiven = ...,
        service_tier: Literal["auto", "standard_only"] | NotGiven = ...,
        stop_sequences: list[str] | NotGiven = ...,
        system: str | Iterable[TextBlockParam] | NotGiven = ...,
        temperature: float | NotGiven = ...,
        thinking: ThinkingConfigParam | NotGiven = ...,
        tool_choice: ToolChoiceParam | NotGiven = ...,
        tools: Iterable[ToolUnionParam] | NotGiven = ...,
        top_k: int | NotGiven = ...,
        top_p: float | NotGiven = ...,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = ...,
    ) -> AsyncStream[RawMessageStreamEvent]:
        """Create a message (streaming)."""
        ...

    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = ...,
        service_tier: Literal["auto", "standard_only"] | NotGiven = ...,
        stop_sequences: list[str] | NotGiven = ...,
        stream: Literal[False] | Literal[True] | NotGiven = ...,
        system: str | Iterable[TextBlockParam] | NotGiven = ...,
        temperature: float | NotGiven = ...,
        thinking: ThinkingConfigParam | NotGiven = ...,
        tool_choice: ToolChoiceParam | NotGiven = ...,
        tools: Iterable[ToolUnionParam] | NotGiven = ...,
        top_k: int | NotGiven = ...,
        top_p: float | NotGiven = ...,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = ...,
    ) -> Message | AsyncStream[RawMessageStreamEvent]:
        """Create a message with optional streaming."""
        ...

    def stream(
        self,
        *,
        max_tokens: int,
        messages: Iterable[MessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = ...,
        container: str | None | NotGiven = ...,
        service_tier: Literal["auto", "standard_only"] | NotGiven = ...,
        stop_sequences: list[str] | NotGiven = ...,
        system: str | Iterable[TextBlockParam] | NotGiven = ...,
        temperature: float | NotGiven = ...,
        top_k: int | NotGiven = ...,
        top_p: float | NotGiven = ...,
        thinking: ThinkingConfigParam | NotGiven = ...,
        tool_choice: ToolChoiceParam | NotGiven = ...,
        tools: Iterable[ToolUnionParam] | NotGiven = ...,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = ...,
    ) -> AsyncMessageStreamManager:
        """Create a message stream manager."""
        ...

    async def count_tokens(
        self,
        *,
        messages: Iterable[MessageParam],
        model: ModelParam,
        system: str | Iterable[TextBlockParam] | NotGiven = ...,
        thinking: ThinkingConfigParam | NotGiven = ...,
        tool_choice: ToolChoiceParam | NotGiven = ...,
        tools: Iterable[MessageCountTokensToolParam] | NotGiven = ...,
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = ...,
    ) -> MessageTokensCount:
        """Count tokens in a message."""
        ...
