from typing import Any

from slack_sdk.errors import SlackApiError

from erk_shared.gateway.time.abc import Time
from erkbot.agent.bot import ErkBot
from erkbot.agent.events import TextDelta, ToolEnd, ToolStart
from erkbot.emoji import add_result_emoji, remove_eyes_emoji
from erkbot.utils import chunk_for_slack, extract_slack_message_ts


def _build_progress_display(*, text: str, tool_active: bool) -> str:
    state = "🤖 Thinking..." if tool_active else "🤖 Responding..."
    if not text:
        return state
    # Show last 2000 chars to keep Slack message reasonable
    truncated = text[-2000:] if len(text) > 2000 else text
    return f"{state}\n\n```{truncated}```"


async def run_agent_background(
    *,
    client: Any,
    channel: str,
    reply_thread_ts: str | None,
    source_ts: str,
    prompt: str,
    bot: ErkBot,
    time: Time,
    progress_update_interval_seconds: float,
    max_slack_code_block_chars: int,
    enable_suggested_replies: bool,
    suggested_reply_blocks: list[dict[str, object]],
) -> None:
    success = False
    status_ts: str | None = None
    try:
        status_result = await client.chat_postMessage(
            channel=channel,
            text="🤖 Thinking...",
            thread_ts=reply_thread_ts,
        )
        status_ts = extract_slack_message_ts(status_result)

        accumulated_text = ""
        tool_active = False
        last_update = 0.0

        async for event in bot.chat_stream(prompt=prompt):
            if isinstance(event, TextDelta):
                accumulated_text += event.text
                tool_active = False
            elif isinstance(event, ToolStart):
                tool_active = True
            elif isinstance(event, ToolEnd):
                tool_active = False

            now = time.monotonic()
            if (now - last_update) >= progress_update_interval_seconds and status_ts is not None:
                progress_text = _build_progress_display(
                    text=accumulated_text, tool_active=tool_active
                )
                try:
                    await client.chat_update(channel=channel, ts=status_ts, text=progress_text)
                except SlackApiError:
                    pass  # Best-effort progress update; failure is non-fatal
                last_update = now

        # Final update: remove status message, post final response
        if status_ts is not None:
            try:
                await client.chat_update(channel=channel, ts=status_ts, text="🤖 Done.")
            except SlackApiError:
                pass  # Best-effort status update; failure is non-fatal

        final_text = accumulated_text.strip()
        if final_text:
            for chunk in chunk_for_slack(final_text, max_chars=max_slack_code_block_chars):
                try:
                    await client.chat_postMessage(
                        channel=channel, text=chunk, thread_ts=reply_thread_ts
                    )
                except SlackApiError:
                    pass  # Best-effort response post; failure is non-fatal
        else:
            try:
                await client.chat_postMessage(
                    channel=channel,
                    text="(No response generated.)",
                    thread_ts=reply_thread_ts,
                )
            except SlackApiError:
                pass  # Best-effort fallback message; failure is non-fatal

        if enable_suggested_replies and suggested_reply_blocks:
            try:
                await client.chat_postMessage(
                    channel=channel,
                    blocks=suggested_reply_blocks,
                    text="Suggested follow-ups",
                    thread_ts=reply_thread_ts,
                )
            except SlackApiError:
                pass  # Best-effort suggested replies; failure is non-fatal

        success = True
    except Exception:
        try:
            await client.chat_postMessage(
                channel=channel,
                text="🤖 Agent encountered an error.",
                thread_ts=reply_thread_ts,
            )
        except SlackApiError:
            pass  # Best-effort error report; failure is non-fatal
    finally:
        await remove_eyes_emoji(client, channel=channel, timestamp=source_ts)
        await add_result_emoji(client, channel=channel, timestamp=source_ts, success=success)
