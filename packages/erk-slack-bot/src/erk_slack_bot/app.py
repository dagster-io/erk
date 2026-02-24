from slack_bolt.async_app import AsyncApp

from erk_slack_bot.config import Settings
from erk_slack_bot.slack_handlers import register_handlers


def create_app(*, settings: Settings) -> AsyncApp:
    app = AsyncApp(token=settings.slack_bot_token)
    register_handlers(app, settings=settings)
    return app
