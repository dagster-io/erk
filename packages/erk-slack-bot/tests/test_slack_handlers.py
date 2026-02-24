import unittest
from unittest.mock import MagicMock, patch

from erk_slack_bot.config import Settings
from erk_slack_bot.models import RunResult
from erk_slack_bot.slack_handlers import register_handlers


class FakeApp:
    def __init__(self) -> None:
        self.event_handlers = {}
        self.message_handlers = {}

    def event(self, name: str):
        def decorator(func):
            self.event_handlers[name] = func
            return func

        return decorator

    def message(self, pattern: str):
        def decorator(func):
            self.message_handlers[pattern] = func
            return func

        return decorator


class TestSlackHandlers(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(SLACK_BOT_TOKEN="x", SLACK_APP_TOKEN="y")
        self.app = FakeApp()
        register_handlers(self.app, settings=self.settings)

    @patch("erk_slack_bot.slack_handlers.run_erk_plan_list")
    def test_plan_list(self, mock_run_plan_list) -> None:  # type: ignore[no-untyped-def]
        mock_run_plan_list.return_value = RunResult(exit_code=0, output="plan output")

        handler = self.app.event_handlers["app_mention"]
        say = MagicMock()
        client = MagicMock()
        event = {"text": "<@U123> plan list", "channel": "C1", "ts": "1.23", "user": "U1"}

        handler(event, say, client)

        say.assert_any_call("Running `erk plan list`...", thread_ts="1.23")
        say.assert_any_call("Result from `erk plan list`:", thread_ts="1.23")

    def test_one_shot_missing_message(self) -> None:
        handler = self.app.event_handlers["app_mention"]
        say = MagicMock()
        client = MagicMock()
        event = {"text": "<@U123> one-shot", "channel": "C1", "ts": "1.23", "user": "U1"}

        handler(event, say, client)

        say.assert_called_with("Usage: `@erk one-shot <message>`", thread_ts="1.23")

    @patch("erk_slack_bot.slack_handlers.Thread")
    def test_one_shot_starts_background_thread(self, mock_thread) -> None:  # type: ignore[no-untyped-def]
        thread_instance = MagicMock()
        mock_thread.return_value = thread_instance

        handler = self.app.event_handlers["app_mention"]
        say = MagicMock()
        client = MagicMock()
        event = {
            "text": "<@U123> one-shot Review README",
            "channel": "C1",
            "ts": "1.23",
            "user": "U1",
        }

        handler(event, say, client)

        mock_thread.assert_called_once()
        thread_instance.start.assert_called_once()

    def test_ping(self) -> None:
        handler = self.app.message_handlers["ping"]
        say = MagicMock()
        client = MagicMock()
        message = {"text": "ping", "channel": "C1", "ts": "1.23"}

        handler(message, say, client)

        say.assert_called_once_with("Pong!", thread_ts="1.23")


if __name__ == "__main__":
    unittest.main()
