import asyncio
import json
import random
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol

import structlog
from ddtrace.trace import tracer
from pygit2 import TYPE_CHECKING
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.web.async_slack_response import AsyncSlackResponse

from csbot.slackbot.slackbot_blockkit import Block

logger = structlog.get_logger(__name__)


async def wait_for_file_ready(
    client: AsyncWebClient,
    file_id: str,
    check_ready: Callable[[dict[str, Any]], bool],
    max_attempts: int = 30,
) -> None:
    """Wait for a Slack file upload to be ready by polling files_info.

    Args:
        client: The Slack WebClient to use
        file_id: The ID of the uploaded file
        check_ready: A function that takes the file info dict and returns True if ready
        max_attempts: Maximum number of polling attempts (default 30)

    Raises:
        ValueError: If file info cannot be retrieved or file doesn't become ready
    """
    for _ in range(max_attempts):
        info_response = await client.files_info(file=file_id)
        if not info_response.get("ok"):
            raise ValueError("Failed to get file info")
        if check_ready(info_response.get("file", {})):
            return
        await asyncio.sleep(1)
    raise ValueError(f"File {file_id} did not become ready after {max_attempts} attempts")


@dataclass
class DeleteMessageCall:
    client: AsyncWebClient
    attempts: int
    observability_context: Any | None


@dataclass
class UpdateMessageCall:
    client: AsyncWebClient
    blocks: list[Block]
    text: str
    attempts: int
    observability_context: Any | None


NextSlackCallForMessage = DeleteMessageCall | UpdateMessageCall


class SlackCallError(Exception):
    error: str
    response: AsyncSlackResponse | None

    def __init__(self, error: str, response: AsyncSlackResponse | None):
        super().__init__(f"Slack call error: {error}")
        self.error = error
        self.response = response


