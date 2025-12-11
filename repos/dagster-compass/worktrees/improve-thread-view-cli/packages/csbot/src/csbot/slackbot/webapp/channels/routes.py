from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.slack_utils import (
    create_channel_and_bot_instance,
    delete_channel_and_bot_instance,
)
from csbot.slackbot.webapp.grants import Permission
from csbot.slackbot.webapp.onboarding.utils import is_token_valid
from csbot.slackbot.webapp.referral.referral import REFERRAL_TOKEN_COOKIE_NAME
from csbot.slackbot.webapp.security import (
    LegacyViewerContext,
    OrganizationContext,
    ViewerContext,
    find_governance_bot_for_organization,
    require_permission,
)
from csbot.utils.misc import normalize_channel_name

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


def add_channels_routes(app: web.Application, bot_server: "CompassBotServer"):
    """Add channel management routes to the webapp."""
    app.router.add_get("/api/channels/list", create_channels_list_handler(bot_server))
    app.router.add_post("/api/channels/create", create_channel_handler(bot_server))
    app.router.add_post("/api/channels/update", update_channel_handler(bot_server))
    app.router.add_delete("/api/channels/delete", delete_channel_handler(bot_server))


def create_channels_list_handler(bot_server: "CompassBotServer"):
    """Create channels list API handler."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_CHANNELS,
    )
    async def channels_list_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle channels list API requests."""

        # Get organization context from JWT
        organization_id = organization_context.organization_id

        # Query all bot instances for this organization directly from running bots
        # This works for both traditional governance model and self-governing combined bot model
        channels = []
        for bot_key, bot_instance in bot_server.bots.items():
            # Filter by organization
            if bot_instance.bot_config.organization_id == organization_id:
                from csbot.slackbot.channel_bot.bot import (
                    BotTypeCombined,
                    BotTypeQA,
                )

                # Include data channels: QA (traditional) and Combined (self-governing)
                # Exclude Governance-only bots (admin channels, not data channels)
                if isinstance(bot_instance.bot_type, (BotTypeQA, BotTypeCombined)):
                    bot_id = bot_key.to_bot_id()

                    # Get connections for this bot
                    connection_names = (
                        await bot_server.bot_manager.storage.get_connection_names_for_bot(
                            organization_id, bot_id
                        )
                    )

                    channels.append(
                        {
                            "bot_id": bot_id,
                            "channel_name": bot_key.channel_name,
                            "connection_names": connection_names,
                        }
                    )

        # Sort channels by name
        channels.sort(key=lambda c: c["channel_name"])

        # Get plan limits
        plan_limits_obj = await bot_server.get_plan_limits_from_cache_or_bail(organization_id)
        plan_limits = None
        if plan_limits_obj:
            plan_limits = {
                "num_channels": plan_limits_obj.num_channels,
                "allow_additional_channels": plan_limits_obj.allow_additional_channels,
            }

        # Get available connections
        available_connections = (
            await bot_server.bot_manager.storage.get_connection_names_for_organization(
                organization_id
            )
        )

        return web.json_response(
            {
                "channels": channels,
                "plan_limits": plan_limits,
                "available_connections": available_connections,
            }
        )

    return channels_list_handler


