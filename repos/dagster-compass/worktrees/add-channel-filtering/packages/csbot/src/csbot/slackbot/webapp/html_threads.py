import traceback
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.slackbot_ui import HtmlString, SlackThread
from csbot.slackbot.webapp.security import (
    OrganizationContext,
    create_link,
    find_bot_for_organization,
    require_user,
)

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


def get_error_message_factory(
    bot_server: "CompassBotServer", team_id: str, channel_id: str, thread_ts: str
):
    async def error_message_factory() -> HtmlString:
        body = HtmlString.from_template(
            "Your session is invalid or expired. Please click the 'See all steps' button in Slack to get a new link."
        )
        channel_name = await bot_server.get_channel_name(team_id, channel_id)
        if channel_name:
            bot_key = BotKey.from_channel_name(team_id, channel_name)
            bot_key = await bot_server.canonicalize_bot_key(bot_key)
            bot = bot_server.bots.get(bot_key)
            if bot:
                # Try to get permalink for better user experience
                try:
                    permalink_result = await bot.client.chat_getPermalink(
                        channel=channel_id, message_ts=thread_ts
                    )
                    permalink = permalink_result.get("permalink")
                    if permalink:
                        body = HtmlString.from_template(
                            """
        Your session is invalid or expired.
        Please click the "See all steps" button
        <a href="{permalink}" class="text-blue-500 hover:text-blue-600">in the Slack thread</a>
        to get a new link.
        """,
                            permalink=permalink,
                        )
                except Exception:
                    # If permalink fails, use the simple message
                    traceback.print_exc()

        return body

    return error_message_factory


def create_html_thread_url(
    bot: "CompassChannelBaseBotInstance", user_id: str, channel_id: str, thread_ts: str
) -> str:
    team_id = bot.key.team_id
    return create_link(
        bot,
        user_id=user_id,
        path=f"/thread/{team_id}/{channel_id}/{thread_ts}",
        max_age=timedelta(minutes=5),
    )


def create_thread_api_handler(
    bot_server: "CompassBotServer",
) -> Callable[[web.Request], Awaitable[web.Response]]:
    """Create API handler that returns thread data as JSON for React frontend."""

    @require_user(bot_server=bot_server)
    async def handle_thread_api_request(
        request: web.Request, organization_context: OrganizationContext
    ) -> web.Response:
        # Extract channel_id and thread_ts from URL path
        team_id = request.match_info.get("team_id")
        channel_id = request.match_info.get("channel_id")
        thread_ts = request.match_info.get("thread_ts")

        if not channel_id or not thread_ts or not team_id:
            return web.json_response(
                {"error": "Missing channel_id, thread_ts, or team_id in URL"}, status=400
            )

        bot = find_bot_for_organization(bot_server, organization_context)
        if not bot:
            return web.json_response({"error": "Bot not found for organization"}, status=404)

        # Initialize SlackThread with proper parameters
        thread = SlackThread(
            kv_store=bot.kv_store,
            bot_id=bot.bot_user_id or "unknown",
            channel=channel_id,
            thread_ts=thread_ts,
        )

        thread_html_str = await thread.get_html()
        if not thread_html_str:
            return web.json_response(
                {"error": "Thread not found or no HTML content available"}, status=404
            )

        return web.json_response({"success": True, "thread_content": thread_html_str})

    return handle_thread_api_request
