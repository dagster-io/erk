"""Temporal workflow for dataset sync after connection setup.

This workflow orchestrates the process of syncing datasets after a new connection
is added, including PR creation, dataset processing, and notifications.
"""

import asyncio
from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

from csbot.temporal.constants import Workflow

with workflow.unsafe.imports_passed_through():
    from csbot.temporal.dataset_sync.activity import (
        CreateBranchInput,
        CreateBranchOutput,
        DatasetProgress,
        DatasetProgressStatus,
        FinalizePullRequestInput,
        FinalizePullRequestOutput,
        LogAnalyticsInput,
        LogAnalyticsOutput,
        ProcessDatasetInput,
        ProcessDatasetOutput,
        SendCompletionNotificationInput,
        SendCompletionNotificationOutput,
        SendNotificationInput,
        SendNotificationOutput,
        SendSlackConnectInviteInput,
        SendSlackConnectInviteOutput,
    )


class DatasetSyncWorkflowInput(BaseModel):
    """Input parameters for DatasetSyncWorkflow.

    Attributes:
        bot_id: Bot instance ID (team_id-channel_name format)
        connection_name: Name of the connection being synced
        table_names: List of table/dataset names to process
        governance_channel_id: Slack channel ID for governance alerts
        connection_type: Type of connection (e.g., "connection", "warehouse")
    """

    bot_id: str
    connection_name: str
    table_names: list[str]
    governance_channel_id: str
    connection_type: str = "connection"


class DatasetSyncWorkflowResult(BaseModel):
    """Result of DatasetSyncWorkflow execution.

    Attributes:
        pr_url: URL of the created pull request
        processed_datasets: List of successfully processed datasets
        failed_datasets: List of datasets that failed processing
        sync_duration_seconds: Total duration of the sync in seconds
    """

    pr_url: str
    processed_datasets: list[str]
    failed_datasets: list[str]
    sync_duration_seconds: float


