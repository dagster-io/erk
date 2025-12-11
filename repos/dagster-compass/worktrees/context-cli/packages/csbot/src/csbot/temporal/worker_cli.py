"""Temporal worker CLI entry point.

Provides a minimal worker that connects to Temporal and can execute workflows.
Developers register their own workflows and activities.

Usage:
    compass-temporal-worker start --config local.csbot.config.yaml
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import click
from temporalio.client import Client as TemporalClient
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from csbot.agents.factory import create_agent_from_config
from csbot.agents.protocol import AsyncAgent
from csbot.slackbot import slackbot_slackstream
from csbot.slackbot.bot_server.bot_server import (
    create_bot_reconciler,
    create_secret_store,
    create_storage,
    create_temporal_client,
)
from csbot.slackbot.slackbot_core import (
    CompassBotServerConfig,
    load_bot_server_config_from_path,
)
from csbot.slackbot.slackbot_slackstream import throttler
from csbot.slackbot.storage.interface import SlackbotStorage
from csbot.temporal.daily_exploration.activity import DailyExplorationActivity
from csbot.temporal.daily_exploration.workflow import DailyExplorationWorkflow
from csbot.temporal.dataset_monitor.activity import DatasetMonitoringActivity
from csbot.temporal.dataset_monitor.workflow import DatasetMonitoringWorkflow
from csbot.temporal.dataset_sync.activity import DatasetSyncActivities
from csbot.temporal.dataset_sync.workflow import DatasetSyncWorkflow
from csbot.temporal.interceptor import WorkerInterceptor
from csbot.temporal.org_onboarding_check.activity import OrgOnboardingCheckActivity
from csbot.temporal.org_onboarding_check.workflow import OrgOnboardingCheckWorkflow
from csbot.temporal.shared_activities.context_store_loader import ContextStoreLoaderActivity
from csbot.temporal.thread_health_inspector.activity import ThreadHealthInspectorActivity
from csbot.temporal.thread_health_inspector.workflow import ThreadHealthInspectorWorkflow
from csbot.temporal.utils import BotProvider, BotReconcilerBotProvider
from csbot.utils.cli_utils import cli_context

logger = logging.getLogger(__name__)


def get_task_queue_from_env() -> str:
    """Get the task queue name from environment or use default."""
    return os.environ.get("TEMPORAL_TASK_QUEUE", "compass-queue")


def _setup_daily_exploration(bot_provider: BotProvider):
    daily_exploration_activity = DailyExplorationActivity(bot_provider)
    workflows = [
        DailyExplorationWorkflow,
    ]
    activities = [daily_exploration_activity.send_daily_exploration_activity]
    return workflows, activities


def _setup_thread_health(
    storage: SlackbotStorage, agent: AsyncAgent, server_config: CompassBotServerConfig
):
    # arguably we shouldn't even have the activity/workflow if the config is None, but we do
    # because we might enable it and then disable it and there are still workflows pending so those
    # will still be processed. I think thats better than dropping them after they've been submitted
    thread_inspector_activity = ThreadHealthInspectorActivity(
        storage,
        agent,
        server_config.thread_health_inspector_config.honeycomb
        if server_config.thread_health_inspector_config
        else None,
    )
    workflows = [ThreadHealthInspectorWorkflow]
    activities = [thread_inspector_activity.inspect_thread_health]
    return workflows, activities


def _setup_dataset_monitoring(bot_provider: BotProvider):
    activity = DatasetMonitoringActivity(bot_provider)
    return [DatasetMonitoringWorkflow], [activity.dataset_monitor_activity]


def _setup_shared_activities(bot_provider: BotProvider):
    context_store_load = ContextStoreLoaderActivity(bot_provider)
    return [context_store_load.load_context_store]


def _setup_dataset_sync(bot_provider: BotProvider, temporal_client: TemporalClient):
    dataset_sync_activities = DatasetSyncActivities(bot_provider, temporal_client)
    activities = [
        dataset_sync_activities.create_branch,
        dataset_sync_activities.send_notification_started,
        dataset_sync_activities.process_dataset,
        dataset_sync_activities.finalize_pull_request,
        dataset_sync_activities.send_notification_completed,
        dataset_sync_activities.send_slack_connect_invite,
        dataset_sync_activities.log_analytics,
        dataset_sync_activities.update_progress,
    ]

    return [DatasetSyncWorkflow], activities


def _setup_org_onboarding_check():
    org_onboarding_check_activity = OrgOnboardingCheckActivity()
    workflows = [OrgOnboardingCheckWorkflow]
    activities = [org_onboarding_check_activity.validate_org_onboarding]
    return workflows, activities


async def start_temporal_worker(
    server_config: CompassBotServerConfig,
    config_root: Path,
    max_concurrent_activities: int,
) -> None:
    """Start the Temporal worker.

    Args:
        temporal_config: Temporal configuration
        task_queue: Task queue name to poll (overrides config if provided)
        max_concurrent_activities: Maximum concurrent activities
    """
    temporal_client = await create_temporal_client(server_config)
    secret_store = create_secret_store(server_config)
    storage = await create_storage(server_config)
    agent = create_agent_from_config(server_config.ai_config)
    bot_reconciler = await create_bot_reconciler(
        server_config,
        secret_store,
        config_root,
        storage,
        temporal_client,
        skip_background_tasks=True,
    )

    _throttler_task = asyncio.create_task(slackbot_slackstream.throttler.run())

    # Start the global Slack call throttler
    _throttler_task = asyncio.create_task(throttler.run())
    logger.info("Started Slack call throttler")

    # Initial bot discovery - load bot instances from storage
    logger.info("Loading bot instances...")
    await bot_reconciler.discover_and_update_bots()
    logger.info(f"Loaded {len(bot_reconciler.get_active_bots())} bot instance(s)")

    bot_provider = BotReconcilerBotProvider(bot_reconciler)

    daily_exploration_workflows, daily_exploration_activities = _setup_daily_exploration(
        bot_provider
    )
    thread_health_workflows, thread_health_activities = _setup_thread_health(
        storage, agent, server_config
    )
    dataset_sync_workflows, dataset_sync_activities = _setup_dataset_sync(
        bot_provider, temporal_client
    )
    dataset_monitoring_workflows, dataset_monitoring_activities = _setup_dataset_monitoring(
        bot_provider
    )
    org_onboarding_check_workflows, org_onboarding_check_activities = _setup_org_onboarding_check()
    shared_activities = _setup_shared_activities(bot_provider)

    workflows = [
        *daily_exploration_workflows,
        *thread_health_workflows,
        *dataset_monitoring_workflows,
        *dataset_sync_workflows,
        *org_onboarding_check_workflows,
    ]
    logger.info(f"Worker initialized with workflows: {', '.join(x.__name__ for x in workflows)}. ")

    # Create and start worker
    task_queue = get_task_queue_from_env()
    logger.info(f"Starting worker on task queue: {task_queue}")
    worker = Worker(
        temporal_client,
        task_queue=task_queue,
        workflows=workflows,
        activities=[
            *daily_exploration_activities,
            *thread_health_activities,
            *dataset_monitoring_activities,
            *shared_activities,
            *dataset_sync_activities,
            *org_onboarding_check_activities,
        ],
        interceptors=[WorkerInterceptor()],
        max_concurrent_activities=max_concurrent_activities,
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules("ddtrace", "csbot")
        ),
    )

    logger.info(
        f"Worker started. Polling task queue '{task_queue}' with max {max_concurrent_activities} concurrent activities."
    )
    logger.info("Press Ctrl+C to stop the worker.")

    # Run worker (blocks until shutdown)

    try:
        await worker.run()
    finally:
        logger.info("Shutting down worker...")
        _throttler_task.cancel()
        await asyncio.gather(_throttler_task)


@click.group()
def cli():
    """Temporal worker for Compass bot.

    Connects to Temporal server and executes workflows/activities.
    """
    pass


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to csbot.yaml configuration file",
)
@click.option(
    "--max-concurrent-activities",
    default=4,
    type=int,
    help="Maximum concurrent activities (default: 4)",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Logging level (default: INFO)",
)
def start(
    config: Path,
    max_concurrent_activities: int,
    log_level: str,
):
    """Start the Temporal worker.

    The worker connects to Temporal and polls for workflow tasks.
    Temporal connection settings are read from the csbot.yaml config file.

    Example:
        compass-temporal-worker start --config local.csbot.config.yaml
    """
    with cli_context():
        # Load config from YAML
        logger.info(f"Loading configuration from: {config}")
        server_config = load_bot_server_config_from_path(config)

        try:
            asyncio.run(
                start_temporal_worker(
                    server_config,
                    Path(config).parent.absolute(),
                    max_concurrent_activities=max_concurrent_activities,
                )
            )
        except KeyboardInterrupt:
            logger.info("Worker shutdown requested")
        except Exception as e:
            logger.error(f"Worker failed: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    cli()
