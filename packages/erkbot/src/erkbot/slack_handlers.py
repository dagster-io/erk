from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING, Any

from slack_sdk.errors import SlackApiError

from erk_shared.gateway.time.abc import Time
from erkbot.agent_handler import run_agent_background
from erkbot.config import Settings
from erkbot.models import (
    ChatCommand,
    OneShotCommand,
    OneShotMissingMessageCommand,
    PlanListCommand,
    QuoteCommand,
)
from erkbot.parser import parse_erk_command
from erkbot.runner import run_erk_plan_list, stream_erk_one_shot
from erkbot.utils import (
    build_one_shot_progress_text,
    chunk_for_slack,
    extract_one_shot_links,
    extract_slack_message_ts,
    load_quote_text,
    tail_output_lines,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from erkbot.agent.bot import ErkBot

SUPPORTED_COMMANDS_TEXT = (
    "Supported commands: `@erk plan list`, `@erk chat <message>`, `@erk one-shot <message>`."
)


def register_handlers(app, *, settings: Settings, bot: ErkBot | None, time: Time) -> None:  # type: ignore[no-untyped-def]
    async def add_read_ack(client: Any, channel: str, timestamp: str) -> None:
        try:
            await client.reactions_add(channel=channel, timestamp=timestamp, name="eyes")
        except SlackApiError as exc:
            ignored_errors = {"already_reacted", "missing_scope", "not_reactable"}
            if exc.response.get("error") not in ignored_errors:
                raise

    async def post_message(
        client: Any, *, channel: str, thread_ts: str | None, text: str
    ) -> object | None:
        logger.info("slack_send: channel=%s text=%s", channel, text[:200])
        try:
            return await client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
        except SlackApiError:
            logger.warning("slack_send failed: channel=%s text=%s", channel, text[:200])
            return None

    async def post_chunked_code(
        client: Any, *, channel: str, thread_ts: str | None, text: str
    ) -> None:
        for chunk in chunk_for_slack(text, max_chars=settings.max_slack_code_block_chars):
            await post_message(client, channel=channel, thread_ts=thread_ts, text=f"```{chunk}```")

    async def run_one_shot_background(
        *, client: Any, channel: str, reply_thread_ts: str | None, message: str
    ) -> None:
        logger.info("one-shot started: channel=%s message=%s", channel, message[:100])
        status = await post_message(
            client,
            channel=channel,
            thread_ts=reply_thread_ts,
            text="⏳ Running `erk one-shot`",
        )
        status_ts = extract_slack_message_ts(status)
        can_update_status = bool(status_ts)
        posted_update_fallback_notice = False
        all_lines: deque[str] = deque(maxlen=settings.one_shot_progress_tail_lines)
        pending_lines: list[str] = []
        last_update = 0.0

        async def push_progress_update(*, force: bool, running: bool) -> None:
            nonlocal can_update_status, posted_update_fallback_notice, last_update
            if not pending_lines and not force:
                return
            now = time.monotonic()
            if (
                not force
                and (now - last_update) < settings.one_shot_progress_update_interval_seconds
            ):
                return

            new_lines = list(pending_lines)
            pending_lines.clear()
            if can_update_status and status_ts is not None:
                progress_text = build_one_shot_progress_text(
                    lines=list(all_lines), running=running, settings=settings
                )
                try:
                    logger.debug(
                        "slack_update: channel=%s ts=%s text=%s",
                        channel,
                        status_ts,
                        progress_text[:200],
                    )
                    await client.chat_update(channel=channel, ts=status_ts, text=progress_text)
                    last_update = now
                    return
                except SlackApiError as exc:
                    can_update_status = False
                    if not posted_update_fallback_notice:
                        error_code = exc.response.get("error") if exc.response else "unknown_error"
                        await post_message(
                            client,
                            channel=channel,
                            thread_ts=reply_thread_ts,
                            text=(
                                "Live status updates are unavailable in this channel "
                                f"({error_code}); streaming new output in replies."
                            ),
                        )
                        posted_update_fallback_notice = True

            if not posted_update_fallback_notice and not can_update_status:
                await post_message(
                    client,
                    channel=channel,
                    thread_ts=reply_thread_ts,
                    text=(
                        "Live status updates are unavailable in this channel; "
                        "streaming new output in replies."
                    ),
                )
                posted_update_fallback_notice = True

            new_output = "\n".join(new_lines).strip()
            if new_output:
                await post_chunked_code(
                    client, channel=channel, thread_ts=reply_thread_ts, text=new_output
                )
                can_update_status = False
            last_update = now

        async def on_line(line: str) -> None:
            clean_line = line.rstrip()
            if not clean_line:
                return
            all_lines.append(clean_line)
            pending_lines.append(clean_line)
            await push_progress_update(force=False, running=True)

        result = await stream_erk_one_shot(
            message,
            timeout_seconds=settings.one_shot_timeout_seconds,
            on_line=on_line,
        )
        await push_progress_update(force=True, running=False)
        logger.info(
            "one-shot completed: channel=%s exit_code=%d output_len=%d",
            channel,
            result.exit_code,
            len(result.output),
        )

        pr_url, run_url = extract_one_shot_links(result.output)
        if result.exit_code == 0:
            summary_lines: list[str] = []
            if pr_url is not None:
                summary_lines.append(f"PR: {pr_url}")
            if run_url is not None:
                summary_lines.append(f"Run: {run_url}")
            if summary_lines:
                await post_message(
                    client,
                    channel=channel,
                    thread_ts=reply_thread_ts,
                    text="\n".join(summary_lines),
                )
            return

        logger.warning(
            "one-shot failed: channel=%s exit_code=%d timed_out=%s",
            channel,
            result.exit_code,
            result.timed_out,
        )
        timeout_suffix = " (timed out)." if result.timed_out else "."
        await post_message(
            client,
            channel=channel,
            thread_ts=reply_thread_ts,
            text=f"`erk one-shot` failed (exit {result.exit_code}){timeout_suffix}",
        )
        if result.output:
            tail_output = tail_output_lines(
                result.output,
                max_lines=settings.one_shot_failure_tail_lines,
            )
            if tail_output:
                await post_chunked_code(
                    client, channel=channel, thread_ts=reply_thread_ts, text=tail_output
                )

    @app.event("app_mention")
    async def handle_app_mention(event, say, client) -> None:  # type: ignore[no-untyped-def]
        user = event.get("user", "there")
        channel = event.get("channel")
        source_ts = event.get("ts")
        text = event.get("text", "")
        logger.info("app_mention: user=%s channel=%s text=%s", user, channel, text[:100])
        if channel and source_ts:
            await add_read_ack(client, channel, source_ts)

        reply_thread_ts = event.get("thread_ts") or source_ts
        command = parse_erk_command(text)

        if isinstance(command, PlanListCommand):
            await say("Running `erk plan list`...", thread_ts=reply_thread_ts)
            result = await run_erk_plan_list()
            status_line = (
                "Result from `erk plan list`:"
                if result.exit_code == 0
                else f"`erk plan list` failed (exit {result.exit_code}):"
            )
            logger.info(
                "reply: channel=%s command=plan-list exit_code=%d", channel, result.exit_code
            )
            await say(status_line, thread_ts=reply_thread_ts)
            for chunk in chunk_for_slack(
                result.output, max_chars=settings.max_slack_code_block_chars
            ):
                await say(f"```{chunk}```", thread_ts=reply_thread_ts)
            return

        if isinstance(command, QuoteCommand):
            quote = load_quote_text()
            logger.info("reply: channel=%s command=quote len=%d", channel, len(quote))
            for chunk in chunk_for_slack(quote, max_chars=settings.max_slack_code_block_chars):
                await say(chunk, thread_ts=reply_thread_ts)
            return

        if isinstance(command, OneShotMissingMessageCommand):
            logger.info("reply: channel=%s command=one-shot-missing-message", channel)
            await say("Usage: `@erk one-shot <message>`", thread_ts=reply_thread_ts)
            return

        if isinstance(command, ChatCommand):
            if bot is None:
                await say("Agent mode is not configured.", thread_ts=reply_thread_ts)
                return
            if not channel:
                await say(
                    "Could not determine channel for this mention.", thread_ts=reply_thread_ts
                )
                return
            asyncio.create_task(
                run_agent_background(
                    client=client,
                    channel=channel,
                    reply_thread_ts=reply_thread_ts,
                    source_ts=source_ts,
                    prompt=command.message,
                    bot=bot,
                    time=time,
                    progress_update_interval_seconds=settings.one_shot_progress_update_interval_seconds,
                    max_slack_code_block_chars=settings.max_slack_code_block_chars,
                )
            )
            return

        if isinstance(command, OneShotCommand):
            if len(command.message) > settings.max_one_shot_message_chars:
                logger.warning(
                    "reply: channel=%s command=one-shot rejected=too_long len=%d",
                    channel,
                    len(command.message),
                )
                await say(
                    (
                        "One-shot message is too long "
                        f"({len(command.message)} chars, "
                        f"max {settings.max_one_shot_message_chars})."
                    ),
                    thread_ts=reply_thread_ts,
                )
                return
            if not channel:
                logger.warning("reply: command=one-shot rejected=no_channel")
                await say(
                    "Could not determine channel for this mention.", thread_ts=reply_thread_ts
                )
                return
            asyncio.create_task(
                run_one_shot_background(
                    client=client,
                    channel=channel,
                    reply_thread_ts=reply_thread_ts,
                    message=command.message,
                )
            )
            return

        logger.info("reply: channel=%s command=unknown", channel)
        await say(f"Hi <@{user}>. {SUPPORTED_COMMANDS_TEXT}", thread_ts=reply_thread_ts)

    @app.message("ping")
    async def handle_ping(message, say, client) -> None:  # type: ignore[no-untyped-def]
        logger.info("ping: channel=%s", message.get("channel"))
        channel = message.get("channel")
        source_ts = message.get("ts")
        if channel and source_ts:
            await add_read_ack(client, channel, source_ts)

        reply_thread_ts = message.get("thread_ts") or source_ts
        logger.info("reply: channel=%s command=ping", channel)
        await say("Pong!", thread_ts=reply_thread_ts)
