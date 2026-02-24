import asyncio

from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from erk_shared.gateway.time.real import RealTime
from erkbot.app import create_app
from erkbot.config import Settings


async def _run() -> None:
    load_dotenv()
    settings = Settings()
    time = RealTime()
    app = create_app(settings=settings, bot=None, time=time)
    handler = AsyncSocketModeHandler(app, settings.slack_app_token)
    await handler.start_async()


def main() -> None:
    asyncio.run(_run())
