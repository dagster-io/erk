"""Temporal activities for dataset sync workflow.

This module provides the activity implementations for the dataset sync workflow,
including PR creation, dataset processing, Slack notifications, and analytics logging.
"""

import asyncio
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast

import backoff
from github.GithubException import GithubException
from github.Repository import Repository
from pydantic import BaseModel
from temporalio import activity
from temporalio.client import Client

from csbot.contextengine.contextstore_protocol import Dataset
from csbot.contextengine.serializer import serialize_context_store
from csbot.ctx_admin.dataset_documentation import (
    analyze_table_schema,
    update_dataset,
)
from csbot.local_context_store.github.api import create_and_merge_pull_request
from csbot.local_context_store.github.utils import get_file_updates
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.dataset_processor import notify_dataset_error
from csbot.slackbot.slackbot_analytics import AnalyticsEventType, log_analytics_event_unified
from csbot.slackbot.slackbot_blockkit import (
    SectionBlock,
    TextObject,
    TextType,
)
from csbot.slackbot.slackbot_slackstream import SlackstreamMessage
from csbot.temporal import constants

if TYPE_CHECKING:
    import logging

    from csbot.temporal.utils import BotProvider


@backoff.on_exception(backoff.expo, GithubException, giveup=lambda e: e.status != 409, max_time=30)
def create_or_update_file(repo: Repository, path: str, content: str, message: str, branch: str):
    """Create or update a file in the repository.

    PyGithub does not provide a separate existence check, so we must catch
    GithubException to determine if the file exists and choose create vs update.

    Args:
        repo: PyGithub Repository object
        path: Path to file in repository
        content: File content
        message: Commit message
        branch: Target branch
    """
    # PyGithub raises GithubException with status 404 when file not found

    try:
        existing_file = repo.get_contents(path, ref=branch)
        # File exists, update it
        repo.update_file(
            path=path,
            message=message,
            content=content,
            sha=existing_file.sha,  # type: ignore
            branch=branch,
        )
    except GithubException as e:
        # Status 404 means file doesn't exist, create it
        if e.status == 404:
            repo.create_file(
                path=path,
                message=message,
                content=content,
                branch=branch,
            )
        else:
            # Re-raise other errors (auth, rate limit, etc)
            raise


class CreateBranchInput(BaseModel):
    """Input for create_branch activity."""

    bot_id: str
    connection_name: str


class CreateBranchOutput(BaseModel):
    """Output of create_branch activity."""

    pr_branch: str


class SendNotificationInput(BaseModel):
    """Input for send notification activities."""

    bot_id: str
    connection_name: str
    governance_channel_id: str
    table_names: list[str]  # List of tables to show in initial status


class SendNotificationOutput(BaseModel):
    """Output of send notification activities."""

    message_ts: str | None


class ProcessDatasetInput(BaseModel):
    """Input for process_dataset activity."""

    bot_id: str
    connection_name: str
    table_name: str
    pr_branch: str
    governance_channel_id: str  # For posting detailed progress messages
    message_ts: str | None  # Thread timestamp for progress messages


class ProcessDatasetOutput(BaseModel):
    """Output of process_dataset activity."""

    success: bool
    error_message: str | None = None


class FinalizePullRequestInput(BaseModel):
    """Input for finalize_pull_request activity."""

    bot_id: str
    connection_name: str
    table_names: list[str]
    pr_branch: str


class FinalizePullRequestOutput(BaseModel):
    """Output of finalize_pull_request activity."""

    pr_url: str


class SendCompletionNotificationInput(BaseModel):
    """Input for send_completion_notification activity."""

    bot_id: str
    connection_name: str
    governance_channel_id: str
    pr_url: str | None
    processed_datasets: list[str]
    failed_datasets: list[str]
    message_ts: str | None
    failed_dataset_errors: dict[str, str] | None = None  # Optional map of dataset -> error message


class SendCompletionNotificationOutput(BaseModel):
    """Output of send_completion_notification activity."""

    message_ts: str | None


class LogAnalyticsInput(BaseModel):
    """Input for log_analytics activity."""

    bot_id: str
    connection_name: str
    connection_type: str
    table_count: int
    pr_url: str
    sync_duration_seconds: float
    processed_datasets: list[str]
    failed_datasets: list[str]
    governance_channel_id: str | None = None


