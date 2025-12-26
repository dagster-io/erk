"""
Reusable webserver for hosting thread viewer and Slack endpoints.

Provides a context manager-based webserver that can be shared across
different Slack event handler implementations.
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING

import aiohttp_cors
import structlog
from aiohttp import web

from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.routes import add_webapp_routes

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer

logger = structlog.get_logger(__name__)

# Frontend dev server URL for CORS (Vite default port)
FRONTEND_DEV_URL = "http://localhost:5173"


class WebServer:
    """Reusable HTTP server for thread viewer and optional Slack endpoints."""

    def __init__(self, server: "CompassBotServer"):
        self.server = server
        # Create application with error handling middleware
        self.app = build_web_application(self.server)
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        # Always add thread viewer endpoint
        add_webapp_routes(self.app, server)

        # Add root redirect for production environments
        self.app.router.add_get("/", self._redirect_to_landing_page)
        self.app.router.add_get("/healthz", self._health_check)

        # Setup CORS for local development (must be called after all routes are registered)
        self._setup_cors_for_dev()

    def _setup_cors_for_dev(self) -> None:
        """Setup CORS for local development.

        In production, the React app is served from the same origin as the API,
        so CORS is not needed. In local dev, the frontend runs on localhost:5173
        (Vite dev server) and backend on localhost:3000, requiring CORS.

        Only applies CORS when COMPASS_ENV is not set or is "development".
        """
        env_name = os.getenv("COMPASS_ENV")
        if env_name is None or env_name == "development":
            cors = aiohttp_cors.setup(
                self.app,
                defaults={
                    FRONTEND_DEV_URL: aiohttp_cors.ResourceOptions(
                        allow_credentials=True,
                        expose_headers="*",
                        allow_headers="*",
                    )
                },
            )
            # Apply CORS to all registered routes
            for route in list(self.app.router.routes()):
                cors.add(route)

    async def _redirect_to_landing_page(self, _: web.Request) -> web.Response:
        """Redirect root requests to the Compass landing page."""
        return web.Response(status=302, headers={"Location": "https://compass.dagster.io"})

    async def _health_check(self, _: web.Request) -> web.Response:
        """Health check endpoint for bot server readiness.

        Verifies that the bot server and reconciler have successfully spun up instances.
        Returns 200 with status information if healthy, appropriate status codes otherwise.
        """
        return await asyncio.to_thread(self._health_check_sync)

    def _health_check_sync(self):
        try:
            bot_manager = self.server.bot_manager

            initial_sync_complete = bot_manager.initial_sync_complete

            background_tasks_healthy = len(self.server.background_task_manager.tasks) > 0

            if initial_sync_complete and background_tasks_healthy:
                status = "healthy"
                http_status = 200
            else:
                logger.warn(
                    f"initial sync complete: {initial_sync_complete}, background tasks healthy: {background_tasks_healthy}"
                )
                status = "unhealthy"
                http_status = 503

            health_data = {
                "status": status,
                "timestamp": datetime.now().isoformat(),
            }

            return web.json_response(health_data, status=http_status)

        except Exception:
            # Return 503 for any unexpected errors during health check
            logger.exception("Health check failed")
            error_data = {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
            }
            return web.json_response(error_data, status=503)

    def add_route(self, method: str, path: str, handler) -> None:
        """Add a new route to the webserver."""
        self.app.router.add_route(method, path, handler)

    @asynccontextmanager
    async def run(self) -> AsyncGenerator["WebServer"]:
        """Context manager for webserver lifecycle management.

        Creates a webserver, starts it, yields it for use, and ensures proper cleanup.

        Args:
            server: The CompassBotServer instance

        Yields:
            WebServer: The running webserver instance

        Example:
            async with webserver_context(server) as webserver:
                # Register additional endpoints if needed
                webserver.add_route("POST", "/slack/events", handler)

                # Server is running and ready to handle requests
                await some_other_operation()

            # Server is automatically stopped and cleaned up
        """
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(
                self.runner,
                self.server.config.http_host,
                self.server.config.http_port,
            )
            await self.site.start()

            self.server.logger.info(
                f"🌐 HTTP server running on {self.server.config.http_host}:"
                f"{self.server.config.http_port}"
            )
            yield self
        finally:
            if self.site:
                # Stop the TCP site before cleaning up the runner to avoid aiohttp exceptions
                await self.site.stop()
                self.site = None
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
