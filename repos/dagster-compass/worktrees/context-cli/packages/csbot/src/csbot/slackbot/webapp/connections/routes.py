import asyncio
from typing import TYPE_CHECKING

from aiohttp import web
from slack_sdk.errors import SlackApiError

from csbot.slackbot.admin_commands import AdminCommands
from csbot.slackbot.channel_bot.personalization import get_cached_user_info
from csbot.slackbot.datasets import get_connection_dataset_map
from csbot.slackbot.webapp.grants import Permission
from csbot.slackbot.webapp.security import (
    LegacyViewerContext,
    OrganizationContext,
    ViewerContext,
    find_bot_for_organization,
    find_governance_bot_for_organization,
    find_governance_bot_for_organization_with_connection,
    find_qa_bot_for_organization_with_connection,
    require_permission,
)
from csbot.temporal.client_wrapper import start_workflow_with_search_attributes

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


def add_connections_routes(app: web.Application, bot_server: "CompassBotServer"):
    """Add connections management routes to the webapp."""
    app.router.add_get("/api/connections/list", create_connections_list_handler(bot_server))
    app.router.add_get(
        "/api/connections/list_datasets", create_connections_list_datasets_handler(bot_server)
    )
    app.router.add_get(
        "/api/connections/tables",
        create_connection_tables_handler(bot_server),
    )
    app.router.add_post(
        "/api/connections/datasets/add",
        create_connection_add_datasets_handler(bot_server),
    )
    app.router.add_post(
        "/api/connections/datasets/remove",
        create_connection_remove_datasets_handler(bot_server),
    )


def create_connections_list_handler(bot_server: "CompassBotServer"):
    """Create connections list API handler (without datasets for fast page load)."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_CONNECTIONS,
    )
    async def connections_list_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle connections list API requests without datasets."""

        organization_id = organization_context.organization_id

        # Get connections with details (fast - from database only)
        connections = (
            await bot_server.bot_manager.storage.get_organization_connections_with_details(
                organization_id
            )
        )

        serialized_connections = []
        for connection in connections:
            connection_dict = connection.model_dump()
            # No datasets - will be fetched separately
            connection_dict["datasets"] = []
            serialized_connections.append(connection_dict)

        return web.json_response({"connections": serialized_connections})

    return connections_list_handler


def create_connections_list_datasets_handler(bot_server: "CompassBotServer"):
    """Create connections datasets list API handler (may be slow due to GitHub)."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_CONNECTIONS,
    )
    async def connections_list_datasets_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle connections datasets list API requests."""

        organization_id = organization_context.organization_id

        # Get connections with details
        connections = (
            await bot_server.bot_manager.storage.get_organization_connections_with_details(
                organization_id
            )
        )

        dataset_map: dict[str, list[str]] = {}
        bot = find_bot_for_organization(bot_server, organization_context)
        if bot:
            connection_names = {connection.connection_name for connection in connections}
            try:
                # Add timeout to prevent excessive GitHub API delays
                dataset_map = await asyncio.wait_for(
                    get_connection_dataset_map(bot, connection_names), timeout=10.0
                )
            except TimeoutError:
                bot_server.logger.warning(
                    "Timeout fetching dataset map for connections",
                    extra={"organization_id": organization_id},
                )
                # Return empty dataset map on timeout

        # Return map of connection_name -> datasets
        return web.json_response({"dataset_map": dataset_map})

    return connections_list_datasets_handler


