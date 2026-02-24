from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler

from erk_slack_bot.app import create_app
from erk_slack_bot.config import Settings


def main() -> None:
    load_dotenv()
    settings = Settings()
    app = create_app(settings=settings)
    SocketModeHandler(app, settings.slack_app_token).start()
