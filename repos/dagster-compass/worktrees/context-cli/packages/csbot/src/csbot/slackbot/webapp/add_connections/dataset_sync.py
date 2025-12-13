"""
Shared dataset sync functionality for connection routes.

This module provides the common dataset sync functionality used after adding
new connections to automatically analyze and document table schemas via Temporal workflow.
"""

import asyncio
import time
from typing import TYPE_CHECKING

from aiohttp import web
from ddtrace.trace import tracer
from temporalio.client import WorkflowExecutionStatus, WorkflowFailureError

from csbot.slackbot.channel_bot.personalization import get_cached_user_info
from csbot.slackbot.webapp.api_types import error_response
from csbot.slackbot.webapp.security import ensure_token_is_valid
from csbot.temporal.client_wrapper import start_workflow_with_search_attributes
from csbot.temporal.constants import DEFAULT_TASK_QUEUE, Workflow
from csbot.temporal.dataset_sync.activity import DatasetProgressStatus
from csbot.temporal.dataset_sync.workflow import DatasetSyncWorkflowInput
from csbot.utils.tracing import try_set_root_tags, try_set_tag


def sanitize_connection_name(connection_name: str) -> str:
    """Sanitize connection name to prevent injection attacks.

    Removes any characters that are not alphanumeric, underscores, hyphens, or dots.
    This matches common database connection naming patterns.

    Args:
        connection_name: Connection name to sanitize

    Returns:
        Sanitized connection name with only safe characters
    """
    import re

    # Remove any characters that are not alphanumeric, underscore, hyphen, or dot
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "", connection_name)


if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassBotServer, CompassChannelBaseBotInstance

# Short delay to accommodate bot instance reload
SLEEP_TIME = 1


async def sleep_until_ready():
    await asyncio.sleep(SLEEP_TIME)


DATASET_SYNC_BATCH_SIZE = 8


@tracer.wrap()
async def sync_datasets_after_connection(
    bot_key,
    bot_server: "CompassBotServer",
    connection_name: str,
    table_names: list[str],
    logger,
    connection_type: str = "connection",
):
    try_set_tag("connection", connection_name)
    for i in range(0, len(table_names), DATASET_SYNC_BATCH_SIZE):
        await sync_datasets_after_connection_partial(
            bot_key,
            bot_server,
            connection_name,
            table_names[i : i + DATASET_SYNC_BATCH_SIZE],
            logger,
            connection_type,
        )


@tracer.wrap()
async def sync_datasets_after_connection_partial(
    bot_key,
    bot_server: "CompassBotServer",
    connection_name: str,
    table_names: list[str],
    logger,
    connection_type: str = "connection",
):
    """Trigger dataset sync for tables added during connection setup, similar to admin command."""

    try:
        bot = bot_server.bots.get(bot_key)
        if not bot:
            logger.error(f"Bot instance not found for key: {bot_key}")
            return

        try_set_root_tags(
            {
                "channel": bot.bot_config.channel_name,
                "organization": bot.bot_config.organization_name,
            }
        )

        assert bot is not None
        governance_channel_id = None
        if bot.governance_alerts_channel:
            governance_channel_id = await bot.kv_store.get_channel_id(bot.governance_alerts_channel)

        if not governance_channel_id:
            logger.error(
                f"Could not find governance channel ID for: {bot.governance_alerts_channel}"
            )
            return

        # Wait for bot instance to be restarted after connection addition
        logger.info(
            f"Waiting {SLEEP_TIME} seconds before syncing datasets for connection {connection_name}"
        )
        await sleep_until_ready()

        # Get the fresh bot instance after the delay
        bot = bot_server.bots.get(bot_key)
        if not bot:
            logger.error(f"Bot instance not found after {SLEEP_TIME}s delay for key: {bot_key}")
            return
        assert bot is not None

        # Execute dataset sync via Temporal workflow
        workflow_id = f"dataset-sync-{bot.key.to_bot_id()}-{connection_name}-{int(time.time())}"

        logger.info(f"Starting Temporal workflow for dataset sync: {workflow_id}")

        await start_workflow_with_search_attributes(
            bot_server.temporal_client,
            bot_server.config.temporal,
            Workflow.DATASET_SYNC_WORKFLOW_NAME.value,
            DatasetSyncWorkflowInput(
                bot_id=bot.key.to_bot_id(),
                connection_name=connection_name,
                table_names=table_names,
                governance_channel_id=governance_channel_id,
                connection_type=connection_type,
            ),
            id=workflow_id,
            task_queue=DEFAULT_TASK_QUEUE,
            organization_name=bot.bot_config.organization_name,
        )

    except Exception as e:
        logger.error(f"Error syncing datasets after connection setup: {e}", exc_info=True)