class SlackCallThrottler:
    def __init__(self, slack_api_timeout_seconds: float = 10.0):
        # channel_id -> message_ts -> NextSlackCallForMessage
        self.queues: dict[str, dict[str, NextSlackCallForMessage]] = defaultdict(lambda: {})
        self.running = False
        self.slack_api_timeout_seconds = slack_api_timeout_seconds
        self.lock = threading.RLock()

    def stop(self):
        self.running = False

    def chat_update(
        self,
        client: AsyncWebClient,
        channel_id: str,
        message_ts: str,
        blocks: list[Block],
        text: str,
    ):
        if not self.running:
            raise Exception("Throttler is not running")

        # Capture current observability context
        observability_context = tracer.current_trace_context()

        with self.lock:
            next_message = self.queues[channel_id].get(message_ts)
            if isinstance(next_message, DeleteMessageCall):
                # No updates after a delete (this should never happen)
                return

            self.queues[channel_id][message_ts] = UpdateMessageCall(
                client=client,
                blocks=blocks,
                text=text,
                attempts=0,
                observability_context=observability_context,
            )

    def chat_delete(self, client: AsyncWebClient, channel_id: str, message_ts: str):
        if not self.running:
            raise Exception("Throttler is not running")

        # Capture current observability context
        observability_context = tracer.current_trace_context()

        self.queues[channel_id][message_ts] = DeleteMessageCall(
            client=client, attempts=0, observability_context=observability_context
        )

    def _select_next_message(
        self, max_attempts: int
    ) -> tuple[str, str, NextSlackCallForMessage] | None:
        if len(self.queues) == 0:
            return None

        shuffled_channel_ids = list(self.queues.keys())
        random.shuffle(shuffled_channel_ids)
        for channel_id in shuffled_channel_ids:
            message_ts_to_call = self.queues[channel_id]
            if len(message_ts_to_call) == 0:
                del self.queues[channel_id]
                continue
            message_ts = next(iter(sorted(message_ts_to_call.keys())))
            next_message = message_ts_to_call[message_ts]
            if next_message.attempts >= max_attempts:
                logger.warning(
                    f"Max attempts for {next_message.__class__.__name__} reached for message {message_ts} in channel {channel_id}"
                )
                del self.queues[channel_id][message_ts]
                continue
            return channel_id, message_ts, next_message
        return None

    async def _chat_update_with_block_mismatch_guard(
        self, channel_id: str, message_ts: str, message: UpdateMessageCall
    ):
        async def try_update():
            await message.client.chat_update(
                channel=channel_id,
                ts=message_ts,
                blocks=[block.to_dict() for block in message.blocks],
                text=message.text,
            )

        try:
            await try_update()
        except SlackApiError as e:
            if e.response.get("error") == "block_mismatch":
                # delete the blocks, then try again
                await message.client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    blocks=[],
                    text=" ",
                )
                await try_update()
            else:
                raise

    async def _tick(self, max_attempts: int):
        with self.lock:
            selected_message = self._select_next_message(max_attempts)
            if selected_message is None:
                return False
            channel_id, message_ts, next_message = selected_message

            next_message.attempts += 1

        # Restore observability context for this Slack call
        original_context = tracer.current_trace_context()
        if next_message.observability_context is not None:
            tracer.context_provider.activate(next_message.observability_context)

        try:
            if isinstance(next_message, UpdateMessageCall):
                await asyncio.wait_for(
                    self._chat_update_with_block_mismatch_guard(
                        channel_id, message_ts, next_message
                    ),
                    timeout=self.slack_api_timeout_seconds,
                )
            elif isinstance(next_message, DeleteMessageCall):
                await asyncio.wait_for(
                    next_message.client.chat_delete(channel=channel_id, ts=message_ts),
                    timeout=self.slack_api_timeout_seconds,
                )
            else:
                raise ValueError(f"Invalid next message: {next_message}")
        except TimeoutError:
            logger.warning(
                f"Slack API call timed out after {self.slack_api_timeout_seconds}s for message {message_ts} in channel {channel_id}"
            )
            raise SlackCallError(error="timeout", response=None)
        except SlackApiError as e:
            raise SlackCallError(error=e.response.get("error"), response=e.response)
        finally:
            # Always restore the original context
            tracer.context_provider.activate(original_context)

        with self.lock:
            if self.queues[channel_id].get(message_ts) == next_message:
                del self.queues[channel_id][message_ts]

        return True

    async def run(
        self,
        min_delay_seconds: float = 0.1,
        recovery_seconds: float = 60,
        min_backoff_seconds: float = 0.25,
        max_backoff_seconds: float = 10,
        max_attempts: int = 3,
    ):
        backoff_seconds = 0
        backoff_last_updated_at_seconds = 0
        self.running = True

        while self.running:
            ran_call = True
            try:
                ran_call = await self._tick(max_attempts)
            except SlackCallError as e:
                if e.error == "ratelimited":
                    backoff_seconds = min(
                        max_backoff_seconds, max(backoff_seconds * 2, min_backoff_seconds)
                    )
                    logger.warning(f"Slack rate limited, backing off for {backoff_seconds} seconds")
                    backoff_last_updated_at_seconds = time.time()
                elif e.error == "timeout":
                    logger.warning("Slack API call timed out, retrying")
                    # Don't increase backoff for timeouts, just retry
                else:
                    logger.error(f"Slack call error from throttler: {e.error}", exc_info=True)
            except Exception as e:
                logger.error(f"Error calling Slack API from throttler: {e}", exc_info=True)

            if not ran_call:
                # Don't spin cpu
                await asyncio.sleep(0.02)
                continue

            if (
                backoff_seconds > 0
                and time.time() - backoff_last_updated_at_seconds > recovery_seconds
            ):
                backoff_seconds = 0
                backoff_last_updated_at_seconds = time.time()
            target_sleep_seconds = min_delay_seconds + backoff_seconds
            await asyncio.sleep(target_sleep_seconds)


# Global throttle per bot process
# Good enough for now
throttler = SlackCallThrottler(slack_api_timeout_seconds=10.0)


@dataclass(frozen=True)
class SlackMessage:
    channel_id: str
    ts: str
    prev_content_hash: int


