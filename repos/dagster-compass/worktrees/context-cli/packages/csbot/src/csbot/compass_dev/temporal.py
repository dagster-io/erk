"""Temporal workflow execution CLI commands."""

import asyncio
import json

import click

from csbot.slackbot.bot_server.bot_server import create_temporal_client
from csbot.slackbot.slackbot_core import load_bot_server_config_from_path
from csbot.temporal import constants


@click.group()
def temporal():
    """Temporal workflow execution commands."""
    pass


@temporal.command()
@click.option(
    "--config-file",
    required=True,
    help="Path to bot configuration YAML file",
)
@click.option(
    "--workflow-type",
    required=True,
    type=click.Choice([w.value for w in constants.Workflow]),
    help="Type of workflow to execute",
)
@click.option(
    "--input",
    "input_json",
    required=True,
    help="Workflow input as JSON string",
)
def execute(
    config_file: str,
    workflow_type: str,
    input_json: str,
):
    """Execute a Temporal workflow.

    This command executes a Temporal workflow with the provided input.

    Example:
        compass-dev temporal execute \\
            --config-file local.csbot.config.yaml \\
            --workflow-type daily_exploration \\
            --input '{"bot_id": "TCC8P0589-my-channel", "channel_name": "my-channel"}'
    """

    async def run():
        # Load bot config
        click.echo("Loading bot configuration...")
        bot_config = load_bot_server_config_from_path(config_file)

        # Create Temporal client
        click.echo("Connecting to Temporal...")
        temporal_client = await create_temporal_client(bot_config)

        # Parse input JSON
        click.echo("Parsing workflow input...")
        workflow_input = json.loads(input_json)

        # Generate workflow ID
        import time

        workflow_id = f"{workflow_type}-{int(time.time())}"
        click.echo(f"Starting workflow: {workflow_id}")

        # Execute workflow
        result = await temporal_client.execute_workflow(
            workflow_type,
            workflow_input,
            id=workflow_id,
            task_queue=constants.DEFAULT_TASK_QUEUE,
        )

        click.echo("✅ Workflow completed successfully")
        click.echo(f"Workflow ID: {workflow_id}")
        click.echo()
        click.echo("Result:")
        click.echo(json.dumps(result, indent=2))

    try:
        asyncio.run(run())
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback

        traceback.print_exc()
        raise click.Abort()
