"""Dataset monitoring background task for CompassChannelBotInstance."""

import logging
import os
from datetime import timedelta
from typing import TYPE_CHECKING

from temporalio.client import ScheduleIntervalSpec, ScheduleSpec

from csbot.slackbot.channel_bot.tasks.bot_instance_temporal_task import (
    BotInstanceTemporalBackgroundTask,
)
from csbot.temporal.constants import Workflow

if TYPE_CHECKING:
    from csbot.slackbot.slackbot_core import CompassBotServerConfig
from csbot.temporal.constants import (
    DATASET_MONITORING_TASK_QUEUE,
    DEFAULT_TASK_QUEUE,
)

logger = logging.getLogger(__name__)


def _get_dataset_monitoring_minutes() -> float:
    """Get dataset monitoring interval in minutes from env var."""
    env_value = os.getenv("DATASET_MONITORING_MINUTES", "15")
    try:
        minutes = float(env_value)
        if minutes <= 0:
            logger.warning(
                f"Invalid DATASET_MONITORING_MINUTES value '{env_value}' (must be > 0), using default 15"
            )
            return 15.0
        return minutes
    except ValueError:
        logger.warning(
            f"Invalid DATASET_MONITORING_MINUTES value '{env_value}' (not a number), using default 15"
        )
        return 15.0


DATASET_MONITORING_MINUTES = _get_dataset_monitoring_minutes()


class DatasetMonitoringTask(BotInstanceTemporalBackgroundTask):
    def get_schedule_id(self) -> str:
        """Return the unique schedule ID for this workflow."""
        return f"dataset-monitoring-{self.bot.key.to_bot_id()}"

    def get_workflow_id_prefix(self) -> str:
        """Return the workflow ID prefix for workflow executions."""
        return f"dataset-monitoring-{self.bot.key.to_bot_id()}"

    def get_workflow_type(self) -> Workflow:
        return Workflow.DATASET_MONITORING_WORKFLOW_NAME

    def get_schedule_spec(self) -> ScheduleSpec:
        return ScheduleSpec(
            intervals=[
                ScheduleIntervalSpec(
                    every=timedelta(minutes=DATASET_MONITORING_MINUTES),
                )
            ],
            jitter=timedelta(hours=1),
        )

    def get_workflow_args(self) -> list:
        """Return the arguments to pass to the workflow."""
        from csbot.temporal.dataset_monitor.workflow import DatasetMonitoringWorkflowInput

        return [
            DatasetMonitoringWorkflowInput(
                bot_id=self.bot.key.to_bot_id(),
            )
        ]

    def get_task_queue(self, server_config: "CompassBotServerConfig") -> str:
        """Return the task queue for dataset monitoring.

        In local development, use the standard task queue.
        In production, use the dedicated dataset monitoring queue.
        """
        if server_config.is_local:
            return DEFAULT_TASK_QUEUE
        return DATASET_MONITORING_TASK_QUEUE
