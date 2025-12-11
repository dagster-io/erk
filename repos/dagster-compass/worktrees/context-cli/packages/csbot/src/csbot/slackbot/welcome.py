"""Utilities for sending welcome messages to Compass channels."""

import logging
from typing import TYPE_CHECKING

from csbot.slackbot.storage.onboarding_state import ProspectorDataType

if TYPE_CHECKING:
    from slack_sdk.web.async_client import AsyncWebClient


async def send_compass_pinned_welcome_message(
    client: "AsyncWebClient",
    channel_id: str,
    logger: logging.Logger,
) -> None:
    """Send and pin welcome message to a Compass channel.

    The Slack SDK will automatically raise SlackApiError if the API call fails.

    Args:
        client: Slack AsyncWebClient instance
        channel_id: ID of the channel to send welcome message to
        logger: Logger instance for operation logging

    Raises:
        SlackApiError: If sending or pinning the message fails

    Example:
        from csbot.slackbot.slack_client import create_slack_client
        from slack_sdk.errors import SlackApiError

        client = create_slack_client(token=bot_token)
        try:
            await send_compass_pinned_welcome_message(client, channel_id, logger)
        except SlackApiError as e:
            logger.error(f"Failed to send welcome: {e.response['error']}")
    """
    welcome_text = (
        ":wave: Welcome to Compass!\n\n"
        "I'm your AI data assistant. I can create charts, run analyses, and answer questions about your data.\n\n"
        "To get started, @ mention me and ask something like:\n"
        '"Which customers churned this month?"\n\n'
        ":bulb: I'll remember context within each thread. Visit https://docs.compass.dagster.io for help.\n\n"
        ":gear: Need admin actions? Type `!admin` in this channel."
    )

    response = await client.chat_postMessage(
        channel=channel_id,
        text=welcome_text,
        unfurl_links=False,
        unfurl_media=False,
    )

    message_ts = response.get("ts")
    logger.info(f"Successfully sent welcome message to channel {channel_id}")

    # Pin the welcome message to the channel
    await client.pins_add(channel=channel_id, timestamp=message_ts)
    logger.info(f"Successfully pinned welcome message in channel {channel_id}")

    response = await client.chat_postMessage(
        channel=channel_id,
        text="🎬 <https://www.loom.com/share/98e15fae0ea54bf89f97fca3cd743442|Watch a video to get started>",
        unfurl_links=True,
        unfurl_media=True,
    )
    message_ts = response.get("ts")
    if not message_ts:
        logger.error("No message timestamp in video response")
        return
    await client.pins_add(channel=channel_id, timestamp=message_ts)
    logger.info(f"Successfully pinned welcome video in channel {channel_id}")


async def send_prospector_pinned_welcome_message(
    client: "AsyncWebClient",
    channel_id: str,
    logger: logging.Logger,
    data_type: "ProspectorDataType | None" = None,
) -> None:
    video_url = None
    if data_type == ProspectorDataType.SALES:
        example_question = "Can you give me a list of the 5 fastest growing SAAS startups?"
        video_url = "https://www.loom.com/share/62422205b2754b6a97f70a4d3880f8e9"
    elif data_type == ProspectorDataType.RECRUITING:
        video_url = "https://www.loom.com/share/63a834dae37941329d30ab587dcc8170"
        example_question = (
            "Can you find me senior software engineers with 5+ years of Python experience?"
        )
    elif data_type == ProspectorDataType.INVESTING:
        example_question = "Can you analyze recent AI startup funding rounds and identify promising investment opportunities?"
    else:
        example_question = "What can you help me with?"

    welcome_text = (
        "👋 Welcome to Compass!\n\n"
        "I'm your AI data assistant. I can create charts, run analyses, and answer questions about your data.\n\n"
        "To get started, @ mention me and ask something like:\n"
        f'"{example_question}"\n\n'
        "💡 Visit the <https://docs.compass.dagster.io|Compass Docs> for help.\n\n"
        ":gear: Need admin actions? Type `!admin` in this channel."
    )
    message_response = await client.chat_postMessage(
        channel=channel_id,
        text=welcome_text,
        unfurl_links=False,
        unfurl_media=False,
    )
    if message_response.get("ok") and message_response.get("ts"):
        await client.pins_add(channel=channel_id, timestamp=message_response["ts"])
        logger.info(f"Posted and pinned welcome message to {channel_id}")

    if video_url:
        response = await client.chat_postMessage(
            channel=channel_id,
            text=f"🎬 <{video_url}|Watch a video to get started>",
            unfurl_links=True,
            unfurl_media=True,
        )
        message_ts = response.get("ts")
        if not message_ts:
            logger.error("No message timestamp in video response")
            return
