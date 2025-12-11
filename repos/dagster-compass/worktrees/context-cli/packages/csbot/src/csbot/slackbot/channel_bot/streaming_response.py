"""
Streaming response handler for Claude AI interactions in Slack.

This module handles the streaming of Claude responses, including real-time UI updates,
block component rendering, HTML generation, and analytics tracking.
"""

import asyncio
import html
import json
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

from slack_sdk.web.async_client import AsyncWebClient

from csbot.agents.messages import (
    AgentBlockDelta,
    AgentContentBlock,
    AgentTextMessage,
)
from csbot.agents.protocol import AsyncAgent
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.personalization import (
    get_person_info_from_slack_user_id,
    resolve_user_mentions_in_message,
)
from csbot.slackbot.slackbot_analytics import (
    AnalyticsEventType,
    SlackbotAnalyticsStore,
    log_analytics_event_unified,
)
from csbot.slackbot.slackbot_blockkit import (
    ActionsBlock,
    ButtonElement,
    ImageBlock,
    SectionBlock,
    TextObject,
    TextType,
)
from csbot.slackbot.slackbot_slackstream import SlackstreamReply
from csbot.slackbot.slackbot_ui import (
    BlockComponentContext,
    SlackThread,
    _get_block_component,
    render_block_component,
    render_block_component_to_html,
    run_block_component_side_effects,
)
from csbot.utils import tracing
from csbot.utils.ensure_valid_utf8 import ensure_valid_utf8

if TYPE_CHECKING:
    from csbot.agents.messages import AgentBlockEvent
    from csbot.slackbot.channel_bot.personalization import EnrichedPerson
    from csbot.slackbot.slackbot_blockkit import Block


async def _log_token_usage_to_segment(
    analytics_store: SlackbotAnalyticsStore,
    bot_key: BotKey,
    channel: str,
    user: str | None,
    thread_ts: str,
    total_tokens: int,
    token_breakdown: dict[str, Any],
    enriched_person: "EnrichedPerson | None",
    organization_id: int | None,
    organization_name: str,
) -> None:
    """Log token usage to both database and Segment."""

    tracing.try_incr_metrics("token_usage", {"total_tokens": total_tokens, **token_breakdown})

    await log_analytics_event_unified(
        analytics_store=analytics_store,
        event_type=AnalyticsEventType.TOKEN_USAGE,
        bot_id=bot_key.to_bot_id(),
        channel_id=channel,
        user_id=user,
        thread_ts=thread_ts,
        message_ts=thread_ts,
        tokens_used=total_tokens,
        metadata=token_breakdown,
        enriched_person=enriched_person,
        user_email=enriched_person.email if enriched_person and enriched_person.email else None,
        organization_id=organization_id,
        organization_name=organization_name,
        send_to_segment=True,
    )


