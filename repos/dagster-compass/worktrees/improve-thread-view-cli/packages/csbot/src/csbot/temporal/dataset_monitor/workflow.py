import asyncio
from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

from csbot.temporal import constants
from csbot.temporal.dataset_monitor.activity import (
    DatasetMonitoringActivityInput,
    DatasetMonitoringFailure,
    DatasetMonitoringResult,
    DatasetMonitoringSuccess,
)
from csbot.temporal.shared_activities.context_store_loader import (
    ContextStoreLoaderInput,
    ContextStoreLoadResult,
)


class DatasetMonitoringWorkflowInput(BaseModel):
    bot_id: str


class DatasetMonitoringWorkflowResult(BaseModel):
    success: bool = True


@workflow.defn(name=constants.Workflow.DATASET_MONITORING_WORKFLOW_NAME.value)
class DatasetMonitoringWorkflow:
    @workflow.run
    async def run(self, args: DatasetMonitoringWorkflowInput) -> DatasetMonitoringWorkflowResult:
        bot_id = args.bot_id
        context_store_loader_result: ContextStoreLoadResult = await workflow.execute_activity(
            constants.Activity.CONTEXT_STORE_LOADER_ACTIVITY_NAME.value,
            ContextStoreLoaderInput(
                bot_id=bot_id,
            ),
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10),
                maximum_interval=timedelta(minutes=2),
            ),
            result_type=ContextStoreLoadResult,  # type: ignore
        )
        context_store = context_store_loader_result.context_store
        results: list[DatasetMonitoringResult] = await asyncio.gather(
            *[
                workflow.execute_activity(
                    constants.Activity.DATASET_MONITORING_ACTIVITY_NAME.value,
                    DatasetMonitoringActivityInput(
                        bot_id=bot_id,
                        table_name=dataset.table_name,
                        connection=dataset.connection,
                        frontmatter=documentation.frontmatter,
                    ),
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=RetryPolicy(
                        maximum_attempts=3,
                        initial_interval=timedelta(seconds=10),
                        maximum_interval=timedelta(minutes=2),
                    ),
                    result_type=DatasetMonitoringResult,  # type: ignore
                )
                for dataset, documentation in context_store.datasets
            ]
        )
        for (dataset, _), result in zip(context_store.datasets, results):
            if isinstance(result, DatasetMonitoringSuccess):
                if result.pr_url:
                    workflow.logger.info(
                        f"Created PR for bot {bot_id}, connection {dataset.connection}, table {dataset.table_name}: {result.pr_url}"
                    )
                else:
                    workflow.logger.info(
                        f"No changes for bot {bot_id}, connection {dataset.connection}, table {dataset.table_name}"
                    )
            elif isinstance(result, DatasetMonitoringFailure):
                workflow.logger.error(
                    f"Dataset monitoring failed for {bot_id}, connection {dataset.connection}, table {dataset.table_name}: {result.error}"
                )
        return DatasetMonitoringWorkflowResult()
