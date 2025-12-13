import json
from typing import TYPE_CHECKING

import jwt
from aiohttp import web

from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.slack_utils import generate_urlsafe_team_name
from csbot.slackbot.webapp.add_connections.routes.athena import add_onboarding_athena_routes
from csbot.slackbot.webapp.add_connections.routes.bigquery import add_onboarding_bigquery_routes
from csbot.slackbot.webapp.add_connections.routes.databricks import (
    add_onboarding_databricks_routes,
)
from csbot.slackbot.webapp.add_connections.routes.motherduck import add_onboarding_motherduck_routes
from csbot.slackbot.webapp.add_connections.routes.postgres import add_onboarding_postgres_routes
from csbot.slackbot.webapp.add_connections.routes.redshift import add_onboarding_redshift_routes
from csbot.slackbot.webapp.add_connections.routes.snowflake import add_onboarding_snowflake_routes
from csbot.slackbot.webapp.grants import Permission
from csbot.slackbot.webapp.onboarding.utils import is_token_valid
from csbot.slackbot.webapp.referral.referral import REFERRAL_TOKEN_COOKIE_NAME
from csbot.slackbot.webapp.security import (
    LegacyViewerContext,
    OnboardingViewerContext,
    OrganizationContext,
    ViewerContext,
    require_permission,
)

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


