"""Thread utility commands for querying SlackThread information."""

import asyncio
import json
import os
import traceback

import click

from csbot.compass_dev.database_config import (
    Environment,
    build_connection_string,
    get_database_password,
)
from csbot.slackbot.config import UnsupportedKekConfig


async def get_storage_for_env(env: Environment):
    """Get storage instance for the given environment.

    This centralizes the logic for going from env -> Storage.

    Args:
        env: Environment (staging or prod)

    Returns:
        SlackbotStorage instance
    """
    from csbot.slackbot.storage.factory import create_storage_from_uri

    # Get database password and build connection string
    db_password = get_database_password(env)
    connection_string = build_connection_string(env, db_password)

    # Create storage in a thread since it's synchronous
    def _create_storage():
        return create_storage_from_uri(connection_string, UnsupportedKekConfig())

    return await asyncio.to_thread(_create_storage)


async def parse_datadog_log(
    log_file_path: str, slack_token: str
) -> tuple[Environment, str, str, str, str]:
    """Parse Datadog log JSON file to extract thread information.

    Args:
        log_file_path: Path to JSON file containing Datadog log
        slack_token: Slack bot token for API access

    Returns:
        Tuple of (env, team_id, channel_id, channel_name, thread_ts)

    Raises:
        ValueError: If required fields are missing or invalid
        FileNotFoundError: If log file doesn't exist
    """
    from pathlib import Path

    log_path = Path(log_file_path)
    if not log_path.exists():
        raise FileNotFoundError(f"Datadog log file not found: {log_file_path}")

    try:
        log_json = log_path.read_text(encoding="utf-8")
        log_data = json.loads(log_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {log_file_path}: {e}")

    # Extract attributes
    content = log_data.get("content", {})
    attributes = content.get("attributes", {})

    # Get environment (from dd.env)
    dd_info = attributes.get("dd", {})
    dd_env = dd_info.get("env")
    if dd_env not in ("staging", "prod"):
        raise ValueError(f"Invalid or missing dd.env: {dd_env}. Must be 'staging' or 'prod'")
    env: Environment = dd_env  # type: ignore

    # Get channel ID
    channel_id = attributes.get("channel")
    if not channel_id:
        raise ValueError("Missing channel in attributes")

    # Get thread_ts
    thread_ts = attributes.get("thread_ts")
    if not thread_ts:
        raise ValueError("Missing thread_ts in attributes")

    # Look up team_id and channel_name from channel_mapping table by channel_id
    # Use the oldest team_id (by created_at) for this channel_id
    db_password = get_database_password(env)
    connection_string = build_connection_string(env, db_password)

    def _query_channel_mapping():
        import psycopg

        conn = psycopg.connect(connection_string)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT team_id, normalized_channel_name
                    FROM channel_mapping
                    WHERE channel_id = %s
                    ORDER BY created_at ASC
                    LIMIT 1
                    """,
                    (channel_id,),
                )
                return cursor.fetchone()
        finally:
            conn.close()

    result = await asyncio.to_thread(_query_channel_mapping)

    if not result:
        raise ValueError(
            f"No channel_mapping found for channel_id={channel_id}. "
            f"The channel may not have been seen by the bot yet."
        )

    team_id, channel_name = result

    # For the bot_id in kv store, we need the governance channel name
    # If the channel doesn't end with 'governance', append it
    if channel_name.endswith("governance"):
        governance_channel_name = channel_name
    else:
        governance_channel_name = f"{channel_name}-governance"

    # Import MessageInfo API
    from csbot.compass_dev.slack_utils import get_message_info

    # Get message info to resolve the actual thread_ts
    # The message_ts from logs might be a reply in a thread, we need the parent thread_ts
    message_info = await get_message_info(channel_id, thread_ts, slack_token)

    # Use the thread_ts from the message (or the message ts itself if it's the parent)
    actual_thread_ts = message_info.thread_ts if message_info.thread_ts else message_info.ts

    return env, team_id, channel_id, governance_channel_name, actual_thread_ts


async def get_thread_events_impl(
    bot_id: str, channel: str, thread_ts: str, env: Environment
) -> None:
    """Get events stored in a SlackThread.

    Args:
        bot_id: Bot ID for the thread
        channel: Slack channel ID
        thread_ts: Thread timestamp
        env: Environment (staging or prod)
    """
    storage = await get_storage_for_env(env)
    instance_storage = storage.for_instance(bot_id)

    # Build the cache key using the same format as SlackThread
    cache_key = f"{channel}:{thread_ts}"
    cache_family = "slack_thread_events"

    # Get the cached events
    cached_events = await instance_storage.get(cache_family, cache_key)

    if not cached_events:
        click.echo("No events found for this thread", err=True)
        return

    # Parse and display the events
    events = json.loads(cached_events)

    click.echo("📝 Thread Events")
    click.echo("=" * 60)
    click.echo(f"Bot ID:        {bot_id}")
    click.echo(f"Channel:       {channel}")
    click.echo(f"Thread TS:     {thread_ts}")
    click.echo(f"Event Count:   {len(events)}")
    click.echo()

    for i, event in enumerate(events, 1):
        click.echo(f"Event {i}:")
        click.echo(f"  Role:        {event.get('role')}")
        content = event.get("content", [])
        if isinstance(content, list):
            click.echo(f"  Content:     {len(content)} block(s)")
            for j, block in enumerate(content, 1):
                block_type = block.get("type") if isinstance(block, dict) else type(block).__name__
                click.echo(f"    Block {j}:  {block_type}")
        else:
            click.echo(f"  Content:     {content}")
        click.echo()

    # Full JSON output
    click.echo("Full JSON:")
    click.echo("-" * 60)
    click.echo(json.dumps(events, indent=2))


async def get_thread_html_impl(bot_id: str, channel: str, thread_ts: str, env: Environment) -> None:
    """Get HTML representation stored in a SlackThread.

    Args:
        bot_id: Bot ID for the thread
        channel: Slack channel ID
        thread_ts: Thread timestamp
        env: Environment (staging or prod)
    """
    storage = await get_storage_for_env(env)
    instance_storage = storage.for_instance(bot_id)

    # Build the cache key using the same format as SlackThread
    cache_key = f"{channel}:{thread_ts}"
    cache_family = "slack_thread_html"

    # Get the cached HTML
    html = await instance_storage.get(cache_family, cache_key)

    if not html:
        click.echo("No HTML found for this thread", err=True)
        return

    click.echo("🌐 Thread HTML")
    click.echo("=" * 60)
    click.echo(f"Bot ID:        {bot_id}")
    click.echo(f"Channel:       {channel}")
    click.echo(f"Thread TS:     {thread_ts}")
    click.echo(f"HTML Length:   {len(html)} characters")
    click.echo()
    click.echo("HTML Content:")
    click.echo("-" * 60)
    click.echo(html)


async def get_thread_lock_status_impl(
    bot_id: str, channel: str, thread_ts: str, env: Environment
) -> None:
    """Get lock status for a SlackThread.

    Args:
        bot_id: Bot ID for the thread
        channel: Slack channel ID
        thread_ts: Thread timestamp
        env: Environment (staging or prod)
    """
    from datetime import datetime, timedelta

    storage = await get_storage_for_env(env)
    instance_storage = storage.for_instance(bot_id)

    # Build the cache key using the same format as SlackThread
    cache_key = f"{channel}:{thread_ts}"
    cache_family = "slack_thread_locked_at"

    # Get the lock timestamp
    locked_at_iso8601 = await instance_storage.get(cache_family, cache_key)

    click.echo("🔒 Thread Lock Status")
    click.echo("=" * 60)
    click.echo(f"Bot ID:        {bot_id}")
    click.echo(f"Channel:       {channel}")
    click.echo(f"Thread TS:     {thread_ts}")
    click.echo()

    if not locked_at_iso8601:
        click.echo("Status:        Not locked")
        return

    locked_at = datetime.fromisoformat(locked_at_iso8601)
    now = datetime.now()
    # Default timeout from SlackThread is 5 minutes
    timeout_seconds = 5 * 60
    expires_at = locked_at + timedelta(seconds=timeout_seconds)
    is_locked = expires_at > now

    click.echo(f"Status:        {'Locked' if is_locked else 'Lock expired'}")
    click.echo(f"Locked At:     {locked_at.isoformat()}")
    click.echo(f"Expires At:    {expires_at.isoformat()}")
    click.echo(f"Now:           {now.isoformat()}")

    if is_locked:
        time_remaining = expires_at - now
        click.echo(f"Time Remaining: {time_remaining.total_seconds():.1f} seconds")


async def list_thread_keys_impl(bot_id: str, env: Environment, limit: int) -> None:
    """List all thread cache keys for a bot instance.

    Args:
        bot_id: Bot ID to list threads for
        env: Environment (staging or prod)
        limit: Maximum number of keys to display
    """
    import psycopg
    from psycopg.rows import dict_row

    # Get database password and build connection string
    db_password = get_database_password(env)
    connection_string = build_connection_string(env, db_password)

    def _query_db():
        conn = psycopg.connect(connection_string)
        try:
            with conn.cursor(row_factory=dict_row) as cursor:
                # Query the kv table for slack_thread_events entries
                cursor.execute(
                    """
                    SELECT family, key, LENGTH(value) as value_length, expires_at_seconds
                    FROM kv
                    WHERE bot_id = %s
                      AND family IN ('slack_thread_events', 'slack_thread_html', 'slack_thread_locked_at')
                    ORDER BY expires_at_seconds DESC NULLS LAST
                    LIMIT %s
                    """,
                    (bot_id, limit),
                )
                return cursor.fetchall()
        finally:
            conn.close()

    rows = await asyncio.to_thread(_query_db)

    if not rows:
        click.echo(f"No thread cache entries found for bot_id: {bot_id}")
        return

    click.echo("🧵 Thread Cache Keys")
    click.echo("=" * 60)
    click.echo(f"Bot ID:        {bot_id}")
    click.echo(f"Total Found:   {len(rows)}")
    click.echo()

    for row in rows:
        from datetime import datetime

        family = row["family"]
        key = row["key"]
        value_length = row["value_length"]
        expires_at_seconds = row["expires_at_seconds"]

        # Convert Unix timestamp to human-readable format
        if expires_at_seconds == -1:
            expires_display = "Never (no expiry)"
        else:
            expires_dt = datetime.fromtimestamp(expires_at_seconds)
            now = datetime.now()
            if expires_dt < now:
                expires_display = f"{expires_dt.isoformat()} (EXPIRED)"
            else:
                time_remaining = expires_dt - now
                expires_display = f"{expires_dt.isoformat()} ({time_remaining.total_seconds() / 3600:.1f} hours remaining)"

        click.echo(f"Family:        {family}")
        click.echo(f"Key:           {key}")
        click.echo(f"Value Length:  {value_length} bytes")
        click.echo(f"Expires At:    {expires_display}")
        click.echo()


@click.group()
def thread():
    """Thread utility commands for querying SlackThread information."""
    pass


@thread.command()
@click.option("--bot-id", help="Bot ID for the thread")
@click.option("--channel", help="Slack channel ID (e.g., C01234567)")
@click.option("--thread-ts", help="Thread timestamp (e.g., 1234567890.123456)")
@click.option(
    "--env",
    type=click.Choice(["staging", "prod"]),
    help="Database environment to connect to",
)
@click.option(
    "--datadog-log",
    type=click.Path(exists=True),
    help="Path to Datadog log JSON file (auto-extracts all other params)",
)
@click.option(
    "--slack-token",
    help="Slack bot token (or set SLACK_BOT_TOKEN env var, required for --datadog-log)",
)
def get_events(
    bot_id: str | None,
    channel: str | None,
    thread_ts: str | None,
    env: Environment | None,
    datadog_log: str | None,
    slack_token: str | None,
) -> None:
    """Get events stored in a SlackThread.

    This command retrieves the agent messages (events) stored in the thread cache.
    Each event contains a role and content blocks representing the conversation history.

    You can either provide all parameters manually OR use --datadog-log to auto-extract them.

    Examples:
        # Manual mode
        compass-dev thread get-events \\
            --bot-id T01234567-my-channel \\
            --channel C01234567 \\
            --thread-ts 1234567890.123456 \\
            --env staging

        # Datadog log mode (auto-extracts everything)
        compass-dev thread get-events --datadog-log /path/to/datadog-log.json
    """
    try:

        async def run():
            nonlocal bot_id, channel, thread_ts, env

            if datadog_log:
                # Get slack token from argument or environment
                token = slack_token or os.environ.get("SLACK_BOT_TOKEN")
                if not token:
                    raise click.UsageError(
                        "Slack bot token required when using --datadog-log. "
                        "Provide via --slack-token or SLACK_BOT_TOKEN env var"
                    )

                # Parse Datadog log to get all parameters
                (
                    parsed_env,
                    team_id,
                    channel_id,
                    channel_name,
                    parsed_thread_ts,
                ) = await parse_datadog_log(datadog_log, token)

                env = parsed_env
                bot_id = f"{team_id}-{channel_name}"
                channel = channel_id
                thread_ts = parsed_thread_ts

                click.echo("📊 Parsed from Datadog Log")
                click.echo("=" * 60)
                click.echo(f"Environment:   {env}")
                click.echo(f"Bot ID:        {bot_id}")
                click.echo(f"Channel:       {channel}")
                click.echo(f"Thread TS:     {thread_ts}")
                click.echo()
            else:
                # Validate required parameters for manual mode
                if not bot_id:
                    raise click.UsageError(
                        "Missing --bot-id. Provide either --bot-id/--channel/--thread-ts or --datadog-log"
                    )
                if not channel:
                    raise click.UsageError(
                        "Missing --channel. Provide either --bot-id/--channel/--thread-ts or --datadog-log"
                    )
                if not thread_ts:
                    raise click.UsageError(
                        "Missing --thread-ts. Provide either --bot-id/--channel/--thread-ts or --datadog-log"
                    )
                if not env:
                    env = "staging"  # Default to staging if not provided

            await get_thread_events_impl(bot_id, channel, thread_ts, env)

        asyncio.run(run())
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"❌ Error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()


@thread.command()
@click.option("--bot-id", help="Bot ID for the thread")
@click.option("--channel", help="Slack channel ID (e.g., C01234567)")
@click.option("--thread-ts", help="Thread timestamp (e.g., 1234567890.123456)")
@click.option(
    "--env",
    type=click.Choice(["staging", "prod"]),
    help="Database environment to connect to",
)
@click.option(
    "--datadog-log",
    type=click.Path(exists=True),
    help="Path to Datadog log JSON file (auto-extracts all other params)",
)
@click.option(
    "--slack-token",
    help="Slack bot token (or set SLACK_BOT_TOKEN env var, required for --datadog-log)",
)
def get_html(
    bot_id: str | None,
    channel: str | None,
    thread_ts: str | None,
    env: Environment | None,
    datadog_log: str | None,
    slack_token: str | None,
) -> None:
    """Get HTML representation stored in a SlackThread.

    This command retrieves the HTML representation of the thread that is used
    for web rendering. The HTML is styled with Tailwind CSS to emulate Slack UI.

    You can either provide all parameters manually OR use --datadog-log to auto-extract them.

    Examples:
        # Manual mode
        compass-dev thread get-html \\
            --bot-id T01234567-my-channel \\
            --channel C01234567 \\
            --thread-ts 1234567890.123456 \\
            --env staging

        # Datadog log mode
        compass-dev thread get-html --datadog-log /path/to/datadog-log.json
    """
    try:

        async def run():
            nonlocal bot_id, channel, thread_ts, env

            if datadog_log:
                # Get slack token from argument or environment
                token = slack_token or os.environ.get("SLACK_BOT_TOKEN")
                if not token:
                    raise click.UsageError(
                        "Slack bot token required when using --datadog-log. "
                        "Provide via --slack-token or SLACK_BOT_TOKEN env var"
                    )

                (
                    parsed_env,
                    team_id,
                    channel_id,
                    channel_name,
                    parsed_thread_ts,
                ) = await parse_datadog_log(datadog_log, token)
                env = parsed_env
                bot_id = f"{team_id}-{channel_name}"
                channel = channel_id
                thread_ts = parsed_thread_ts
            else:
                if not bot_id or not channel or not thread_ts:
                    raise click.UsageError(
                        "Missing required parameters. Provide --bot-id/--channel/--thread-ts or --datadog-log"
                    )
                if not env:
                    env = "staging"

            await get_thread_html_impl(bot_id, channel, thread_ts, env)

        asyncio.run(run())
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"❌ Error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()


@thread.command()
@click.option("--bot-id", help="Bot ID for the thread")
@click.option("--channel", help="Slack channel ID (e.g., C01234567)")
@click.option("--thread-ts", help="Thread timestamp (e.g., 1234567890.123456)")
@click.option(
    "--env",
    type=click.Choice(["staging", "prod"]),
    help="Database environment to connect to",
)
@click.option(
    "--datadog-log",
    type=click.Path(exists=True),
    help="Path to Datadog log JSON file (auto-extracts all other params)",
)
@click.option(
    "--slack-token",
    help="Slack bot token (or set SLACK_BOT_TOKEN env var, required for --datadog-log)",
)
def lock_status(
    bot_id: str | None,
    channel: str | None,
    thread_ts: str | None,
    env: Environment | None,
    datadog_log: str | None,
    slack_token: str | None,
) -> None:
    """Get lock status for a SlackThread.

    This command checks if the thread is currently locked and shows when the lock
    was acquired and when it will expire. Threads are locked to prevent concurrent
    processing of the same thread.

    You can either provide all parameters manually OR use --datadog-log to auto-extract them.

    Examples:
        # Manual mode
        compass-dev thread lock-status \\
            --bot-id T01234567-my-channel \\
            --channel C01234567 \\
            --thread-ts 1234567890.123456 \\
            --env staging

        # Datadog log mode
        compass-dev thread lock-status --datadog-log /path/to/datadog-log.json
    """
    try:

        async def run():
            nonlocal bot_id, channel, thread_ts, env

            if datadog_log:
                # Get slack token from argument or environment
                token = slack_token or os.environ.get("SLACK_BOT_TOKEN")
                if not token:
                    raise click.UsageError(
                        "Slack bot token required when using --datadog-log. "
                        "Provide via --slack-token or SLACK_BOT_TOKEN env var"
                    )

                (
                    parsed_env,
                    team_id,
                    channel_id,
                    channel_name,
                    parsed_thread_ts,
                ) = await parse_datadog_log(datadog_log, token)
                env = parsed_env
                bot_id = f"{team_id}-{channel_name}"
                channel = channel_id
                thread_ts = parsed_thread_ts
            else:
                if not bot_id or not channel or not thread_ts:
                    raise click.UsageError(
                        "Missing required parameters. Provide --bot-id/--channel/--thread-ts or --datadog-log"
                    )
                if not env:
                    env = "staging"

            await get_thread_lock_status_impl(bot_id, channel, thread_ts, env)

        asyncio.run(run())
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"❌ Error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()


@thread.command()
@click.option("--bot-id", help="Bot ID to list threads for")
@click.option(
    "--env",
    type=click.Choice(["staging", "prod"]),
    help="Database environment to connect to",
)
@click.option(
    "--limit",
    default=50,
    help="Maximum number of thread keys to display",
)
@click.option(
    "--datadog-log",
    type=click.Path(exists=True),
    help="Path to Datadog log JSON file (auto-extracts bot-id and env)",
)
@click.option(
    "--slack-token",
    help="Slack bot token (or set SLACK_BOT_TOKEN env var, required for --datadog-log)",
)
def list_keys(
    bot_id: str | None,
    env: Environment | None,
    limit: int,
    datadog_log: str | None,
    slack_token: str | None,
) -> None:
    """List all thread cache keys for a bot instance.

    This command lists all cached thread data (events, HTML, locks) for a specific
    bot instance. Useful for debugging and understanding what threads have cached data.

    You can either provide parameters manually OR use --datadog-log to auto-extract them.

    Examples:
        # Manual mode
        compass-dev thread list-keys \\
            --bot-id T01234567-my-channel \\
            --env staging \\
            --limit 100

        # Datadog log mode (extracts bot-id and env)
        compass-dev thread list-keys --datadog-log /path/to/datadog-log.json --limit 100
    """
    try:

        async def run():
            nonlocal bot_id, env

            if datadog_log:
                # Get slack token from argument or environment
                token = slack_token or os.environ.get("SLACK_BOT_TOKEN")
                if not token:
                    raise click.UsageError(
                        "Slack bot token required when using --datadog-log. "
                        "Provide via --slack-token or SLACK_BOT_TOKEN env var"
                    )

                parsed_env, team_id, _, channel_name, _ = await parse_datadog_log(
                    datadog_log, token
                )
                env = parsed_env
                bot_id = f"{team_id}-{channel_name}"
            else:
                if not bot_id:
                    raise click.UsageError("Missing --bot-id. Provide --bot-id or --datadog-log")
                if not env:
                    env = "staging"

            await list_thread_keys_impl(bot_id, env, limit)

        asyncio.run(run())
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"❌ Error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()
