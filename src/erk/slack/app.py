"""Entry point for the Slack bot."""

import os
from pathlib import Path

import click
from erk_shared.integrations.time.real import RealTime

from erk.slack.agent.real import RealAgentSpawner
from erk.slack.listener.real import RealSlackListener
from erk.slack.service import SlackBotService
from erk.slack.thread_store.sqlite import SQLiteThreadStore


def run_bot(repo_path: Path) -> None:
    """Run the Slack bot.

    Initializes all components and starts the main event loop.

    Args:
        repo_path: Path to repository for agent context

    Environment variables:
        SLACK_BOT_TOKEN: Bot User OAuth Token (xoxb-...)
        SLACK_APP_TOKEN: App-Level Token for Socket Mode (xapp-...)
        SLACK_TEAM_ID: Workspace ID for MCP server
    """
    # Validate required environment variables
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    team_id = os.environ.get("SLACK_TEAM_ID")

    if bot_token is None:
        click.echo("Error: SLACK_BOT_TOKEN environment variable required", err=True)
        raise SystemExit(1)

    if app_token is None:
        click.echo("Error: SLACK_APP_TOKEN environment variable required", err=True)
        raise SystemExit(1)

    if team_id is None:
        click.echo("Error: SLACK_TEAM_ID environment variable required", err=True)
        raise SystemExit(1)

    # Initialize components
    listener = RealSlackListener(
        bot_token=bot_token,
        app_token=app_token,
    )

    thread_store = SQLiteThreadStore(db_path=Path.home() / ".erk" / "slack_threads.db")

    agent_spawner = RealAgentSpawner(
        bot_token=bot_token,
        team_id=team_id,
    )

    service = SlackBotService(
        listener=listener,
        thread_store=thread_store,
        agent_spawner=agent_spawner,
        time=RealTime(),
        repo_path=repo_path,
    )

    click.echo(f"Starting Slack bot for repository: {repo_path}")
    click.echo("Listening for events... (Ctrl+C to stop)")

    # Run the service
    service.run()