@dataclass(frozen=True)
class BlockMessage:
    blocks: list[Block]

    def to_json_string(self):
        return json.dumps([block.to_dict() for block in self.blocks], sort_keys=True)


def blocks_to_messages(
    blocks: Sequence[Block], max_message_length: int, max_blocks_per_message: int
) -> list[BlockMessage]:
    if len(blocks) == 0:
        return []

    messages: list[BlockMessage] = [BlockMessage(blocks=[])]
    for block in blocks:
        current_message = messages[-1]

        current_message.blocks.append(block)
        if len(current_message.blocks) != 1 and (
            len(current_message.blocks) > max_blocks_per_message
            or len(current_message.to_json_string()) > max_message_length
        ):
            current_message.blocks.pop()
            messages.append(BlockMessage(blocks=[block]))

    return messages


class BlockSingleMessageReconciler:
    def __init__(
        self,
        slack_client: AsyncWebClient,
        channel_id: str,
        message_ts: str,
        slack_message: SlackMessage,
    ):
        self.slack_client = slack_client
        self.channel_id = channel_id
        self.message_ts = message_ts
        self.slack_message: SlackMessage = slack_message

    async def reconcile(self, block_message: BlockMessage):
        markdowns = [block.to_markdown() for block in block_message.blocks]
        text = "\n".join(markdown for markdown in markdowns if markdown is not None)

        block_message_content_hash = hash(block_message.to_json_string())

        # update the existing message if the content has changed
        if self.slack_message.prev_content_hash == block_message_content_hash:
            # nothing to do since the content hasn't changed
            return

        throttler.chat_update(
            client=self.slack_client,
            channel_id=self.slack_message.channel_id,
            message_ts=self.slack_message.ts,
            blocks=block_message.blocks,
            text=text,
        )

        self.slack_message = replace(
            self.slack_message, prev_content_hash=block_message_content_hash
        )


class BlockMessageReconciler:
    def __init__(
        self,
        slack_client: AsyncWebClient,
        channel_id: str,
        thread_ts: str | None,
        max_preview_message_length: int,
    ):
        self.slack_client = slack_client
        self.channel_id = channel_id
        self.thread_ts = thread_ts
        self.slack_messages: list[SlackMessage] = []
        self.max_preview_message_length = max_preview_message_length

    def get_thread_ts(self) -> str | None:
        if self.thread_ts:
            return self.thread_ts
        if len(self.slack_messages) > 0:
            return self.slack_messages[0].ts
        return None

    async def reconcile(self, block_messages: Sequence[BlockMessage]):
        for block_message_id, block_message in enumerate(block_messages):
            slack_message = (
                self.slack_messages[block_message_id]
                if block_message_id < len(self.slack_messages)
                else None
            )

            # we might be the first message in the thread
            thread_ts = self.get_thread_ts()

            if not thread_ts and block_message_id != 0:
                raise ValueError("This should never happen")

            markdowns = [block.to_markdown() for block in block_message.blocks]
            text = "\n".join(markdown for markdown in markdowns if markdown is not None)[
                : self.max_preview_message_length
            ]

            block_message_content_hash = hash(block_message.to_json_string())

            try:
                if not slack_message:
                    # send a new one and record the state
                    response = await self.slack_client.chat_postMessage(
                        channel=self.channel_id,
                        thread_ts=self.thread_ts,
                        blocks=[block.to_dict() for block in block_message.blocks],
                        text=text,
                    )
                    self.slack_messages.append(
                        SlackMessage(
                            channel_id=response["channel"],  # type: ignore  # Slack API response dict access returns Any
                            ts=response["ts"],  # type: ignore  # Slack API response dict access returns Any
                            prev_content_hash=block_message_content_hash,
                        )
                    )
                else:
                    # update the existing message if the content has changed
                    if slack_message.prev_content_hash == block_message_content_hash:
                        # nothing to do since the content hasn't changed
                        continue
                    channel_id = slack_message.channel_id
                    ts = slack_message.ts
                    throttler.chat_update(
                        client=self.slack_client,
                        channel_id=channel_id,
                        message_ts=ts,
                        blocks=block_message.blocks,
                        text=text,
                    )
                    self.slack_messages[block_message_id] = replace(
                        slack_message, prev_content_hash=block_message_content_hash
                    )

            except Exception as e:
                block_dicts = [block.to_dict() for block in block_message.blocks]
                logger.error(
                    f"Error posting or updating message: {e}\nBlocks: {block_dicts}", exc_info=True
                )
                raise e

        # delete messages that are no longer used
        num_slack_messages_to_delete = len(self.slack_messages) - len(block_messages)
        if num_slack_messages_to_delete > 0:
            slack_messages_to_delete = self.slack_messages[-num_slack_messages_to_delete:]
            self.slack_messages = self.slack_messages[:-num_slack_messages_to_delete]
            for slack_message in slack_messages_to_delete:
                throttler.chat_delete(
                    client=self.slack_client,
                    channel_id=slack_message.channel_id,
                    message_ts=slack_message.ts,
                )


