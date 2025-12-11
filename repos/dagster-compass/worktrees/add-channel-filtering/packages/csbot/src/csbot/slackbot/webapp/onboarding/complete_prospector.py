"""Complete prospector onboarding after data types selected."""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.storage.onboarding_state import ProspectorDataType
from csbot.slackbot.webapp.onboarding.utils import is_token_valid
from csbot.slackbot.webapp.referral.referral import REFERRAL_TOKEN_COOKIE_NAME
from csbot.slackbot.webapp.security import check_legacy_jwt_cookie, check_onboarding_cookie

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


def create_complete_prospector_handler(
    bot_server: "CompassBotServer",
) -> Callable[[web.Request], Awaitable[web.Response]]:
    """Complete prospector onboarding after minimal setup and data type selection.

    Creates channels, bot instance, prospector connection, and sends Slack Connect.
    """

    async def handle_complete_prospector_post(request: web.Request) -> web.Response:
        """Complete prospector setup with selected data types."""
        import json

        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        data_types = data.get("dataTypes", [])
        token = request.cookies.get(REFERRAL_TOKEN_COOKIE_NAME)  # Optional referral token

        # Validate data types
        if not data_types or len(data_types) == 0:
            return web.json_response(
                {"error": "At least one data type must be selected"}, status=400
            )

        valid_data_types = [
            ProspectorDataType.SALES.value,
            ProspectorDataType.RECRUITING.value,
            ProspectorDataType.INVESTING.value,
        ]
        for data_type in data_types:
            if data_type not in valid_data_types:
                return web.json_response({"error": "Invalid data type provided"}, status=400)

        onboarding_context = await check_onboarding_cookie(request, bot_server)
        if not onboarding_context:
            # check the legacy cookie
            legacy_context = await check_legacy_jwt_cookie(request, bot_server, require_user=False)
            if not legacy_context or not legacy_context.email:
                return web.json_response({"error": "Invalid or expired session"}, status=401)
            onboarding_context = legacy_context

        organization_id = onboarding_context.organization_id
        team_id = onboarding_context.team_id
        email = onboarding_context.email

        has_valid_token, error_message = await is_token_valid(token, organization_id, bot_server)
        if not has_valid_token:
            return web.json_response({"success": False, "error": error_message}, status=400)

        # Determine if this is community prospector based on token
        from csbot.slackbot.flags import is_community_prospector_token

        is_community_prospector = False
        if token and has_valid_token and is_community_prospector_token(token):
            is_community_prospector = True
            bot_server.logger.info(f"Community prospector mode detected for org {organization_id}")

        bot_server.logger.info(
            f"Completing prospector setup for org {organization_id} with data_types={data_types}, "
            f"email={email}, is_community_prospector={is_community_prospector}"
        )

        try:
            # Get organization details from database
            org = await bot_server.bot_manager.storage.get_organization_by_id(organization_id)
            if not org:
                bot_server.logger.error(f"Organization {organization_id} not found")
                return web.json_response({"error": "Organization not found"}, status=404)

            organization_name = org.organization_name

            # Convert data types to enums
            data_type_enums = [ProspectorDataType(dt) for dt in data_types]

            # Step 1 & 2: Create Slack channel and bot instance with prospector-specific fields
            from csbot.slackbot.slack_utils import (
                create_channel_and_bot_instance,
                generate_urlsafe_team_name,
            )
            from csbot.slackbot.storage.interface import BotInstanceType

            channel_name = f"{generate_urlsafe_team_name(organization_name)}-compass"

            # Validate required config
            if not bot_server.config.slack_admin_token:
                bot_server.logger.error("Missing Slack admin token")
                return web.json_response({"error": "Server configuration error"}, status=500)

            if not bot_server.config.compass_dev_tools_bot_token:
                bot_server.logger.error("Missing dev tools bot token")
                return web.json_response({"error": "Server configuration error"}, status=500)

            if not bot_server.config.compass_bot_token:
                bot_server.logger.error("Missing compass bot token")
                return web.json_response({"error": "Server configuration error"}, status=500)

            admin_token = bot_server.config.slack_admin_token.get_secret_value()
            dev_tools_bot_token = bot_server.config.compass_dev_tools_bot_token.get_secret_value()
            compass_bot_token = bot_server.config.compass_bot_token.get_secret_value()

            # Get org contextstore repo
            contextstore_repo = org.contextstore_github_repo
            if not contextstore_repo:
                bot_server.logger.error("Organization has no contextstore repo")
                return web.json_response({"error": "Organization setup incomplete"}, status=500)

            # Create channel and bot instance with prospector-specific parameters
            # Use COMMUNITY_PROSPECTOR type if community token was used
            instance_type = (
                BotInstanceType.COMMUNITY_PROSPECTOR
                if is_community_prospector
                else BotInstanceType.STANDARD
            )

            bot_server.logger.info(
                f"Creating channel and bot instance for {channel_name} with instance_type={instance_type}"
            )
            creation_result = await create_channel_and_bot_instance(
                bot_server=bot_server,
                channel_name=channel_name,
                user_id="onboarding",  # Placeholder for notifications
                team_id=team_id,
                organization_id=organization_id,
                storage=bot_server.bot_manager.storage,
                governance_bot=None,  # No separate governance bot for prospector
                contextstore_github_repo=contextstore_repo,
                dev_tools_bot_token=dev_tools_bot_token,
                admin_token=admin_token,
                compass_bot_token=compass_bot_token,
                logger=bot_server.logger,
                token=token,
                has_valid_token=has_valid_token,
                pending_invite_user_id=None,
                pending_invite_email=email,  # Store email for Slack Connect
                instance_type=instance_type,
                icp_text="",
                data_types=data_type_enums,
            )

            if not creation_result["success"]:
                error_msg = creation_result.get("error", "unknown")
                bot_server.logger.error(f"Failed to create channel and bot: {error_msg}")
                return web.json_response(
                    {"error": f"Failed to create channel and bot: {error_msg}"}, status=500
                )

            channel_id = creation_result["channel_id"]
            bot_server.logger.info(
                f"Successfully created channel {channel_name} ({channel_id}) and bot instance"
            )

            # Step 3: Create prospector connection with shared docs repo
            from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME
            from csbot.slackbot.webapp.onboarding.prospector_helpers import (
                create_prospector_connection_for_organization,
            )

            try:
                await create_prospector_connection_for_organization(bot_server, organization_id)
            except ValueError as e:
                bot_server.logger.error(f"Prospector configuration error: {e}")
                return web.json_response({"error": "Server configuration error"}, status=500)

            # Step 4: Associate connection with bot
            from csbot.slackbot.bot_server.bot_server import BotKey

            bot_id = BotKey.from_channel_name(team_id, channel_name).to_bot_id()

            await bot_server.bot_manager.storage.add_bot_connection(
                organization_id=organization_id,
                bot_id=bot_id,
                connection_name=PROSPECTOR_CONNECTION_NAME,
            )

            bot_server.logger.info("Associated connection with bot")

            # Reload the bot to pick up the new connection
            bot_key = BotKey(team_id=team_id, channel_name=channel_name)
            await bot_server.bot_manager.discover_and_update_bots_for_keys([bot_key])
            bot_server.logger.info(f"Reloaded bot {bot_id} with prospector connection")

            # Step 5: Send Slack Connect invitation
            # Email was stored in bot's KV store by create_channel_and_bot_instance
            # Now trigger the actual Slack Connect invitation
            from csbot.slackbot.webapp.add_connections.dataset_sync import (
                send_pending_slack_connect_invite,
            )

            bot_instance = bot_server.bots.get(bot_key)

            if not bot_instance:
                bot_server.logger.error(f"Could not find bot instance for {channel_name}")
                return web.json_response(
                    {"error": "Failed to find bot instance for Slack Connect"}, status=500
                )

            bot_server.logger.info(
                f"Sending Slack Connect invite to {email} for channel {channel_name}"
            )

            await send_pending_slack_connect_invite(
                bot_server=bot_server,
                bot=bot_instance,
                logger=bot_server.logger,
            )

            # Note: organization_created analytics event is already logged by create_organization_step
            # during minimal onboarding with onboarding_type="prospector"

            bot_server.logger.info(
                f"Prospector setup completed successfully for org {organization_id}"
            )

            return web.json_response(
                {
                    "success": True,
                    "message": "Prospector setup completed successfully",
                }
            )

        except Exception as e:
            bot_server.logger.error(f"Error completing prospector setup: {e}", exc_info=True)
            return web.json_response(
                {"error": "Failed to complete setup. Please contact support."}, status=500
            )

    return handle_complete_prospector_post
