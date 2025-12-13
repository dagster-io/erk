"""Anthropic agent implementation that exposes only Agent* types."""

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TYPE_CHECKING, Any, cast

import structlog
from anthropic import AsyncAnthropic, AsyncAnthropicBedrock, DefaultAsyncHttpxClient
from ddtrace.trace import tracer
from mcp import ClientSessionGroup

from csbot.agents.anthropic.client_protocol import AnthropicClientProtocol
from csbot.agents.anthropic.conversions import (
    agent_to_anthropic_message_param,
    anthropic_raw_message_stream_event_to_agent,
    component_name_hook,
    create_anthropic_tool_param,
    prepare_messages_with_cache_control,
)
from csbot.agents.anthropic.retry_logging_transport import RetryLoggingTransport
from csbot.agents.messages import (
    AgentBlockDelta,
    AgentBlockEvent,
    AgentContentBlock,
    AgentMessage,
    AgentModelSpecificMessage,
    AgentTextBlock,
    AgentToolUseBlock,
)
from csbot.agents.protocol import AsyncAgent
from csbot.agents.timeouts import iterator_with_timeout
from csbot.slackbot.exceptions import UserFacingError
from csbot.utils.json_utils import safe_json_dumps

if TYPE_CHECKING:
    from anthropic.types import ToolParam

    from csbot.agents.messages import (
        AgentInputJSONDelta,
        AgentTextDelta,
    )

logger = structlog.get_logger(__name__)

DEFAULT_ANTHROPIC_RETRIES = 5
DEFAULT_BEDROCK_RETRIES = 5


def _is_expected_tool_failure(tool: str, e: Exception):
    # the AI frequently makes mistakes constructing SQL queries, so
    # try to categorize all these failures in order to log/respond appropriately
    if tool == "run_sql_query":
        return True

    if tool == "attach_csv" and "SQL compilation error" in str(e):
        return True

    return False


class ContentBlockAggregator:
    """Aggregates streaming content blocks into complete blocks."""

    def __init__(self):
        self.current_content_block: AgentContentBlock | None = None
        self.deltas: list[AgentBlockDelta] = []

    def handle_event(
        self, event: AgentBlockEvent
    ) -> tuple[AgentContentBlock, list[AgentBlockDelta]] | None:
        """Handle a block event and return completed block if available."""
        if event.type == "start":
            if self.current_content_block is not None:
                raise ValueError("Content block start without stop")
            self.current_content_block = event.content_block
        elif event.type == "delta":
            if self.current_content_block is None:
                raise ValueError("Content block delta without start")
            self.deltas.append(event.delta)
        elif event.type == "stop":
            if self.current_content_block is None:
                raise ValueError("Content block stop without start")
            rv = (self.current_content_block, self.deltas)
            self.current_content_block = None
            self.deltas = []
            return rv
        return None


