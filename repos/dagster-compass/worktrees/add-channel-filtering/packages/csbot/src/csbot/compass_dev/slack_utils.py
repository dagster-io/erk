"""Slack utility commands for debugging and inspection."""

import asyncio
import csv
import json
import os
from dataclasses import dataclass

import click
import psycopg
from psycopg.rows import dict_row
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from csbot.slackbot.slack_utils import (
    get_bot_user_id as get_bot_user_id_impl,
)
from csbot.slackbot.slack_utils import (
    invite_bot_to_channel as invite_bot_to_channel_impl,
)
from csbot.utils.misc import normalize_channel_name

from .database_config import (
    Environment,
    build_connection_string,
    get_database_password,
)


@dataclass
class MessageInfo:
    """Information about a Slack message."""

    channel_id: str
    ts: str
    user: str | None
    message_type: str
    subtype: str | None
    thread_ts: str | None
    is_thread_parent: bool
    reply_count: int | None
    text: str
    raw_data: dict


async def get_channel_id_from_name(
    slack_client: AsyncWebClient, channel_name: str, team_id: str
) -> str | None:
    """Get channel ID from channel name using Slack API.

    Args:
        slack_client: Slack client with appropriate token
        channel_name: Name of the channel (without #)
        team_id: Slack team ID

    Returns:
        Channel ID if found, None otherwise
    """
    try:
        cursor = None
        while True:
            response = await slack_client.conversations_list(
                types="public_channel,private_channel", limit=200, cursor=cursor, team_id=team_id
            )

            if not response.get("ok"):
                return None

            channels = response.get("channels", [])
            for channel in channels:
                if channel.get("name") == channel_name:
                    return channel.get("id")

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return None

    except Exception:
        return None


async def get_channel_info_impl(channel_id: str, slack_token: str) -> None:
    """Get information about a Slack channel.

    Args:
        channel_id: The Slack channel ID to inspect
        slack_token: Slack bot token for API access
    """
    client = AsyncWebClient(token=slack_token)

    try:
        # Get channel info
        response = await client.conversations_info(channel=channel_id)

        if not response.get("ok"):
            error = response.get("error", "unknown error")
            click.echo(f"❌ Failed to get channel info: {error}", err=True)
            return

        channel = response.get("channel")
        if not channel:
            click.echo("❌ No channel data in response", err=True)
            return

        # Pretty print the channel information
        click.echo("📺 Channel Information")
        click.echo("=" * 60)
        click.echo(f"ID:                {channel.get('id')}")
        click.echo(f"Name:              {channel.get('name')}")
        click.echo(f"Team ID:           {channel.get('context_team_id', channel.get('team'))}")
        click.echo(f"Created:           {channel.get('created')}")
        click.echo(f"Is Private:        {channel.get('is_private')}")
        click.echo(f"Is Channel:        {channel.get('is_channel')}")
        click.echo(f"Is Group:          {channel.get('is_group')}")
        click.echo(f"Is IM:             {channel.get('is_im')}")
        click.echo(f"Is Archived:       {channel.get('is_archived')}")
        click.echo(f"Is General:        {channel.get('is_general')}")
        click.echo(f"Member Count:      {channel.get('num_members')}")

        topic = channel.get("topic")
        if topic and isinstance(topic, dict):
            click.echo(f"Topic:             {topic.get('value')}")

        purpose = channel.get("purpose")
        if purpose and isinstance(purpose, dict):
            click.echo(f"Purpose:           {purpose.get('value')}")

        # Full JSON output
        click.echo()
        click.echo("Full JSON Response:")
        click.echo("-" * 60)
        click.echo(json.dumps(channel, indent=2))

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise


