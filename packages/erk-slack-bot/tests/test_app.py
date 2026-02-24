# NOTE: @patch usage is deliberate here. erk-slack-bot is a standalone package that
# tests third-party Slack SDK wiring and does not use erk's gateway layer.
import unittest
from unittest.mock import MagicMock, patch

from erk_slack_bot.config import Settings


class TestCreateApp(unittest.TestCase):
    @patch("erk_slack_bot.app.register_handlers")
    @patch("erk_slack_bot.app.App")
    def test_create_app_returns_app_with_handlers(
        self, mock_app_cls: MagicMock, mock_register: MagicMock
    ) -> None:
        from erk_slack_bot.app import create_app

        settings = Settings(SLACK_BOT_TOKEN="xoxb-token", SLACK_APP_TOKEN="xapp-token")
        result = create_app(settings=settings)

        mock_app_cls.assert_called_once_with(token="xoxb-token")
        mock_register.assert_called_once_with(mock_app_cls.return_value, settings=settings)
        self.assertIs(result, mock_app_cls.return_value)