def create_connection_tables_handler(bot_server: "CompassBotServer"):
    """Create handler to list available tables for a connection."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_CONNECTIONS,
    )
    async def connection_tables_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle connection tables list API requests."""
        connection_name = request.query.get("connection_name")
        bot_server.logger.info(
            "[Autocomplete] Received table list request",
            extra={
                "connection_name": connection_name,
                "organization_id": organization_context.organization_id,
            },
        )

        if not connection_name:
            bot_server.logger.warning("[Autocomplete] Missing connection_name parameter")
            return web.json_response({"error": "connection_name parameter required"}, status=400)

        organization_id = organization_context.organization_id

        # Verify connection exists for this organization
        bot_server.logger.info("[Autocomplete] Verifying connection exists for organization")
        connection_names = (
            await bot_server.bot_manager.storage.get_connection_names_for_organization(
                organization_id
            )
        )
        bot_server.logger.info(
            "[Autocomplete] Available connections",
            extra={"connection_names": connection_names, "organization_id": organization_id},
        )

        if connection_name not in connection_names:
            bot_server.logger.warning(
                "[Autocomplete] Connection not found",
                extra={"connection_name": connection_name, "available": connection_names},
            )
            return web.json_response({"error": "Connection not found"}, status=404)

        # Find a bot with this connection to get its configuration
        bot_server.logger.info("[Autocomplete] Finding governance bot for connection")
        governance_bot = find_governance_bot_for_organization_with_connection(
            bot_server, organization_context, connection_name
        )
        if not governance_bot:
            bot_server.logger.error(
                "[Autocomplete] No bot found with connection",
                extra={"connection_name": connection_name},
            )
            return web.json_response(
                {"error": f"No bot found with connection {connection_name}"}, status=500
            )

        bot_server.logger.info(
            "[Autocomplete] Found bot",
            extra={"bot_id": governance_bot.key.to_bot_id()},
        )

        # Get the connection profile from the bot's profile (not bot_config)
        if connection_name not in governance_bot.profile.connections:
            bot_server.logger.error(
                "[Autocomplete] Connection not in bot profile",
                extra={
                    "connection_name": connection_name,
                    "available_connections": list(governance_bot.profile.connections.keys()),
                },
            )
            return web.json_response(
                {"error": f"Connection {connection_name} not found in bot profile"},
                status=500,
            )

        connection_profile = governance_bot.profile.connections[connection_name]
        bot_server.logger.info(
            "[Autocomplete] Got connection profile",
            extra={"url_prefix": connection_profile.url[:50]},
        )

        # Check if connection URL is in jsonconfig format (required for table listing)
        if not connection_profile.url.startswith("jsonconfig:"):
            bot_server.logger.warning(
                "[Autocomplete] Connection URL not in jsonconfig format - cannot list tables",
                extra={
                    "connection_name": connection_name,
                    "url_prefix": connection_profile.url[:20],
                },
            )
            return web.json_response(
                {
                    "success": False,
                    "error": "Table listing not supported for this connection type",
                    "tables": [],
                },
                status=400,
            )

        # Parse the connection URL to get warehouse config
        from csbot.slackbot.webapp.add_connections.models import (
            JsonConfig,
            compass_warehouse_config_from_json_config,
        )
        from csbot.slackbot.webapp.add_connections.routes.warehouse_factory import (
            list_tables,
        )

        try:
            bot_server.logger.info("[Autocomplete] Parsing connection URL")
            json_config = JsonConfig.from_url(connection_profile.url)
            warehouse_config = compass_warehouse_config_from_json_config(json_config)
            bot_server.logger.info(
                "[Autocomplete] Warehouse config created",
                extra={"warehouse_type": type(warehouse_config).__name__},
            )

            # Use shared list_tables function - skip AI recommendations for autocomplete performance
            bot_server.logger.info("[Autocomplete] Calling list_tables")
            result = await list_tables(
                bot_server=bot_server,
                warehouse_config=warehouse_config,
                selected_schemas=None,
                include_ai_recommendations=False,
            )

            bot_server.logger.info(
                "[Autocomplete] list_tables completed",
                extra={
                    "success": result["success"],
                    "table_count": len(result["tables"]),
                },
            )

            # For autocomplete, we don't need the recommended flag - just return simple list
            tables = [
                {"name": t["name"], "description": t["description"]} for t in result["tables"]
            ]

            return web.json_response({"success": True, "tables": tables})

        except Exception as e:
            bot_server.logger.error(
                f"[Autocomplete] Failed to list tables for connection {connection_name}: {e}",
                exc_info=True,
            )
            return web.json_response(
                {"success": False, "error": f"Failed to list tables: {str(e)}"}, status=500
            )

    return connection_tables_handler