@tracer.wrap()
async def send_pending_slack_connect_invite(
    bot_server: "CompassBotServer",
    bot: "CompassChannelBaseBotInstance",
    logger,
):
    """Send Slack Connect invite to newly created channel.

    This function is used for cases where there is no dataset sync workflow
    (e.g., empty channels, prospector setup). For dataset sync workflows,
    the invite is sent automatically by the Temporal workflow activity.

    This applies to both first-time onboarding channels and subsequent new channels
    created by users. The invite is sent only after data processing is complete.
    """
    from csbot.slackbot.slackbot_analytics import AnalyticsEventType, log_analytics_event_unified

    try:
        # Get the Q&A channel ID (not governance channel)
        qa_channel_id = await bot.kv_store.get_channel_id(bot.key.channel_name)
        if not qa_channel_id:
            raise ValueError(f"Could not find Q&A channel ID for: {bot.key.channel_name}")

        governance_channel_id = await bot.kv_store.get_channel_id(bot.governance_alerts_channel)
        if not governance_channel_id:
            logger.error(
                f"Could not find governance channel ID for: {bot.governance_alerts_channel}"
            )
            return

        # Only invite the single user who is explicitly stored in pending_invites
        # This ensures we invite only the initiator of the channel creation, not all governance members

        # Check for pending invite user ID (from channel creation via web UI or admin flow)
        pending_user_id = await bot.kv_store.get("pending_invites", "user_ids")
        if pending_user_id:
            logger.info(
                f"Found pending invite for user {pending_user_id} in channel {bot.key.channel_name}"
            )

        # Check for pending invite emails (from onboarding flow before user has Slack account)
        pending_email = await bot.kv_store.get("pending_invites", "emails")
        pending_emails = []
        if pending_email:
            logger.info(
                f"Found pending invite for email {pending_email} in channel {bot.key.channel_name}"
            )
            pending_emails.append(pending_email)

        # If no pending invites, return early
        if not pending_user_id and not pending_emails:
            logger.info("No pending invites found, skipping Slack Connect invite")
            return

        # Pre-generate welcome message for the pending user before sending invite... should reduce
        # the latency of generating the ephemeral welcome message.  Runs in the background...
        # can switch to blocking if we decide the setup latency is worth it
        if pending_user_id or pending_email:
            asyncio.create_task(
                bot.pregenerate_and_store_welcome_message(pending_user_id, pending_email)
            )

        # Send Slack Connect invite for user ID
        from csbot.slackbot.slack_utils import (
            create_slack_connect_channel,
            send_slack_connect_invite_to_channel,
        )

        connect_results = []
        user_invite_success = False
        if pending_user_id:
            user_id_results = await send_slack_connect_invite_to_channel(
                channel_id=qa_channel_id,
                user_ids=[pending_user_id],
                bot_server_config=bot_server.config,
                logger=logger,
                channel_name=bot.key.channel_name,
            )
            connect_results.extend(user_id_results)

            if user_id_results and user_id_results[0]["success"]:
                user_invite_success = True
                logger.info(
                    f"Successfully sent Slack Connect invite to Q&A channel for user {pending_user_id}"
                )

        # Send Slack Connect invites for emails (onboarding flow)
        if pending_emails and bot_server.config.compass_dev_tools_bot_token:
            org_bot_token = bot_server.config.compass_dev_tools_bot_token.get_secret_value()
            email_result = await create_slack_connect_channel(
                bot_token=org_bot_token,
                channel=qa_channel_id,
                emails=pending_emails,
            )
            # Wrap single result in list for consistent processing
            email_results = [email_result]
            connect_results.extend(email_results)

            if email_result["success"]:
                logger.info(
                    f"Successfully sent Slack Connect invite to Q&A channel for emails: {pending_emails}"
                )

        if any(connect_result["success"] for connect_result in connect_results):
            logger.info("Successfully sent Slack Connect invite to Q&A channel")

            # Clear pending invites after successful send
            if pending_user_id:
                await bot.kv_store.delete("pending_invites", "user_ids")
            if pending_emails:
                await bot.kv_store.delete("pending_invites", "emails")

            # Mark onboarding step: SLACK_CONNECT_SENT (but NOT COMPLETED - waiting for user to join)
            from csbot.slackbot.slack_utils import _mark_onboarding_step_if_exists

            await _mark_onboarding_step_if_exists(
                bot_server.bot_manager.storage,
                bot.bot_config.organization_id,
                "SLACK_CONNECT_SENT",
                logger,
            )

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
                        "is_first_dataset_sync_for_channel": False,  # Not via workflow
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

                    logger.info(
                        f"Finished pending message stream for channel {bot.key.channel_name}"
                    )

                    # Clear the stored message stream metadata
                    await bot.kv_store.delete("pending_invites", "message_stream_metadata")
                except Exception as e:
                    logger.error(f"Failed to finish pending message stream: {e}", exc_info=True)
            else:
                # No pending message stream - post fresh notification that the channel is ready
                if bot.client:
                    await bot.client.chat_postMessage(
                        channel=governance_channel_id,
                        text=f"Your new Compass channel <#{qa_channel_id}> is ready!",
                    )

            # Force refresh the local context store to ensure the datasets are available
            # immediately once the user joins the channel
            logger.info(
                "Force refreshing local context store to ensure new datasets are available immediately"
            )
            await asyncio.to_thread(bot.local_context_store.shared_repo.force_refresh)
            logger.info("Local context store force refreshed")
        else:
            logger.error(
                f"Failed to create Slack Connect invite for Q&A channel: {connect_results}"
            )
    except Exception as e:
        logger.error(f"Error sending Q&A channel Slack Connect invite: {e}", exc_info=True)


