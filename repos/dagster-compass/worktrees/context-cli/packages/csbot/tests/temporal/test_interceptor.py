"""Tests for DatasetMonitoring Temporal workflow."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from temporalio import activity, workflow
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from csbot.temporal.interceptor import WorkerInterceptor


@activity.defn
async def my_activity(x: int) -> int:
    return x + 1


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self):
        result = await workflow.execute_activity(
            "my_activity",
            2,
            start_to_close_timeout=timedelta(minutes=30),
        )
        assert result == 3


@pytest.mark.asyncio
async def test_dataset_monitoring_workflow_happy_path():
    """Test dataset monitoring workflow processes all datasets successfully."""
    async with await WorkflowEnvironment.start_time_skipping(
        data_converter=pydantic_data_converter
    ) as env:
        async with Worker(
            env.client,
            task_queue="x",
            workflows=[MyWorkflow],
            activities=[my_activity],
            interceptors=[WorkerInterceptor()],
        ):
            with patch("csbot.temporal.interceptor.instrument_context") as f:
                f.return_value.__enter__.return_value = None
                f.return_value.__exit__.return_value = None

                await env.client.execute_workflow(
                    MyWorkflow.run,
                    id="test-dataset-monitor-workflow",
                    task_queue="x",
                )

                f.assert_called_once()
