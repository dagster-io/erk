"""Thread health inspection CLI commands."""

import asyncio

import click

from csbot.slackbot.bot_server.bot_server import create_temporal_client
from csbot.slackbot.slackbot_core import load_bot_server_config_from_path
from csbot.temporal.thread_health_inspector import ThreadHealthInspectorWorkflowInput
from csbot.temporal.thread_health_inspector.activity import (
    ThreadHealthEmptyThread,
    ThreadHealthInspectorResult,
    ThreadHealthInspectorSuccess,
)


@click.group()
def thread_health():
    """Thread health inspection commands."""
    pass


@thread_health.command()
@click.option(
    "--config-file",
    required=True,
    help="Path to bot configuration YAML file",
)
@click.option(
    "--governance-bot-id",
    required=True,
    help="Governance bot ID (format: team_id-channel_name-governance)",
)
@click.option(
    "--channel-id",
    required=True,
    help="Slack channel ID (e.g., C01234567)",
)
@click.option(
    "--thread-ts",
    required=True,
    help="Thread timestamp (e.g., 1234567890.123456)",
)
def inspect(
    config_file: str,
    governance_bot_id: str,
    channel_id: str,
    thread_ts: str,
):
    """Trigger thread health inspection workflow.

    This command starts a Temporal workflow to inspect a thread's conversation
    quality and rate the bot's performance.

    Example:
        compass-dev thread-health inspect \\
            --config-file local.csbot.config.yaml \\
            --governance-bot-id TCC8P0589-my-channel-governance \\
            --channel-id C09FXFPTAP6 \\
            --thread-ts 1760419180.152800
    """

    async def run():
        # Load bot config
        click.echo("Loading bot configuration...")
        bot_config = load_bot_server_config_from_path(config_file)

        # Create Temporal client
        click.echo("Connecting to Temporal...")
        temporal_client = await create_temporal_client(bot_config)

        # Create workflow input
        workflow_input = ThreadHealthInspectorWorkflowInput(
            governance_bot_id=governance_bot_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
        )

        # Start workflow
        from csbot.temporal import constants

        workflow_id = f"thread-health-{governance_bot_id}-{channel_id}-{thread_ts}"
        click.echo(f"Starting workflow: {workflow_id}")

        handle = await temporal_client.start_workflow(
            constants.Workflow.THREAD_HEALTH_INSPECTOR_WORKFLOW_NAME.value,
            workflow_input,
            id=workflow_id,
            task_queue=constants.DEFAULT_TASK_QUEUE,
            result_type=ThreadHealthInspectorResult,  # pyright: ignore
        )

        click.echo("✅ Workflow started successfully")
        click.echo(f"Workflow ID: {handle.id}")
        click.echo(f"Run ID: {handle.result_run_id}")
        click.echo()
        click.echo("Waiting for result...")

        # Wait for result
        result = await handle.result()

        if isinstance(result, ThreadHealthInspectorSuccess):
            click.echo()
            click.echo("🎯 Thread Health Inspection Results")
            click.echo("=" * 60)
            click.echo(f"Event Count:       {result.event_count}")
            click.echo(f"Tokens Consumed:   {result.tokens_consumed}")
            click.echo(f"Accuracy:          {result.score.accuracy}/10")
            click.echo(f"Responsiveness:    {result.score.responsiveness}/10")
            click.echo(f"Helpfulness:       {result.score.helpfulness}/10")
            click.echo()
            click.echo("Reasoning:")
            click.echo("-" * 60)
            click.echo(result.score.reasoning)
        elif isinstance(result, ThreadHealthEmptyThread):
            click.echo()
            click.echo("Empty thread")
        else:
            raise Exception(f"Unknown result type: {result}")

    try:
        asyncio.run(run())
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()
