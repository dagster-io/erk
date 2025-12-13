"""Daily exploration background task for CompassChannelBotInstance."""

from datetime import timedelta

from temporalio.client import ScheduleCalendarSpec, ScheduleRange, ScheduleSpec

from csbot.slackbot.channel_bot.tasks.bot_instance_temporal_task import (
    BotInstanceTemporalBackgroundTask,
)
from csbot.slackbot.flags import is_exempt_from_daily_exploration
from csbot.temporal.constants import Workflow


class DailyExplorationTask(BotInstanceTemporalBackgroundTask):
    """Manages the daily exploration Temporal scheduled workflow.

    This task reconciles a Temporal scheduled workflow that sends
    daily explorations to the channel. The actual work is done by
    the DailyExplorationWorkflow, not by this task directly.
    """

    def get_schedule_id(self) -> str:
        """Return the unique schedule ID for this workflow."""
        return f"daily-exploration-{self.bot.key.to_bot_id()}"

    def get_workflow_id_prefix(self) -> str:
        """Return the workflow ID prefix for workflow executions."""
        return f"daily-exploration-{self.bot.key.to_bot_id()}"

    def get_workflow_type(self) -> Workflow:
        return Workflow.DAILY_EXPLORATION_WORKFLOW_NAME

    def get_schedule_spec(self) -> ScheduleSpec:
        """Return the schedule specification.

        Runs Monday-Friday at 9 AM with 1 hour jitter.
        """
        # Run at 9 AM on weekdays (Monday=1, Friday=5) with 1 hour jitter
        return ScheduleSpec(
            calendars=[
                ScheduleCalendarSpec(
                    hour=[ScheduleRange(start=9, end=9)],
                    day_of_week=[ScheduleRange(start=1, end=5)],
                )
            ],
            jitter=timedelta(hours=1),
        )

    def get_workflow_args(self) -> list:
        """Return the arguments to pass to the workflow."""
        from csbot.temporal.daily_exploration.workflow import DailyExplorationWorkflowInput

        return [
            DailyExplorationWorkflowInput(
                bot_id=self.bot.key.to_bot_id(),
                channel_name=self.bot.key.channel_name,
            )
        ]

    async def execute_tick(self) -> None:
        """Reconcile the Temporal scheduled workflow."""
        # Check if exempt before reconciling
        if is_exempt_from_daily_exploration(self.bot):
            self.bot.logger.info("Skipping daily exploration schedule for exempt organization")
            return

        # Call parent to reconcile the schedule
        await super().execute_tick()