@dataclass(frozen=True)
class ImageAttachment:
    id: str
    url: str


@dataclass(frozen=True)
class CsvAttachment:
    id: str
    url: str
    filename: str


class StreamProtocol(Protocol):
    async def update(self, blocks: Sequence[Block]): ...

    async def finish(self): ...


class BaseSlackstream:
    """
    Base class for throttled Slack message streaming.

    Provides common functionality for updating Slack messages with blocks while
    respecting throttling limits to avoid hitting Slack's rate limits. Subclasses
    implement specific rendering strategies (single message vs multiple messages).

    The throttling mechanism ensures that rapid updates are batched together,
    with a configurable minimum time between actual Slack API calls.
    """

    def __init__(
        self,
        client: AsyncWebClient,
        channel_id: str,
        throttle_time_seconds: float = 0.5,
    ):
        self.client = client
        self.channel_id = channel_id
        self.throttle_time_seconds = throttle_time_seconds
        self.last_render_time = 0
        self.call_later_handle: asyncio.TimerHandle | None = None
        self.dirty = False
        self.finished = False
        self.blocks: list[Block] = []

    async def update(self, blocks: Sequence[Block]):
        if self.finished:
            raise ValueError("Cannot update after finish")
        self.blocks = list(blocks)
        self.dirty = True
        await self._render()

    async def _flush_from_timer(self):
        if self.call_later_handle is None:
            raise ValueError("No call later handle")
        self.call_later_handle = None
        await self._render()

    async def _render(self):
        if not self.dirty:
            return

        now = time.time()
        next_render_time = self.last_render_time + self.throttle_time_seconds

        if now < next_render_time:
            if self.call_later_handle is None:
                self.call_later_handle = asyncio.get_event_loop().call_later(
                    next_render_time - now,
                    lambda: asyncio.create_task(self._flush_from_timer()),
                )
            return
        self.last_render_time = now
        self.dirty = False

        await self._render_blocks()

    async def _render_blocks(self):
        raise NotImplementedError("Subclasses must implement _render_blocks")

    async def finish(self):
        await self._render()


