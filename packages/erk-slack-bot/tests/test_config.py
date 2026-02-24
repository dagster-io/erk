import os
import unittest
from unittest.mock import patch

from erk_slack_bot.config import Settings
from pydantic import ValidationError


class TestSettings(unittest.TestCase):
    def test_settings_from_env_vars(self) -> None:
        settings = Settings(SLACK_BOT_TOKEN="xoxb-token", SLACK_APP_TOKEN="xapp-token")
        self.assertEqual(settings.slack_bot_token, "xoxb-token")
        self.assertEqual(settings.slack_app_token, "xapp-token")

    def test_settings_defaults(self) -> None:
        settings = Settings(SLACK_BOT_TOKEN="x", SLACK_APP_TOKEN="y")
        self.assertEqual(settings.max_slack_code_block_chars, 2800)
        self.assertEqual(settings.max_one_shot_message_chars, 1200)
        self.assertEqual(settings.one_shot_progress_tail_lines, 40)
        self.assertEqual(settings.one_shot_progress_update_interval_seconds, 1.0)
        self.assertEqual(settings.one_shot_failure_tail_lines, 60)
        self.assertEqual(settings.one_shot_timeout_seconds, 900.0)

    def test_settings_missing_required_raises(self) -> None:
        with patch.dict(os.environ, clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)
