from typing import TYPE_CHECKING

import structlog
from aiohttp import web

from csbot.slackbot.channel_bot.personalization import get_cached_user_info
from csbot.slackbot.webapp.grants import Permission
from csbot.slackbot.webapp.security import (
    OrganizationContext,
    require_permission,
)

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer

EXCLUDED_USERS = [
    {"name": "Dagster Compass", "email": "dagstercompass@dagsterlabs.com"},
    {"name": "Dagster Support", "email": "ben@dagsterlabs.com"},
]


def add_org_users_routes(app: web.Application, bot_server: "CompassBotServer"):
    """Add org users management routes to the webapp."""
    app.router.add_get("/api/org-users/list", create_org_users_list_handler(bot_server))
    app.router.add_post("/api/users/edit", create_users_edit_handler(bot_server))


def create_org_users_list_handler(bot_server: "CompassBotServer"):
    """Create org users list API handler."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_USERS,
    )
    async def org_users_list_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle org users list API requests."""
        logger = structlog.get_logger(__name__)

        # Get organization context from JWT
        organization_id = organization_context.organization_id

        # Get all org users for this organization
        org_users = await bot_server.bot_manager.storage.get_org_users(organization_id)

        # Get a bot instance to access Slack client and kv_store
        # We need any bot from this organization to access Slack API
        bot_instance = None
        for _, bot in bot_server.bots.items():
            if bot.bot_config.organization_id == organization_id:
                bot_instance = bot
                break

        # Format response with Slack profile info
        users_data = []
        for user in org_users:
            user_data = {
                "id": user.id,
                "slack_user_id": user.slack_user_id,
                "email": user.email,
                "is_org_admin": user.is_org_admin,
                "channels": [],
                "name": user.name,
                "avatar_url": None,
            }

            # Fetch Slack profile info if we have a bot instance
            if bot_instance:
                try:
                    slack_user_info = await get_cached_user_info(
                        client=bot_instance.client,
                        kv_store=bot_instance.kv_store,
                        user_id=user.slack_user_id,
                    )

                    if slack_user_info:
                        user_data["avatar_url"] = slack_user_info.avatar_url
                        if not user_data["name"]:
                            user_data["name"] = slack_user_info.real_name
                        if not user_data["email"]:
                            user_data["email"] = slack_user_info.email

                except Exception as e:
                    logger.warning(
                        "Failed to fetch Slack user info",
                        extra={
                            "user_id": user.slack_user_id,
                            "error": str(e),
                        },
                    )

            # Check if user should be excluded
            should_exclude = False
            for excluded in EXCLUDED_USERS:
                if user.name == excluded["name"] and user.email == excluded["email"]:
                    should_exclude = True
                    break

            if should_exclude:
                continue

            users_data.append(user_data)

        # Sort users alphabetically by name, then by email (case-insensitive)
        users_data.sort(key=lambda user: ((user["name"] or "").lower(), user["email"].lower()))

        return web.json_response({"users": users_data})

    return org_users_list_handler


def create_users_edit_handler(bot_server: "CompassBotServer"):
    """Create users edit API handler."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_USERS,
    )
    async def users_edit_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle user edit API requests."""
        logger = structlog.get_logger(__name__)

        # Parse request body
        body = await request.json()
        slack_user_id = body.get("slack_user_id")
        is_org_admin = body.get("is_org_admin")

        # Validate required fields
        if not slack_user_id:
            return web.json_response({"error": "slack_user_id is required"}, status=400)

        if is_org_admin is None:
            return web.json_response({"error": "is_org_admin is required"}, status=400)

        # Get organization context from JWT
        organization_id = organization_context.organization_id

        # Update user admin status
        try:
            await bot_server.bot_manager.storage.update_org_user_admin_status(
                slack_user_id=slack_user_id,
                organization_id=organization_id,
                is_org_admin=is_org_admin,
            )

            logger.info(
                "Updated user admin status",
                extra={
                    "slack_user_id": slack_user_id,
                    "organization_id": organization_id,
                    "is_org_admin": is_org_admin,
                },
            )

            return web.json_response({"success": True})

        except ValueError as e:
            logger.warning(
                "User not found",
                extra={
                    "slack_user_id": slack_user_id,
                    "organization_id": organization_id,
                    "error": str(e),
                },
            )
            return web.json_response({"error": "User not found"}, status=404)
        except Exception as e:
            logger.error(
                "Failed to update user admin status",
                extra={
                    "slack_user_id": slack_user_id,
                    "organization_id": organization_id,
                    "error": str(e),
                },
            )
            return web.json_response({"error": "Failed to update user"}, status=500)

    return users_edit_handler
