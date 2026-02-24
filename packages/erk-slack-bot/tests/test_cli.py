import unittest
from unittest.mock import MagicMock, patch


class TestMain(unittest.TestCase):
    @patch("erk_slack_bot.cli.SocketModeHandler")
    @patch("erk_slack_bot.cli.create_app")
    @patch("erk_slack_bot.cli.Settings")
    @patch("erk_slack_bot.cli.load_dotenv")
    def test_main_wires_app_and_starts_handler(
        self,
        mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        from erk_slack_bot.cli import main

        main()

        mock_load_dotenv.assert_called_once()
        mock_settings_cls.assert_called_once()
        mock_create_app.assert_called_once_with(settings=mock_settings_cls.return_value)
        mock_handler_cls.assert_called_once_with(
            mock_create_app.return_value,
            mock_settings_cls.return_value.slack_app_token,
        )
        mock_handler_cls.return_value.start.assert_called_once()
