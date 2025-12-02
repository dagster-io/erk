"""Main app: FastAPI + Slack Bolt integration using Socket Mode."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from slackbot.erk_service import ErkService
from slackbot.handlers import register_handlers

# Initialize Slack Bolt app with bot token from environment
slack_app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))

# Get repository path from environment or default to current directory
repo_path = Path(os.environ.get("ERK_REPO_PATH", ".")).resolve()

# Initialize ErkService
erk_service = ErkService(repo_path)

# Register handlers
register_handlers(slack_app, erk_service)


# Store the handler reference for cleanup
_socket_handler: AsyncSocketModeHandler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage Slack socket mode connection lifecycle."""
    global _socket_handler

    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise RuntimeError("SLACK_APP_TOKEN environment variable is required")

    # Startup: connect socket mode handler
    _socket_handler = AsyncSocketModeHandler(slack_app, app_token)
    asyncio.create_task(_socket_handler.connect_async())

    yield

    # Shutdown: close connection
    if _socket_handler is not None:
        await _socket_handler.close_async()


# Initialize FastAPI with lifespan
web_app = FastAPI(
    title="Erk Slackbot",
    description="Slack bot for Erk plan management",
    lifespan=lifespan,
)


@web_app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@web_app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with service info."""
    return {
        "service": "erk-slackbot",
        "status": "running",
        "repo_path": str(repo_path),
    }
