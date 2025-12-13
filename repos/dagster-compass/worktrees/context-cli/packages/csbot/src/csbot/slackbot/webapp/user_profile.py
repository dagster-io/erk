"""User profile API endpoint for fetching current user information."""

from typing import TYPE_CHECKING

from aiohttp import web
from slack_sdk.errors import SlackApiError

from csbot.slackbot.channel_bot.personalization import get_cached_user_info
from csbot.slackbot.webapp.grants import Permission
from csbot.slackbot.webapp.security import (
    LegacyViewerContext,
    OrganizationContext,
    ViewerContext,
    find_bot_for_organization,
    require_permission,
)

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


def create_user_profile_handler(bot_server: "CompassBotServer"):
    """Create user profile API handler that returns current user's Slack profile."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_CHANNELS,
    )
    async def user_profile_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle user profile API requests.

        Extracts user_id from JWT and fetches their Slack profile.
        """
        if isinstance(organization_context, ViewerContext):
            user_id = organization_context.org_user.slack_user_id
        elif isinstance(organization_context, LegacyViewerContext):
            user_id = organization_context.slack_user_id
        else:
            user_id = None

        if not user_id:
            return web.json_response({"error": "Unauthorized"}, status=401)

        # Get bot instance to access Slack client
        bot = find_bot_for_organization(bot_server, organization_context)
        if not bot:
            return web.json_response(
                {"error": "No bot available", "user_id": user_id},
                status=200,
            )

        # Fetch user profile from Slack cache
        try:
            user = await get_cached_user_info(bot.client, bot.kv_store, user_id)
            if not user:
                return web.json_response(
                    {
                        "error": "Failed to fetch user info from Slack",
                        "user_id": user_id,
                    },
                    status=200,
                )

            return web.json_response(
                {
                    "user_id": user_id,
                    "display_name": user.real_name or "User",
                    "real_name": user.real_name,
                    "avatar_url": user.avatar_url,
                    "email": user.email,
                }
            )

        except SlackApiError as e:
            bot_server.logger.warning(f"Failed to fetch user profile for {user_id}: {e}")
            return web.json_response(
                {
                    "error": "Failed to fetch user profile",
                    "user_id": user_id,
                },
                status=200,
            )
        except Exception as e:
            bot_server.logger.error(f"Error fetching user profile for {user_id}: {e}")
            return web.json_response(
                {
                    "error": "Internal error",
                    "user_id": user_id,
                },
                status=500,
            )

    return user_profile_handler
