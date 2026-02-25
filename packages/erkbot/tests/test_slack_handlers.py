# NOTE: @patch usage is deliberate here. These tests patch asyncio.create_task
# and run_erk_plan_list to verify Slack handler dispatch without launching real
# background tasks or subprocess calls.
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from erkbot.config import Settings
from erkbot.models import RunResult
from erkbot.slack_handlers import register_handlers

from erk_shared.gateway.time.fake import FakeTime


class FakeApp:
    def __init__(self) -> None:
        self.event_handlers: dict = {}
        self.message_handlers: dict = {}

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


class TestSlackHandlers(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = Settings(SLACK_BOT_TOKEN="x", SLACK_APP_TOKEN="y")
        self.app = FakeApp()
        register_handlers(self.app, settings=self.settings, bot=None, time=FakeTime())

    @patch("erkbot.slack_handlers.run_erk_plan_list", new_callable=AsyncMock)
    async def test_plan_list(self, mock_run_plan_list: AsyncMock) -> None:
        mock_run_plan_list.return_value = RunResult(exit_code=0, output="plan output")

        handler = self.app.event_handlers["app_mention"]
        say = AsyncMock()
        client = AsyncMock()
        event = {"text": "<@U123> plan list", "channel": "C1", "ts": "1.23", "user": "U1"}

        await handler(event, say, client)

        say.assert_any_call("Running `erk pr list`...", thread_ts="1.23")
        say.assert_any_call("Result from `erk pr list`:", thread_ts="1.23")

    async def test_one_shot_missing_message(self) -> None:
        handler = self.app.event_handlers["app_mention"]
        say = AsyncMock()
        client = AsyncMock()
        event = {"text": "<@U123> one-shot", "channel": "C1", "ts": "1.23", "user": "U1"}

        await handler(event, say, client)

        say.assert_called_with("Usage: `@erk one-shot <message>`", thread_ts="1.23")

    @patch("erkbot.slack_handlers.asyncio")
    async def test_one_shot_starts_background_task(self, mock_asyncio: MagicMock) -> None:
        handler = self.app.event_handlers["app_mention"]
        say = AsyncMock()
        client = AsyncMock()
        event = {
            "text": "<@U123> one-shot Review README",
            "channel": "C1",
            "ts": "1.23",
            "user": "U1",
        }

        await handler(event, say, client)

        mock_asyncio.create_task.assert_called_once()
        mock_asyncio.create_task.call_args[0][0].close()

    async def test_chat_without_bot_returns_not_configured(self) -> None:
        handler = self.app.event_handlers["app_mention"]
        say = AsyncMock()
        client = AsyncMock()
        event = {
            "text": "<@U123> chat hello there",
            "channel": "C1",
            "ts": "1.23",
            "user": "U1",
        }

        await handler(event, say, client)

        say.assert_called_with("Agent mode is not configured.", thread_ts="1.23")

    @patch("erkbot.slack_handlers.asyncio")
    async def test_chat_with_bot_starts_background_task(self, mock_asyncio: MagicMock) -> None:
        bot = MagicMock()
        app = FakeApp()
        register_handlers(app, settings=self.settings, bot=bot, time=FakeTime())

        handler = app.event_handlers["app_mention"]
        say = AsyncMock()
        client = AsyncMock()
        event = {
            "text": "<@U123> chat hello there",
            "channel": "C1",
            "ts": "1.23",
            "user": "U1",
        }

        await handler(event, say, client)

        mock_asyncio.create_task.assert_called_once()
        mock_asyncio.create_task.call_args[0][0].close()

    async def test_ping(self) -> None:
        handler = self.app.message_handlers["ping"]
        say = AsyncMock()
        client = AsyncMock()
        message = {"text": "ping", "channel": "C1", "ts": "1.23"}

        await handler(message, say, client)

        say.assert_called_once_with("Pong!", thread_ts="1.23")


if __name__ == "__main__":
    unittest.main()
