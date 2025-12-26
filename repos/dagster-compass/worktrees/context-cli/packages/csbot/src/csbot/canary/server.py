import asyncio
import os

import structlog
import uvicorn

from csbot.agents.factory import create_agent_from_config
from csbot.agents.messages import AgentTextMessage
from csbot.slackbot.slackbot_core import CompassBotServerConfig
from csbot.slackbot.storage.factory import create_connection_factory
from csbot.slackbot.storage.interface import SqlConnectionFactory
from csbot.utils.logging import get_logging_config

CANARY_PORT = int(os.getenv("CANARY_PORT", "8567"))

logger = structlog.get_logger(__name__)


def check_conn_factory(conn_factory: SqlConnectionFactory):
    with conn_factory.with_conn() as conn:
        conn.cursor().execute("SELECT 1")


async def start(server_config: CompassBotServerConfig):
    # verify we can construct a connection factory and execute a basic SQL statement
    sql_conn_factory = await asyncio.to_thread(
        create_connection_factory,
        server_config.db_config,
    )
    await asyncio.to_thread(check_conn_factory, sql_conn_factory)

    # verify we can talk to the AI backend
    agent = create_agent_from_config(server_config.ai_config)
    result = await agent.create_completion(
        agent.model,
        "this is just a check that the model can be reached. respond with 'ok'",
        [
            AgentTextMessage(
                role="user",
                content="this is just a check that the model can be reached. respond with 'ok'",
            )
        ],
    )
    logger.info(f"Got result from model check: {result}")

    logger.info(f"Canary deployment. Starting canary test server on port {CANARY_PORT}")
    config = uvicorn.Config(
        "csbot.canary.app:app",
        host="0.0.0.0",
        port=CANARY_PORT,
        log_config=get_logging_config(),
    )
    server = uvicorn.Server(config)
    await server.serve()