async def stream_claude_response(
    agent: AsyncAgent,
    system_prompt: str,
    tools: dict[str, Callable[..., Awaitable[Any]]],
    thread: SlackThread,
    channel: str,
    thread_ts: str,
    user: str | None,
    message: str,
    collapse_thinking_steps: bool,
    analytics_store: SlackbotAnalyticsStore,
    bot_key: BotKey,
    slack_client: AsyncWebClient,
    organization_name: str,
    logger: logging.Logger,
    log_prefix: str,
    organization_id: int | None,
    is_prospector_mode: bool,
) -> None:
    """Handle streaming Claude response with real-time Slack UI updates.

    This function manages the complete streaming workflow:
    - Initiates Claude streaming with tools and context
    - Processes streaming events and renders UI components
    - Updates Slack messages in real-time
    - Generates HTML for web view
    - Handles collapsed thinking steps mode
    - Tracks analytics for token usage

    Args:
        agent: The AI agent to stream responses from
        system_prompt: System prompt for the AI conversation
        tools: Available tools for the AI agent
        thread: Slack thread to update
        channel: Slack channel ID
        thread_ts: Thread timestamp
        user: User ID who initiated the request
        message: User's message content
        collapse_thinking_steps: Whether to collapse intermediate tool calls
        analytics_store: Analytics tracking store
        bot_key: Bot identification key
        slack_client: Slack API client
        logger: Logger instance
        log_prefix: Prefix for log messages
        error_context: Context for error messages
    """
    logger.info(f"{log_prefix}: streaming request from {user} in {channel}")

    user_info_str = ""
    enriched_person = None
    if user:
        try:
            enriched_person = await get_person_info_from_slack_user_id(
                slack_client, thread.kv_store, user
            )
        except Exception as e:
            tracing.try_set_exception()

            logger.error(f"Error getting person info from slack user id: {e}")
            enriched_person = None

        if enriched_person:
            parts: list[str] = []
            if enriched_person.real_name:
                parts.append(enriched_person.real_name)
            if enriched_person.job_title:
                parts.append(enriched_person.job_title)
            if enriched_person.timezone:
                parts.append(f"timezone: {enriched_person.timezone}")
            user_info_str = ", ".join(parts)

    # Resolve user mentions in the message before processing
    resolved_message = await resolve_user_mentions_in_message(
        slack_client, thread.kv_store, message
    )

    message_prefix = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}] <@{user}>{user_info_str}: "
    )

    # Add the current user message with resolved mentions
    await thread.add_event(
        AgentTextMessage(
            role="user",
            content=message_prefix + resolved_message,
        )
    )

    # Start streaming response
    stream = agent.stream_messages_with_tools(
        model=agent.model,
        max_tokens=32000,
        system=system_prompt,
        messages=await thread.get_events(),
        tools=tools,
        on_history_added=thread.add_event,
        on_token_usage=lambda total_tokens, token_breakdown: asyncio.create_task(
            _log_token_usage_to_segment(
                analytics_store=analytics_store,
                bot_key=bot_key,
                channel=channel,
                user=user,
                thread_ts=thread_ts,
                total_tokens=total_tokens,
                token_breakdown=token_breakdown,
                enriched_person=enriched_person,
                organization_id=organization_id,
                organization_name=organization_name,
            )
        ),
    )

    last_user_message_html = f"""
<div class="bg-white rounded-lg border border-gray-200 shadow-sm mb-4">
    <div class="flex gap-3 p-4">
        <div class="user-avatar flex items-center justify-center text-white text-xl">
            <i class="ph ph-user-circle"></i>
        </div>
        <div class="flex-1 min-w-0">
            <div class="flex items-baseline gap-2">
                <span class="font-semibold text-gray-900 text-md">User</span>
            </div>
            <div class="text-gray-900 text-md leading-relaxed -mt-1">{html.escape(message)}</div>
        </div>
    </div>
</div>
"""

    prev_html = await thread.get_html()

    slackstream = SlackstreamReply(slack_client, channel, thread.thread_ts)
    all_events: list[AgentBlockEvent] = []
    stop_event_tasks: dict[int, asyncio.Task] = {}
    completed_states: dict[int, Any | None] = {}

    async def run_side_effect(
        i: int,
        content_block: AgentContentBlock,
        deltas: list[AgentBlockDelta],
    ):
        if i in completed_states:
            raise ValueError("Side effect already completed")
        completed_states[i] = await run_block_component_side_effects(
            content_block, deltas, slackstream, is_prospector_mode=is_prospector_mode
        )
        return completed_states[i]

    last_html_update_time: float | None = None
    html_update_interval = 0.5

    async def refresh(final_refresh: bool):
        nonlocal last_html_update_time

        blocks: list[tuple[AgentContentBlock, list[Block]]] = []
        html_components = []
        current_content_block: AgentContentBlock | None = None
        deltas: list[AgentBlockDelta] = []

        for i, event in enumerate(all_events):
            await asyncio.sleep(0)
            if event.type == "start":
                if current_content_block is not None:
                    raise ValueError("Content block already started")
                if len(deltas) > 0:
                    raise ValueError("Deltas already started")
                current_content_block = event.content_block
            elif event.type == "delta":
                deltas.append(event.delta)
            elif event.type == "stop":
                if current_content_block is None:
                    raise ValueError("Content block not started")
                blocks.append(
                    (
                        current_content_block,
                        render_block_component(
                            current_content_block,
                            deltas,
                            True,
                            completed_states.get(i),
                            is_prospector_mode=is_prospector_mode,
                        ),
                    )
                )
                html_components.append(
                    render_block_component_to_html(
                        current_content_block,
                        deltas,
                        True,
                        completed_states.get(i),
                        is_prospector_mode=is_prospector_mode,
                    )
                )

                if i not in stop_event_tasks:
                    stop_event_tasks[i] = asyncio.create_task(
                        run_side_effect(i, current_content_block, deltas)
                    )
                current_content_block = None
                deltas = []
        if current_content_block is not None:
            blocks.append(
                (
                    current_content_block,
                    render_block_component(
                        current_content_block,
                        deltas,
                        False,
                        None,
                        is_prospector_mode=is_prospector_mode,
                    ),
                )
            )

            html_components.append(
                render_block_component_to_html(
                    current_content_block,
                    deltas,
                    False,
                    None,
                    is_prospector_mode=is_prospector_mode,
                )
            )

        blocks_to_render: list[Block] = []
        if (
            final_refresh
            and collapse_thinking_steps
            and current_content_block is None
            and len(blocks) > 0
            and blocks[-1][0].type == "output_text"
        ):
            # current content block is not None if there is some sort of crash
            # Summarize all tool calls using render_aggregate and put them in a single section block with a blockquote
            tool_call_groups: dict[str, list[tuple[BlockComponentContext, Any]]] = {}

            # Group tool calls by tool name
            for content_block, _ in blocks[:-1]:  # Exclude the final text block
                if content_block.type == "call_tool":
                    tool_name = content_block.name
                    if tool_name not in tool_call_groups:
                        tool_call_groups[tool_name] = []

                    # Create context for this tool call
                    context = BlockComponentContext(
                        content_block=content_block,
                        deltas=[],  # Deltas not needed for render_aggregate
                        completed=True,
                        is_prospector_mode=is_prospector_mode,
                    )
                    completed_state = completed_states.get(blocks.index((content_block, _)))
                    tool_call_groups[tool_name].append((context, completed_state))

            # Generate aggregate summaries
            aggregate_summaries = []
            for tool_name, contexts_and_states in tool_call_groups.items():
                await asyncio.sleep(0)
                if contexts_and_states:  # Only if we have tool calls for this tool
                    # Get the component for this tool type
                    sample_content_block = contexts_and_states[0][0].content_block
                    component = _get_block_component(sample_content_block)

                    # Generate aggregate summary
                    summary = component.render_aggregate(contexts_and_states)
                    if summary:  # Only add non-empty summaries
                        aggregate_summaries.append(summary)

            # Add summary block if we have summaries
            if aggregate_summaries:
                summary_text = "\n".join(aggregate_summaries)
                blocks_to_render.append(
                    SectionBlock(
                        text=TextObject(
                            type=TextType.MRKDWN,
                            text=summary_text,
                        ),
                    )
                )

            # Keep all the data visualizations
            for content_block, slack_blocks in blocks:
                if (
                    content_block.type == "call_tool"
                    and content_block.name == "render_data_visualization"
                    and len(slack_blocks) > 0
                    and isinstance(slack_blocks[-1], ImageBlock)
                ):
                    blocks_to_render.append(slack_blocks[-1])

            # Keep the final text block
            blocks_to_render.extend(blocks[-1][1])

            # Add action buttons to the end
            blocks_to_render.append(
                ActionsBlock(
                    elements=[
                        ButtonElement(
                            text=TextObject.plain_text("🌐 See all steps"),
                            value=json.dumps({"channel": channel, "thread_ts": thread_ts}),
                            action_id="view_thread_steps",
                        ),
                        ButtonElement(
                            text=TextObject.plain_text("👍"),
                            value=json.dumps({"channel": channel, "thread_ts": thread_ts}),
                            action_id="thumbs_up",
                        ),
                        ButtonElement(
                            text=TextObject.plain_text("👎"),
                            value=json.dumps({"channel": channel, "thread_ts": thread_ts}),
                            action_id="thumbs_down",
                        ),
                    ],
                    block_id="thumbs_actions",
                )
            )
        else:
            for content_block, slack_blocks in blocks:
                blocks_to_render.extend(slack_blocks)

        if len(blocks_to_render) == 0 and not final_refresh:
            blocks_to_render.append(SectionBlock(text=TextObject(type=TextType.MRKDWN, text="🤔")))

        await slackstream.update(blocks_to_render)
        if final_refresh or (
            last_html_update_time is None
            or time.time() - last_html_update_time > html_update_interval
        ):
            # Wrap all bot HTML components in a single chat message card
            bot_message_html = ""
            if html_components:
                bot_content = "".join(html_components)
                bot_message_html = f"""
<div class="bg-white rounded-lg border border-gray-200 shadow-sm mb-4">
    <div class="flex gap-3 p-4">
        <img src="/static/logo-square.svg" class="h-9 w-9 flex-shrink-0 rounded-md" alt="Compass">
        <div class="flex-1 min-w-0">
            <div class="flex items-baseline gap-2">
                <span class="font-semibold text-gray-900 text-md">Compass</span>
            </div>
            <div class="text-gray-900 text-md leading-relaxed -mt-1">{bot_content}</div>
        </div>
    </div>
</div>
"""

            next_html = (prev_html or "") + last_user_message_html + bot_message_html
            await thread.set_html(ensure_valid_utf8(next_html))
            last_html_update_time = time.time()

    try:
        await refresh(False)
        async for event in stream:
            all_events.append(event)
            await refresh(False)

    finally:
        try:
            for task in stop_event_tasks.values():
                try:
                    await task
                except Exception as e:
                    logger.error(
                        f"Error in {log_prefix.lower()} block component side effects: {e}",
                        exc_info=True,
                    )
            # one for the road (aka flush the side effect state)
            await refresh(True)
        finally:
            await slackstream.finish()
            logger.info(f"{log_prefix}: sent streaming response to {channel}")
