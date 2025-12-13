"""Temporal workflow for daily exploration background task."""

from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

from csbot.temporal import constants
from csbot.temporal.daily_exploration.activity import DailyExplorationInput, DailyExplorationResult


class DailyExplorationWorkflowInput(BaseModel):
    bot_id: str
    channel_name: str


@workflow.defn(name=constants.Workflow.DAILY_EXPLORATION_WORKFLOW_NAME.value)
class DailyExplorationWorkflow:
    """Workflow for sending daily exploration to a Slack channel.

    This workflow is scheduled to run on weekdays at 9 AM via Temporal's
    calendar-based scheduling. The schedule ensures this only runs Monday-Friday,
    so no weekend checking is needed in the workflow implementation.
    """

    @workflow.run
    async def run(self, args: DailyExplorationWorkflowInput) -> DailyExplorationResult:
        """Execute daily exploration workflow.

        Args:
            bot_id: Bot instance ID (team_id-channel_name format)
            channel_name: Slack channel name to send exploration to

        Returns:
            DailyExplorationResult indicating success
        """
        bot_id = args.bot_id
        channel_name = args.channel_name
        workflow.logger.info(f"Starting daily exploration for {channel_name}")

        # Execute the activity to send daily exploration
        result = await workflow.execute_activity(
            constants.Activity.SEND_DAILY_EXPLORATION_ACTIVITY_NAME.value,
            DailyExplorationInput(
                bot_id=bot_id,
                channel_name=channel_name,
            ),
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10),
                maximum_interval=timedelta(minutes=2),
            ),
            result_type=DailyExplorationResult,
        )

        workflow.logger.info(f"Completed daily exploration for {channel_name}")
        return result
