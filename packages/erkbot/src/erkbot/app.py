from slack_bolt.async_app import AsyncApp

from erk_shared.gateway.time.abc import Time
from erkbot.config import Settings
from erkbot.slack_handlers import register_handlers


def create_app(*, settings: Settings, time: Time) -> AsyncApp:
    app = AsyncApp(token=settings.slack_bot_token)
    register_handlers(app, settings=settings, time=time)
    return app
