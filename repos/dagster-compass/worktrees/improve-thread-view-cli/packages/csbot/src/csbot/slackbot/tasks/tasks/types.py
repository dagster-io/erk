from typing import Any, Protocol

from temporalio.client import (
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    WorkflowHandle,
)

from csbot.temporal.daily_exploration.activity import DailyExplorationResult
from csbot.temporal.daily_exploration.workflow import DailyExplorationWorkflowInput
from csbot.temporal.thread_health_inspector.workflow import ThreadHealthInspectorWorkflowInput


class BotBackgroundTaskManager(Protocol):
    async def submit_inspect_thread_health(
        self, input: ThreadHealthInspectorWorkflowInput
    ) -> WorkflowHandle[Any, Any]: ...

    async def execute_daily_exploration(
        self, input: DailyExplorationWorkflowInput
    ) -> DailyExplorationResult: ...

    async def reconcile(
        self,
        schedule_id: str,
        schedule_spec: ScheduleSpec,
        action: ScheduleActionStartWorkflow,
    ): ...