class AnthropicAgent(AsyncAgent):
    """Anthropic implementation that exposes only Agent* types."""

    @staticmethod
    def from_api_key(
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> "AnthropicAgent":
        """Create an Anthropic agent from an API key.

        Args:
            api_key: Anthropic API key
            model: Model to use
            enable_retry_logging: If True, logs when SDK retries due to 429/5xx errors
        """

        return AnthropicAgent(
            anthropic_client=AsyncAnthropic(
                api_key=api_key,
                max_retries=DEFAULT_ANTHROPIC_RETRIES,
                http_client=DefaultAsyncHttpxClient(transport=RetryLoggingTransport()),
            ),
            model=model,
        )

    @staticmethod
    def from_bedrock(
        aws_access_key: str | None,
        aws_secret_key: str | None,
        aws_region: str | None,
        inference_profile_arn: str,
    ) -> "AnthropicAgent":
        return AnthropicAgent(
            anthropic_client=AsyncAnthropicBedrock(
                aws_access_key=aws_access_key,
                aws_secret_key=aws_secret_key,
                aws_region=aws_region,
                max_retries=DEFAULT_BEDROCK_RETRIES,
                http_client=DefaultAsyncHttpxClient(transport=RetryLoggingTransport()),
            ),
            model=inference_profile_arn,
        )

    def __init__(
        self, anthropic_client: AnthropicClientProtocol, model: str = "claude-sonnet-4-20250514"
    ):
        self.client = anthropic_client
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @tracer.wrap()
    async def stream_messages_with_tools(  # type: ignore[override]
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

        # figure out how much customer info is in prompt, rbac for datadog,
        # data retention, etc.
        # try_set_tag("prompt", system)

        async with ClientSessionGroup(component_name_hook=component_name_hook) as group:
            # Check for naming conflicts
            for tool_name in group.tools.keys():
                if tool_name in tools:
                    raise ValueError(f"Tool {tool_name} already defined in tools")

            mcp_tools = [
                cast(
                    "ToolParam",
                    {
                        "name": tool_name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema,
                    },
                )
                for tool_name, tool in group.tools.items()
            ]

            history = messages[:]
            looping = True

            while looping:
                looping = False

                history_with_cache_control = prepare_messages_with_cache_control(history)

                next_messages = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=[
                        {
                            "type": "text",
                            "text": system,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=[
                        agent_to_anthropic_message_param(message)
                        for message in history_with_cache_control
                    ],
                    stream=True,
                    tools=[create_anthropic_tool_param(name, tool) for name, tool in tools.items()]
                    + mcp_tools,
                )

                # Track token usage from streaming events
                # Note: Anthropic reports CUMULATIVE totals in both message_start and message_delta,
                # not incremental deltas. We store values and use the final ones from message_delta.
                # IMPORTANT: These variables are scoped to this loop iteration and reset on each
                # iteration (e.g., when tool use triggers another API call via looping=True).
                # This prevents race conditions and ensures each API call is tracked independently.
                input_tokens_from_start = 0
                cache_creation_tokens_from_start = 0
                cache_read_tokens_from_start = 0
                # Store the latest usage object for accessing metadata fields
                latest_usage_object = None

                content_block_aggregator = ContentBlockAggregator()
                async for anthropic_message in iterator_with_timeout(next_messages, 60):
                    # Capture token usage from message_start event
                    # Store these as fallback values in case message_delta doesn't have them
                    if anthropic_message.type == "message_start":
                        if hasattr(anthropic_message, "message") and hasattr(
                            anthropic_message.message, "usage"
                        ):
                            usage = anthropic_message.message.usage
                            latest_usage_object = usage
                            input_tokens_from_start = getattr(usage, "input_tokens", None) or 0
                            cache_creation_tokens_from_start = (
                                getattr(usage, "cache_creation_input_tokens", None) or 0
                            )
                            cache_read_tokens_from_start = (
                                getattr(usage, "cache_read_input_tokens", None) or 0
                            )

                    if (
                        anthropic_message.type == "message_delta"
                        and anthropic_message.delta.stop_reason == "max_tokens"
                    ):
                        raise UserFacingError(
                            title="Token Limit Exceeded",
                            message="Query used too many tokens; please try again.",
                        )

                    if (
                        anthropic_message.type == "message_delta"
                        and anthropic_message.delta.stop_reason == "end_turn"
                    ):
                        if on_token_usage:
                            # Get final token counts from message_delta
                            # Anthropic reports CUMULATIVE totals, not deltas
                            if hasattr(anthropic_message, "usage"):
                                usage = anthropic_message.usage
                                latest_usage_object = usage

                                # Use values from message_delta (final cumulative totals)
                                # Fall back to message_start values ONLY if field is None (not present)
                                # Use explicit None checks to avoid masking legitimate 0 values
                                delta_input = getattr(usage, "input_tokens", None)
                                input_tokens = (
                                    delta_input
                                    if delta_input is not None
                                    else input_tokens_from_start
                                )

                                delta_output = getattr(usage, "output_tokens", None)
                                output_tokens = delta_output if delta_output is not None else 0

                                delta_cache_creation = getattr(
                                    usage, "cache_creation_input_tokens", None
                                )
                                cache_creation_tokens = (
                                    delta_cache_creation
                                    if delta_cache_creation is not None
                                    else cache_creation_tokens_from_start
                                )

                                delta_cache_read = getattr(usage, "cache_read_input_tokens", None)
                                cache_read_tokens = (
                                    delta_cache_read
                                    if delta_cache_read is not None
                                    else cache_read_tokens_from_start
                                )

                                # Detect potential API changes: if message_delta has explicit 0
                                # but message_start had a value, this may indicate API behavior change.
                                # Exception: Don't warn if we have cache tokens (legitimate for cached responses)
                                if (
                                    delta_input == 0
                                    and input_tokens_from_start > 0
                                    and cache_creation_tokens == 0
                                    and cache_read_tokens == 0
                                ):
                                    logger.warning(
                                        f"API behavior change detected: message_delta has input_tokens=0 "
                                        f"but message_start had {input_tokens_from_start} with no cache tokens. "
                                        f"This may indicate Anthropic changed from cumulative to delta reporting."
                                    )

                                # Validate token values are non-negative
                                # Log warning if API returns malformed data
                                if input_tokens < 0:
                                    logger.error(
                                        f"Invalid negative input_tokens: {input_tokens}. Setting to 0."
                                    )
                                    input_tokens = 0
                                if output_tokens < 0:
                                    logger.error(
                                        f"Invalid negative output_tokens: {output_tokens}. Setting to 0."
                                    )
                                    output_tokens = 0
                                if cache_creation_tokens < 0:
                                    logger.error(
                                        f"Invalid negative cache_creation_input_tokens: {cache_creation_tokens}. Setting to 0."
                                    )
                                    cache_creation_tokens = 0
                                if cache_read_tokens < 0:
                                    logger.error(
                                        f"Invalid negative cache_read_input_tokens: {cache_read_tokens}. Setting to 0."
                                    )
                                    cache_read_tokens = 0
                            else:
                                # No usage in message_delta, use values from message_start
                                input_tokens = input_tokens_from_start
                                output_tokens = 0
                                cache_creation_tokens = cache_creation_tokens_from_start
                                cache_read_tokens = cache_read_tokens_from_start

                            total_tokens = (
                                input_tokens
                                + output_tokens
                                + cache_creation_tokens
                                + cache_read_tokens
                            )

                            # Log a warning if we're seeing unexpected zero values
                            if (
                                input_tokens == 0
                                and cache_read_tokens == 0
                                and cache_creation_tokens == 0
                            ):
                                logger.warning(
                                    f"Unexpected token usage: all input tokens are 0 but output_tokens={output_tokens}. "
                                    f"This may indicate an issue with token tracking."
                                )

                            # Build comprehensive token breakdown
                            token_breakdown = {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "cache_creation_input_tokens": cache_creation_tokens,
                                "cache_read_input_tokens": cache_read_tokens,
                                "total_tokens": total_tokens,
                            }

                            # Add cache creation breakdown if available (from latest usage object)
                            cache_creation = (
                                getattr(latest_usage_object, "cache_creation", None)
                                if latest_usage_object
                                else None
                            )
                            if cache_creation:
                                token_breakdown["cache_creation"] = {
                                    "ephemeral_5m_input_tokens": getattr(
                                        cache_creation, "ephemeral_5m_input_tokens", None
                                    )
                                    or 0,
                                    "ephemeral_1h_input_tokens": getattr(
                                        cache_creation, "ephemeral_1h_input_tokens", None
                                    )
                                    or 0,
                                }

                            # Add service tier if available (from latest usage object)
                            service_tier = (
                                getattr(latest_usage_object, "service_tier", None)
                                if latest_usage_object
                                else None
                            )
                            if service_tier:
                                token_breakdown["service_tier"] = service_tier

                            # Add server tool usage if available (from latest usage object)
                            server_tool_use = (
                                getattr(latest_usage_object, "server_tool_use", None)
                                if latest_usage_object
                                else None
                            )
                            if server_tool_use:
                                token_breakdown["server_tool_use"] = {
                                    "web_search_requests": getattr(
                                        server_tool_use, "web_search_requests", None
                                    )
                                    or 0,
                                }

                            # Log comprehensive token info for debugging
                            logger.debug(
                                f"Token usage: input={input_tokens}, output={output_tokens}, "
                                f"cache_creation={cache_creation_tokens}, cache_read={cache_read_tokens}, "
                                f"total={total_tokens}"
                            )

                            await on_token_usage(total_tokens, token_breakdown)

                    message = anthropic_raw_message_stream_event_to_agent(anthropic_message)

                    if message is None:
                        continue

                    async def add_to_history(message: AgentMessage):
                        history.append(message)
                        if on_history_added:
                            await on_history_added(message)

                    completed_block = content_block_aggregator.handle_event(message)

                    if completed_block:
                        content_block, deltas = completed_block
                        if isinstance(content_block, AgentTextBlock):
                            await add_to_history(
                                AgentModelSpecificMessage(
                                    role="assistant",
                                    content="".join(
                                        cast("AgentTextDelta", delta).text for delta in deltas
                                    ),
                                )
                            )
                        elif isinstance(content_block, AgentToolUseBlock):
                            content_block_content = "".join(
                                cast("AgentInputJSONDelta", delta).partial_json for delta in deltas
                            )

                            try:
                                if content_block.name in group.tools:
                                    with tracer.trace("tool.call") as span:
                                        span.set_tag("tool", content_block.name)
                                        tool_result = await group.call_tool(
                                            content_block.name,
                                            json.loads(content_block_content),
                                        )
                                else:
                                    if content_block.name not in tools:
                                        raise ValueError(
                                            f"Tool {content_block.name} not found in tools"
                                        )

                                    if not asyncio.iscoroutinefunction(tools[content_block.name]):
                                        raise TypeError(
                                            f"Tool {content_block.name} must be async. Synchronous tools are no longer supported."
                                        )
                                    with tracer.trace("tool.call") as span:
                                        span.set_tag("tool", content_block.name)
                                        if len(content_block_content.strip()) == 0:
                                            tool_result = await tools[content_block.name]()
                                        else:
                                            tool_result = await tools[content_block.name](
                                                **json.loads(content_block_content)
                                            )

                                tool_result = {"result": tool_result}
                            except Exception as e:
                                is_expected_error = _is_expected_tool_failure(content_block.name, e)
                                if is_expected_error:
                                    logger.warning(
                                        f"Error calling tool {content_block.name}", exc_info=True
                                    )
                                else:
                                    logger.exception(f"Error calling tool {content_block.name}")
                                tool_result = {
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                    "tool_name": content_block.name,
                                    "args": json.loads(content_block_content)
                                    if content_block_content.strip()
                                    else {},
                                }

                            await add_to_history(
                                AgentModelSpecificMessage(
                                    role="assistant",
                                    content=[
                                        {
                                            "type": "tool_use",
                                            "id": content_block.id,
                                            "name": content_block.name,
                                            "input": json.loads(content_block_content)
                                            if len(content_block_content.strip()) > 0
                                            else {},
                                        }
                                    ],
                                )
                            )
                            await add_to_history(
                                AgentModelSpecificMessage(
                                    role="user",
                                    content=[
                                        {
                                            "type": "tool_result",
                                            "tool_use_id": content_block.id,
                                            "content": safe_json_dumps(tool_result),
                                        }
                                    ],
                                )
                            )
                            looping = True
                        else:
                            raise NotImplementedError(
                                f"Unknown content block type: {type(content_block)}"
                            )

                    yield message

    async def _create_long_completion(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        max_tokens: int,
    ) -> str:
        """Create a long text completion."""
        texts = []
        anthropic_messages = [agent_to_anthropic_message_param(msg) for msg in messages]
        async with self.client.messages.stream(
            model=model,
            system=system,
            messages=anthropic_messages,
            max_tokens=max_tokens,
        ) as response:
            async for text in response.text_stream:
                texts.append(text)

        return "".join(texts)

    async def create_completion(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        max_tokens: int = 4000,
    ) -> str:
        """Create a simple text completion."""
        if max_tokens > 8192:
            return await self._create_long_completion(model, system, messages, max_tokens)

        response, _ = await self.create_completion_with_tokens(model, system, messages, max_tokens)
        return response

    async def create_completion_with_tokens(
        self,
        model: str,
        system: str,
        messages: list[AgentMessage],
        max_tokens: int = 4000,
    ) -> tuple[str, int]:
        anthropic_messages = [agent_to_anthropic_message_param(msg) for msg in messages]

        response = await self.client.messages.create(
            model=model,
            system=system,
            messages=anthropic_messages,
            max_tokens=max_tokens,
        )

        # Extract text from response
        text = ""
        if response.content:
            content_block = response.content[0]
            if hasattr(content_block, "text"):
                text = content_block.text  # type: ignore  # Anthropic response content blocks are dynamically typed
            # TODO: Make this type-safe by using isinstance(content_block, TextBlock) check instead of hasattr + type ignore

        # Calculate total tokens from usage
        usage = response.usage
        total_tokens = (
            (usage.input_tokens or 0)
            + (usage.output_tokens or 0)
            + (usage.cache_creation_input_tokens or 0)
            + (usage.cache_read_input_tokens or 0)
        )

        return text, total_tokens

    async def close(self) -> None:
        """Clean up Anthropic client."""
        await self.client.close()