def add_onboarding_connections_routes(app: web.Application, bot_server: "CompassBotServer"):
    async def _validate_request_payload(
        request: web.Request, bot_server: "CompassBotServer"
    ) -> tuple[str, dict, str]:
        """Validate and extract connection name, channel selection, and connection token from request."""
        try:
            request_body = await request.json()
        except json.JSONDecodeError as e:
            bot_server.logger.error(f"JSON decode error in request body: {e}", exc_info=True)
            raise web.HTTPBadRequest(text="Invalid JSON in request body")

        connection_name = request_body.get("connection_name")
        if not connection_name:
            raise web.HTTPBadRequest(text="Missing required field: connection_name")

        connection_token = request_body.get("connection_token")
        if not connection_token:
            raise web.HTTPBadRequest(text="Missing required field: connection_token")

        channel_selection = request_body.get("channelSelection")
        if not channel_selection:
            raise web.HTTPBadRequest(text="Missing required field: channelSelection")

        selection_type = channel_selection.get("type")
        if not selection_type:
            raise web.HTTPBadRequest(text="Missing required field: channelSelection.type")

        selected_channels = channel_selection.get("channels")
        if not selected_channels:
            raise web.HTTPBadRequest(text="Missing required field: channelSelection.channels")

        return connection_name, channel_selection, connection_token

    def _count_organization_channels(
        organization_id: int,
        team_id: str,
        bot_server: "CompassBotServer",
    ) -> int:
        """Count data channels for an organization.

        Returns the number of QA and Combined bot instances (data channels)
        for the given organization, excluding Governance-only bots.
        """
        from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeQA

        count = 0
        for bot_instance in bot_server.bots.values():
            if (
                bot_instance.bot_config.organization_id == organization_id
                and bot_instance.bot_config.team_id == team_id
            ):
                if isinstance(bot_instance.bot_type, (BotTypeQA, BotTypeCombined)):
                    count += 1

        return count

    async def _get_governance_bot_for_organization(
        organization_id: int,
        team_id: str,
        bot_server: "CompassBotServer",
    ) -> "CompassChannelBaseBotInstance":
        """Find and validate the governance bot for an organization.

        Searches all active bot instances to find a governance bot matching
        the organization_id and team_id.
        """
        from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeGovernance

        # Search for governance bot matching organization + team
        for bot_key, bot_instance in bot_server.bots.items():
            if (
                bot_instance.bot_config.organization_id == organization_id
                and bot_instance.bot_config.team_id == team_id
            ):
                # Check if it's a governance bot
                if isinstance(bot_instance.bot_type, BotTypeGovernance | BotTypeCombined):
                    bot_server.logger.info(
                        f"Found governance bot for organization {organization_id}: {bot_key}"
                    )
                    return bot_instance

        # No governance bot found - this is expected during onboarding before first connection
        bot_server.logger.warning(
            f"No governance bot found for organization {organization_id}, team {team_id}"
        )
        raise web.HTTPNotFound(
            text=(
                "No governance workspace found for your organization. "
                "This will be created after your first connection."
            )
        )

    async def _get_slack_tokens(bot_server: "CompassBotServer") -> tuple[str, str, str]:
        """Extract and validate required Slack tokens."""
        config = bot_server.config

        # Check token availability
        if not config.compass_dev_tools_bot_token:
            raise web.HTTPBadRequest(text="No dev tools bot token available")
        if not config.slack_admin_token:
            raise web.HTTPBadRequest(text="No admin token available for channel creation")
        if not config.compass_bot_token:
            raise web.HTTPBadRequest(text="No compass bot token available")

        # Extract actual token values
        dev_tools_token = config.compass_dev_tools_bot_token.get_secret_value()
        admin_token = config.slack_admin_token.get_secret_value()
        compass_token = config.compass_bot_token.get_secret_value()

        # Validate tokens are not empty
        if not dev_tools_token:
            raise web.HTTPBadRequest(text="Dev tools bot token is empty")
        if not admin_token:
            raise web.HTTPBadRequest(text="Admin token is empty")
        if not compass_token:
            raise web.HTTPBadRequest(text="Compass bot token is empty")

        return dev_tools_token, admin_token, compass_token

    async def _handle_create_channel(
        new_channel_name: str,
        context: OrganizationContext,
        bot_server: "CompassBotServer",
        token: str | None,
        has_valid_token: bool,
        is_first_connection: bool = False,
    ) -> dict:
        """Handle creating a new channel with associated bot.

        Returns dict with creation result (not web.Response).
        """
        if not new_channel_name:
            return {"success": False, "error": "Channel name cannot be empty"}

        # Get governance bot for organization (needed for plan limits check)
        # For first connection, no governance bot exists yet, so we skip this
        governance_bot = None
        if not is_first_connection:
            governance_bot = await _get_governance_bot_for_organization(
                context.organization_id, context.team_id, bot_server
            )

            # Check plan limits before creating channel
            plan_limits = await bot_server.get_plan_limits_from_cache_or_bail(
                context.organization_id
            )

            if plan_limits:
                # Count current channels for this organization
                current_channel_count = _count_organization_channels(
                    context.organization_id, context.team_id, bot_server
                )

                # Check if we can create more channels
                can_create = (
                    current_channel_count < plan_limits.num_channels
                    or plan_limits.allow_additional_channels
                )

                if not can_create:
                    return {
                        "success": False,
                        "error": f"Cannot create new channel: at plan limit of {plan_limits.num_channels} channels. Upgrade your plan to add more channels.",
                    }

        # Get contextstore repo from organization table
        contextstore_github_repo = None

        # First try to get from organization table (primary source of truth)
        organization = await bot_server.bot_manager.storage.get_organization_by_id(
            context.organization_id
        )
        if not organization or not organization.contextstore_github_repo:
            return {
                "success": False,
                "error": "No contextstore GitHub repository found for organization",
            }

        contextstore_github_repo = organization.contextstore_github_repo

        dev_tools_token, admin_token, compass_token = await _get_slack_tokens(bot_server)

        # Import here to avoid circular imports
        from csbot.slackbot.slack_utils import create_channel_and_bot_instance

        # Create the channel and bot
        # For first connection during onboarding: use email for Slack invite (no user_id yet)
        # For subsequent connections: use user_id for Slack invite
        # For onboarding flows without a Slack user yet, use placeholder for notifications
        if isinstance(context, ViewerContext):
            user_id = context.org_user.slack_user_id
            email = None
        elif isinstance(context, LegacyViewerContext):
            user_id = context.slack_user_id
            email = None
        elif isinstance(context, OnboardingViewerContext):
            user_id = None
            email = context.email
        else:
            user_id = None
            email = None

        notification_user_id = user_id if user_id else "onboarding"
        pending_email_param = email if (is_first_connection and not user_id) else None

        creation_result = await create_channel_and_bot_instance(
            bot_server=bot_server,
            channel_name=new_channel_name,
            user_id=notification_user_id,
            team_id=context.team_id,
            organization_id=context.organization_id,
            storage=bot_server.bot_manager.storage,
            governance_bot=governance_bot,
            contextstore_github_repo=contextstore_github_repo,
            dev_tools_bot_token=dev_tools_token,
            admin_token=admin_token,
            compass_bot_token=compass_token,
            logger=bot_server.logger,
            pending_invite_user_id=user_id,  # Can be None - will skip invite
            pending_invite_email=pending_email_param,  # For onboarding: email invite
            token=token,
            has_valid_token=has_valid_token,
        )

        bot_server.logger.info(
            f"Created channel {new_channel_name} with pending invite for user {user_id}"
        )

        return creation_result

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CHANNELS,
        allow_onboarding_access=True,
    )
    async def handle_channel_selection(
        request: web.Request, context: OrganizationContext
    ) -> web.Response:
        """Handle channel selection and associate connection with appropriate bots."""

        try:
            # Extract and validate request data
            connection_name, channel_selection, connection_token = await _validate_request_payload(
                request, bot_server
            )

            # Check if this is the first connection for the organization
            # We check this before creating the connection, so we need to count existing connections
            existing_connections = (
                await bot_server.bot_manager.storage.get_connection_names_for_organization(
                    context.organization_id
                )
            )
            # At this point in the flow, the connection has already been validated but not yet created
            # So we check if there are 0 existing connections (meaning this will be the first)
            is_first_connection = len(existing_connections) == 0

            # Decode connection token and create the connection before processing channels
            # Import here to avoid circular imports
            from csbot.slackbot.webapp.add_connections.routes.warehouse_factory import (
                ConnectionTokenData,
                create_connection_from_url,
            )

            try:
                token_data = ConnectionTokenData.from_jwt(
                    connection_token,
                    bot_server.config.jwt_secret.get_secret_value(),
                )
            except (jwt.InvalidTokenError, ValueError) as e:
                bot_server.logger.error(f"Invalid connection token: {e}", exc_info=True)
                return web.json_response(
                    {
                        "success": False,
                        "error": "Connection configuration expired or invalid. Please try creating the connection again.",
                    }
                )

            token = request.cookies.get(REFERRAL_TOKEN_COOKIE_NAME)  # Optional referral token
            has_valid_token, error_message = await is_token_valid(
                token, context.organization_id, bot_server
            )
            if not has_valid_token:
                return web.json_response({"success": False, "error": error_message}, status=400)

            # Process channel selection based on type
            selection_type = channel_selection["type"]
            selected_channels = channel_selection["channels"]

            # Step 1: Create channel if needed and determine bot IDs
            if selection_type == "create":
                if len(selected_channels) != 1:
                    return web.json_response(
                        {
                            "success": False,
                            "error": f"Create channel operation requires exactly 1 channel name, got {len(selected_channels)}",
                        }
                    )

                new_channel_name = selected_channels[0].strip()

                # Create the channel first
                channel_creation_result = await _handle_create_channel(
                    new_channel_name,
                    context,
                    bot_server,
                    token,
                    has_valid_token,
                    is_first_connection,
                )

                if not channel_creation_result["success"]:
                    return web.json_response(channel_creation_result)

                # Use the newly created bot's ID
                new_bot_key = BotKey.from_channel_name(context.team_id, new_channel_name)
                bot_ids_for_connection = [new_bot_key.to_bot_id()]

            elif selection_type == "existing":
                # Use existing channel bot IDs
                bot_ids_for_connection = [
                    BotKey.from_channel_name(context.team_id, channel_name).to_bot_id()
                    for channel_name in selected_channels
                ]
                channel_creation_result = None

            else:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"Unsupported selection type '{selection_type}'. Valid types are 'create' or 'existing'.",
                    }
                )

            # Step 2: Create connection and attach to all target bots
            try:
                connection_result = await create_connection_from_url(
                    bot_server,
                    token_data.warehouse_url,
                    token_data.warehouse_type,
                    bot_ids_for_connection,
                    token_data.connection_name,
                    token_data.table_names,
                )
                if not connection_result.success:
                    return web.json_response(
                        {
                            "success": False,
                            "error": f"Failed to create connection: {connection_result}",
                        }
                    )
            except Exception as e:
                bot_server.logger.error(f"Failed to create connection: {e}", exc_info=True)
                return web.json_response({"success": False, "error": "Failed to create connection"})

            # Step 3: Return success response
            if selection_type == "create":
                # Remove non-serializable objects before returning
                assert channel_creation_result is not None
                json_safe_result = {
                    k: v for k, v in channel_creation_result.items() if k != "message_stream"
                }
                # Add connection name to response for dataset sync polling
                json_safe_result["connection_name"] = token_data.connection_name
                return web.json_response(json_safe_result)
            else:
                return web.json_response(
                    {
                        "success": True,
                        "success_channels": selected_channels,
                        "failed_channels": [],
                        "message": f"Connection added to {len(selected_channels)} channels",
                        "connection_name": token_data.connection_name,
                    }
                )

        except web.HTTPError:
            # Re-raise HTTP errors (they're handled by aiohttp)
            raise
        except Exception as e:
            bot_server.logger.error(f"Error processing channel selection: {e}", exc_info=True)
            return web.json_response(
                {"success": False, "error": "An error occurred processing your request"}
            )

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CHANNELS,
        allow_onboarding_access=True,
    )
    async def handle_fetch_channels(
        request: web.Request, context: OrganizationContext
    ) -> web.Response:
        """Fetch channels with existing Compass bot instances for the current user's organization."""
        try:
            # Check if this is the first connection for the organization
            # This endpoint is called when the user reaches the channel selection page,
            # before the connection is created, so we check if there are 0 existing connections
            existing_connections = (
                await bot_server.bot_manager.storage.get_connection_names_for_organization(
                    context.organization_id
                )
            )
            is_first_connection = len(existing_connections) == 0

            # Get all active bot instances for this organization and team
            from csbot.slackbot.channel_bot.bot import BotTypeGovernance

            org_team_channels = []
            for bot_key, active_bot in bot_server.bots.items():
                # Filter by organization_id and team_id
                if (
                    active_bot.bot_config.organization_id == context.organization_id
                    and bot_key.team_id == context.team_id
                ):
                    # Include Q&A channels and combined channels
                    # Exclude governance-only channels (BotTypeGovernance where this is the governance channel)
                    is_governance_only = (
                        isinstance(active_bot.bot_type, BotTypeGovernance)
                        and bot_key.channel_name == active_bot.governance_alerts_channel
                    )

                    if not is_governance_only:
                        # Add the channel as an object with id and name
                        org_team_channels.append(
                            {"id": bot_key.channel_name, "name": bot_key.channel_name}
                        )

            # Sort channels alphabetically by name for better UX
            org_team_channels.sort(key=lambda x: x["name"])

            # Get organization name from storage or bot config
            organization_name = None

            # First try to get from storage (works for first connection during onboarding)
            organization = await bot_server.bot_manager.storage.get_organization_by_id(
                context.organization_id
            )
            if organization:
                organization_name = organization.organization_name
            else:
                # Fallback to bot config (for existing connections)
                for bot_instance in bot_server.bots.values():
                    if (
                        bot_instance.bot_config
                        and bot_instance.bot_config.organization_id == context.organization_id
                    ):
                        organization_name = bot_instance.bot_config.organization_name
                        break

            if not organization_name:
                bot_server.logger.error(
                    f"Could not determine organization name for organization_id={context.organization_id}. "
                    f"Organization not found in database."
                )
                raise web.HTTPBadRequest(text="Organization not found.")

            # Use generate_urlsafe_team_name to properly handle special characters
            formatted_org_name = generate_urlsafe_team_name(organization_name)

            if is_first_connection:
                # For first connection, automatically create and return the default channel
                # Format: {organization_name}-compass
                # Skip plan limit checks - first channel is always allowed
                default_channel_name = f"{formatted_org_name}-compass"

                bot_server.logger.info(
                    f"DEBUG: fetch_channels - first connection detected, returning: {default_channel_name}"
                )

                return web.json_response(
                    {
                        "success": True,
                        "is_first_connection": True,
                        "auto_selected_channel": default_channel_name,
                        "channels": [],
                    }
                )

            # Check plan limits to determine if new channels can be created
            # Only needed for non-first-connection cases
            can_create_channel = True
            plan_limit_message = None

            plan_limits = await bot_server.get_plan_limits_from_cache_or_bail(
                context.organization_id
            )
            if plan_limits:
                # Count current channels for this organization
                current_channel_count = _count_organization_channels(
                    context.organization_id, context.team_id, bot_server
                )

                # Check if we can create more channels
                can_create_channel = (
                    current_channel_count < plan_limits.num_channels
                    or plan_limits.allow_additional_channels
                )

                if not can_create_channel:
                    plan_limit_message = (
                        f"At plan limit of {plan_limits.num_channels} channels. "
                        "Upgrade your plan to add more channels."
                    )

            if org_team_channels:
                return web.json_response(
                    {
                        "success": True,
                        "is_first_connection": False,
                        "channels": org_team_channels,
                        "organization_name": formatted_org_name,
                        "can_create_channel": can_create_channel,
                        "plan_limit_message": plan_limit_message,
                    }
                )
            else:
                # No bot instances found for this org/team
                # This should not happen in normal operation - indicates configuration issue
                bot_server.logger.error(
                    f"No bot instances found for organization {context.organization_id}, "
                    f"team {context.team_id}. This indicates a configuration issue."
                )
                return web.json_response(
                    {
                        "success": False,
                        "is_first_connection": False,
                        "organization_name": formatted_org_name,
                        "error": "No Compass bot instances found for your organization",
                        "fallback_channels": [],
                        "can_create_channel": can_create_channel,
                        "plan_limit_message": plan_limit_message,
                    }
                )

        except web.HTTPError:
            # Re-raise HTTP errors (they're handled by aiohttp)
            raise
        except Exception as e:
            bot_server.logger.error(f"Error fetching bot channels: {e}", exc_info=True)
            return web.json_response(
                {
                    "success": False,
                    "error": "An error occurred fetching channels",
                    "fallback_channels": [],
                }
            )

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CHANNELS,
        allow_onboarding_access=False,
    )
    async def handle_add_prospector_connection(
        request: web.Request, context: OrganizationContext
    ) -> web.Response:
        """Add prospector connection to selected channels.

        This endpoint handles adding the pre-baked prospector connection to channels
        for organizations that already have the prospector connection created
        (either from initial prospector onboarding or created on-demand).
        """
        try:
            request_body = await request.json()
        except json.JSONDecodeError as e:
            bot_server.logger.error(f"JSON decode error in request body: {e}", exc_info=True)
            return web.json_response({"success": False, "error": "Invalid JSON in request body"})

        channel_selection = request_body.get("channelSelection")
        if not channel_selection:
            return web.json_response(
                {"success": False, "error": "Missing required field: channelSelection"}
            )

        selection_type = channel_selection.get("type")
        if not selection_type:
            return web.json_response(
                {"success": False, "error": "Missing required field: channelSelection.type"}
            )

        selected_channels = channel_selection.get("channels")
        if not selected_channels:
            return web.json_response(
                {"success": False, "error": "Missing required field: channelSelection.channels"}
            )

        # Import prospector connection name and shared helper
        from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME
        from csbot.slackbot.webapp.onboarding.prospector_helpers import (
            create_prospector_connection_for_organization,
        )

        # Create prospector connection if it doesn't exist (handles both initial setup and on-demand creation)
        try:
            await create_prospector_connection_for_organization(bot_server, context.organization_id)
        except ValueError as e:
            bot_server.logger.error(f"Prospector configuration error: {e}")
            return web.json_response(
                {"success": False, "error": f"Server configuration error: {str(e)}"}
            )

        token = request.cookies.get(REFERRAL_TOKEN_COOKIE_NAME)  # Optional referral token
        has_valid_token, error_message = await is_token_valid(
            token, context.organization_id, bot_server
        )
        if not has_valid_token:
            return web.json_response({"success": False, "error": error_message}, status=400)

        # Step 1: Create channel if needed and determine bot IDs
        channel_creation_result = None
        new_channel_name = None

        if selection_type == "create":
            if len(selected_channels) != 1:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"Create channel operation requires exactly 1 channel name, got {len(selected_channels)}",
                    }
                )

            new_channel_name = selected_channels[0].strip()

            # Create the channel first
            channel_creation_result = await _handle_create_channel(
                new_channel_name,
                context,
                bot_server,
                token,
                has_valid_token,
                is_first_connection=False,
            )

            if not channel_creation_result["success"]:
                return web.json_response(channel_creation_result)

            # Use the newly created bot's ID
            from csbot.slackbot.bot_server.bot_server import BotKey

            new_bot_key = BotKey.from_channel_name(context.team_id, new_channel_name)
            bot_ids_for_connection = [new_bot_key.to_bot_id()]

        elif selection_type == "existing":
            # Use existing channel bot IDs
            from csbot.slackbot.bot_server.bot_server import BotKey

            bot_ids_for_connection = [
                BotKey.from_channel_name(context.team_id, channel_name).to_bot_id()
                for channel_name in selected_channels
            ]

        else:
            return web.json_response(
                {
                    "success": False,
                    "error": f"Unsupported selection type '{selection_type}'. Valid types are 'create' or 'existing'.",
                }
            )

        # Step 2: Add prospector connection to all target bots and send invites for new channels
        try:
            for bot_id in bot_ids_for_connection:
                await bot_server.bot_manager.storage.add_bot_connection(
                    organization_id=context.organization_id,
                    bot_id=bot_id,
                    connection_name=PROSPECTOR_CONNECTION_NAME,
                )

            bot_server.logger.info(
                f"Added prospector connection to {len(bot_ids_for_connection)} bot(s) for org {context.organization_id}"
            )

            # Step 3: Send Slack Connect invitation if we created a new channel
            # The user_id was already stored in pending_invites by _handle_create_channel,
            # but since prospector doesn't trigger a sync, we need to manually send the invite
            if selection_type == "create" and new_channel_name and channel_creation_result:
                from csbot.slackbot.bot_server.bot_server import BotKey
                from csbot.slackbot.slack_utils import send_slack_connect_invite_to_channel

                # Get the bot to check for pending invite
                new_bot_key = BotKey.from_channel_name(context.team_id, new_channel_name)
                active_bots = bot_server.bot_manager.get_active_bots()
                bot = active_bots.get(new_bot_key)

                if bot:
                    # Check for pending invite user ID
                    pending_user_id = await bot.kv_store.get("pending_invites", "user_ids")

                    if pending_user_id:
                        bot_server.logger.info(
                            f"Sending Slack Connect invite to user {pending_user_id} for prospector channel {new_channel_name}"
                        )

                        # Get channel ID from creation result
                        channel_id = channel_creation_result.get("channel_id")

                        if channel_id:
                            invite_results = await send_slack_connect_invite_to_channel(
                                channel_id=channel_id,
                                user_ids=[pending_user_id],
                                bot_server_config=bot_server.config,
                                logger=bot_server.logger,
                                channel_name=new_channel_name,
                            )

                            # Check if invitation was successful
                            if invite_results and invite_results[0].get("success"):
                                bot_server.logger.info(
                                    f"Successfully sent Slack Connect invite for prospector channel {new_channel_name}"
                                )
                                # Clear the pending invite since we successfully sent it
                                await bot.kv_store.delete("pending_invites", "user_ids")
                            else:
                                error_msg = (
                                    invite_results[0].get("error")
                                    if invite_results
                                    else "Unknown error"
                                )
                                bot_server.logger.warning(
                                    f"Failed to send Slack Connect invite to {new_channel_name}: {error_msg}"
                                )

        except Exception as e:
            bot_server.logger.error(
                f"Failed to add prospector connection to bots: {e}", exc_info=True
            )
            return web.json_response(
                {"success": False, "error": f"Failed to add connection: {str(e)}"}
            )

        # Step 4: Return success response
        return web.json_response(
            {
                "success": True,
                "message": f"Prospector connection added to {len(selected_channels)} channel(s)",
                "channels": selected_channels,
            }
        )

    # React uses: /onboarding/connections route is now served by React SPA in routes.py
    app.router.add_get("/api/onboarding/connections/fetch-channels", handle_fetch_channels)
    app.router.add_post("/api/onboarding/connections/complete", handle_channel_selection)
    app.router.add_post("/api/connections/prospector/add", handle_add_prospector_connection)

    # Database-specific routes - these register /api/* mirrors that React uses
    add_onboarding_snowflake_routes(app, bot_server)
    add_onboarding_bigquery_routes(app, bot_server)
    add_onboarding_athena_routes(app, bot_server)
    add_onboarding_redshift_routes(app, bot_server)
    add_onboarding_postgres_routes(app, bot_server)
    add_onboarding_motherduck_routes(app, bot_server)
    add_onboarding_databricks_routes(app, bot_server)