def create_channel_handler(bot_server: "CompassBotServer"):
    """Create new channel API handler."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CHANNELS,
    )
    async def channel_create_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle channel creation requests."""

        # Get organization context from JWT
        organization_id = organization_context.organization_id
        team_id = organization_context.team_id

        # Find governance bot for this organization
        bot = find_governance_bot_for_organization(bot_server, organization_context)
        if not bot:
            return web.json_response({"error": "No governance bot found"}, status=401)

        if isinstance(organization_context, ViewerContext):
            user_id = organization_context.org_user.slack_user_id
        elif isinstance(organization_context, LegacyViewerContext):
            user_id = organization_context.slack_user_id
        else:
            user_id = None

        if not user_id:
            return web.json_response({"error": "User ID not found in token"}, status=500)

        # Parse request body
        data = await request.json()
        channel_name = data.get("channel_name")
        connection_names = data.get("connection_names", [])
        token = request.cookies.get(REFERRAL_TOKEN_COOKIE_NAME)  # Optional referral token

        if not channel_name:
            return web.json_response({"error": "Channel name is required"}, status=400)

        # Normalize channel name
        channel_name = normalize_channel_name(channel_name)

        # Check plan limits
        plan_limits = await bot_server.get_plan_limits_from_cache_or_bail(organization_id)
        if plan_limits:
            from csbot.slackbot.channel_bot.bot import BotTypeCombined, BotTypeQA

            # Count all data channels (QA + Combined) for this organization
            # Exclude governance-only bots from the count
            current_channel_count = sum(
                1
                for bot_instance in bot_server.bots.values()
                if bot_instance.bot_config.organization_id == organization_id
                and isinstance(bot_instance.bot_type, (BotTypeQA, BotTypeCombined))
            )

            can_create = (
                current_channel_count < plan_limits.num_channels
                or plan_limits.allow_additional_channels
            )

            if not can_create:
                return web.json_response(
                    {
                        "error": f"Cannot create new channel: at plan limit of {plan_limits.num_channels} channels. Upgrade your plan to add more channels."
                    },
                    status=403,
                )

        # Validate referral token if provided
        has_valid_token, error_message = await is_token_valid(token, organization_id, bot_server)
        if not has_valid_token:
            return web.json_response({"success": False, "error": error_message}, status=400)

        # Get required tokens
        bot_server_config = bot_server.config
        if not bot_server_config.compass_dev_tools_bot_token:
            return web.json_response({"error": "Dev tools bot token not available"}, status=500)
        if not bot_server_config.slack_admin_token:
            return web.json_response({"error": "Admin token not available"}, status=500)
        if not bot_server_config.compass_bot_token:
            return web.json_response({"error": "Compass bot token not available"}, status=500)

        dev_tools_bot_token = bot_server_config.compass_dev_tools_bot_token.get_secret_value()
        admin_token = bot_server_config.slack_admin_token.get_secret_value()
        compass_bot_token = bot_server_config.compass_bot_token.get_secret_value()

        if not dev_tools_bot_token or not admin_token or not compass_bot_token:
            return web.json_response({"error": "Required tokens are missing"}, status=500)

        # Create channel and bot instance
        result = await create_channel_and_bot_instance(
            bot_server=bot_server,
            channel_name=channel_name,
            user_id=user_id,
            team_id=team_id,
            organization_id=organization_id,
            storage=bot_server.bot_manager.storage,
            governance_bot=bot,
            contextstore_github_repo=bot.bot_config.contextstore_github_repo,
            dev_tools_bot_token=dev_tools_bot_token,
            admin_token=admin_token,
            compass_bot_token=compass_bot_token,
            logger=bot_server.logger,
            pending_invite_user_id=user_id,
            token=token,
            has_valid_token=has_valid_token,
        )

        if not result["success"]:
            return web.json_response({"error": result["error"]}, status=400)

        # Configure connections if any were provided
        new_bot_key = BotKey(team_id=team_id, channel_name=channel_name)
        new_bot_id = new_bot_key.to_bot_id()

        if connection_names:
            await bot_server.bot_manager.storage.reconcile_bot_connection(
                organization_id, new_bot_id, connection_names
            )
            # Trigger bot discovery to update the new bot with connections
            await bot_server.bot_manager.discover_and_update_bots_for_keys([new_bot_key])

        # Send pending invite for both cases:
        # - With connections: User is associating existing datasets to the new channel
        # - Without connections: User needs to be invited to the empty channel
        new_bot = bot_server.bots.get(new_bot_key)
        if new_bot:
            from csbot.slackbot.webapp.add_connections.dataset_sync import (
                send_pending_slack_connect_invite,
            )

            await send_pending_slack_connect_invite(
                bot_server=bot_server,
                bot=new_bot,
                logger=bot_server.logger,
            )
        else:
            bot_server.logger.warning(
                f"Could not find newly created bot to send invite for {channel_name}"
            )

        return web.json_response(
            {"success": True, "bot_id": new_bot_id, "channel_name": channel_name}
        )

    return channel_create_handler


def update_channel_handler(bot_server: "CompassBotServer"):
    """Update channel connections API handler."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CHANNELS,
    )
    async def channel_update_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle channel update requests."""

        # Get organization context from JWT
        organization_id = organization_context.organization_id

        # Parse request body
        data = await request.json()
        bot_id = data.get("bot_id")
        connection_names = data.get("connection_names", [])

        if not bot_id:
            return web.json_response({"error": "Bot ID is required"}, status=400)

        # Update bot connections
        await bot_server.bot_manager.storage.reconcile_bot_connection(
            organization_id, bot_id, connection_names
        )

        # Trigger targeted bot discovery
        target_bot_key = BotKey.from_bot_id(bot_id)
        await bot_server.bot_manager.discover_and_update_bots_for_keys([target_bot_key])

        return web.json_response({"success": True})

    return channel_update_handler


def delete_channel_handler(bot_server: "CompassBotServer"):
    """Delete channel API handler."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CHANNELS,
    )
    async def channel_delete_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle channel deletion requests."""

        # Get organization context from JWT
        organization_id = organization_context.organization_id

        # Find governance bot for this organization
        bot = find_governance_bot_for_organization(bot_server, organization_context)
        if not bot:
            return web.json_response({"error": "No governance bot found"}, status=401)

        # Extract user_id from JWT for attribution
        if isinstance(organization_context, ViewerContext):
            user_id = organization_context.org_user.slack_user_id
        elif isinstance(organization_context, LegacyViewerContext):
            user_id = organization_context.slack_user_id
        else:
            user_id = None
        if not user_id:
            return web.json_response({"error": "User ID not found in token"}, status=500)

        # Parse request body
        data = await request.json()
        bot_id = data.get("bot_id")

        if not bot_id:
            return web.json_response({"error": "Bot ID is required"}, status=400)

        # Get channel name from bot_id
        target_bot_key = BotKey.from_bot_id(bot_id)
        channel_name = target_bot_key.channel_name

        # Delete channel and bot instance
        result = await delete_channel_and_bot_instance(
            bot_server=bot_server,
            channel_name=channel_name,
            bot_id=bot_id,
            organization_id=organization_id,
            storage=bot_server.bot_manager.storage,
            governance_bot=bot,
            governance_alerts_channel=bot.governance_alerts_channel,
            logger=bot_server.logger,
            user_id=user_id,
        )

        if not result["success"]:
            return web.json_response({"error": result["error"]}, status=400)

        return web.json_response({"success": True})

    return channel_delete_handler
