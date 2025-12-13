"""
Dataset processing utilities for remove operations and error notifications.

This module provides utilities for dataset removal (which hasn't been migrated to Temporal yet)
and error notifications used by both Temporal activities and admin commands.
"""

import asyncio
import threading
from enum import Enum
from typing import TYPE_CHECKING

from ddtrace.trace import tracer

from csbot.contextengine.contextstore_protocol import ContextStore, Dataset
from csbot.contextengine.protocol import ContextStoreManager
from csbot.slackbot.slackbot_blockkit import (
    SectionBlock,
    TextObject,
    TextType,
)
from csbot.slackbot.slackbot_slackstream import SlackstreamMessage

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


class DatasetStatus(Enum):
    """Status tracking for individual datasets."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


async def remove_datasets_with_pr(
    context_store: ContextStore,
    mutator: ContextStoreManager,
    connection: str,
    datasets: list[str],
    pr_title: str,
    pr_body: str,
    automerge: bool,
    preamble: str,
    message: SlackstreamMessage,
) -> str:
    """Remove dataset documentation files via pull request."""

    if len(pr_title) > 72:
        pr_title = pr_title[: 72 - 3] + "..."

    dataset_status = {dataset: DatasetStatus.PENDING for dataset in datasets}
    status_lock = threading.Lock()

    def create_dataset_status_blocks() -> list[SectionBlock]:
        status_emoji = {
            DatasetStatus.PENDING: "*️⃣",
            DatasetStatus.IN_PROGRESS: "🔄",
            DatasetStatus.COMPLETED: "🗑️",
            DatasetStatus.FAILED: "❌",
        }

        dataset_lines = []
        with status_lock:
            for dataset in datasets:
                emoji = status_emoji[dataset_status[dataset]]
                dataset_lines.append(f"{emoji} `{dataset}`")

        header_text = f"{preamble}:\n\n" + "\n".join(dataset_lines)

        return [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=header_text,
                )
            )
        ]

    async def update_progress():
        updated_blocks = create_dataset_status_blocks()
        await message.update(blocks=updated_blocks)

    blocks = create_dataset_status_blocks()
    await message.update(blocks=blocks)

    def run_sync_operations(context_store: ContextStore) -> ContextStore:
        for dataset in datasets:
            with status_lock:
                dataset_status[dataset] = DatasetStatus.IN_PROGRESS
            asyncio.run(update_progress())

            context_store = context_store.remove_dataset(
                Dataset(connection=connection, table_name=dataset)
            )

            with status_lock:
                dataset_status[dataset] = DatasetStatus.COMPLETED
            asyncio.run(update_progress())

        return context_store

    after = await asyncio.to_thread(run_sync_operations, context_store)
    mutation_token = await mutator.mutate(
        pr_title,
        pr_body,
        automerge,
        before=context_store,
        after=after,
    )

    return mutation_token


@tracer.wrap()
async def notify_dataset_error(
    bot: "CompassChannelBaseBotInstance",
    error_message: str,
    governance_channel_id: str | None = None,
    thread_ts: str | None = None,
):
    """Send error notification to Slack channel/thread."""
    if governance_channel_id and bot.client:
        await bot.client.chat_postMessage(
            channel=governance_channel_id,
            thread_ts=thread_ts,
            text=f"❌ *Error:* {error_message}",
        )
