import asyncio
import logging
import os
import signal
import traceback
from pathlib import Path

import click
import structlog
from datadog.dogstatsd.base import statsd

from csbot.slackbot.bot_server.bot_server import create_secret_store
from csbot.slackbot.initialize import (
    initialize_dynamic_compass_bot_server,
)
from csbot.slackbot.slackbot_core import (
    BotGitHubConfig,
    load_bot_server_config_from_path,
    load_db_config_from_path,
)
from csbot.slackbot.slackbot_slackstream import throttler
from csbot.slackbot.storage.factory import create_connection_factory
from csbot.slackbot.storage.postgresql import maybe_setup_rds_connection_pooling
from csbot.utils.cli_utils import cli_context

from .backfill_channel_members import backfill_channel_members_command
from .data_migrations import execute_data_migration

logger = structlog.get_logger(__name__)

IS_PRIMARY_DEPLOYMENT = os.getenv("IS_PRIMARY_DEPLOYMENT")


def sigterm_handler(signum, frame):
    """Handle SIGTERM by ignoring it."""
    logger.info(
        "Received SIGTERM signal, ignoring to ensure graceful shutdown. Send SIGKILL to force shutdown."
    )


async def monitor_loop(threshold: float = 0.1, interval: float = 0.05):
    """
    Monitor the asyncio event loop for blocking.

    Args:
        threshold: Seconds of delay considered a "block".
        interval: How often to check (seconds).
    """
    import time

    last = time.perf_counter()
    while True:
        await asyncio.sleep(interval)
        now = time.perf_counter()
        delay = now - last - interval
        if delay > threshold:
            logging.warning(f"Event loop blocked for {delay:.3f} seconds")
        last = now


async def monitor_github_rate_limits(github_config: BotGitHubConfig):
    auth_source = github_config.get_auth_source()
    github_client = auth_source.get_github_client()
    try:
        while True:
            rate_limit = await asyncio.to_thread(github_client.get_rate_limit)
            remaining = rate_limit.rate.remaining
            limit = rate_limit.rate.limit
            statsd.gauge("compass.github.rate_limits.remaining", remaining)
            statsd.gauge("compass.github.rate_limits.limit", limit)
            await asyncio.sleep(30)
    except Exception:
        logger.exception("Github rate limit loop failed")
    finally:
        logger.warning("Github rate limit loop terminating")


def bot_main(config_path: str, no_reset_db: bool = False) -> None:
    if os.getenv("RENDER"):
        # Set up SIGTERM handler to ignore the signal, locally allow the
        # signal to propagate
        signal.signal(signal.SIGTERM, sigterm_handler)

    server_config = load_bot_server_config_from_path(config_path)
    if server_config.canary_enabled and not IS_PRIMARY_DEPLOYMENT:
        from csbot.canary.server import start

        asyncio.run(start(server_config))
        return

    # Override seed_database_from if --no-reset-db is specified
    if no_reset_db:
        server_config.db_config.seed_database_from = None

    secret_store = create_secret_store(server_config)

    # Use dynamic bot server for automatic bot discovery
    async def run_bot():
        asyncio.create_task(monitor_loop())
        if server_config.github.rate_limiting_monitor_enabled:
            asyncio.create_task(monitor_github_rate_limits(server_config.github))
        asyncio.create_task(throttler.run())
        with maybe_setup_rds_connection_pooling(server_config.db_config):
            async with initialize_dynamic_compass_bot_server(
                server_config, secret_store, Path(config_path).parent.absolute()
            ):
                # Context manager handles everything including main loop and dynamic discovery
                pass

    asyncio.run(run_bot())


@click.group()
def cli():
    """Slack AI Bot CLI - A bot that uses Claude AI with streaming responses that update a
    single message."""
    pass


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Path to the compassbot.config.yaml file",
)
@click.option(
    "--no-reset-db",
    is_flag=True,
    default=False,
    help="Skip resetting/re-seeding the SQLite database when running locally",
)
def start(
    config: str,
    no_reset_db: bool,
):
    """Start the AI Bot with streaming responses."""

    try:
        with cli_context():
            bot_main(config, no_reset_db)
    except Exception as e:
        traceback.print_exc()
        click.echo(click.style(f"Error starting bot: {e}", fg="red"))


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Path to the .yaml file with a DatabaseConfig",
)
def migrate_schema(
    config: str,
):
    try:
        with cli_context():
            db_config = load_db_config_from_path(config)

            assert db_config.initialize_db

            # this also implicitly creates the db :/
            create_connection_factory(db_config)

    except Exception as e:
        traceback.print_exc()
        click.echo(click.style(f"Error running db schema migration: {e}", fg="red"))
        raise


cli.add_command(execute_data_migration)
cli.add_command(backfill_channel_members_command)

if __name__ == "__main__":
    cli()