@workflow.defn(name=Workflow.DATASET_SYNC_WORKFLOW_NAME.value)
class DatasetSyncWorkflow:
    """Workflow for syncing datasets after connection setup.

    This workflow handles the complete dataset sync process using GitHub APIs:
    1. Create a GitHub PR branch
    2. Send initial Slack notification with button to view progress page
    3. Process each dataset (analyze schema, generate documentation, update files via GitHub API)
    4. Create and merge the pull request
    5. Send completion Slack notifications
    6. Send Slack Connect invite if this is first dataset sync (checks for pending invites)
    7. Log analytics events

    The workflow uses GitHub APIs directly instead of maintaining a local repository copy,
    allowing each dataset to be processed independently and files to be added to the PR branch
    individually using repo.update_file().

    The workflow is designed to be idempotent and handle partial failures gracefully.

    Progress tracking is available via the get_dataset_progress() query method, which returns
    the current status of all datasets being processed.
    """

    def __init__(self) -> None:
        """Initialize workflow state for progress tracking."""
        self._dataset_statuses: dict[str, DatasetProgress] = {}  # table_name -> latest status
        self._all_table_names: list[str] = []  # All tables to process (for pending state)

    @workflow.signal
    def update_dataset_status(self, progress: DatasetProgress) -> None:
        """Signal handler for dataset status updates.

        This signal is sent by activities to update the workflow state,
        which can be queried via get_dataset_progress().

        Args:
            progress: Progress update with table_name, status, and optional message
        """
        self._dataset_statuses[progress.table_name] = progress
        workflow.logger.info(f"Updated dataset status: {progress.table_name} - {progress.status}")

    @workflow.query
    def get_dataset_progress(self) -> list[DatasetProgress]:
        """Query method to get current progress of all datasets.

        Returns:
            List of DatasetProgress for all datasets being processed
        """
        progress_updates = []
        for table_name in self._all_table_names:
            if table_name in self._dataset_statuses:
                progress_updates.append(self._dataset_statuses[table_name])
            else:
                # Dataset not yet processed - show as pending
                progress_updates.append(
                    DatasetProgress(
                        table_name=table_name,
                        status=DatasetProgressStatus.PROCESSING,
                        message="Pending",
                    )
                )
        return progress_updates

    @workflow.run
    async def run(self, args: DatasetSyncWorkflowInput) -> DatasetSyncWorkflowResult:
        """Execute dataset sync workflow.

        Args:
            args: Input parameters for the workflow

        Returns:
            DatasetSyncWorkflowResult with PR URL and processing results
        """
        workflow.logger.info(
            f"Starting dataset sync for connection {args.connection_name} "
            f"with {len(args.table_names)} tables"
        )

        start_time = workflow.now()

        # Track all tables for query support
        self._all_table_names = args.table_names

        # Step 1: Create PR branch via GitHub API
        workflow.logger.info("Creating PR branch")
        branch_result = await workflow.execute_activity(
            "create_branch",
            CreateBranchInput(
                bot_id=args.bot_id,
                connection_name=args.connection_name,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=1),
            ),
            result_type=CreateBranchOutput,  # type: ignore
        )

        pr_branch = branch_result.pr_branch
        workflow.logger.info(f"Created PR branch: {pr_branch}")

        # Step 2: Send initial Slack notification with all datasets as PENDING
        workflow.logger.info("Sending initial Slack notification")
        notification_result = await workflow.execute_activity(
            "send_notification_started",
            SendNotificationInput(
                bot_id=args.bot_id,
                connection_name=args.connection_name,
                governance_channel_id=args.governance_channel_id,
                table_names=args.table_names,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=1),
            ),
            result_type=SendNotificationOutput,  # type: ignore
        )

        message_ts = notification_result.message_ts

        # Step 3: Process datasets in parallel (update files via GitHub API on pr_branch)
        workflow.logger.info(f"Processing {len(args.table_names)} datasets in parallel")
        processed_datasets: list[str] = []
        failed_datasets: list[str] = []
        failed_dataset_errors: dict[str, str] = {}  # Map dataset name to error message

        # Create tasks for all datasets to process them in parallel
        async def process_single_dataset(table_name: str) -> tuple[str, bool, str | None]:
            """Process a single dataset and return (table_name, success, error_message)."""
            try:
                workflow.logger.info(f"Processing dataset: {table_name}")
                result = await workflow.execute_activity(
                    "process_dataset",
                    ProcessDatasetInput(
                        bot_id=args.bot_id,
                        connection_name=args.connection_name,
                        table_name=table_name,
                        pr_branch=pr_branch,
                        governance_channel_id=args.governance_channel_id,
                        message_ts=message_ts,
                    ),
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=RetryPolicy(
                        maximum_attempts=2,
                        initial_interval=timedelta(seconds=10),
                        maximum_interval=timedelta(minutes=2),
                    ),
                    result_type=ProcessDatasetOutput,  # type: ignore
                )

                # Check if activity reported success
                if result.success:
                    workflow.logger.info(f"Successfully processed: {table_name}")
                    return (table_name, True, None)

                # Activity completed but reported failure
                error_msg = result.error_message or "Unknown error"
                workflow.logger.error(f"Failed to process dataset {table_name}: {error_msg}")
                return (table_name, False, error_msg)

            except Exception as e:
                error_msg = str(e)
                workflow.logger.error(f"Failed to process dataset {table_name}: {error_msg}")
                return (table_name, False, error_msg)

        # Process all datasets in parallel using asyncio.gather
        # gather returns results in the same order as input tasks
        results = await asyncio.gather(
            *[process_single_dataset(table_name) for table_name in args.table_names]
        )

        # Collect successful and failed datasets with error messages from results
        for table_name, success, error_msg in results:
            if success:
                processed_datasets.append(table_name)
            else:
                failed_datasets.append(table_name)
                if error_msg:
                    failed_dataset_errors[table_name] = error_msg

        # Step 4: Finalize PR (create and merge PR from branch)
        workflow.logger.info("Finalizing pull request")
        pr_result = await workflow.execute_activity(
            "finalize_pull_request",
            FinalizePullRequestInput(
                bot_id=args.bot_id,
                connection_name=args.connection_name,
                table_names=args.table_names,
                pr_branch=pr_branch,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=1),
            ),
            result_type=FinalizePullRequestOutput,  # type: ignore
        )

        pr_url = pr_result.pr_url
        workflow.logger.info(f"Created and merged PR: {pr_url}")

        # Step 5: Send completion Slack notification with granular error details
        workflow.logger.info("Sending completion notification")
        await workflow.execute_activity(
            "send_notification_completed",
            SendCompletionNotificationInput(
                bot_id=args.bot_id,
                connection_name=args.connection_name,
                governance_channel_id=args.governance_channel_id,
                message_ts=message_ts,
                pr_url=pr_url,
                processed_datasets=processed_datasets,
                failed_datasets=failed_datasets,
                failed_dataset_errors=failed_dataset_errors,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=1),
            ),
            result_type=SendCompletionNotificationOutput,  # type: ignore
        )

        # Step 6: Send Slack Connect invite if this is first dataset sync for the channel
        # The activity checks for pending invites and only sends if found
        workflow.logger.info("Checking for Slack Connect invite")
        await workflow.execute_activity(
            "send_slack_connect_invite",
            SendSlackConnectInviteInput(
                bot_id=args.bot_id,
                governance_channel_id=args.governance_channel_id,
            ),
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=1),
            ),
            result_type=SendSlackConnectInviteOutput,  # type: ignore
        )

        # Step 7: Log analytics
        sync_duration = (workflow.now() - start_time).total_seconds()
        workflow.logger.info("Logging analytics events")
        await workflow.execute_activity(
            "log_analytics",
            LogAnalyticsInput(
                bot_id=args.bot_id,
                connection_name=args.connection_name,
                connection_type=args.connection_type,
                governance_channel_id=args.governance_channel_id,
                table_count=len(args.table_names),
                pr_url=pr_url,
                sync_duration_seconds=sync_duration,
                processed_datasets=processed_datasets,
                failed_datasets=failed_datasets,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=1),
            ),
            result_type=LogAnalyticsOutput,  # type: ignore
        )

        workflow.logger.info(
            f"Dataset sync completed. Processed: {len(processed_datasets)}, "
            f"Failed: {len(failed_datasets)}"
        )

        return DatasetSyncWorkflowResult(
            pr_url=pr_url,
            processed_datasets=processed_datasets,
            failed_datasets=failed_datasets,
            sync_duration_seconds=sync_duration,
        )
