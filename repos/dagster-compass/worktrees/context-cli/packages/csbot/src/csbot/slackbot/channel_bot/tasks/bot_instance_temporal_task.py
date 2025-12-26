"""Base class for background tasks that reconcile Temporal scheduled workflows."""

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING

from temporalio.client import ScheduleSpec

from csbot.slackbot.tasks.background_task import BackgroundTask
from csbot.temporal.client_wrapper import create_schedule_action_with_search_attributes
from csbot.temporal.constants import DEFAULT_TASK_QUEUE, Workflow

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
    from csbot.slackbot.slackbot_core import CompassBotServerConfig


class BotInstanceTemporalBackgroundTask(BackgroundTask):
    """Base class for background tasks that manage Temporal scheduled workflows.

    This task reconciles a Temporal scheduled workflow definition with the Temporal instance.
    The actual work is done by the Temporal workflow, not in execute_tick().
    """

    def __init__(self, bot: "CompassChannelBaseBotInstance"):
        self.bot = bot
        # Execute on init to reconcile schedule immediately
        super().__init__(execute_on_init=True)

    @property
    def logger(self) -> logging.Logger:
        return self.bot.logger

    @abstractmethod
    def get_schedule_id(self) -> str:
        """Return the unique schedule ID for this workflow."""
        ...

    @abstractmethod
    def get_workflow_id_prefix(self) -> str:
        """Return the workflow ID prefix for workflow executions."""
        ...

    @abstractmethod
    def get_workflow_type(self) -> Workflow:
        """Return the workflow type name (workflow class name)."""
        ...

    @abstractmethod
    def get_schedule_spec(self) -> ScheduleSpec:
        """Return the schedule specification for when to run the workflow."""
        ...

    @abstractmethod
    def get_workflow_args(self) -> list:
        """Return the arguments to pass to the workflow."""
        ...

    def get_task_queue(self, server_config: "CompassBotServerConfig") -> str:
        """Return the task queue name for this workflow.

        Subclasses can override this method to use a dedicated task queue.
        Default implementation returns the standard task queue.
        """
        return DEFAULT_TASK_QUEUE

    async def execute_tick(self) -> None:
        """Reconcile the Temporal scheduled workflow with desired state."""
        schedule_id = self.get_schedule_id()
        workflow_id_prefix = self.get_workflow_id_prefix()
        workflow_type = self.get_workflow_type()
        schedule_spec = self.get_schedule_spec()
        workflow_args = self.get_workflow_args()
        task_queue = self.get_task_queue(self.bot.server_config)

        self.logger.info(
            f"Reconciling Temporal schedule '{schedule_id}' for workflow '{workflow_type}'"
        )

        # Create the schedule action with search attributes
        action = create_schedule_action_with_search_attributes(
            temporal_config=self.bot.server_config.temporal,
            workflow_type=workflow_type.value,
            workflow_id_pattern=f"{workflow_id_prefix}-{{ScheduledTime}}",
            task_queue=task_queue,
            workflow_args=workflow_args,
            organization_name=self.bot.bot_config.organization_name,
        )

        await self.bot.bot_background_task_manager.reconcile(schedule_id, schedule_spec, action)

    def get_sleep_seconds(self) -> float:
        """Sleep for 1 hour between reconciliations."""
        return 3600.0