async def get_message_info(channel_id: str, message_ts: str, slack_token: str) -> MessageInfo:
    """Get information about a Slack message.

    Args:
        channel_id: The Slack channel ID
        message_ts: Message timestamp (can be thread_ts or message within thread)
        slack_token: Slack bot token for API access

    Returns:
        MessageInfo with message details

    Raises:
        ValueError: If message not found or API error
    """
    client = AsyncWebClient(token=slack_token)

    try:
        # Get message info using conversations.history
        response = await client.conversations_history(
            channel=channel_id, latest=message_ts, inclusive=True, limit=1
        )

        if not response.get("ok"):
            error = response.get("error", "unknown error")
            raise ValueError(f"Failed to get message info: {error}")

        messages = response.get("messages", [])
        if not messages:
            raise ValueError("No message found")

        message = messages[0]

        thread_ts = message.get("thread_ts")
        is_thread_parent = thread_ts == message.get("ts") if thread_ts else False

        return MessageInfo(
            channel_id=channel_id,
            ts=message.get("ts", message_ts),
            user=message.get("user"),
            message_type=message.get("type", "unknown"),
            subtype=message.get("subtype"),
            thread_ts=thread_ts,
            is_thread_parent=is_thread_parent,
            reply_count=message.get("reply_count"),
            text=message.get("text", ""),
            raw_data=message,
        )

    except SlackApiError as e:
        raise ValueError(f"Slack API error: {e.response['error']}")


async def get_message_info_impl(channel_id: str, message_ts: str, slack_token: str) -> None:
    """Get and display information about a Slack message.

    Args:
        channel_id: The Slack channel ID
        message_ts: Message timestamp (can be thread_ts or message within thread)
        slack_token: Slack bot token for API access
    """
    try:
        message_info = await get_message_info(channel_id, message_ts, slack_token)

        # Pretty print the message information
        click.echo("💬 Message Information")
        click.echo("=" * 60)
        click.echo(f"Channel:           {message_info.channel_id}")
        click.echo(f"Timestamp:         {message_info.ts}")
        click.echo(f"User:              {message_info.user or 'N/A'}")
        click.echo(f"Type:              {message_info.message_type}")
        click.echo(f"Subtype:           {message_info.subtype or 'N/A'}")

        if message_info.thread_ts:
            click.echo(f"Thread TS:         {message_info.thread_ts}")
            click.echo(f"Is Thread Parent:  {message_info.is_thread_parent}")

        if message_info.reply_count:
            click.echo(f"Reply Count:       {message_info.reply_count}")

        if message_info.text:
            if len(message_info.text) > 500:
                text_preview = message_info.text[:500] + "..."
            else:
                text_preview = message_info.text
            click.echo(f"Text:              {text_preview}")

        # Full JSON output
        click.echo()
        click.echo("Full JSON Response:")
        click.echo("-" * 60)
        click.echo(json.dumps(message_info.raw_data, indent=2))

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise


@click.group()
def slack():
    """Slack utility commands for debugging and inspection."""
    pass