async def get_channel_user_ids(
    bot: "CompassChannelBaseBotInstance", channel_id: str, logger, bot_server: "CompassBotServer"
) -> list[str]:
    """Get user IDs of users in the channel, excluding bots."""
    try:
        if not bot.client:
            logger.error("Bot client not available to query channel members")
            return []

        # Get channel members
        response = await bot.client.conversations_members(channel=channel_id)
        member_ids = response.get("members", [])

        # Fetch user info in parallel using cached calls to check validity and filter bots
        user_infos = [
            get_cached_user_info(bot.client, bot.kv_store, user_id) for user_id in member_ids
        ]
        user_datas = await asyncio.gather(*user_infos)

        # Keep only valid user IDs (where user info was successfully retrieved and not a bot)
        valid_user_ids = [
            user_id
            for user_id, data in zip(member_ids, user_datas)
            if data is not None and not data.is_bot
        ]

        return valid_user_ids

    except Exception as e:
        logger.error(f"Error getting channel user IDs: {e}", exc_info=True)
        return []


def add_dataset_sync_routes(app: web.Application, bot_server: "CompassBotServer"):
    """Register dataset sync status endpoints."""

    async def handle_dataset_sync_status(request: web.Request) -> web.Response:
        """Get overall status of dataset sync for a connection.

        Query parameters:
        - connection_name: Name of the connection (required)

        Returns JSON with:
        - status: "in_progress" | "completed" | "failed" | "not_found"
        - connection_name: The connection name queried
        - workflow_id: The Temporal workflow ID (if found)
        """
        from csbot.slackbot.webapp.add_connections.routes.shared import get_unauthorized_message

        try:
            connection_name = request.query.get("connection_name")
            if not connection_name:
                return web.json_response(error_response("Missing connection_name"), status=400)

            # Sanitize connection name to prevent injection attacks
            connection_name = sanitize_connection_name(connection_name)
            if not connection_name:
                return web.json_response(error_response("Invalid connection_name"), status=400)

            # Validate JWT token
            org_context = await ensure_token_is_valid(
                bot_server, get_unauthorized_message, request, require_user=False
            )

            # Find the most recent workflow for this connection
            # Workflow ID format: dataset-sync-{bot_id}-{connection_name}-{timestamp}
            # We need to query Temporal to find workflows matching this pattern
            bot_id_prefix = f"{org_context.team_id}-"  # Bot IDs start with team_id

            try:
                workflows = []
                async for workflow in bot_server.temporal_client.list_workflows(
                    query=f'WorkflowId STARTS_WITH "dataset-sync-{bot_id_prefix}"'
                ):
                    if connection_name in workflow.id:
                        workflows.append(workflow)

                if not workflows:
                    return web.json_response(
                        {
                            "status": "not_found",
                            "connection_name": connection_name,
                            "message": "No dataset sync workflow found for this connection",
                        }
                    )

                # Get the most recent workflow
                latest_workflow = max(workflows, key=lambda w: w.start_time)
                workflow_id = latest_workflow.id

                # Get workflow status
                workflow_handle = bot_server.temporal_client.get_workflow_handle(workflow_id)

                # Check if workflow is still running
                workflow_status = (await workflow_handle.describe()).status

                if workflow_status == WorkflowExecutionStatus.RUNNING:
                    status = "in_progress"
                elif workflow_status == WorkflowExecutionStatus.COMPLETED:
                    status = "completed"
                elif workflow_status in (
                    WorkflowExecutionStatus.FAILED,
                    WorkflowExecutionStatus.TERMINATED,
                    WorkflowExecutionStatus.CANCELED,
                    WorkflowExecutionStatus.TIMED_OUT,
                ):
                    status = "failed"
                else:
                    status = "unknown"

                return web.json_response(
                    {
                        "status": status,
                        "connection_name": connection_name,
                        "workflow_id": workflow_id,
                    }
                )

            except Exception as e:
                bot_server.logger.error(f"Error querying workflow status: {e}", exc_info=True)
                return web.json_response(
                    error_response("Failed to query workflow status"), status=500
                )

        except web.HTTPError:
            raise
        except Exception as e:
            bot_server.logger.error(f"Error in dataset sync status endpoint: {e}", exc_info=True)
            return web.json_response(error_response("An error occurred"), status=500)

    async def handle_dataset_sync_details(request: web.Request) -> web.Response:
        """Get detailed per-dataset status for a connection sync workflow.

        Query parameters:
        - connection_name: Name of the connection (required)

        Returns JSON with:
        - workflow_id: The Temporal workflow ID
        - connection_name: The connection name
        - status: Overall workflow status
        - datasets: Array of dataset statuses with:
          - table_name: Dataset/table name
          - status: "not_started" | "processing" | "completed" | "failed"
          - message: Optional status message
        - pr_url: Pull request URL (if completed)
        """
        from csbot.slackbot.webapp.add_connections.routes.shared import get_unauthorized_message

        try:
            connection_name = request.query.get("connection_name")
            if not connection_name:
                return web.json_response(error_response("Missing connection_name"), status=400)

            # Sanitize connection name to prevent injection attacks
            connection_name = sanitize_connection_name(connection_name)
            if not connection_name:
                return web.json_response(error_response("Invalid connection_name"), status=400)

            # Validate JWT token
            org_context = await ensure_token_is_valid(
                bot_server, get_unauthorized_message, request, require_user=False
            )

            # Find the most recent workflow for this connection
            bot_id_prefix = f"{org_context.team_id}-"

            workflow_id: str | None = None
            try:
                workflows = []
                async for workflow in bot_server.temporal_client.list_workflows(
                    query=f'WorkflowId STARTS_WITH "dataset-sync-{bot_id_prefix}"'
                ):
                    if connection_name in workflow.id:
                        workflows.append(workflow)

                if not workflows:
                    return web.json_response(
                        error_response("No dataset sync workflow found for this connection"),
                        status=404,
                    )

                # Get the most recent workflow
                latest_workflow = max(workflows, key=lambda w: w.start_time)
                workflow_id = latest_workflow.id

                assert workflow_id is not None

                # Get workflow handle and query details
                workflow_handle = bot_server.temporal_client.get_workflow_handle(workflow_id)
                workflow_desc = await workflow_handle.describe()

                # Query workflow state to get dataset progress
                dataset_statuses: list[dict] = []
                pr_url = None

                if workflow_desc.status == WorkflowExecutionStatus.COMPLETED:
                    # For completed workflows, get the final result
                    result_raw = await workflow_handle.result(follow_runs=True)

                    # Temporal returns the result as a dict, not as the Pydantic model
                    if isinstance(result_raw, dict):
                        result_dict = result_raw
                    else:
                        # If it's a Pydantic model, convert to dict
                        result_dict = result_raw.model_dump()

                    pr_url = result_dict.get("pr_url")
                    processed_datasets = result_dict.get("processed_datasets", [])
                    failed_datasets = result_dict.get("failed_datasets", [])

                    # Build dataset statuses from completed result
                    for table_name in processed_datasets:
                        dataset_statuses.append(
                            {
                                "table_name": table_name,
                                "status": DatasetProgressStatus.COMPLETED.value,
                                "message": "Successfully processed",
                            }
                        )

                    for table_name in failed_datasets:
                        dataset_statuses.append(
                            {
                                "table_name": table_name,
                                "status": DatasetProgressStatus.FAILED.value,
                                "message": "Processing failed",
                            }
                        )
                elif workflow_desc.status == WorkflowExecutionStatus.RUNNING:
                    # For running workflows, query the workflow state to get real-time progress
                    progress_list = await workflow_handle.query("get_dataset_progress")

                    # Convert DatasetProgress objects to dicts for JSON response
                    for progress_item in progress_list:
                        if isinstance(progress_item, dict):
                            dataset_statuses.append(
                                {
                                    "table_name": progress_item.get("table_name", ""),
                                    "status": progress_item.get("status", "processing"),
                                    "message": progress_item.get("message", ""),
                                }
                            )
                        else:
                            # If it's a Pydantic model
                            dataset_statuses.append(
                                {
                                    "table_name": progress_item.table_name,
                                    "status": progress_item.status.value
                                    if hasattr(progress_item.status, "value")
                                    else str(progress_item.status),
                                    "message": progress_item.message or "",
                                }
                            )

                # Determine overall status
                if workflow_desc.status == WorkflowExecutionStatus.RUNNING:
                    overall_status = "in_progress"
                elif workflow_desc.status == WorkflowExecutionStatus.COMPLETED:
                    overall_status = "completed"
                elif workflow_desc.status in (
                    WorkflowExecutionStatus.FAILED,
                    WorkflowExecutionStatus.TERMINATED,
                    WorkflowExecutionStatus.CANCELED,
                    WorkflowExecutionStatus.TIMED_OUT,
                ):
                    overall_status = "failed"
                else:
                    overall_status = "unknown"

                response_data = {
                    "workflow_id": workflow_id,
                    "connection_name": connection_name,
                    "status": overall_status,
                    "datasets": dataset_statuses,
                }

                if pr_url:
                    response_data["pr_url"] = pr_url

                return web.json_response(response_data)

            except WorkflowFailureError as e:
                bot_server.logger.error(f"Workflow execution failed: {e}", exc_info=True)
                return web.json_response(
                    {
                        "workflow_id": workflow_id,
                        "connection_name": connection_name,
                        "status": "failed",
                        "error": str(e),
                        "datasets": [],
                    }
                )
            except Exception as e:
                bot_server.logger.error(f"Error querying workflow details: {e}", exc_info=True)
                return web.json_response(
                    error_response("Failed to query workflow details"), status=500
                )

        except web.HTTPError:
            raise
        except Exception as e:
            bot_server.logger.error(f"Error in dataset sync details endpoint: {e}", exc_info=True)
            return web.json_response(error_response("An error occurred"), status=500)

    # Register routes
    app.router.add_get("/api/dataset-sync/status", handle_dataset_sync_status)
    app.router.add_get("/api/dataset-sync/details", handle_dataset_sync_details)
