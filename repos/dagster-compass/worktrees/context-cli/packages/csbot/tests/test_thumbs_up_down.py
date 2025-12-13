"""
Test cases for thumbs up/down voting functionality.

This module tests the thumbs up/down voting system including:
- Empty state transitions to upvote/downvote
- Vote switching between up/down
- Vote resetting (clicking same vote twice)
- Vote count updates and button text changes
- Analytics event logging
- KV store state management
"""

import asyncio
import json
import unittest
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

from pydantic import SecretStr

from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.bot import BotTypeGovernance, CompassChannelGovernanceBotInstance
from csbot.slackbot.issue_creator.github import GithubIssueCreator
from csbot.slackbot.slack_types import SlackInteractivePayload
from csbot.slackbot.slackbot_core import AnthropicConfig


class TestThumbsUpDown(unittest.TestCase):
    """Test cases for thumbs up/down voting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock all dependencies
        self.mock_key = Mock()
        self.mock_key.to_bot_id.return_value = "test_bot_id"

        self.mock_logger = Mock()
        self.mock_client = AsyncMock()
        self.mock_kv_store = AsyncMock()
        self.mock_analytics_store = AsyncMock()
        self.mock_bot_config = Mock()
        self.mock_bot_server = Mock()

        # Create mock ai_config
        mock_ai_config = AnthropicConfig(
            provider="anthropic",
            api_key=SecretStr("test_api_key"),
            model="claude-sonnet-4-20250514",
        )

        # Create bot instance with minimal mocking
        target_bot_key = BotKey.from_channel_name("test", "test")
        self.bot = CompassChannelGovernanceBotInstance(
            key=self.mock_key,
            logger=self.mock_logger,
            github_config=Mock(),
            local_context_store=Mock(),
            client=self.mock_client,
            bot_background_task_manager=AsyncMock(),
            ai_config=mock_ai_config,
            kv_store=self.mock_kv_store,
            governance_alerts_channel="governance",
            analytics_store=self.mock_analytics_store,
            profile=Mock(),
            csbot_client=Mock(),
            data_request_github_creds=Mock(),
            slackbot_github_monitor=Mock(),
            scaffold_branch_enabled=False,
            bot_config=self.mock_bot_config,
            bot_type=BotTypeGovernance(governed_bot_keys=set([target_bot_key])),
            server_config=Mock(),
            storage=Mock(),
            issue_creator=GithubIssueCreator(Mock()),
        )
        self.mock_bot_server.bots = {target_bot_key: self.bot}

        # Common test data
        self.channel_id = "C123456789"
        self.message_ts = "1234567890.123456"
        self.thread_ts = "1234567890.123456"
        self.user_id = "U123456789"

        # Base payload for thumbs interactions
        self.base_payload = {
            "user": {"id": self.user_id},
            "message": {"ts": self.message_ts, "blocks": []},
        }

    def _create_thumbs_payload(
        self, action: str, thread_ts: str | None = None
    ) -> SlackInteractivePayload:
        """Create a thumbs up/down interaction payload."""
        return cast(
            "SlackInteractivePayload",
            {
                **self.base_payload,
                "actions": [
                    {
                        "action_id": action,
                        "value": json.dumps(
                            {"channel": self.channel_id, "thread_ts": thread_ts or self.thread_ts}
                        ),
                    }
                ],
            },
        )

    def _create_message_with_thumbs_buttons(
        self, thumbs_up_count: int = 0, thumbs_down_count: int = 0
    ) -> dict[str, Any]:
        """Create a message with thumbs up/down buttons."""
        thumbs_up_text = f"👍 {thumbs_up_count if thumbs_up_count > 0 else ''}".strip()
        thumbs_down_text = f"👎 {thumbs_down_count if thumbs_down_count > 0 else ''}".strip()

        return {
            "ts": self.message_ts,
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "Some message text"}},
                {
                    "type": "actions",
                    "block_id": "thumbs_actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "🌐 See all steps"},
                            "action_id": "view_thread_steps",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": thumbs_up_text},
                            "action_id": "thumbs_up",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": thumbs_down_text},
                            "action_id": "thumbs_down",
                        },
                    ],
                },
            ],
        }

    def test_empty_to_upvote(self):
        """Test transitioning from empty state to upvote."""

        async def run_test():
            # Mock KV store to return empty state
            self.mock_kv_store.get.return_value = None

            # Create payload and message
            payload = self._create_thumbs_payload("thumbs_up")
            payload["message"] = self._create_message_with_thumbs_buttons()

            # Handle the interaction
            result = await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            self.assertTrue(result)

            # Verify vote was stored correctly
            vote_key = f"thumbs_votes:{self.channel_id}:{self.message_ts}"
            expected_votes = {
                "thumbs_up": 1,
                "thumbs_down": 0,
                "user_votes": {self.user_id: "thumbs_up"},
            }

            self.mock_kv_store.set.assert_any_call("thumbs", vote_key, json.dumps(expected_votes))

            # Verify analytics event was logged
            self.mock_analytics_store.log_analytics_event_with_enriched_user.assert_called_once()

            # Verify message update
            self.mock_client.chat_update.assert_called_once()
            call_args = self.mock_client.chat_update.call_args
            updated_blocks = call_args[1]["blocks"]

            # Find thumbs buttons and verify counts
            thumbs_actions = None
            for block in updated_blocks:
                if block.get("block_id") == "thumbs_actions":
                    thumbs_actions = block
                    break

            self.assertIsNotNone(thumbs_actions)
            assert thumbs_actions is not None  # Type guard for mypy
            elements = thumbs_actions["elements"]

            # Find thumbs up button
            thumbs_up_button = None
            for element in elements:
                if element.get("action_id") == "thumbs_up":
                    thumbs_up_button = element
                    break

            self.assertIsNotNone(thumbs_up_button)
            assert thumbs_up_button is not None  # Type guard for mypy
            self.assertEqual(thumbs_up_button["text"]["text"], "👍 1")

        asyncio.run(run_test())

    def test_empty_to_downvote(self):
        """Test transitioning from empty state to downvote."""

        async def run_test():
            # Mock KV store to return empty state
            self.mock_kv_store.get.return_value = None

            # Create payload and message
            payload = self._create_thumbs_payload("thumbs_down")
            payload["message"] = self._create_message_with_thumbs_buttons()

            # Handle the interaction
            result = await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            self.assertTrue(result)

            # Verify vote was stored correctly
            vote_key = f"thumbs_votes:{self.channel_id}:{self.message_ts}"
            expected_votes = {
                "thumbs_up": 0,
                "thumbs_down": 1,
                "user_votes": {self.user_id: "thumbs_down"},
            }

            self.mock_kv_store.set.assert_any_call("thumbs", vote_key, json.dumps(expected_votes))

            # Verify analytics event was logged
            self.mock_analytics_store.log_analytics_event_with_enriched_user.assert_called_once()

        asyncio.run(run_test())

    def test_upvote_to_downvote(self):
        """Test switching from upvote to downvote."""

        async def run_test():
            # Mock KV store to return existing upvote state
            existing_votes = {
                "thumbs_up": 1,
                "thumbs_down": 0,
                "user_votes": {self.user_id: "thumbs_up"},
            }
            self.mock_kv_store.get.return_value = json.dumps(existing_votes)

            # Create payload and message
            payload = self._create_thumbs_payload("thumbs_down")
            payload["message"] = self._create_message_with_thumbs_buttons(1, 0)

            # Handle the interaction
            await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            # Verify vote was updated correctly
            vote_key = f"thumbs_votes:{self.channel_id}:{self.message_ts}"
            expected_votes = {
                "thumbs_up": 0,
                "thumbs_down": 1,
                "user_votes": {self.user_id: "thumbs_down"},
            }

            self.mock_kv_store.set.assert_any_call("thumbs", vote_key, json.dumps(expected_votes))

            # Verify analytics event was logged
            self.mock_analytics_store.log_analytics_event_with_enriched_user.assert_called_once()

        asyncio.run(run_test())

    def test_downvote_to_upvote(self):
        """Test switching from downvote to upvote."""

        async def run_test():
            # Mock KV store to return existing downvote state
            existing_votes = {
                "thumbs_up": 0,
                "thumbs_down": 1,
                "user_votes": {self.user_id: "thumbs_down"},
            }
            self.mock_kv_store.get.return_value = json.dumps(existing_votes)

            # Create payload and message
            payload = self._create_thumbs_payload("thumbs_up")
            payload["message"] = self._create_message_with_thumbs_buttons(0, 1)

            # Handle the interaction
            await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            # Verify vote was updated correctly
            vote_key = f"thumbs_votes:{self.channel_id}:{self.message_ts}"
            expected_votes = {
                "thumbs_up": 1,
                "thumbs_down": 0,
                "user_votes": {self.user_id: "thumbs_up"},
            }

            self.mock_kv_store.set.assert_any_call("thumbs", vote_key, json.dumps(expected_votes))

            # Verify analytics event was logged
            self.mock_analytics_store.log_analytics_event_with_enriched_user.assert_called_once()

        asyncio.run(run_test())

    def test_upvote_reset(self):
        """Test clicking upvote twice to reset vote."""

        async def run_test():
            # Mock KV store to return existing upvote state
            existing_votes = {
                "thumbs_up": 1,
                "thumbs_down": 0,
                "user_votes": {self.user_id: "thumbs_up"},
            }
            self.mock_kv_store.get.return_value = json.dumps(existing_votes)

            # Create payload and message
            payload = self._create_thumbs_payload("thumbs_up")
            payload["message"] = self._create_message_with_thumbs_buttons(1, 0)

            # Handle the interaction
            await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            # Verify vote was reset
            vote_key = f"thumbs_votes:{self.channel_id}:{self.message_ts}"
            expected_votes = {"thumbs_up": 0, "thumbs_down": 0, "user_votes": {self.user_id: None}}

            self.mock_kv_store.set.assert_any_call("thumbs", vote_key, json.dumps(expected_votes))

            # Verify analytics event was logged
            self.mock_analytics_store.log_analytics_event_with_enriched_user.assert_called_once()

        asyncio.run(run_test())

    def test_downvote_reset(self):
        """Test clicking downvote twice to reset vote."""

        async def run_test():
            # Mock KV store to return existing downvote state
            existing_votes = {
                "thumbs_up": 0,
                "thumbs_down": 1,
                "user_votes": {self.user_id: "thumbs_down"},
            }
            self.mock_kv_store.get.return_value = json.dumps(existing_votes)

            # Create payload and message
            payload = self._create_thumbs_payload("thumbs_down")
            payload["message"] = self._create_message_with_thumbs_buttons(0, 1)

            # Handle the interaction
            await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            # Verify vote was reset
            vote_key = f"thumbs_votes:{self.channel_id}:{self.message_ts}"
            expected_votes = {"thumbs_up": 0, "thumbs_down": 0, "user_votes": {self.user_id: None}}

            self.mock_kv_store.set.assert_any_call("thumbs", vote_key, json.dumps(expected_votes))

            # Verify analytics event was logged
            self.mock_analytics_store.log_analytics_event_with_enriched_user.assert_called_once()

        asyncio.run(run_test())

    def test_multiple_users_voting(self):
        """Test multiple users voting on the same message."""

        async def run_test():
            user2_id = "U987654321"

            # Mock KV store to return state with user2 having upvoted
            existing_votes = {
                "thumbs_up": 1,
                "thumbs_down": 0,
                "user_votes": {user2_id: "thumbs_up"},
            }
            self.mock_kv_store.get.return_value = json.dumps(existing_votes)

            # Create payload for user1 downvoting
            payload = self._create_thumbs_payload("thumbs_down")
            payload["message"] = self._create_message_with_thumbs_buttons(1, 0)

            # Handle the interaction
            await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            # Verify both users' votes are tracked
            vote_key = f"thumbs_votes:{self.channel_id}:{self.message_ts}"
            expected_votes = {
                "thumbs_up": 1,  # user2 still has upvote
                "thumbs_down": 1,  # user1 now has downvote
                "user_votes": {user2_id: "thumbs_up", self.user_id: "thumbs_down"},
            }

            self.mock_kv_store.set.assert_any_call("thumbs", vote_key, json.dumps(expected_votes))

        asyncio.run(run_test())

    def test_button_text_updates(self):
        """Test that button text updates correctly with vote counts."""

        async def run_test():
            # Mock KV store to return empty state
            self.mock_kv_store.get.return_value = None

            # Create payload and message
            payload = self._create_thumbs_payload("thumbs_up")
            payload["message"] = self._create_message_with_thumbs_buttons(0, 0)

            # Handle the interaction
            await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            # Verify message update was called
            self.mock_client.chat_update.assert_called_once()
            call_args = self.mock_client.chat_update.call_args
            updated_blocks = call_args[1]["blocks"]

            # Find and verify button texts
            thumbs_actions = None
            for block in updated_blocks:
                if block.get("block_id") == "thumbs_actions":
                    thumbs_actions = block
                    break

            self.assertIsNotNone(thumbs_actions)
            assert thumbs_actions is not None  # Type guard for mypy
            elements = thumbs_actions["elements"]

            # Check thumbs up button shows count
            thumbs_up_button = next(
                (e for e in elements if e.get("action_id") == "thumbs_up"), None
            )
            self.assertIsNotNone(thumbs_up_button)
            assert thumbs_up_button is not None  # Type guard for mypy
            self.assertEqual(thumbs_up_button["text"]["text"], "👍 1")

            # Check thumbs down button shows no count
            thumbs_down_button = next(
                (e for e in elements if e.get("action_id") == "thumbs_down"), None
            )
            self.assertIsNotNone(thumbs_down_button)
            assert thumbs_down_button is not None  # Type guard for mypy
            self.assertEqual(thumbs_down_button["text"]["text"], "👎")

        asyncio.run(run_test())

    def test_missing_message_timestamp(self):
        """Test handling when message timestamp is missing."""

        async def run_test():
            # Create payload with missing message timestamp
            payload = self._create_thumbs_payload("thumbs_up")
            payload["message"] = {"blocks": []}  # No timestamp

            # Handle the interaction
            result = await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            # Should return False and log warning
            self.assertFalse(result)
            self.mock_logger.warning.assert_called_with(
                "No message timestamp found in thumbs payload"
            )

        asyncio.run(run_test())

    def test_invalid_vote_data_structure(self):
        """Test handling of corrupted vote data in KV store."""

        async def run_test():
            # Mock KV store to return invalid data
            self.mock_kv_store.get.return_value = "invalid json"

            # Create payload
            payload = self._create_thumbs_payload("thumbs_up")
            payload["message"] = self._create_message_with_thumbs_buttons()

            # Handle the interaction - should raise exception for invalid JSON
            with self.assertRaises(json.JSONDecodeError):
                await self.bot.handle_interactive_message(self.mock_bot_server, payload)

        asyncio.run(run_test())

    def test_message_update_failure(self):
        """Test handling when message update fails."""

        async def run_test():
            # Mock KV store to return empty state
            self.mock_kv_store.get.return_value = None

            # Mock chat_update to raise exception
            self.mock_client.chat_update.side_effect = Exception("Update failed")

            # Create payload and message
            payload = self._create_thumbs_payload("thumbs_up")
            payload["message"] = self._create_message_with_thumbs_buttons()

            # Handle the interaction - should not raise but log error
            result = await self.bot.handle_interactive_message(self.mock_bot_server, payload)

            # Should return True and still update KV store and log analytics
            self.assertTrue(result)
            self.mock_kv_store.set.assert_called()
            self.mock_analytics_store.log_analytics_event_with_enriched_user.assert_called()
            self.mock_logger.error.assert_called()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