@slack.command()
@click.argument("channel_id")
@click.option(
    "--slack-token",
    help="Slack bot token (or set SLACK_BOT_TOKEN env var)",
)
def channel_info(channel_id: str, slack_token: str | None) -> None:
    """Get information about a Slack channel.

    CHANNEL_ID: The Slack channel ID to inspect (e.g., C01234567)

    Example:
        compass-dev slack channel-info C01234567

        # Or with explicit token
        compass-dev slack channel-info C01234567 --slack-token xoxb-...
    """
    # Get token from argument or environment
    token = slack_token or os.environ.get("SLACK_BOT_TOKEN")

    if not token:
        click.echo(
            "❌ Error: Slack bot token required. Provide via --slack-token or SLACK_BOT_TOKEN env var",
            err=True,
        )
        raise click.Abort()

    try:
        asyncio.run(get_channel_info_impl(channel_id, token))
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@slack.command()
@click.argument("channel_id")
@click.argument("message_ts")
@click.option(
    "--slack-token",
    help="Slack bot token (or set SLACK_BOT_TOKEN env var)",
)
def message_info(channel_id: str, message_ts: str, slack_token: str | None) -> None:
    """Get information about a Slack message.

    CHANNEL_ID: The Slack channel ID (e.g., C01234567)
    MESSAGE_TS: Message timestamp / thread_ts (e.g., 1234567890.123456)

    Example:
        compass-dev slack message-info C01234567 1234567890.123456

        # Or with explicit token
        compass-dev slack message-info C01234567 1234567890.123456 --slack-token xoxb-...
    """
    # Get token from argument or environment
    token = slack_token or os.environ.get("SLACK_BOT_TOKEN")

    if not token:
        click.echo(
            "❌ Error: Slack bot token required. Provide via --slack-token or SLACK_BOT_TOKEN env var",
            err=True,
        )
        raise click.Abort()

    try:
        asyncio.run(get_message_info_impl(channel_id, message_ts, token))
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@slack.command()
@click.option(
    "--slack-token",
    help="Slack bot token (or set SLACK_BOT_TOKEN env var)",
)
def bot_user_id(slack_token: str | None) -> None:
    """Get the bot's user ID from a Slack bot token.

    Example:
        compass-dev slack bot-user-id

        # Or with explicit token
        compass-dev slack bot-user-id --slack-token xoxb-...
    """
    # Get token from argument or environment
    token = slack_token or os.environ.get("SLACK_BOT_TOKEN")

    if not token:
        click.echo(
            "❌ Error: Slack bot token required. Provide via --slack-token or SLACK_BOT_TOKEN env var",
            err=True,
        )
        raise click.Abort()

    try:
        result = asyncio.run(get_bot_user_id_impl(token))

        if result.get("success"):
            click.echo("✅ Bot User Information")
            click.echo("=" * 60)
            click.echo(f"User ID:           {result.get('user_id')}")
            click.echo(f"Bot ID:            {result.get('bot_id')}")
            click.echo()
            click.echo("Full Response:")
            click.echo("-" * 60)
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"❌ Failed to get bot user ID: {result.get('error')}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@slack.command()
@click.argument("channel_id")
@click.option(
    "--bot-token",
    help="Slack bot token (or set SLACK_BOT_TOKEN env var)",
)
@click.option(
    "--admin-token",
    required=True,
    help="Slack admin token with admin.conversations:write scope",
)
def invite_bot(channel_id: str, bot_token: str | None, admin_token: str) -> None:
    """Invite a bot to a Slack channel.

    CHANNEL_ID: The Slack channel ID to invite the bot to (e.g., C01234567)

    This command:
    1. Uses the bot token to get the bot's user ID
    2. Uses the admin token to invite the bot to the channel

    Example:
        compass-dev slack invite-bot C01234567 --admin-token xoxp-...

        # Or with explicit bot token
        compass-dev slack invite-bot C01234567 \\
            --bot-token xoxb-... \\
            --admin-token xoxp-...
    """
    # Get bot token from argument or environment
    token = bot_token or os.environ.get("SLACK_BOT_TOKEN")

    if not token:
        click.echo(
            "❌ Error: Slack bot token required. Provide via --bot-token or SLACK_BOT_TOKEN env var",
            err=True,
        )
        raise click.Abort()

    try:
        # Get bot user ID
        click.echo("Getting bot user ID...")
        bot_info = asyncio.run(get_bot_user_id_impl(token))

        if not bot_info.get("success"):
            click.echo(f"❌ Failed to get bot user ID: {bot_info.get('error')}", err=True)
            raise click.Abort()

        bot_user_id = bot_info.get("user_id")
        if not bot_user_id:
            click.echo("❌ No user_id in bot info response", err=True)
            raise click.Abort()

        click.echo(f"Bot User ID: {bot_user_id}")
        click.echo()

        # Invite bot to channel
        click.echo(f"Inviting bot to channel {channel_id}...")
        result = asyncio.run(invite_bot_to_channel_impl(admin_token, channel_id, bot_user_id))

        if result.get("success"):
            click.echo(f"✅ Successfully invited bot to channel {channel_id}")
            click.echo()
            click.echo("Response:")
            click.echo("-" * 60)
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"❌ Failed to invite bot: {result.get('error')}", err=True)
            raise click.Abort()

    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@slack.command()
