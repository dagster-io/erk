"""Base class for background tasks that reconcile Temporal scheduled workflows."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog
from temporalio.client import Client as TemporalClient
from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleUpdate,
    ScheduleUpdateInput,
    WorkflowHandle,
)
from temporalio.service import RPCError

from csbot.temporal import constants
from csbot.temporal.daily_exploration.workflow import (
    DailyExplorationResult,
    DailyExplorationWorkflow,
    DailyExplorationWorkflowInput,
)
from csbot.temporal.thread_health_inspector.activity import ThreadHealthInspectorResult
from csbot.temporal.thread_health_inspector.workflow import ThreadHealthInspectorWorkflowInput

if TYPE_CHECKING:
    from csbot.slackbot.tasks.background_tasks import BackgroundTaskManager


logger = structlog.get_logger(__name__)


class TemporalBackgroundTaskManager:
    def __init__(self, temporal_client: TemporalClient, thread_health_start_delay_seconds: int):
        self._temporal_client = temporal_client
        self._thread_health_start_delay_seconds = thread_health_start_delay_seconds

    async def execute_daily_exploration(
        self, input: DailyExplorationWorkflowInput
    ) -> DailyExplorationResult:
        workflow_id = f"on-demand-daily-exploration-{int(datetime.now(UTC).timestamp())}"
        logger.info(f"Starting workflow {workflow_id} on task queue {constants.DEFAULT_TASK_QUEUE}")

        return await self._temporal_client.execute_workflow(
            DailyExplorationWorkflow.run,
            input,
            id=workflow_id,
            task_queue=constants.DEFAULT_TASK_QUEUE,
        )

    async def submit_inspect_thread_health(
        self, input: ThreadHealthInspectorWorkflowInput
    ) -> WorkflowHandle[Any, Any]:
        workflow_id = f"thread-health-{input.channel_id}-{input.thread_ts}-{str(uuid4())[:8]}"
        return await self._temporal_client.start_workflow(
            constants.Workflow.THREAD_HEALTH_INSPECTOR_WORKFLOW_NAME.value,
            input,
            id=workflow_id,
            task_queue=constants.DEFAULT_TASK_QUEUE,
            result_type=ThreadHealthInspectorResult,  # type: ignore
            start_delay=timedelta(seconds=self._thread_health_start_delay_seconds),
        )

    async def reconcile(
        self,
        schedule_id: str,
        schedule_spec: ScheduleSpec,
        action: ScheduleActionStartWorkflow,
    ):
        # Check if schedule already exists
        schedule_handle = self._temporal_client.get_schedule_handle(schedule_id)
        schedule_exists = False

        try:
            # Try to describe the schedule - will raise RPCError if not found
            await schedule_handle.describe()
            schedule_exists = True
        except RPCError as e:
            # Schedule doesn't exist (status code 5 = NOT_FOUND)
            if e.status.value != 5:
                # Some other error, re-raise
                raise
            schedule_exists = False

        if not schedule_exists:
            # Create new schedule
            schedule = Schedule(
                action=action,
                spec=schedule_spec,
            )
            await self._temporal_client.create_schedule(
                schedule_id,
                schedule,
            )
            logger.info(f"Created Temporal schedule '{schedule_id}'")
        else:
            # Update existing schedule
            def updater(input_schedule: ScheduleUpdateInput):
                update = input_schedule.description.schedule
                update.action = action
                update.spec = schedule_spec
                return ScheduleUpdate(schedule=update)

            await schedule_handle.update(updater)
            logger.info(f"Updated Temporal schedule '{schedule_id}'")


if TYPE_CHECKING:
    _: BackgroundTaskManager = TemporalBackgroundTaskManager(...)  # type: ignore[abstract]
