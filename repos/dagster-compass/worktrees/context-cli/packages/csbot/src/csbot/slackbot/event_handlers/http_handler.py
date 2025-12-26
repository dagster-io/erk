"""
HTTP Slack Event Handler for Production

Receives Slack events via HTTP webhooks. Designed for production deployments
with scalability, security, and reliability requirements. Requires public
endpoints but supports load balancing and horizontal scaling.

Key features:
- Cryptographic signature verification
- Immediate HTTP responses (< 3 seconds)
- Asynchronous event processing
- Stateless operation
"""

import asyncio
import json
import time
from typing import TYPE_CHECKING, cast

from aiohttp import web
from ddtrace.trace import tracer

from csbot.slackbot.exceptions import UserFacingError
from csbot.utils import tracing
from csbot.utils.datadog import (
    augment_span_from_slack_event_data,
    augment_span_from_slack_interactive_data,
)
from csbot.utils.misc import detect_team_from_interactive_payload

from .abstract import AbstractSlackEventHandler

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.slack_types import (
        SlackEvent,
        SlackEventPayload,
        SlackInteractivePayload,
        SlackSlashCommandPayload,
        SlackUrlVerificationPayload,
    )
    from csbot.slackbot.webapp.server import WebServer


class HttpSlackEventHandler(AbstractSlackEventHandler):
    """HTTP webhook handler for production deployments.

    Receives Slack events via HTTP POST requests with signature verification,
    immediate responses, and asynchronous processing. Supports both regular
    events and interactive messages.
    """

    def __init__(self, server: "CompassBotServer", webserver: "WebServer"):
        self.server = server
        self.webserver = webserver

    def _verify_slack_signature(self, request_body: bytes, timestamp: str, signature: str) -> bool:
        """Verify that the request is from Slack using cryptographic signatures.

        This implements Slack's signature verification protocol to ensure requests
        are authentic and haven't been tampered with.

        Args:
            request_body: Raw request body bytes
            timestamp: X-Slack-Request-Timestamp header value
            signature: X-Slack-Signature header value

        Returns:
            True if signature is valid, False otherwise
        """
        import hashlib
        import hmac

        if not self.server.config.slack_signing_secret:
            self.server.logger.warning("No signing secret configured - skipping verification")
            return True

        # Reject requests older than 5 minutes to prevent replay attacks
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False

        # Create signature using Slack's algorithm
        sig_basestring = f"v0:{timestamp}:{request_body.decode('utf-8')}"
        secret_bytes = self.server.config.slack_signing_secret.get_secret_value().encode()
        message_bytes = sig_basestring.encode()
        hash_obj = hmac.new(secret_bytes, message_bytes, hashlib.sha256)
        my_signature = f"v0={hash_obj.hexdigest()}"

        return hmac.compare_digest(my_signature, signature)

    @tracer.wrap()
    async def handle_slack_events(self, request: web.Request) -> web.Response:
        """Handle incoming events from Slack via HTTP webhooks.

        This method implements Slack's Events API requirements:
        1. Verify request authenticity
        2. Handle URL verification challenges
        3. Respond immediately with HTTP 200 OK
        4. Process events asynchronously

        This ensures compliance with Slack's 3-second timeout requirement.
        """
        # Get request data
        request_body = await request.read()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        # Verify request is from Slack
        if not self._verify_slack_signature(request_body, timestamp, signature):
            self.server.logger.warning("Invalid Slack signature in event request")
            return web.Response(status=401, text="Invalid signature")

        try:
            payload_dict = json.loads(request_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.server.logger.warning("Invalid JSON in request body")
            return web.Response(status=400, text="Invalid JSON")

        # Handle URL verification challenge (required during initial setup)
        if payload_dict.get("type") == "url_verification":
            challenge_payload = cast("SlackUrlVerificationPayload", payload_dict)
            return web.Response(text=challenge_payload.get("challenge", ""))

        # Respond immediately with 200 OK as per Slack Events API best practices
        # This ensures we respond within 3 seconds to avoid retry attempts
        response = web.Response(status=200, text="OK")

        # Process the event asynchronously after responding
        payload = cast("SlackEventPayload", payload_dict)
        event = payload["event"]
        event_type = event["type"]
        team_id = payload.get("team_id")

        if not team_id:
            self.server.logger.error("No team_id found in event payload")
            return response

        # Schedule event processing to run after the response is sent
        augment_span_from_slack_event_data(event)
        asyncio.create_task(
            self._process_event_async(
                event,
                event_type,
                team_id,
            )
        )

        return response

    @tracer.wrap()
    async def _process_event_async(
        self,
        event: "SlackEvent",
        event_type: str | None,
        team_id: str,
    ) -> None:
        """Process Slack event asynchronously after HTTP response is sent.

        This method handles the actual event processing logic after we've already
        responded to Slack, ensuring we don't hit timeout limits.
        """
        augment_span_from_slack_event_data(event)
        try:
            await self.server.handle_event(dict(event), event_type or "", team_id)
        except UserFacingError as e:
            tracing.try_set_exception()

            # Log user-facing errors with rich context but don't re-raise since
            # we've already responded to Slack
            self.server.logger.error(
                f"UserFacingError during event {event_type}: {e.title} - {e.message}",
                team_id=team_id,
                exc_info=True,
            )
        except Exception as e:
            self.server.logger.error(
                f"Error handling event {event_type}: {e}", exc_info=True, team_id=team_id
            )

    @tracer.wrap()
    async def handle_slack_interactive(self, request: web.Request) -> web.Response:
        """Handle interactive messages from Slack via HTTP webhooks.

        Interactive messages include button clicks, menu selections, and other
        UI interactions. Like events, these must be responded to quickly.
        """
        # Get request data
        request_body = await request.read()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        # Verify request is from Slack
        if not self._verify_slack_signature(request_body, timestamp, signature):
            self.server.logger.warning("Invalid Slack signature in interactive request")
            return web.Response(status=401, text="Invalid signature")

        try:
            # Parse form data (interactive payloads are form-encoded)
            form_data = await request.post()
            payload_field = form_data.get("payload", "")
            if isinstance(payload_field, str):
                payload_str = payload_field
            else:
                payload_str = ""
            payload_dict = json.loads(payload_str)
        except (json.JSONDecodeError, KeyError):
            tracing.try_set_exception()

            self.server.logger.warning("Invalid payload in interactive request")
            return web.Response(status=400, text="Invalid payload")

        # Respond immediately with 200 OK as per Slack Events API best practices
        response = web.Response(status=200)

        # Process the interactive message asynchronously after responding
        payload = cast("SlackInteractivePayload", payload_dict)
        team_id = detect_team_from_interactive_payload(payload)

        augment_span_from_slack_interactive_data(payload)
        if team_id:
            asyncio.create_task(
                self._process_interactive_async(
                    payload,
                    team_id,
                )
            )
        else:
            self.server.logger.warning(f"No team_id found in interactive payload: {payload}")

        return response

    @tracer.wrap()
    async def _process_interactive_async(
        self,
        payload: "SlackInteractivePayload",
        team_id: str,
    ) -> None:
        """Process Slack interactive message asynchronously after HTTP response is sent."""
        augment_span_from_slack_interactive_data(payload)
        try:
            await self.server.handle_interactive(payload, team_id)
        except Exception as e:
            tracing.try_set_exception()

            self.server.logger.error(
                f"Error handling interactive message: {e}", exc_info=True, team_id=team_id
            )

    @tracer.wrap()
    async def handle_slack_commands(self, request: web.Request) -> web.Response:
        """Handle slash commands from Slack via HTTP webhooks.

        Slash commands are form-encoded requests that must be responded to quickly.
        """
        # Get request data
        request_body = await request.read()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")

        # Verify request is from Slack
        if not self._verify_slack_signature(request_body, timestamp, signature):
            self.server.logger.warning("Invalid Slack signature in slash command")
            return web.Response(status=401, text="Invalid signature")

        try:
            # Parse form data (slash command payloads are form-encoded)
            form_data = await request.post()

            # Extract the command payload
            command_data = {}
            for key, value in form_data.items():
                if isinstance(value, str):
                    command_data[key] = value
                else:
                    command_data[key] = ""

            # Validate required fields
            if not command_data.get("command") or not command_data.get("team_id"):
                self.server.logger.warning("Missing required fields in slash command")
                return web.Response(status=400, text="Missing required fields")

        except Exception as e:
            tracing.try_set_exception()

            self.server.logger.warning(f"Error parsing slash command: {e}")
            return web.Response(status=400, text="Invalid payload")

        # Respond immediately with 200 OK as per Slack API best practices
        response = web.Response(status=200)

        # Process the slash command asynchronously after responding
        payload = cast("SlackSlashCommandPayload", command_data)
        team_id = payload.get("team_id")

        if not team_id:
            self.server.logger.error("No team_id found in slash command payload")
            return response

        asyncio.create_task(self._process_slash_command_async(payload, team_id))

        return response

    async def _process_slash_command_async(
        self, payload: "SlackSlashCommandPayload", team_id: str
    ) -> None:
        """Process Slack slash command asynchronously after HTTP response is sent."""
        try:
            await self.server.handle_slash_command(payload, team_id)
        except Exception as e:
            self.server.logger.error(f"Error handling slash command: {e}", exc_info=True)

    async def start(self) -> None:
        """Start the HTTP server for receiving Slack webhooks."""
        # Register Slack endpoints with the provided webserver
        self.webserver.add_route("POST", "/slack/events", self.handle_slack_events)
        self.webserver.add_route("POST", "/slack/interactive", self.handle_slack_interactive)
        self.webserver.add_route("POST", "/slack/commands", self.handle_slack_commands)

        self.server.logger.info(
            f"Event endpoint: http://{self.server.config.http_host}:{self.server.config.http_port}/slack/events"
        )
        self.server.logger.info(
            f"Interactive endpoint: http://{self.server.config.http_host}:{self.server.config.http_port}/slack/interactive"
        )
        self.server.logger.info(
            f"Commands endpoint: http://{self.server.config.http_host}:{self.server.config.http_port}/slack/commands"
        )

    async def stop(self) -> None:
        """Stop the HTTP server and clean up resources."""
        pass
