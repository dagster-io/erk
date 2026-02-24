# NOTE: @patch usage is deliberate here. erkbot is a standalone package that
# tests third-party Slack SDK wiring and does not use erk's gateway layer.
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from erkbot.cli import _run


class TestMain(unittest.TestCase):
    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_wires_app_and_starts_handler(
        self,
        mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        mock_handler_cls.return_value.start_async = AsyncMock()

        asyncio.run(_run())

        mock_load_dotenv.assert_called_once()
        mock_settings_cls.assert_called_once()
        mock_create_app.assert_called_once_with(settings=mock_settings_cls.return_value)
        mock_handler_cls.assert_called_once_with(
            mock_create_app.return_value,
            mock_settings_cls.return_value.slack_app_token,
        )
        mock_handler_cls.return_value.start_async.assert_awaited_once()
