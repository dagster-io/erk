import unittest
from unittest.mock import AsyncMock

from erkbot.emoji import add_eyes_emoji, add_result_emoji, remove_eyes_emoji
from slack_sdk.errors import SlackApiError


def _slack_api_error(error_code: str) -> SlackApiError:
    return SlackApiError(message="error", response={"error": error_code})


class TestAddEyesEmoji(unittest.IsolatedAsyncioTestCase):
    async def test_adds_eyes_reaction(self) -> None:
        client = AsyncMock()
        await add_eyes_emoji(client, channel="C1", timestamp="1.23")
        client.reactions_add.assert_awaited_once_with(channel="C1", timestamp="1.23", name="eyes")

    async def test_ignores_already_reacted(self) -> None:
        client = AsyncMock()
        client.reactions_add.side_effect = _slack_api_error("already_reacted")
        await add_eyes_emoji(client, channel="C1", timestamp="1.23")

    async def test_ignores_missing_scope(self) -> None:
        client = AsyncMock()
        client.reactions_add.side_effect = _slack_api_error("missing_scope")
        await add_eyes_emoji(client, channel="C1", timestamp="1.23")

    async def test_reraises_unexpected_error(self) -> None:
        client = AsyncMock()
        client.reactions_add.side_effect = _slack_api_error("channel_not_found")
        with self.assertRaises(SlackApiError):
            await add_eyes_emoji(client, channel="C1", timestamp="1.23")


class TestRemoveEyesEmoji(unittest.IsolatedAsyncioTestCase):
    async def test_removes_eyes_reaction(self) -> None:
        client = AsyncMock()
        await remove_eyes_emoji(client, channel="C1", timestamp="1.23")
        client.reactions_remove.assert_awaited_once_with(
            channel="C1", timestamp="1.23", name="eyes"
        )

    async def test_ignores_no_reaction(self) -> None:
        client = AsyncMock()
        client.reactions_remove.side_effect = _slack_api_error("no_reaction")
        await remove_eyes_emoji(client, channel="C1", timestamp="1.23")

    async def test_reraises_unexpected_error(self) -> None:
        client = AsyncMock()
        client.reactions_remove.side_effect = _slack_api_error("channel_not_found")
        with self.assertRaises(SlackApiError):
            await remove_eyes_emoji(client, channel="C1", timestamp="1.23")


class TestAddResultEmoji(unittest.IsolatedAsyncioTestCase):
    async def test_adds_checkmark_on_success(self) -> None:
        client = AsyncMock()
        await add_result_emoji(client, channel="C1", timestamp="1.23", success=True)
        client.reactions_add.assert_awaited_once_with(
            channel="C1", timestamp="1.23", name="white_check_mark"
        )

    async def test_adds_x_on_failure(self) -> None:
        client = AsyncMock()
        await add_result_emoji(client, channel="C1", timestamp="1.23", success=False)
        client.reactions_add.assert_awaited_once_with(channel="C1", timestamp="1.23", name="x")

    async def test_ignores_already_reacted(self) -> None:
        client = AsyncMock()
        client.reactions_add.side_effect = _slack_api_error("already_reacted")
        await add_result_emoji(client, channel="C1", timestamp="1.23", success=True)


if __name__ == "__main__":
    unittest.main()
