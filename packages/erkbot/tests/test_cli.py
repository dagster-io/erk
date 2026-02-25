# NOTE: @patch usage is deliberate here. erkbot is a standalone package that
# tests third-party Slack SDK wiring and does not use erk's gateway layer.
import asyncio
import unittest
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from erkbot.cli import _run


def _make_settings_mock(
    *,
    anthropic_api_key: str | None,
    erk_repo_path: str | None,
    erk_model: str,
    max_turns: int,
    webhook_enabled: bool = False,
    webhook_host: str = "0.0.0.0",
    webhook_port: int = 8080,
) -> MagicMock:
    mock = MagicMock()
    mock.anthropic_api_key = anthropic_api_key
    mock.erk_repo_path = erk_repo_path
    mock.erk_model = erk_model
    mock.max_turns = max_turns
    mock.slack_app_token = "xapp-token"
    mock.webhook_enabled = webhook_enabled
    mock.webhook_host = webhook_host
    mock.webhook_port = webhook_port
    return mock


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
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key=None,
            erk_repo_path=None,
            erk_model="claude-sonnet-4-20250514",
            max_turns=10,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        asyncio.run(_run())

        mock_load_dotenv.assert_called_once()
        mock_settings_cls.assert_called_once()
        mock_create_app.assert_called_once_with(
            settings=mock_settings_cls.return_value, bot=None, time=ANY
        )
        mock_handler_cls.assert_called_once_with(
            mock_create_app.return_value,
            mock_settings_cls.return_value.slack_app_token,
        )
        mock_handler_cls.return_value.start_async.assert_awaited_once()

    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.ErkBot")
    @patch("erkbot.cli.get_erk_system_prompt", return_value="mock-system-prompt")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_constructs_erkbot_when_agent_config_present(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        _mock_get_prompt: MagicMock,
        mock_erkbot_cls: MagicMock,
        mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key="sk-ant-test",
            erk_repo_path="/tmp/repo",
            erk_model="claude-opus-4-20250514",
            max_turns=20,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        with patch.object(Path, "is_dir", return_value=True):
            asyncio.run(_run())

        mock_erkbot_cls.assert_called_once_with(
            model="claude-opus-4-20250514",
            max_turns=20,
            cwd=Path("/tmp/repo"),
            system_prompt="mock-system-prompt",
            permission_mode="bypassPermissions",
        )
        mock_create_app.assert_called_once_with(
            settings=mock_settings_cls.return_value,
            bot=mock_erkbot_cls.return_value,
            time=ANY,
        )

    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.ErkBot")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_bot_none_when_agent_config_missing(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        mock_erkbot_cls: MagicMock,
        mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key=None,
            erk_repo_path=None,
            erk_model="claude-sonnet-4-20250514",
            max_turns=10,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        asyncio.run(_run())

        mock_erkbot_cls.assert_not_called()
        mock_create_app.assert_called_once_with(
            settings=mock_settings_cls.return_value, bot=None, time=ANY
        )

    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.ErkBot")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_bot_none_when_only_api_key_set(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        mock_erkbot_cls: MagicMock,
        mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key="sk-ant-test",
            erk_repo_path=None,
            erk_model="claude-sonnet-4-20250514",
            max_turns=10,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        asyncio.run(_run())

        mock_erkbot_cls.assert_not_called()
        mock_create_app.assert_called_once_with(
            settings=mock_settings_cls.return_value, bot=None, time=ANY
        )

    # --- Node 1.5+1.6: Startup logging tests ---

    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.ErkBot")
    @patch("erkbot.cli.get_erk_system_prompt", return_value="mock-system-prompt")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_logs_agent_enabled_mode(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        _mock_get_prompt: MagicMock,
        mock_erkbot_cls: MagicMock,
        _mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key="sk-ant-test",
            erk_repo_path="/tmp/repo",
            erk_model="claude-opus-4-20250514",
            max_turns=20,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        with (
            patch.object(Path, "is_dir", return_value=True),
            self.assertLogs("erkbot.cli", level="INFO") as cm,
        ):
            asyncio.run(_run())

        agent_logs = [r for r in cm.output if "mode=agent-enabled" in r]
        self.assertEqual(len(agent_logs), 1)
        self.assertIn("model=claude-opus-4-20250514", agent_logs[0])
        self.assertIn("repo_path=/tmp/repo", agent_logs[0])
        self.assertIn("max_turns=20", agent_logs[0])

    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_logs_slack_only_mode(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        _mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key=None,
            erk_repo_path=None,
            erk_model="claude-sonnet-4-20250514",
            max_turns=10,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        with self.assertLogs("erkbot.cli", level="INFO") as cm:
            asyncio.run(_run())

        slack_only_logs = [r for r in cm.output if "mode=slack-only" in r]
        self.assertEqual(len(slack_only_logs), 1)

    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.ErkBot")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_warns_when_repo_path_not_directory(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        mock_erkbot_cls: MagicMock,
        mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key="sk-ant-test",
            erk_repo_path="/nonexistent/path",
            erk_model="claude-sonnet-4-20250514",
            max_turns=10,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        with (
            patch.object(Path, "is_dir", return_value=False),
            self.assertLogs("erkbot.cli", level="WARNING") as cm,
        ):
            asyncio.run(_run())

        warning_logs = [r for r in cm.output if "not a valid directory" in r]
        self.assertEqual(len(warning_logs), 1)
        self.assertIn("/nonexistent/path", warning_logs[0])

        # Bot should be None (slack-only fallback)
        mock_erkbot_cls.assert_not_called()
        mock_create_app.assert_called_once_with(
            settings=mock_settings_cls.return_value, bot=None, time=ANY
        )

    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.ErkBot")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_bot_none_when_only_repo_path_set(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        mock_erkbot_cls: MagicMock,
        mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key=None,
            erk_repo_path="/tmp/repo",
            erk_model="claude-sonnet-4-20250514",
            max_turns=10,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        asyncio.run(_run())

        mock_erkbot_cls.assert_not_called()
        mock_create_app.assert_called_once_with(
            settings=mock_settings_cls.return_value, bot=None, time=ANY
        )

    # --- Node 2.1: Webhook server tests ---

    @patch("erkbot.cli.asyncio.gather", new_callable=AsyncMock)
    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_gather_one_coro_when_webhook_disabled(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        _mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
        mock_gather: AsyncMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key=None,
            erk_repo_path=None,
            erk_model="claude-sonnet-4-20250514",
            max_turns=10,
            webhook_enabled=False,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()

        asyncio.run(_run())

        mock_gather.assert_awaited_once()
        args = mock_gather.call_args[0]
        self.assertEqual(len(args), 1)

    @patch("erkbot.cli.create_webhook_server")
    @patch("erkbot.cli.create_webhook_app")
    @patch("erkbot.cli.asyncio.gather", new_callable=AsyncMock)
    @patch("erkbot.cli.AsyncSocketModeHandler")
    @patch("erkbot.cli.create_app")
    @patch("erkbot.cli.Settings")
    @patch("erkbot.cli.load_dotenv")
    def test_run_gather_two_coros_when_webhook_enabled(
        self,
        _mock_load_dotenv: MagicMock,
        mock_settings_cls: MagicMock,
        _mock_create_app: MagicMock,
        mock_handler_cls: MagicMock,
        mock_gather: AsyncMock,
        mock_create_webhook_app: MagicMock,
        mock_create_webhook_server: MagicMock,
    ) -> None:
        mock_settings_cls.return_value = _make_settings_mock(
            anthropic_api_key=None,
            erk_repo_path=None,
            erk_model="claude-sonnet-4-20250514",
            max_turns=10,
            webhook_enabled=True,
            webhook_host="127.0.0.1",
            webhook_port=9090,
        )
        mock_handler_cls.return_value.start_async = AsyncMock()
        mock_create_webhook_server.return_value.serve = AsyncMock()

        asyncio.run(_run())

        mock_create_webhook_app.assert_called_once()
        mock_create_webhook_server.assert_called_once_with(
            app=mock_create_webhook_app.return_value,
            host="127.0.0.1",
            port=9090,
        )
        mock_gather.assert_awaited_once()
        args = mock_gather.call_args[0]
        self.assertEqual(len(args), 2)