@click.option("--channel-id", required=True, help="Channel ID to remove bot from")
@click.option("--bot-token", help="Slack bot token (or set SLACK_BOT_TOKEN env var)")
@click.option("--admin-token", required=True, help="Slack admin token for conversations.kick")
def remove_bot(channel_id: str, bot_token: str | None, admin_token: str) -> None:
    """Remove a bot from a Slack channel (auto-detects bot user ID from bot token)."""
    token = bot_token or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        click.echo("❌ Error: Bot token required", err=True)
        raise click.Abort()

    async def run():
        # Get bot user ID from bot token
        click.echo("Getting bot user ID from token...")
        bot_info = await get_bot_user_id_impl(token)

        if not bot_info.get("success"):
            click.echo(f"❌ Failed to get bot user ID: {bot_info.get('error')}", err=True)
            raise click.Abort()

        bot_user_id = bot_info.get("user_id")
        if not bot_user_id:
            click.echo("❌ No user_id in response", err=True)
            raise click.Abort()

        click.echo(f"Bot User ID: {bot_user_id}")

        # Remove bot from channel using admin token
        admin_client = AsyncWebClient(token=admin_token)
        try:
            click.echo(f"Removing bot from channel {channel_id}...")
            response = await admin_client.conversations_kick(channel=channel_id, user=bot_user_id)
            if response.get("ok"):
                click.echo("✅ Successfully removed bot from channel")
            else:
                click.echo(f"❌ Failed: {response.get('error')}", err=True)
                raise click.Abort()
        except SlackApiError as e:
            click.echo(f"❌ Slack API error: {e.response['error']}", err=True)
            raise click.Abort()

    try:
        asyncio.run(run())
    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@slack.command()
