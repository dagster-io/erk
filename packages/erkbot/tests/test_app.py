# NOTE: @patch usage is deliberate here. erkbot is a standalone package that
# tests third-party Slack SDK wiring and does not use erk's gateway layer.
import unittest
from unittest.mock import MagicMock, patch

from erkbot.app import create_app
from erkbot.config import Settings

from erk_shared.gateway.time.fake import FakeTime


class TestCreateApp(unittest.TestCase):
    @patch("erkbot.app.register_handlers")
    @patch("erkbot.app.AsyncApp")
    def test_create_app_returns_app_with_handlers(
        self, mock_app_cls: MagicMock, mock_register: MagicMock
    ) -> None:
        settings = Settings(SLACK_BOT_TOKEN="xoxb-token", SLACK_APP_TOKEN="xapp-token")
        fake_time = FakeTime()
        result = create_app(settings=settings, time=fake_time)

        mock_app_cls.assert_called_once_with(token="xoxb-token")
        mock_register.assert_called_once_with(
            mock_app_cls.return_value, settings=settings, time=fake_time
        )
        self.assertIs(result, mock_app_cls.return_value)