class LogAnalyticsOutput(BaseModel):
    """Output of log_analytics activity."""

    success: bool


class SendSlackConnectInviteInput(BaseModel):
    """Input for send_slack_connect_invite activity."""

    bot_id: str
    governance_channel_id: str


class SendSlackConnectInviteOutput(BaseModel):
    """Output of send_slack_connect_invite activity."""

    success: bool
    invited_users: list[str]  # List of user IDs that were successfully invited


class DatasetProgressStatus(str, Enum):
    """Status values for dataset processing progress."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DatasetProgress(BaseModel):
    """Progress update for a dataset being processed.

    Attributes:
        table_name: Name of the table/dataset
        status: Current status
        message: Optional progress message
    """

    table_name: str
    status: DatasetProgressStatus
    message: str = ""


class UpdateProgressInput(BaseModel):
    """Input for update_progress activity."""

    bot_id: str
    governance_channel_id: str
    message_ts: str
    connection_name: str
    progress_updates: list[DatasetProgress]


class UpdateProgressOutput(BaseModel):
    """Output of update_progress activity."""

    success: bool


class DatasetSyncActivities:
    """Collection of activities for dataset sync workflow.

    This class groups all the activities needed for the dataset sync workflow,
    providing them access to the bot reconciler to retrieve bot instances.
    """

    def __init__(self, bot_provider: "BotProvider", temporal_client: Client):
        self.bot_provider = bot_provider
        self.temporal_client = temporal_client

    async def _fetch_bot(self, bot_id: str):
        return await self.bot_provider.fetch_bot(BotKey.from_bot_id(bot_id))

    # Activities are ordered by workflow execution sequence:
    # 1. create_branch
    # 2. send_notification_started (sends simple message with View Progress button)
    # 3. process_dataset (called in parallel - updates files via GitHub API, updates workflow state)
    # 4. finalize_pull_request (creates and merges PR from branch)
    # 5. send_notification_completed (sends completion notification in thread)
    # 6. log_analytics

    @activity.defn(name=constants.Activity.CREATE_BRANCH_ACTIVITY_NAME.value)
    async def create_branch(self, input: CreateBranchInput) -> CreateBranchOutput:
        """Create PR branch using GitHub API.

        This activity creates a new branch off main using the GitHub API,
        preparing it for file updates during dataset processing.

        Args:
            input: CreateBranchInput with bot_id and connection_name

        Returns:
            CreateBranchOutput with pr_branch name
        """
        bot_id = input.bot_id
        connection_name = input.connection_name

        activity.logger.info(f"Creating PR branch for connection {connection_name}")

        bot = await self._fetch_bot(bot_id)

        # Generate unique branch name
        branch_name = f"dataset-sync-{connection_name}-{int(time.time())}"

        # Create branch via GitHub API
        github_config = bot.local_context_store.shared_repo.repo_config.github_config

        def create_branch_sync():
            """Create branch using GitHub API in sync context."""
            g = github_config.auth_source.get_github_client()
            repo = g.get_repo(github_config.repo_name)

            # Get the main branch's latest commit SHA
            main_branch = repo.get_branch(repo.default_branch)
            main_sha = main_branch.commit.sha

            # Create new branch from main
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_sha)

            return branch_name

        branch = await asyncio.to_thread(create_branch_sync)

        activity.logger.info(f"Created PR branch: {branch}")

        return CreateBranchOutput(pr_branch=branch)

    @activity.defn(name=constants.Activity.SEND_NOTIFICATION_STARTED_ACTIVITY_NAME.value)
    async def send_notification_started(
        self, input: SendNotificationInput
    ) -> SendNotificationOutput:
        """Send initial Slack notification that dataset sync has started.

        Shows all datasets in PENDING state, matching the format of existing dataset processor.

        Args:
            input: SendNotificationInput with bot_id, connection_name, governance_channel_id, table_names

        Returns:
            SendNotificationOutput with message_ts
        """
        bot_id = input.bot_id
        connection_name = input.connection_name
        governance_channel_id = input.governance_channel_id
        table_names = input.table_names

        activity.logger.info(
            f"Sending started notification for connection {connection_name} with {len(table_names)} tables"
        )

        bot = await self._fetch_bot(bot_id)

        from csbot.slackbot.slackbot_blockkit import ActionsBlock, ButtonElement

        # Build simple message with button to view progress
        dataset_count = len(table_names)
        message_text = (
            f"⏳ Processing {dataset_count} dataset{'s' if dataset_count != 1 else ''} "
            f"for connection `{connection_name}`"
        )

        # Post initial message with button that triggers modal
        # The action_id is used to identify this button click in the interaction handler
        message = await SlackstreamMessage.post_message(
            client=bot.client,
            channel_id=governance_channel_id,
            blocks=[
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=message_text,
                    )
                ),
                ActionsBlock(
                    elements=[
                        ButtonElement(
                            text=TextObject.plain_text("View Progress"),
                            action_id=f"view_dataset_sync_progress:{connection_name}",
                            style="primary",
                        )
                    ]
                ),
            ],
        )

        return SendNotificationOutput(message_ts=message.message_ts if message else None)

    @activity.defn(name=constants.Activity.PROCESS_DATASET_ACTIVITY_NAME.value)
    async def process_dataset(self, input: ProcessDatasetInput) -> ProcessDatasetOutput:
        """Process a single dataset (analyze schema and generate documentation).

        This activity processes a dataset and updates files on the PR branch using GitHub API.

        Args:
            input: ProcessDatasetInput with bot_id, connection_name, table_name, pr_branch

        Returns:
            ProcessDatasetOutput with success status and optional error_message
        """
        bot_id = input.bot_id
        connection_name = input.connection_name
        table_name = input.table_name
        pr_branch = input.pr_branch

        activity.logger.info(f"Processing dataset {table_name} from connection {connection_name}")

        bot = await self._fetch_bot(bot_id)

        # Get workflow handle to update query state
        workflow_id = activity.info().workflow_id
        workflow_handle = self.temporal_client.get_workflow_handle(workflow_id)

        # Update workflow state for query support
        await workflow_handle.signal(
            "update_dataset_status",
            DatasetProgress(
                table_name=table_name,
                status=DatasetProgressStatus.PROCESSING,
                message="Processing",
            ),
        )

        original_context_store = await bot.load_context_store()

        def process_dataset_sync():
            """Process dataset in sync context (required by load_project_from_tree)."""
            # Use a temporary directory to process the dataset
            with tempfile.TemporaryDirectory() as temp_dir:
                # Analyze table schema - use bot.profile which has connections already loaded
                github_config = bot.local_context_store.shared_repo.repo_config.github_config
                g = github_config.auth_source.get_github_client()
                repo = g.get_repo(github_config.repo_name)

                dataset_to_reconcile = Dataset(
                    table_name=table_name,
                    connection=connection_name,
                )

                activity.logger.info(f"Analyzing schema for {table_name}")

                table_schema_analysis = analyze_table_schema(
                    cast("logging.Logger", activity.logger),
                    bot.profile,
                    dataset_to_reconcile,
                )

                # Generate documentation
                activity.logger.info(f"Generating documentation for {table_name}")

                with ThreadPoolExecutor(max_workers=4) as column_analysis_threadpool:
                    updated = update_dataset(
                        cast("logging.Logger", activity.logger),
                        original_context_store,
                        bot.profile,
                        dataset_to_reconcile,
                        table_schema_analysis,
                        bot.agent,
                        column_analysis_threadpool,
                    )

                # Commit files to PR branch using GitHub API
                activity.logger.info(f"Committing files to PR branch {pr_branch}")

                serialize_context_store(updated, Path(temp_dir))
                file_updates = get_file_updates(
                    bot.local_context_store.shared_repo.repo_path, Path(temp_dir)
                )

                activity.logger.info(f"Found {len(file_updates)} files to commit")

                # Commit each file to the branch
                for rel_path, content in file_updates.items():
                    if content is None:
                        # shouldnt happen
                        continue

                    commit_message = f"Add dataset documentation for {table_name}"

                    create_or_update_file(
                        repo=repo,
                        path=rel_path,
                        content=content,
                        message=commit_message,
                        branch=pr_branch,
                    )

                    activity.logger.info(f"Committed {rel_path}")

                activity.logger.info(f"Successfully processed dataset {table_name}")

        try:
            await asyncio.to_thread(process_dataset_sync)

            # Update workflow state for query support
            await workflow_handle.signal(
                "update_dataset_status",
                DatasetProgress(
                    table_name=table_name,
                    status=DatasetProgressStatus.COMPLETED,
                    message="Completed",
                ),
            )

            return ProcessDatasetOutput(success=True, error_message=None)

        except Exception as e:
            error_msg = f"Failed to process dataset {table_name}: {str(e)}"
            activity.logger.error(error_msg, exc_info=True)

            # Update workflow state for query support
            await workflow_handle.signal(
                "update_dataset_status",
                DatasetProgress(
                    table_name=table_name,
                    status=DatasetProgressStatus.FAILED,
                    message=str(e)[:200],  # Truncate long error messages
                ),
            )

            return ProcessDatasetOutput(success=False, error_message=str(e))

    @activity.defn(name=constants.Activity.FINALIZE_PULL_REQUEST_ACTIVITY_NAME.value)
    async def finalize_pull_request(
        self, input: FinalizePullRequestInput
    ) -> FinalizePullRequestOutput:
        """Create and merge pull request from the branch.

        This activity creates the actual GitHub pull request from the branch
        that was populated with dataset files, and immediately merges it.

        Args:
            input: FinalizePullRequestInput with bot_id, connection_name, table_names, pr_branch

        Returns:
            FinalizePullRequestOutput with pr_url
        """
        bot_id = input.bot_id
        connection_name = input.connection_name
        table_names = input.table_names
        pr_branch = input.pr_branch

        activity.logger.info(f"Finalizing pull request for connection {connection_name}")

        bot = await self._fetch_bot(bot_id)

        pr_title = f"CONNECTION: Add datasets from {connection_name}"
        # Truncate title if too long
        if len(pr_title) > 72:
            pr_title = pr_title[: 72 - 3] + "..."

        pr_body = (
            f"Add datasets `{', '.join(table_names)}` from new connection `{connection_name}`.\n\n"
            f"Initiated by:\n- Connection setup via web interface\n- Automatic sync after connection creation"
        )

        # Create and merge PR using GitHub API
        github_config = bot.local_context_store.shared_repo.repo_config.github_config

        def create_and_merge_pr_sync():
            """Create and merge PR using GitHub API in sync context."""
            return create_and_merge_pull_request(
                config=github_config,
                title=pr_title,
                body=pr_body,
                head_branch=pr_branch,
            )

        pr_url = await asyncio.to_thread(create_and_merge_pr_sync)

        activity.logger.info(f"Created and merged PR: {pr_url}")

        return FinalizePullRequestOutput(pr_url=pr_url)

    @activity.defn(name=constants.Activity.SEND_NOTIFICATION_COMPLETED_ACTIVITY_NAME.value)
    async def send_notification_completed(
        self, input: SendCompletionNotificationInput
    ) -> SendCompletionNotificationOutput:
        """Send completion Slack notification with sync results.

        Args:
            input: SendCompletionNotificationInput with sync results

        Returns:
            SendCompletionNotificationOutput with message_ts
        """
        bot_id = input.bot_id
        connection_name = input.connection_name
        governance_channel_id = input.governance_channel_id
        processed_datasets = input.processed_datasets
        failed_datasets = input.failed_datasets
        message_ts = input.message_ts
        failed_dataset_errors = input.failed_dataset_errors or {}

        activity.logger.info(f"Sending completion notification for connection {connection_name}")

        bot = await self._fetch_bot(bot_id)

        from csbot.slackbot.slackbot_blockkit import ActionsBlock, ButtonElement

        # Update the original message to show completion status
        dataset_count = len(processed_datasets) + len(failed_datasets)

        # Determine emoji and message based on success/failure
        if failed_datasets:
            emoji = "⚠️"
            status_text = f"Completed with {len(failed_datasets)} error{'s' if len(failed_datasets) != 1 else ''}"
        else:
            emoji = "✅"
            status_text = "Completed successfully"

        message_text = (
            f"{emoji} {status_text}: {dataset_count} dataset{'s' if dataset_count != 1 else ''} "
            f"for connection `{connection_name}`"
        )

        # Update the original message (if we have a message_ts)
        if not message_ts:
            activity.logger.warning("No message_ts provided, skipping message update")
            return SendCompletionNotificationOutput(message_ts=None)

        slack_message = SlackstreamMessage(
            bot.client,
            governance_channel_id,
            message_ts,
        )

        await slack_message.update(
            blocks=[
                SectionBlock(
                    text=TextObject(
                        type=TextType.MRKDWN,
                        text=message_text,
                    )
                ),
                ActionsBlock(
                    elements=[
                        ButtonElement(
                            text=TextObject.plain_text("View Progress"),
                            action_id=f"view_dataset_sync_progress:{connection_name}",
                            style="primary" if not failed_datasets else None,
                        )
                    ]
                ),
            ]
        )

        # If there were failures, send error details in thread
        if failed_datasets:
            # Build detailed error message with per-dataset errors
            if failed_dataset_errors:
                error_lines = []
                for dataset in failed_datasets:
                    error_msg = failed_dataset_errors.get(dataset, "Unknown error")
                    # Truncate long error messages
                    if len(error_msg) > 200:
                        error_msg = error_msg[:197] + "..."
                    error_lines.append(f"• `{dataset}`: {error_msg}")
                error_message = "Failed to process the following datasets:\n" + "\n".join(
                    error_lines
                )
            else:
                error_message = f"Failed to process datasets: {', '.join(failed_datasets)}"

            await notify_dataset_error(
                bot=bot,
                error_message=error_message,
                governance_channel_id=governance_channel_id,
                thread_ts=message_ts,
            )

        return SendCompletionNotificationOutput(message_ts=message_ts)

    @activity.defn(name=constants.Activity.LOG_ANALYTICS_ACTIVITY_NAME.value)
    async def log_analytics(self, input: LogAnalyticsInput) -> LogAnalyticsOutput:
        """Log analytics events for dataset sync.

        Args:
            input: LogAnalyticsInput with analytics data

        Returns:
            LogAnalyticsOutput with success status
        """
        bot_id = input.bot_id
        connection_name = input.connection_name

        activity.logger.info(f"Logging analytics for connection {connection_name}")

        bot = await self._fetch_bot(bot_id)

        # Determine if sync was successful
        failed_datasets = input.failed_datasets
        event_type = (
            AnalyticsEventType.CONNECTION_SETUP_SUCCEEDED
            if not failed_datasets
            else AnalyticsEventType.CONNECTION_SETUP_FAILED
        )

        # Log the event
        await log_analytics_event_unified(
            analytics_store=bot.analytics_store,
            event_type=event_type,
            bot_id=bot.key.to_bot_id(),
            channel_id=input.governance_channel_id,
            metadata={
                "connection_name": connection_name,
                "connection_type": input.connection_type,
                "table_count": input.table_count,
                "organization_id": bot.bot_config.organization_id,
                "sync_duration_seconds": input.sync_duration_seconds,
                "pr_url": input.pr_url,
                "processed_datasets": input.processed_datasets,
                "failed_datasets": failed_datasets,
            },
            organization_name=bot.bot_config.organization_name,
            organization_id=bot.bot_config.organization_id,
            team_id=bot.key.team_id,
        )

        activity.logger.info("Analytics logged successfully")
        return LogAnalyticsOutput(success=True)

    @activity.defn(name="update_progress")
    async def update_progress(self, input: UpdateProgressInput) -> UpdateProgressOutput:
        """Update Slack message with dataset processing progress.

        Uses SlackstreamMessage to maintain identical output format to existing dataset processing.

        Args:
            input: UpdateProgressInput with progress updates

        Returns:
            UpdateProgressOutput with success status
        """
        bot_id = input.bot_id
        governance_channel_id = input.governance_channel_id
        message_ts = input.message_ts
        connection_name = input.connection_name
        progress_updates = input.progress_updates

        activity.logger.info(
            f"Updating progress for {len(progress_updates)} datasets. "
            f"Channel: {governance_channel_id}, Message TS: {message_ts}"
        )

        bot = await self._fetch_bot(bot_id)

        # Use same emoji mapping as existing dataset processor
        status_emojis = {
            DatasetProgressStatus.PROCESSING.value: "🔄",  # IN_PROGRESS
            DatasetProgressStatus.COMPLETED.value: "✅",  # COMPLETED
            DatasetProgressStatus.FAILED.value: "❌",  # FAILED
        }

        # Build dataset status lines matching existing format
        dataset_lines = []
        for progress in progress_updates:
            emoji = status_emojis.get(progress.status.value, "*️⃣")  # PENDING fallback
            dataset_lines.append(f"{emoji} `{progress.table_name}`")

        preamble = f"Processing datasets for connection `{connection_name}`"
        header_text = f"{preamble}:\n\n" + "\n".join(dataset_lines)

        activity.logger.info(f"Updating message with text: {header_text[:100]}...")

        # Build blocks with consistent formatting
        blocks = [
            SectionBlock(
                text=TextObject(
                    type=TextType.MRKDWN,
                    text=header_text,
                )
            )
        ]

        # Use SlackstreamMessage for consistent formatting
        # The throttler is running as a background task in the worker
        slack_message = SlackstreamMessage(
            bot.client,
            governance_channel_id,
            message_ts,
        )

        await slack_message.update(blocks=blocks)

        activity.logger.info("Progress updated successfully")
        return UpdateProgressOutput(success=True)

    @activity.defn(name=constants.Activity.SEND_SLACK_CONNECT_INVITE_ACTIVITY_NAME.value)
    async def send_slack_connect_invite(
        self, input: SendSlackConnectInviteInput
    ) -> SendSlackConnectInviteOutput:
        """Send Slack Connect invite to newly created channel after first dataset sync.

        This activity handles sending Slack Connect invites to users who were stored
        in pending_invites during the channel creation flow. It should only be called
        when this is the first dataset sync for the channel.

        Args:
            input: SendSlackConnectInviteInput with bot_id and governance_channel_id

        Returns:
            SendSlackConnectInviteOutput with success status and list of invited users
        """
        bot_id = input.bot_id
        governance_channel_id = input.governance_channel_id

        activity.logger.info("Processing Slack Connect invite after dataset sync")

        bot = await self._fetch_bot(bot_id)

        try:
            # Get the Q&A channel ID (not governance channel)
            qa_channel_id = await bot.kv_store.get_channel_id(bot.key.channel_name)
            if not qa_channel_id:
                activity.logger.error(f"Could not find Q&A channel ID for: {bot.key.channel_name}")
                return SendSlackConnectInviteOutput(success=False, invited_users=[])

            # Check for pending invite user ID (from channel creation via web UI or admin flow)
            pending_user_id = await bot.kv_store.get("pending_invites", "user_ids")
            if pending_user_id:
                activity.logger.info(
                    f"Found pending invite for user {pending_user_id} in channel {bot.key.channel_name}"
                )

            # Check for pending invite emails (from onboarding flow before user has Slack account)
            pending_email = await bot.kv_store.get("pending_invites", "emails")
            pending_emails = []
            if pending_email:
                activity.logger.info(
                    f"Found pending invite for email {pending_email} in channel {bot.key.channel_name}"
                )
                pending_emails.append(pending_email)

            # If no pending invites, this is not a first sync - return early
            if not pending_user_id and not pending_emails:
                activity.logger.info("No pending invites found, skipping Slack Connect invite")
                return SendSlackConnectInviteOutput(success=True, invited_users=[])

            # Pre-generate welcome message for the pending user before sending invite
            # Runs in the background to reduce latency
            if pending_user_id or pending_email:
                asyncio.create_task(
                    bot.pregenerate_and_store_welcome_message(pending_user_id, pending_email)
                )

            # Send Slack Connect invite for user ID
            from csbot.slackbot.slack_utils import (
                create_slack_connect_channel,
                send_slack_connect_invite_to_channel,
            )

            bot_server_config = self.bot_provider.get_config()

            connect_results = []
            user_invite_success = False
            invited_user_ids = []

            if pending_user_id:
                user_id_results = await send_slack_connect_invite_to_channel(
                    channel_id=qa_channel_id,
                    user_ids=[pending_user_id],
                    bot_server_config=bot_server_config,
                    logger=activity.logger,
                    channel_name=bot.key.channel_name,
                )
                connect_results.extend(user_id_results)

                if user_id_results and user_id_results[0]["success"]:
                    user_invite_success = True
                    invited_user_ids.append(pending_user_id)
                    activity.logger.info(
                        f"Successfully sent Slack Connect invite to Q&A channel for user {pending_user_id}"
                    )

            # Send Slack Connect invites for emails (onboarding flow)
            if pending_emails and bot_server_config.compass_dev_tools_bot_token:
                org_bot_token = bot_server_config.compass_dev_tools_bot_token.get_secret_value()
                email_result = await create_slack_connect_channel(
                    bot_token=org_bot_token,
                    channel=qa_channel_id,
                    emails=pending_emails,
                )
                # Wrap single result in list for consistent processing
                email_results = [email_result]
                connect_results.extend(email_results)

                if email_result["success"]:
                    activity.logger.info(
                        f"Successfully sent Slack Connect invite to Q&A channel for emails: {pending_emails}"
                    )

            if any(connect_result["success"] for connect_result in connect_results):
                activity.logger.info("Successfully sent Slack Connect invite to Q&A channel")

                # Clear pending invites after successful send
                if pending_user_id:
                    await bot.kv_store.delete("pending_invites", "user_ids")
                if pending_emails:
                    await bot.kv_store.delete("pending_invites", "emails")

                # Log coworker invited analytics event for successful user ID invitation
                # Note: We only log analytics for user_id invites, not email invites
                if user_invite_success and pending_user_id:
                    # Use unified logging to send COWORKER_INVITED to both systems
                    await log_analytics_event_unified(
                        analytics_store=bot.analytics_store,
                        event_type=AnalyticsEventType.COWORKER_INVITED,
                        bot_id=bot.key.to_bot_id(),
                        channel_id=qa_channel_id,
                        user_id=pending_user_id,
                        metadata={
                            "invite_type": "slack_connect_new_channel",
                            "organization_id": bot.bot_config.organization_id,
                            "governance_channel": governance_channel_id,
                            "channel_name": bot.key.channel_name,
                            "is_first_dataset_sync_for_channel": True,
                            "invite_method": "user_id",
                        },
                        # Enhanced context for Segment
                        organization_name=bot.bot_config.organization_name,
                        organization_id=bot.bot_config.organization_id,
                        team_id=bot.key.team_id,
                    )

                # Mark invite as sent to prevent duplicate invites
                invite_key = f"slack_connect_invite_sent_{bot.key.channel_name}"
                await bot.kv_store.set("invite_tracking", invite_key, "true")

                # Check for pending message stream to finish
                message_metadata_json = await bot.kv_store.get(
                    "pending_invites", "message_stream_metadata"
                )
                if message_metadata_json:
                    import json

                    from csbot.slackbot.slackbot_blockkit import SectionBlock, TextObject
                    from csbot.slackbot.slackbot_slackstream import SlackstreamMessage

                    try:
                        message_metadata = json.loads(message_metadata_json)
                        stream_channel_id = message_metadata["channel_id"]
                        message_ts = message_metadata["message_ts"]
                        user_id = message_metadata["user_id"]

                        # Reconstruct message stream
                        message_stream = SlackstreamMessage(
                            client=bot.client,
                            channel_id=stream_channel_id,
                            message_ts=message_ts,
                        )

                        # Update with final success message
                        final_blocks = [
                            SectionBlock(
                                text=TextObject.mrkdwn(
                                    f"<@{user_id}> created a new Compass channel <#{qa_channel_id}>"
                                )
                            )
                        ]
                        await message_stream.update(final_blocks)
                        await message_stream.finish()

                        activity.logger.info(
                            f"Finished pending message stream for channel {bot.key.channel_name}"
                        )

                        # Clear the stored message stream metadata
                        await bot.kv_store.delete("pending_invites", "message_stream_metadata")
                    except Exception as e:
                        activity.logger.error(
                            f"Failed to finish pending message stream: {e}", exc_info=True
                        )
                else:
                    # No pending message stream - post fresh notification that the channel is ready
                    if bot.client:
                        await bot.client.chat_postMessage(
                            channel=governance_channel_id,
                            text=f"Your new Compass channel <#{qa_channel_id}> is ready!",
                        )

                # Force refresh the local context store to ensure the datasets are available
                # immediately once the user joins the channel
                activity.logger.info(
                    "Force refreshing local context store to ensure new datasets are available immediately"
                )
                await asyncio.to_thread(bot.local_context_store.shared_repo.force_refresh)
                activity.logger.info("Local context store force refreshed")

                return SendSlackConnectInviteOutput(success=True, invited_users=invited_user_ids)
            else:
                activity.logger.error(
                    f"Failed to create Slack Connect invite for Q&A channel: {connect_results}"
                )
                return SendSlackConnectInviteOutput(success=False, invited_users=[])

        except Exception as e:
            activity.logger.error(
                f"Error sending Q&A channel Slack Connect invite: {e}", exc_info=True
            )
            return SendSlackConnectInviteOutput(success=False, invited_users=[])