class SlackstreamReply(BaseSlackstream):
    """
    Streams content as multiple threaded replies in a Slack conversation.

    Unlike SlackstreamMessage which updates a single message, SlackstreamReply
    can create and manage multiple messages in a thread to handle large amounts
    of content. It automatically splits blocks across multiple messages based on
    Slack's message length and block count limits.

    This is ideal for streaming long-form responses like analysis results, where
    content may exceed single message limits and needs to be broken into logical
    chunks across multiple thread replies.

    Also provides image attachment capabilities for including visual content
    in responses.
    """

    def __init__(
        self,
        client: AsyncWebClient,
        channel_id: str,
        thread_ts: str,
        throttle_time_seconds: float = 0.5,
        max_message_length: int = 4000,
        max_preview_message_length: int = 4000,
        max_blocks_per_message: int = 40,
    ):
        super().__init__(client, channel_id, throttle_time_seconds)
        self.reconciler = BlockMessageReconciler(
            slack_client=client,
            channel_id=channel_id,
            thread_ts=thread_ts,
            max_preview_message_length=max_preview_message_length,
        )
        self.max_blocks_per_message = max_blocks_per_message
        self.max_message_length = max_message_length

    async def _render_blocks(self):
        messages = blocks_to_messages(
            self.blocks,
            self.max_message_length,
            self.max_blocks_per_message,
        )
        await self.reconciler.reconcile(messages)

    async def attach_image(self, image_data: bytes) -> ImageAttachment:
        # TODO: someday we can make this immediate mode but for now we'll just treat it as
        # imperative
        if self.finished:
            raise ValueError("Cannot attach image after finish")

        complete_resp = await self.client.files_upload_v2(filename="image.png", file=image_data)

        if not complete_resp.get("ok"):
            raise ValueError("Failed to complete upload")

        file = complete_resp["files"][0]  # type: ignore  # Slack API response dict access returns Any

        await wait_for_file_ready(
            self.client,
            file["id"],
            lambda file_info: bool(file_info.get("thumb_64")),
        )

        return ImageAttachment(
            id=file["id"],
            url=file["url_private"],
        )

    async def attach_csv(self, csv_data: str, filename: str) -> CsvAttachment:
        """
        Attach a CSV file to the message thread.

        Args:
            csv_data: The CSV file data as str. Please ensure that duplicate rows are removed.
            filename: The filename for the CSV file (must end with .csv)

        Returns:
            CsvAttachment containing the file ID, URL, and filename

        Raises:
            ValueError: If filename doesn't end with .csv or if upload fails
        """
        if self.finished:
            raise ValueError("Cannot attach CSV after finish")

        thread_ts = self.reconciler.get_thread_ts()
        if not thread_ts:
            raise ValueError("Cannot attach CSV without a thread")

        complete_resp = await self.client.files_upload_v2(
            filename=filename,
            content=csv_data,
            thread_ts=thread_ts,
            channel=self.channel_id,
        )

        if not complete_resp.get("ok"):
            raise ValueError("Failed to complete CSV upload")

        file = complete_resp["files"][0]  # type: ignore  # Slack API response dict access returns Any

        # Wait for file to be processed
        await wait_for_file_ready(
            self.client,
            file["id"],
            lambda file_info: bool(file_info.get("url_private")),
        )

        return CsvAttachment(
            id=file["id"],
            url=file["url_private"],
            filename=filename,
        )


class SlackstreamMessage(BaseSlackstream):
    """
    Updates a single Slack message in-place with throttled rendering.

    SlackstreamMessage handles a single pre-existing Slack message, which
    can either be in a thread or a top-level message in a channel.
    """

    def __init__(
        self,
        client: AsyncWebClient,
        channel_id: str,
        message_ts: str,
        throttle_time_seconds: float = 0.5,
    ):
        super().__init__(client, channel_id, throttle_time_seconds)
        self.reconciler = BlockSingleMessageReconciler(
            slack_client=client,
            channel_id=channel_id,
            message_ts=message_ts,
            slack_message=SlackMessage(
                channel_id=channel_id,
                ts=message_ts,
                prev_content_hash=0,
            ),
        )
        self.message_ts = message_ts

    @classmethod
    async def post_message(cls, client: AsyncWebClient, channel_id: str, blocks: Sequence[Block]):
        """Create a new message and return a SlackstreamMessage to update it."""
        markdowns = [block.to_markdown() for block in blocks]
        text = "\n".join(markdown for markdown in markdowns if markdown is not None)
        response = await client.chat_postMessage(
            channel=channel_id,
            blocks=[block.to_dict() for block in blocks],
            text=text,
        )
        result = cls(client, channel_id, response["ts"])  # type: ignore  # Slack API response dict access returns Any
        await result.update(blocks)
        return result

    async def _render_blocks(self):
        await self.reconciler.reconcile(BlockMessage(blocks=self.blocks))


if TYPE_CHECKING:
    _: StreamProtocol = BaseSlackstream(...)  # type: ignore[abstract]
