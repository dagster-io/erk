from typing import TYPE_CHECKING, Literal

from aiohttp import web

from csbot.local_context_store.github.utils import extract_pr_number_from_url
from csbot.slackbot.channel_bot.personalization import get_cached_user_info
from csbot.slackbot.storage.interface import ContextStatusType, ContextUpdateType
from csbot.slackbot.webapp.github_auth import create_github_auth_link
from csbot.slackbot.webapp.grants import Permission
from csbot.slackbot.webapp.security import (
    LegacyViewerContext,
    OrganizationContext,
    ViewerContext,
    find_bot_for_organization,
    require_permission,
)
from csbot.utils.misc import normalize_channel_name

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


async def _get_user_name_from_slack(
    bot: "CompassChannelBaseBotInstance", user_id: str | None
) -> str:
    """Get user display name from Slack, falling back to 'Unknown'."""
    if not user_id:
        return "Unknown"

    try:
        user_info = await get_cached_user_info(bot.client, bot.kv_store, user_id)
        if user_info and user_info.real_name:
            return user_info.real_name
    except Exception:
        pass
    return "Unknown"


async def _handle_pr_action(
    request: web.Request,
    organization_context: OrganizationContext,
    bot_server: "CompassBotServer",
    action: Literal["approve", "reject"],
) -> web.Response:
    """Common handler logic for approve/reject PR actions."""
    # Parse request body
    body = await request.json()
    github_url = body.get("github_url")

    if not github_url:
        return web.json_response({"error": "github_url is required"}, status=400)

    if isinstance(organization_context, ViewerContext):
        user_id = organization_context.org_user.slack_user_id
    elif isinstance(organization_context, LegacyViewerContext):
        user_id = organization_context.slack_user_id
    else:
        user_id = None

    if not user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)

    # Find the bot instance for this organization
    bot = find_bot_for_organization(bot_server, organization_context)
    if not bot:
        return web.json_response({"error": "Bot not found for organization"}, status=404)

    if not bot.github_monitor:
        return web.json_response({"error": "GitHub monitor not configured"}, status=500)

    # Get user name from Slack
    user_name = await _get_user_name_from_slack(bot, user_id)

    github_monitor = bot.github_monitor

    if action == "approve":
        scope = body.get("scope", "all")
        # TODO: add test COM-98
        if scope == "channel":
            await github_monitor.handle_pr_approve_channel(
                github_url,
                user_name,
                automerge=True,
            )
        else:
            await github_monitor.handle_pr_approve(github_url, user_name)
    else:
        await github_monitor.handle_pr_reject(github_url, user_name)

    return web.json_response({"success": True})


def add_context_governance_routes(app: web.Application, bot_server: "CompassBotServer"):
    """Add context status routes to the webapp."""
    app.router.add_get(
        "/api/context-governance/list", create_context_governance_list_handler(bot_server)
    )
    app.router.add_post(
        "/api/context-governance/approve", create_context_governance_approve_handler(bot_server)
    )
    app.router.add_post(
        "/api/context-governance/reject", create_context_governance_reject_handler(bot_server)
    )


def create_context_governance_list_handler(bot_server: "CompassBotServer"):
    """Create context status list API handler."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.VIEW_CONTEXT_STORE,
    )
    async def context_status_list_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle context status list API requests."""

        # Get organization context from JWT
        organization_id = organization_context.organization_id

        # Parse query parameters with enum conversion
        status_param = request.query.get("status")
        status = ContextStatusType(status_param) if status_param else None

        update_type_param = request.query.get("update_type")
        update_type = ContextUpdateType(update_type_param) if update_type_param else None

        limit = int(request.query.get("limit", "100"))
        offset = int(request.query.get("offset", "0"))

        # Get context status entries from database
        entries = await bot_server.bot_manager.storage.get_context_status(
            organization_id=organization_id,
            status=status,
            update_type=update_type,
            limit=limit,
            offset=offset,
        )

        # Find the bot instance for this organization to generate auth links
        bot = find_bot_for_organization(bot_server, organization_context)

        # Enrich entries with github_auth_url for each PR/issue
        enriched_entries = []
        for entry in entries:
            enriched_entry = {
                "organization_id": entry.organization_id,
                "repo_name": entry.repo_name,
                "update_type": entry.update_type.value,
                "github_url": entry.github_url,
                "title": entry.title,
                "description": entry.description,
                "status": entry.status.value,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
                "github_updated_at": entry.github_updated_at,
                "pr_info": entry.pr_info.model_dump() if entry.pr_info else None,
            }

            if bot and ("/pull/" in entry.github_url or "/issues/" in entry.github_url):
                # For governance page, we don't need specific PR/issue numbers
                # Just create a generic auth link that redirects back to governance
                enriched_entry["github_auth_url"] = create_github_auth_link(bot)
            else:
                # No auth link available, just use direct GitHub URL
                enriched_entry["github_auth_url"] = entry.github_url

            pr_info_dict = enriched_entry["pr_info"]

            if pr_info_dict is None and "/pull/" in entry.github_url and bot and bot.github_monitor:
                try:
                    pr_number = extract_pr_number_from_url(entry.github_url)
                    pr_info_obj = await bot.github_monitor.get_pr_info(entry.repo_name, pr_number)
                    if pr_info_obj:
                        pr_info_dict = pr_info_obj.model_dump()
                        enriched_entry["pr_info"] = pr_info_dict
                except Exception:
                    pr_info_dict = None

            channel_review_options: dict[str, object] | None = None
            if pr_info_dict and isinstance(pr_info_dict, dict):
                pr_info_type = pr_info_dict.get("type")
                if pr_info_type in {"context_update_created", "scheduled_analysis_created"}:
                    channel_review_options = {
                        "available": True,
                        "channel_label": None,
                        "channel_name": None,
                    }
                    try:
                        bot_id_value = str(pr_info_dict.get("bot_id", ""))
                        _, raw_channel_name = bot_id_value.split("-", 1)
                        channel_label = normalize_channel_name(raw_channel_name)
                        channel_review_options.update(
                            {
                                "available": True,
                                "channel_label": f"#{channel_label}",
                                "channel_name": raw_channel_name,
                            }
                        )
                    except Exception:
                        pass
            enriched_entry["channel_review_options"] = channel_review_options

            enriched_entries.append(enriched_entry)

        return web.json_response({"entries": enriched_entries})

    return context_status_list_handler


def create_context_governance_approve_handler(bot_server: "CompassBotServer"):
    """Create handler for approving PRs."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CONTEXT_STORE,
    )
    async def approve_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle PR approval requests."""
        return await _handle_pr_action(request, organization_context, bot_server, action="approve")

    return approve_handler


def create_context_governance_reject_handler(bot_server: "CompassBotServer"):
    """Create handler for rejecting PRs."""

    @require_permission(
        bot_server=bot_server,
        permission=Permission.MANAGE_CONTEXT_STORE,
    )
    async def reject_handler(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        """Handle PR rejection requests."""
        return await _handle_pr_action(request, organization_context, bot_server, action="reject")

    return reject_handler
