import os
import unittest
from unittest.mock import patch

from erkbot.config import Settings
from pydantic import ValidationError


class TestSettings(unittest.TestCase):
    def test_settings_from_env_vars(self) -> None:
        settings = Settings(SLACK_BOT_TOKEN="xoxb-token", SLACK_APP_TOKEN="xapp-token")
        self.assertEqual(settings.slack_bot_token, "xoxb-token")
        self.assertEqual(settings.slack_app_token, "xapp-token")

    def test_settings_defaults(self) -> None:
        settings = Settings(SLACK_BOT_TOKEN="x", SLACK_APP_TOKEN="y")
        self.assertTrue(settings.enable_suggested_replies)
        self.assertEqual(settings.max_slack_code_block_chars, 2800)
        self.assertEqual(settings.max_one_shot_message_chars, 1200)
        self.assertEqual(settings.one_shot_progress_tail_lines, 40)
        self.assertEqual(settings.one_shot_progress_update_interval_seconds, 1.0)
        self.assertEqual(settings.one_shot_failure_tail_lines, 60)
        self.assertEqual(settings.one_shot_timeout_seconds, 900.0)

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_agent_defaults(self) -> None:
        settings = Settings(SLACK_BOT_TOKEN="x", SLACK_APP_TOKEN="y", _env_file=None)
        self.assertIsNone(settings.anthropic_api_key)
        self.assertIsNone(settings.erk_repo_path)
        self.assertEqual(settings.erk_model, "claude-sonnet-4-20250514")
        self.assertEqual(settings.max_turns, 10)

    def test_settings_agent_from_env_vars(self) -> None:
        settings = Settings(
            SLACK_BOT_TOKEN="x",
            SLACK_APP_TOKEN="y",
            ANTHROPIC_API_KEY="sk-ant-test",
            ERK_REPO_PATH="/tmp/repo",
            ERK_MODEL="claude-opus-4-20250514",
            ERK_MAX_TURNS=20,
        )
        self.assertEqual(settings.anthropic_api_key, "sk-ant-test")
        self.assertEqual(settings.erk_repo_path, "/tmp/repo")
        self.assertEqual(settings.erk_model, "claude-opus-4-20250514")
        self.assertEqual(settings.max_turns, 20)

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_still_valid_without_agent_config(self) -> None:
        """Existing required fields only — no agent config needed."""
        settings = Settings(
            SLACK_BOT_TOKEN="xoxb-token", SLACK_APP_TOKEN="xapp-token", _env_file=None
        )
        self.assertEqual(settings.slack_bot_token, "xoxb-token")
        self.assertEqual(settings.slack_app_token, "xapp-token")
        self.assertIsNone(settings.anthropic_api_key)
        self.assertIsNone(settings.erk_repo_path)

    # --- Node 1.6: Config edge case tests ---

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_partial_agent_config_api_key_only(self) -> None:
        settings = Settings(
            SLACK_BOT_TOKEN="x",
            SLACK_APP_TOKEN="y",
            ANTHROPIC_API_KEY="sk-ant-test",
            _env_file=None,
        )
        self.assertEqual(settings.anthropic_api_key, "sk-ant-test")
        self.assertIsNone(settings.erk_repo_path)

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_partial_agent_config_repo_path_only(self) -> None:
        settings = Settings(
            SLACK_BOT_TOKEN="x",
            SLACK_APP_TOKEN="y",
            ERK_REPO_PATH="/tmp/repo",
            _env_file=None,
        )
        self.assertIsNone(settings.anthropic_api_key)
        self.assertEqual(settings.erk_repo_path, "/tmp/repo")

    @patch.dict(os.environ, {}, clear=True)
    def test_settings_max_turns_from_env(self) -> None:
        settings = Settings(
            SLACK_BOT_TOKEN="x",
            SLACK_APP_TOKEN="y",
            ERK_MAX_TURNS=25,
            _env_file=None,
        )
        self.assertEqual(settings.max_turns, 25)

    def test_settings_missing_required_raises(self) -> None:
        with patch.dict(os.environ, clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)
