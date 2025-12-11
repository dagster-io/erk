"""Handler for !flood command to test rate limiting."""

import asyncio
import logging
from textwrap import dedent
from typing import TYPE_CHECKING, Any, cast

from slack_sdk.web.async_client import AsyncWebClient

from csbot.agents.messages import AgentTextMessage

if TYPE_CHECKING:
    from csbot.agents.protocol import AsyncAgent


class FloodHandler:
    """Handler for flood testing rate limits on Slack and Anthropic APIs."""

    def __init__(
        self,
        logger: logging.Logger,
        slack_client: AsyncWebClient,
        agent: "AsyncAgent",
    ):
        self.logger = logger
        self.client = slack_client
        self.agent = agent

    async def handle_message(
        self,
        channel: str,
        event: dict[str, Any],
        message_content: str,
        user: str | None,
    ) -> None:
        """Handle !flood command messages."""
        parts = message_content.strip().split()

        # Show help message
        if len(parts) > 1 and parts[1] == "help":
            message_ts = cast("str", event.get("ts"))
            await self._handle_flood_help(channel, message_ts)
            return

        count = 50  # default
        use_async = "async" in parts
        use_edit = "edit" in parts
        use_anthropic = "anthropic" in parts
        large_input = "large_input" in parts
        large_output = "large_output" in parts

        if len(parts) > 1:
            try:
                count = int(parts[1])
            except ValueError:
                count = 50

        message_ts = cast("str", event.get("ts"))

        if use_anthropic:
            await self._handle_anthropic_flood(
                channel=channel,
                thread_ts=message_ts,
                count=count,
                large_input=large_input,
                large_output=large_output,
                user=user or "",
            )
        else:
            await self._handle_slack_flood(
                channel=channel,
                thread_ts=message_ts,
                count=count,
                use_async=use_async,
                use_edit=use_edit,
                user=user or "",
            )

    async def _handle_flood_help(self, channel: str, thread_ts: str) -> None:
        """Display help message for flood command."""
        help_text = dedent("""
            **!flood command usage:**

            **Slack API flood tests:**
            • `!flood 100` - Sequential posts (50 default)
            • `!flood 100 async` - Parallel posts to trigger Slack rate limits
            • `!flood 100 edit` - Sequential edits of same message
            • `!flood 100 async edit` - Parallel edits

            **Anthropic API flood tests:**
            Rate limits (Sonnet 4.x): 50 RPM, 30k ITPM, 8k OTPM

            • `!flood 100 anthropic` - Hit RPM limit
              → 100 concurrent small requests (~20 tokens in, 10 tokens out)
              → Hits RPM limit at 50 requests

            • `!flood 50 anthropic large_input` - Hit ITPM limit
              → 50 concurrent requests with ~700 token prompts each
              → Total: ~35k input tokens > 30k ITPM limit

            • `!flood 50 anthropic large_output` - Hit OTPM limit
              → 50 concurrent requests with ~200 token outputs each
              → Total: ~10k output tokens > 8k OTPM limit

            • `!flood 50 anthropic large_input large_output` - Hit multiple limits
              → Combines large inputs and outputs to test retry behavior
        """).strip()
        await self.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=help_text,
        )

    async def _handle_anthropic_flood(
        self,
        channel: str,
        thread_ts: str,
        count: int,
        large_input: bool,
        large_output: bool,
        user: str,
    ) -> None:
        """Handle Anthropic API flood test."""
        # Configure prompt size and output size based on flags
        if large_input and large_output:
            test_type = "large input (~700 tokens) + large output (~200 tokens)"
            input_tokens_est = 700
            max_tokens = 200
        elif large_input:
            test_type = "large input (~700 tokens)"
            input_tokens_est = 700
            max_tokens = 10
        elif large_output:
            test_type = "large output (~200 tokens)"
            input_tokens_est = 20
            max_tokens = 200
        else:
            test_type = "small input/output (~20 tokens in, 10 out)"
            input_tokens_est = 20
            max_tokens = 10

        total_input_tokens = count * input_tokens_est
        total_output_tokens = count * max_tokens

        self.logger.info(
            f"MENTION: flooding Anthropic API with {count} requests ({test_type}) as requested by {user}"
        )
        await self.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"Starting Anthropic API flood test with {count} concurrent requests\n"
            f"Config: {test_type}\n"
            f"Estimated: ~{total_input_tokens:,} input tokens, ~{total_output_tokens:,} output tokens\n"
            f"Rate limits: 50 RPM, 30k ITPM, 8k OTPM (Sonnet 4.x)",
        )

        try:
            # Make concurrent API calls to trigger 429 rate limits
            tasks = []
            for i in range(count):
                if large_input:
                    # Large prompt (~700 tokens) to hit ITPM limit
                    # 50 requests × 700 tokens = 35k tokens > 30k ITPM limit
                    large_context = " ".join(
                        [
                            f"This is sentence number {j} in a large context prompt to increase the input token count."
                            for j in range(130)
                        ]
                    )
                    prompt = f"Context:\n{large_context}\n\nNumber {i}."
                    if large_output:
                        prompt += " Write a detailed 200-word explanation about this number."
                    else:
                        prompt += " Reply with just the number."
                else:
                    # Small prompt (~20 tokens)
                    if large_output:
                        prompt = f"Write a detailed 200-word explanation of the number {i}."
                    else:
                        prompt = f"Say the number {i} and nothing else."

                task = self.agent.create_completion(
                    model=self.agent.model,
                    system="You are a helpful assistant.",
                    messages=[
                        AgentTextMessage(
                            role="user",
                            content=prompt,
                        )
                    ],
                    max_tokens=max_tokens,
                )
                tasks.append(task)

            # Execute all requests concurrently to aggressively trigger rate limiting
            await asyncio.gather(*tasks)

            # If we get here, all requests succeeded (possibly with retries)
            await self.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="COMPLETE - All Anthropic API requests succeeded!",
            )
        except Exception as e:
            # Other errors
            await self.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"ERROR - {type(e).__name__}: {e}",
            )

    async def _handle_slack_flood(
        self,
        channel: str,
        thread_ts: str,
        count: int,
        use_async: bool,
        use_edit: bool,
        user: str,
    ) -> None:
        """Handle Slack API flood test."""
        mode = "async (parallel)" if use_async else "sequential"
        operation = "edits" if use_edit else "posts"
        self.logger.info(
            f"MENTION: flooding thread in {channel} with {count} {operation} ({mode}) as requested by {user}"
        )
        await self.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"Starting flood test with {count} {operation} ({mode})...",
        )

        if use_edit:
            # Post one message, then edit it many times
            response = await self.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="Initial message (will be edited)",
            )
            edit_msg_ts = str(response["ts"])

            if use_async:
                # Edit the same message in parallel
                tasks = [
                    self.client.chat_update(
                        channel=channel,
                        ts=edit_msg_ts,
                        text=f"Edited flood test message {i + 1}/{count}",
                    )
                    for i in range(count)
                ]
                await asyncio.gather(*tasks)
                # Update one final time to say COMPLETE
                await self.client.chat_update(
                    channel=channel,
                    ts=edit_msg_ts,
                    text="COMPLETE",
                )
            else:
                # Edit the same message sequentially
                for i in range(count):
                    await self.client.chat_update(
                        channel=channel,
                        ts=edit_msg_ts,
                        text=f"Edited flood test message {i + 1}/{count}",
                    )
        else:
            # Regular post messages
            if use_async:
                # Post messages in parallel to aggressively trigger rate limiting
                tasks = [
                    self.client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"Flood test message {i + 1}/{count}",
                    )
                    for i in range(count)
                ]
                await asyncio.gather(*tasks)
            else:
                # Post messages sequentially
                for i in range(count):
                    await self.client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"Flood test message {i + 1}/{count}",
                    )

        await self.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text="Flood test complete!",
        )