async def _resolve_slack_user_name(
    bot_server: "CompassBotServer", bot: "CompassChannelBaseBotInstance", user_id: str
) -> str:
    """Fetch a readable Slack user name for attribution, falling back to user ID."""
    if not hasattr(bot, "client") or not hasattr(bot, "kv_store"):
        return user_id

    try:
        user_info = await get_cached_user_info(bot.client, bot.kv_store, user_id)
    except SlackApiError as error:
        bot_server.logger.warning(
            "Failed to resolve Slack user name", extra={"user_id": user_id, "error": str(error)}
        )
        return user_id

    if user_info and user_info.real_name:
        return user_info.real_name

    return user_id


def create_connection_add_datasets_handler(bot_server: "CompassBotServer"):
    """Create handler for starting dataset additions from the web UI."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CONNECTIONS,
    )
    async def add_datasets_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        payload = await request.json()
        connection_name = payload.get("connection_name")
        datasets_raw = payload.get("datasets")

        if not isinstance(connection_name, str) or len(connection_name.strip()) == 0:
            return web.json_response({"error": "connection_name is required"}, status=400)

        if not isinstance(datasets_raw, list):
            return web.json_response({"error": "datasets must be a list"}, status=400)

        datasets: list[str] = []
        for entry in datasets_raw:
            if not isinstance(entry, str):
                return web.json_response({"error": "datasets must be strings"}, status=400)
            dataset_name = entry.strip()
            if len(dataset_name) == 0:
                continue
            datasets.append(dataset_name)

        if len(datasets) == 0:
            return web.json_response({"error": "At least one dataset is required"}, status=400)

        storage = bot_server.bot_manager.storage
        connection_names = await storage.get_connection_names_for_organization(
            organization_context.organization_id
        )
        if connection_name not in connection_names:
            return web.json_response({"error": "Connection not found"}, status=404)

        # Find the data channel bot that has the connection (needed for database access)
        data_bot = find_qa_bot_for_organization_with_connection(
            bot_server, organization_context, connection_name
        )
        if not data_bot:
            return web.json_response(
                {"error": f"No bot found with connection {connection_name}"}, status=500
            )

        # Find governance bot for notification channel
        governance_bot = find_governance_bot_for_organization(bot_server, organization_context)
        if not governance_bot:
            return web.json_response(
                {"error": "No governance bot found for notifications"}, status=500
            )

        if isinstance(organization_context, ViewerContext):
            user_id = organization_context.org_user.slack_user_id
        elif isinstance(organization_context, LegacyViewerContext):
            user_id = organization_context.slack_user_id
        else:
            user_id = None

        if not user_id:
            return web.json_response({"error": "Unauthorized"}, status=401)

        governance_channel_id = await governance_bot.kv_store.get_channel_id(
            governance_bot.governance_alerts_channel
        )
        if not governance_channel_id:
            return web.json_response({"error": "Governance channel not configured"}, status=500)

        # Start dataset sync via Temporal workflow (similar to add_connection flow)
        import time

        from csbot.temporal.constants import DEFAULT_TASK_QUEUE, Workflow
        from csbot.temporal.dataset_sync.workflow import DatasetSyncWorkflowInput

        workflow_id = (
            f"dataset-sync-{data_bot.key.to_bot_id()}-{connection_name}-{int(time.time())}"
        )

        bot_server.logger.info(
            f"Starting Temporal workflow for dataset addition: {workflow_id}",
            extra={
                "connection_name": connection_name,
                "dataset_count": len(datasets),
                "user_id": user_id,
            },
        )

        # Start workflow asynchronously - don't wait for completion
        asyncio.create_task(
            start_workflow_with_search_attributes(
                bot_server.temporal_client,
                bot_server.config.temporal,
                Workflow.DATASET_SYNC_WORKFLOW_NAME.value,
                DatasetSyncWorkflowInput(
                    bot_id=data_bot.key.to_bot_id(),
                    connection_name=connection_name,
                    table_names=datasets,
                    governance_channel_id=governance_channel_id,
                    connection_type="connection",
                ),
                id=workflow_id,
                task_queue=DEFAULT_TASK_QUEUE,
                organization_name=data_bot.bot_config.organization_name,
            )
        )

        return web.json_response({"status": "processing", "workflow_id": workflow_id})

    return add_datasets_handler


def create_connection_remove_datasets_handler(bot_server: "CompassBotServer"):
    """Create handler for dataset removal requests from the web UI."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CONNECTIONS,
    )
    async def remove_datasets_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        payload = await request.json()
        connection_name = payload.get("connection_name")
        datasets_raw = payload.get("datasets")

        if not isinstance(connection_name, str) or len(connection_name.strip()) == 0:
            return web.json_response({"error": "connection_name is required"}, status=400)

        if not isinstance(datasets_raw, list):
            return web.json_response({"error": "datasets must be a list"}, status=400)

        datasets: list[str] = []
        for entry in datasets_raw:
            if not isinstance(entry, str):
                return web.json_response({"error": "datasets must be strings"}, status=400)
            dataset_name = entry.strip()
            if len(dataset_name) == 0:
                continue
            datasets.append(dataset_name)

        if len(datasets) == 0:
            return web.json_response({"error": "At least one dataset is required"}, status=400)

        # Find the data channel bot that has the connection (needed to list datasets)
        data_bot = find_qa_bot_for_organization_with_connection(
            bot_server, organization_context, connection_name
        )
        if not data_bot:
            return web.json_response(
                {"error": f"No bot found with connection {connection_name}"}, status=500
            )

        # Find governance bot for notifications
        governance_bot = find_governance_bot_for_organization(bot_server, organization_context)
        if not governance_bot:
            return web.json_response(
                {"error": "No governance bot found for notifications"}, status=500
            )

        dataset_map = await get_connection_dataset_map(data_bot, {connection_name})
        available_datasets = dataset_map.get(connection_name)
        if not available_datasets:
            return web.json_response(
                {"error": "No datasets available for this connection"}, status=400
            )

        missing_datasets = [dataset for dataset in datasets if dataset not in available_datasets]
        if len(missing_datasets) > 0:
            return web.json_response(
                {"error": f"Datasets not found: {', '.join(missing_datasets)}"}, status=400
            )

        if isinstance(organization_context, ViewerContext):
            user_id = organization_context.org_user.slack_user_id
        elif isinstance(organization_context, LegacyViewerContext):
            user_id = organization_context.slack_user_id
        else:
            user_id = None

        if not user_id:
            return web.json_response({"error": "Unauthorized"}, status=401)

        user_name = await _resolve_slack_user_name(bot_server, governance_bot, user_id)

        governance_channel_id = await governance_bot.kv_store.get_channel_id(
            governance_bot.governance_alerts_channel
        )
        if not governance_channel_id:
            return web.json_response({"error": "Governance channel not configured"}, status=500)

        admin_commands = AdminCommands(governance_bot, bot_server)
        preamble = f"🗑️ Removing datasets: <@{user_id}> is removing dataset documentation"

        asyncio.create_task(
            admin_commands._process_remove_datasets(
                connection=connection_name,
                datasets=datasets,
                user_name=user_name,
                governance_channel_id=governance_channel_id,
                preamble=preamble,
            )
        )

        return web.json_response({"status": "processing"})

    return remove_datasets_handler
