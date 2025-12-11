"""
Resource initialization and context managers for CompassBot.

This module contains all the resource initialization logic and context managers
for setting up CompassBot instances with proper resource management.
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog

from csbot.slackbot.bot_server.bot_server import create_reconciler_and_bot_server

if TYPE_CHECKING:
    from pathlib import Path


from csbot.slackbot.event_handlers import (
    AbstractSlackEventHandler,
    HttpSlackEventHandler,
    WebSocketSlackEventHandler,
)
from csbot.slackbot.storage.factory import create_connection_factory, create_storage
from csbot.slackbot.webapp.server import WebServer

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer
    from csbot.slackbot.slackbot_core import (
        CompassBotServerConfig,
    )


DISABLE_BACKGROUND_TASKS = os.getenv("DISABLE_BACKGROUND_TASKS") == "true"


@asynccontextmanager
async def create_event_handler(
    mode: str, server: "CompassBotServer", webserver: WebServer
) -> AsyncGenerator[AbstractSlackEventHandler]:
    """
    Create the appropriate event handler based on configuration mode.

    Args:
        mode: Event handler mode ("websocket" or "http")
        server: Server instance to handle events
        webserver: Webserver instance to use for HTTP endpoints

    Returns:
        Configured event handler instance
    """
    mode = mode.lower()

    if mode == "websocket":
        handler = WebSocketSlackEventHandler(server, webserver)
    elif mode == "http":
        handler = HttpSlackEventHandler(server, webserver)
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'websocket' or 'http'")

    try:
        await handler.start()
        yield handler
    finally:
        await handler.stop()


@asynccontextmanager
async def initialize_dynamic_compass_bot_server_for_repl(
    config: "CompassBotServerConfig",
    secret_store,
    config_root: "Path",
) -> AsyncGenerator["CompassBotServer"]:
    """
    Context manager that creates a dynamic CompassBotServer for REPL.

    Args:
        config: Bot configuration containing all necessary settings
        secret_store: Secret store for accessing secrets
        config_root: Root path for configuration files
    """
    sql_conn_factory = await asyncio.to_thread(
        create_connection_factory,
        config.db_config,
    )
    storage = create_storage(sql_conn_factory, config.db_config.kek_config)
    async with create_reconciler_and_bot_server(
        config=config,
        secret_store=secret_store,
        config_root=config_root,
        storage=storage,
        sql_conn_factory=sql_conn_factory,
        skip_background_tasks=True,
    ) as server:
        yield server


@asynccontextmanager
async def initialize_dynamic_compass_bot_server(
    config: "CompassBotServerConfig",
    secret_store,
    config_root: "Path",
) -> AsyncGenerator["CompassBotServer"]:
    """
    Context manager that creates a dynamic CompassBotServer with periodic bot discovery.

    This version periodically checks for new bot instances and spins them up dynamically.

    Args:
        config: Bot configuration containing all necessary settings
        secret_store: Secret store for accessing secrets
        config_root: Root path for configuration files

    Yields:
        Fully configured CompassBotServer with dynamic bot management
    """

    # Create core resources
    sql_conn_factory = await asyncio.to_thread(
        create_connection_factory,
        config.db_config,
    )
    logger = structlog.get_logger("CompassBotServer")

    storage = create_storage(sql_conn_factory, config.db_config.kek_config)
    async with create_reconciler_and_bot_server(
        config=config,
        secret_store=secret_store,
        config_root=config_root,
        storage=storage,
        sql_conn_factory=sql_conn_factory,
        skip_background_tasks=DISABLE_BACKGROUND_TASKS,
    ) as server:
        # Create webserver and event handler
        webserver = WebServer(server)
        async with create_event_handler(config.mode, server, webserver):
            async with webserver.run():
                logger.info(
                    "Started dynamic bot server - bot instances discovered via reconciliation loop"
                )
                logger.info(
                    "Dynamic bot discovery enabled - new instances will be detected automatically"
                )

                # Clean up resources
                try:
                    # Yield the configured server
                    yield server

                    # Main event loop - run until KeyboardInterrupt
                    while True:
                        await asyncio.sleep(1)

                except KeyboardInterrupt:
                    logger.info("🛑 Stopping AI Bot...")
