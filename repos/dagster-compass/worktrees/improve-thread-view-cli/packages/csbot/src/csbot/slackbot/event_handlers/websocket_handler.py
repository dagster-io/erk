"""
WebSocket Slack Event Handler for Development

Receives Slack events via persistent WebSocket connection using Socket Mode.
Ideal for local development - no public endpoints needed, works behind
firewalls. Not suitable for production due to single connection limitation.

Key features:
- Persistent WebSocket connection
- No public endpoints required
- Simple App Token authentication
- Real-time event delivery
"""

import asyncio
from typing import TYPE_CHECKING, cast

from ddtrace.trace import tracer
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from csbot.slackbot.exceptions import BotUserFacingError, UserFacingError
from csbot.utils.misc import detect_team_from_interactive_payload
from csbot.utils.tracing import try_set_tag

from .abstract import AbstractSlackEventHandler

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.slack_types import (
        SlackEvent,
        SlackInteractivePayload,
        SlackSlashCommandPayload,
    )
    from csbot.slackbot.webapp.server import WebServer


class WebSocketSlackEventHandler(AbstractSlackEventHandler):
    """WebSocket handler for development environments.

    Uses Socket Mode for persistent WebSocket connection to Slack. Perfect
    for local development - no public endpoints needed, works behind firewalls.
    Requires App Token authentication.
    """

    def __init__(self, server: "CompassBotServer", webserver: "WebServer"):
        self.server = server
        self.webserver = webserver
        if not server.config.slack_app_token:
            raise ValueError("WebSocket mode requires slack_app_token")

        # Use any bot's Slack client for the socket client
        if not server.bots:
            raise ValueError("WebSocket mode requires at least one bot to be configured")

        any_bot = next(iter(server.bots.values()))
        self.slack_socket_client = SocketModeClient(
            app_token=server.config.slack_app_token.get_secret_value(),
            web_client=any_bot.client,
        )

    def _resolve_bot(self, e: UserFacingError | BotUserFacingError, channel_id: str):
        """Resolve which bot instance to use for sending error messages.

        Args:
            e: The error that occurred
            channel_id: The Slack channel ID where the error should be sent

        Returns:
            The bot instance to use, or None if no suitable bot is found
        """
        if isinstance(e, BotUserFacingError):
            return e.source_bot

        # UserFacingError requires channel lookup. Just grab first one.
        bots = self.server.get_bots_for_channel(channel_id)
        if not bots:
            self.server.logger.warning(
                f"No bot found for channel {channel_id}, cannot send UserFacingError to user"
            )
            return None
        return bots[0]

    async def _send_error_to_slack(self, bot, channel_id: str, message: str, event: "SlackEvent"):
        """Send an error message to a Slack channel.

        Args:
            bot: The bot instance to use for sending the message
            channel_id: The Slack channel ID to send the message to
            message: The error message to send
            event: The original Slack event that triggered the error
        """
        # Check if this is a thread reply or a new message
        thread_ts = event.get("thread_ts") or event.get("ts")

        # Send the error message using the selected bot
        try:
            await bot.client.chat_postMessage(channel=channel_id, text=message, thread_ts=thread_ts)
        except Exception as send_error:
            self.server.logger.error(
                f"Failed to send user-facing error message to channel: {send_error}"
            )

    @tracer.wrap()
    async def handle_events(self, _, req: SocketModeRequest) -> None:
        """Handle incoming events from Slack via WebSocket.

        This method processes different types of Socket Mode requests:
        - events_api: Regular Slack events (messages, mentions, etc.)
        - interactive: Interactive component events (button clicks, etc.)

        For each request, we immediately acknowledge receipt to Slack, then
        process the event asynchronously.
        """
        response = SocketModeResponse(envelope_id=req.envelope_id)
        await self.slack_socket_client.send_socket_mode_response(response)

        try_set_tag("event_type", req.type)

        async def handle_events_worker():
            if req.type == "events_api":
                # Acknowledge the request immediately

                # Process the event
                event = cast("SlackEvent", req.payload.get("event", {}))
                event_type = event.get("type")
                team_id = req.payload.get("team_id")

                if not team_id:
                    self.server.logger.error("No team_id found in event payload")
                    return

                try:
                    await self.server.handle_event(dict(event), event_type or "", team_id)
                except (UserFacingError, BotUserFacingError) as e:
                    # Send user-friendly error message to Slack channel
                    channel = event.get("channel")
                    if not channel:
                        self.server.logger.warning(
                            "No channel found in event, cannot send user-facing error to user"
                        )
                        return

                    # Extract channel ID - channel can be a string (ID) or dict with "id" field
                    if isinstance(channel, dict):
                        channel_id = channel.get("id")
                    else:
                        channel_id = channel

                    if not channel_id:
                        self.server.logger.warning(
                            "No channel ID found in event, cannot send user-facing error to user",
                            channel_id=channel_id,
                            team_id=team_id,
                        )
                        return
                    bot_to_use = self._resolve_bot(e, channel_id)
                    if bot_to_use:
                        # Get enriched user info for analytics
                        user_id = event.get("user")
                        enriched_person = None
                        if user_id:
                            try:
                                from csbot.slackbot.channel_bot.personalization import (
                                    get_person_info_from_slack_user_id,
                                )

                                enriched_person = await get_person_info_from_slack_user_id(
                                    bot_to_use.client, bot_to_use.kv_store, user_id
                                )
                            except Exception as enrich_error:
                                bot_to_use.logger.error(
                                    f"Error getting person info from slack user id: {enrich_error}"
                                )

                        # Log user-facing error analytics event
                        # Use unified logging to send ERROR_OCCURRED to both systems
                        from csbot.slackbot.slackbot_analytics import (
                            AnalyticsEventType,
                            log_analytics_event_unified,
                        )

                        await log_analytics_event_unified(
                            analytics_store=bot_to_use.analytics_store,
                            event_type=AnalyticsEventType.ERROR_OCCURRED,
                            bot_id=bot_to_use.key.to_bot_id(),
                            channel_id=channel_id,
                            user_id=user_id,
                            thread_ts=event.get("thread_ts"),
                            message_ts=event.get("ts"),
                            metadata={
                                "error_type": type(e).__name__,
                                "error_message": str(e)[:500],
                                "event_type": event_type,
                                "is_user_facing": True,
                                "organization_id": bot_to_use.bot_config.organization_id,
                            },
                            enriched_person=enriched_person,
                            # Enhanced context for Segment
                            organization_name=bot_to_use.bot_config.organization_name,
                            organization_id=bot_to_use.bot_config.organization_id,
                            team_id=bot_to_use.key.team_id,
                        )
                        await self._send_error_to_slack(bot_to_use, channel_id, e.message, event)
                except Exception as e:
                    self.server.logger.error(
                        f"Error handling event {event_type}: {e}",
                        exc_info=True,
                        team_id=team_id,
                    )

            elif req.type == "interactive":
                # Handle interactive messages (button clicks, menu selections, etc.)
                response = SocketModeResponse(envelope_id=req.envelope_id)
                await self.slack_socket_client.send_socket_mode_response(response)

                payload = cast("SlackInteractivePayload", req.payload)
                team_id = detect_team_from_interactive_payload(payload)

                if not team_id:
                    self.server.logger.warning(
                        f"No team_id found in interactive payload: {payload}"
                    )
                else:
                    try:
                        await self.server.handle_interactive(payload, team_id)
                    except Exception as e:
                        self.server.logger.error(
                            f"Error handling interactive message: {e}",
                            exc_info=True,
                            team_id=team_id,
                        )
            elif req.type == "slash_commands":
                response = SocketModeResponse(envelope_id=req.envelope_id)
                await self.slack_socket_client.send_socket_mode_response(response)
                payload = cast("SlackSlashCommandPayload", req.payload)
                team_id = payload.get("team_id")
                if not team_id:
                    self.server.logger.error("No team_id found in slash command payload")
                    return
                try:
                    await self.server.handle_slash_command(payload, team_id)
                except Exception as e:
                    self.server.logger.error(f"Error handling slash command: {e}", exc_info=True)

        task = asyncio.create_task(handle_events_worker())
        await task

    async def start(self) -> None:
        """Start the WebSocket client and begin listening for events.

        This establishes a persistent connection to Slack's Socket Mode servers
        and registers our event handler to process incoming requests.
        """
        self.slack_socket_client.socket_mode_request_listeners.append(self.handle_events)
        await self.slack_socket_client.connect()

        self.server.logger.info("🔌 WebSocket Bot is running! Press Ctrl+C to stop.")

    async def stop(self) -> None:
        """Stop the WebSocket client and close the connection."""
        await self.slack_socket_client.close()