@click.argument("slack_team_id")
@click.option("--bot-token", help="Slack bot token (or set SLACK_BOT_TOKEN env var)")
@click.option("--admin-token", required=True, help="Slack admin token for conversations.kick")
@click.option(
    "--env",
    type=click.Choice(["staging", "prod"]),
    default="staging",
    help="Database environment to connect to",
)
def remove_bots(
    slack_team_id: str, bot_token: str | None, admin_token: str, env: Environment
) -> None:
    """Remove bot from all channels for a Slack team and export bot instances to CSV.

    SLACK_TEAM_ID: The Slack team ID to remove bots from

    This command:
    1. Queries bot_instances table for the given Slack team
    2. Resolves channel IDs from channel names
    3. Removes the bot from each channel
    4. Exports bot_instances rows to /tmp/removed-{slack_team_id}.csv
    5. Deletes the bot_instances rows from the database

    Example:
        compass-dev slack remove-bots T01234567 \\
            --admin-token xoxp-... \\
            --env prod
    """
    token = bot_token or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        click.echo("❌ Error: Bot token required", err=True)
        raise click.Abort()

    environment = env

    async def run():
        # Get bot user ID from bot token
        click.echo("Getting bot user ID from token...")
        bot_info = await get_bot_user_id_impl(token)

        if not bot_info.get("success"):
            click.echo(f"❌ Failed to get bot user ID: {bot_info.get('error')}", err=True)
            raise click.Abort()

        bot_user_id = bot_info.get("user_id")
        if not bot_user_id:
            click.echo("❌ No user_id in response", err=True)
            raise click.Abort()

        click.echo(f"Bot User ID: {bot_user_id}")
        click.echo()

        # Connect to database
        db_password = get_database_password(environment)
        connection_string = build_connection_string(environment, db_password)

        click.echo(f"Connecting to {environment} database...")
        conn = psycopg.connect(connection_string)

        try:
            # Query bot_instances for this Slack team
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM bot_instances
                    WHERE slack_team_id = %s
                    ORDER BY channel_name
                    """,
                    (slack_team_id,),
                )
                bot_instances = cursor.fetchall()

            if not bot_instances:
                click.echo(f"No bot instances found for Slack team {slack_team_id}")
                return

            click.echo(f"Found {len(bot_instances)} bot instance(s)")
            click.echo()

            # Create Slack clients
            slack_client = AsyncWebClient(token=token)
            admin_client = AsyncWebClient(token=admin_token)

            # Process each bot instance
            removal_results = []
            governance_channels_processed = set()

            for instance in bot_instances:
                channel_name = instance["channel_name"]
                governance_alerts_channel = instance.get("governance_alerts_channel")

                click.echo(f"Processing channel: {channel_name}")

                # Get channel ID from name
                channel_id = await get_channel_id_from_name(
                    slack_client, normalize_channel_name(channel_name), slack_team_id
                )

                if not channel_id:
                    raise RuntimeError(f"Could not find channel ID for {channel_name}")

                click.echo(f"  Channel ID: {channel_id}")

                # Remove bot from channel
                response = await admin_client.conversations_kick(
                    channel=channel_id, user=bot_user_id
                )
                if not response.get("ok"):
                    error = response.get("error", "unknown")
                    raise RuntimeError(f"Failed to remove bot from {channel_name}: {error}")

                click.echo(f"  ✅ Removed bot from {channel_name}")

                # Remove bot from governance alerts channel if present and not already processed
                governance_channel_id = None
                if (
                    governance_alerts_channel
                    and governance_alerts_channel not in governance_channels_processed
                ):
                    click.echo(
                        f"  Processing governance alerts channel: {governance_alerts_channel}"
                    )

                    governance_channel_id = await get_channel_id_from_name(
                        slack_client,
                        normalize_channel_name(governance_alerts_channel),
                        slack_team_id,
                    )

                    if not governance_channel_id:
                        raise RuntimeError(
                            f"Could not find channel ID for governance alerts channel {governance_alerts_channel}"
                        )

                    click.echo(f"    Governance channel ID: {governance_channel_id}")

                    response = await admin_client.conversations_kick(
                        channel=governance_channel_id, user=bot_user_id
                    )
                    if not response.get("ok"):
                        error = response.get("error", "unknown")
                        raise RuntimeError(
                            f"Failed to remove bot from governance alerts channel {governance_alerts_channel}: {error}"
                        )

                    click.echo(
                        f"    ✅ Removed bot from governance alerts channel {governance_alerts_channel}"
                    )
                    governance_channels_processed.add(governance_alerts_channel)

                removal_results.append((instance, channel_id, governance_channel_id, "success"))
                click.echo()

            # Export to CSV
            csv_path = f"/tmp/removed-{slack_team_id}.csv"
            click.echo(f"Exporting bot instances to {csv_path}...")

            with open(csv_path, "w", newline="") as csvfile:
                if bot_instances:
                    fieldnames = list(bot_instances[0].keys()) + [
                        "channel_id",
                        "governance_channel_id",
                        "removal_status",
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for instance, channel_id, governance_channel_id, status in removal_results:
                        row = dict(instance)
                        row["channel_id"] = channel_id
                        row["governance_channel_id"] = governance_channel_id
                        row["removal_status"] = status
                        writer.writerow(row)

            click.echo(f"✅ Exported {len(bot_instances)} row(s) to {csv_path}")
            click.echo()

            # Delete from database
            click.echo("Deleting bot instances from database...")
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM bot_instances
                    WHERE slack_team_id = %s
                    """,
                    (slack_team_id,),
                )
                deleted_count = cursor.rowcount
                conn.commit()

            click.echo(f"✅ Deleted {deleted_count} bot instance(s) from database")

        finally:
            conn.close()

    try:
        asyncio.run(run())
    except click.Abort:
        raise
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
