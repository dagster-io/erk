from slack_bolt import App

from erk_slack_bot.config import Settings
from erk_slack_bot.slack_handlers import register_handlers


def create_app(*, settings: Settings) -> App:
    app = App(token=settings.slack_bot_token)
    register_handlers(app, settings=settings)
    return app
