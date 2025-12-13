"""Temporal workflow for thread health inspection."""

from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

from csbot.temporal import constants
from csbot.temporal.thread_health_inspector.activity import (
    ThreadHealthInspectorInput,
    ThreadHealthInspectorResult,
    ThreadHealthInspectorSuccess,
)

with workflow.unsafe.imports_passed_through():
    from datadog.dogstatsd import statsd  # pyright: ignore


class ThreadHealthInspectorWorkflowInput(BaseModel):
    """Input for thread health inspector workflow."""

    governance_bot_id: str
    channel_id: str
    thread_ts: str


@workflow.defn(name=constants.Workflow.THREAD_HEALTH_INSPECTOR_WORKFLOW_NAME.value)
class ThreadHealthInspectorWorkflow:
    """Workflow for inspecting thread health and rating conversation quality.

    This workflow loads a SlackThread from the kv store, extracts the conversation
    events, and uses AI to evaluate the quality of the bot's responses.
    """

    @workflow.run
    async def run(self, args: ThreadHealthInspectorWorkflowInput) -> ThreadHealthInspectorResult:
        """Execute thread health inspection workflow.

        Args:
            args: Input containing governance_bot_id, channel_id, thread_ts

        Returns:
            ThreadHealthInspectorResult with AI-generated health scores
        """
        governance_bot_id = args.governance_bot_id
        channel_id = args.channel_id
        thread_ts = args.thread_ts

        workflow.logger.info(
            f"Starting thread health inspection for bot={governance_bot_id}, "
            f"channel={channel_id}, thread={thread_ts}"
        )

        # Execute the activity to inspect thread health
        result: ThreadHealthInspectorResult = await workflow.execute_activity(
            constants.Activity.INSPECT_THREAD_HEALTH_ACTIVITY_NAME.value,
            ThreadHealthInspectorInput(
                governance_bot_id=governance_bot_id,
                channel_id=channel_id,
                thread_ts=thread_ts,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10),
                maximum_interval=timedelta(minutes=1),
            ),
            result_type=ThreadHealthInspectorResult,  # pyright: ignore
        )

        if isinstance(result, ThreadHealthInspectorSuccess):
            statsd.histogram("compass.thread_health.accuracy", result.score.accuracy)
            statsd.histogram("compass.thread_health.responsiveness", result.score.responsiveness)
            statsd.histogram("compass.thread_health.helpfulness", result.score.helpfulness)
            if result.score.failure_occurred:
                statsd.increment("compass.thread_health.failure")
            workflow.logger.info(
                f"Completed thread health inspection: "
                f"accuracy={result.score.accuracy}, "
                f"responsiveness={result.score.responsiveness}, "
                f"helpfulness={result.score.helpfulness}"
            )

        return result
