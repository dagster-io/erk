import asyncio

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from erk_slack_bot.app import create_app
from erk_slack_bot.config import Settings


async def _run() -> None:
    load_dotenv()
    settings = Settings()
    app = create_app(settings=settings)
    handler = AsyncSocketModeHandler(app, settings.slack_app_token)
    await handler.start_async()


def main() -> None:
    asyncio.run(_run())
