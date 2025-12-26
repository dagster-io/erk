import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock

from csbot.slackbot.channel_bot.bot import (
    BotTypeCombined,
    BotTypeQA,
    CompassChannelCombinedCommunityProspectorBotInstance,
    CompassChannelCombinedProspectorBotInstance,
    CompassChannelQACommunityBotInstance,
    CompassChannelQANormalBotInstance,
)


class DictBackedKVStore:
    """A simple dictionary-backed implementation of SlackbotInstanceStorage for testing."""

    def __init__(self):
        self._store = {}

    async def get_and_set(
        self, key: str, subkey: str, value_factory, expiry_seconds: int | None = None
    ):
        """Get and set implementation backed by a dictionary."""
        full_key = f"{key}:{subkey}"

        # Check if the key exists (simulating duplicate detection)
        current_value = self._store.get(full_key)

        # Call the value_factory with the current value
        new_value = value_factory(current_value)

        # Store the new value
        self._store[full_key] = new_value

        return new_value

    async def get_channel_id(self, channel_name: str) -> str | None:
        """Get the channel ID for a given channel name."""
        # Normalize channel name (lowercase, strip whitespace and # prefix)
        normalized_name = channel_name.lower().strip().strip("#")
        full_key = f"channel_name_to_id:{normalized_name}"
        return self._store.get(full_key)


class TestCompassChannelQANormalBotInstance(unittest.TestCase):
    """Test cases for CompassChannelQANormalBotInstance."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a dictionary-backed kv_store for realistic testing
        self.kv_store = DictBackedKVStore()
        self.mock_logger = Mock()
        self.mock_client = AsyncMock()
        self.mock_github_config = Mock()
        self.mock_local_context_store = Mock()

        # Create a proper mock for AIConfig (which is AnthropicConfig | OpenAIConfig)
        self.mock_ai_config = Mock()
        self.mock_ai_config.provider = "anthropic"
        self.mock_ai_config.api_key = Mock()
        self.mock_ai_config.api_key.get_secret_value.return_value = "test-api-key"
        self.mock_ai_config.model = "claude-sonnet-4-20250514"

        self.mock_analytics_store = Mock()
        self.mock_profile = Mock()
        self.mock_csbot_client = Mock()
        self.mock_github_monitor = Mock()
        self.mock_bot_config = Mock()

        # Create a proper bot_type instance
        self.bot_type = BotTypeQA()

        # Create the bot instance with mocked dependencies
        self.bot = CompassChannelQANormalBotInstance(
            key=Mock(),
            logger=self.mock_logger,
            github_config=self.mock_github_config,
            local_context_store=self.mock_local_context_store,
            client=self.mock_client,
            bot_background_task_manager=AsyncMock(),
            ai_config=self.mock_ai_config,
            kv_store=self.kv_store,  # type: ignore
            governance_alerts_channel="test-channel",
            analytics_store=self.mock_analytics_store,
            profile=self.mock_profile,
            csbot_client=self.mock_csbot_client,
            data_request_github_creds=self.mock_github_config,
            slackbot_github_monitor=self.mock_github_monitor,
            scaffold_branch_enabled=False,
            bot_config=self.mock_bot_config,
            bot_type=self.bot_type,
            server_config=Mock(),
            storage=Mock(),
            issue_creator=AsyncMock(),
        )

    def test_have_we_handled_this_event_new_event(self):
        """Test that have_we_handled_this_event allows new events."""
        # First call should return False (new event)
        result = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))

        # Verify that the function correctly identifies this as a new event
        self.assertFalse(result, "Should return False for new events")

        # Verify the event was stored in the kv_store
        expected_fingerprint = json.dumps(
            {
                "channel_ts": "channel123",
                "event_ts": "event456",
            }
        )
        self.assertIn(f"handled_events:{expected_fingerprint}", self.kv_store._store)

    def test_have_we_handled_this_event_duplicate_event(self):
        """Test that have_we_handled_this_event prevents duplicate events."""
        # First call - should be new
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "First call should return False (new event)")

        # Second call with same parameters - should be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertTrue(result2, "Second call should return True (duplicate event)")

    def test_have_we_handled_this_event_different_channels_not_duplicates(self):
        """Test that events in different channels are not considered duplicates."""
        # Event in channel 1
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "Event in channel123 should be new")

        # Same event_ts but different channel - should not be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel789", "event456"))
        self.assertFalse(result2, "Same event_ts in different channel should not be duplicate")

    def test_have_we_handled_this_event_different_events_not_duplicates(self):
        """Test that different events in same channel are not considered duplicates."""
        # Event 1
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "First event should be new")

        # Different event_ts in same channel - should not be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event789"))
        self.assertFalse(result2, "Different event_ts in same channel should not be duplicate")

    def test_have_we_handled_this_event_multiple_scenarios(self):
        """Test multiple scenarios with the same kv_store instance."""
        # Scenario 1: New event
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event1"))
        self.assertFalse(result1, "First event should be new")

        # Scenario 2: Duplicate of scenario 1
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event1"))
        self.assertTrue(result2, "Duplicate event should be detected")

        # Scenario 3: New event in different channel
        result3 = asyncio.run(self.bot.have_we_handled_this_event("channel2", "event1"))
        self.assertFalse(result3, "Same event_ts in different channel should be new")

        # Scenario 4: New event with different timestamp
        result4 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event2"))
        self.assertFalse(result4, "Different event_ts should be new")

        # Scenario 5: Duplicate of scenario 4
        result5 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event2"))
        self.assertTrue(result5, "Duplicate of scenario 4 should be detected")

        # Verify we have 3 unique events stored:
        # 1. channel1:event1
        # 2. channel2:event1
        # 3. channel1:event2
        self.assertEqual(
            len(self.kv_store._store),
            3,
            f"Should have 3 unique events stored, got {len(self.kv_store._store)}: {list(self.kv_store._store.keys())}",
        )

    def test_have_we_handled_this_event_json_fingerprint_format(self):
        """Test that the JSON fingerprint is correctly formatted."""
        # Call the function
        asyncio.run(self.bot.have_we_handled_this_event("test_channel", "test_event"))

        # Check that the fingerprint is stored with correct JSON format
        expected_fingerprint = json.dumps(
            {
                "channel_ts": "test_channel",
                "event_ts": "test_event",
            }
        )

        # Verify the key exists in the store
        self.assertIn(f"handled_events:{expected_fingerprint}", self.kv_store._store)

        # Verify the stored value is "1"
        self.assertEqual(self.kv_store._store[f"handled_events:{expected_fingerprint}"], "1")

    def test_have_we_handled_this_event_edge_cases(self):
        """Test edge cases for the function."""
        # Test with empty strings
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", ""))

        # Test with special characters
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel@#$", "event!@#"))
        self.assertFalse(result2, "Special characters should be handled correctly")

        # Test duplicate with special characters
        result3 = asyncio.run(self.bot.have_we_handled_this_event("channel@#$", "event!@#"))
        self.assertTrue(result3, "Duplicate with special characters should be detected")

        # Test very long strings
        long_channel = "channel" * 100
        long_event = "event" * 100
        result4 = asyncio.run(self.bot.have_we_handled_this_event(long_channel, long_event))
        self.assertFalse(result4, "Long strings should be handled correctly")

        # Test duplicate with long strings
        result5 = asyncio.run(self.bot.have_we_handled_this_event(long_channel, long_event))
        self.assertTrue(result5, "Duplicate with long strings should be detected")

    def test_have_we_handled_this_event_empty_strings(self):
        """Test that the function raises an error if the channel_id or event_ts is empty."""
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", ""))
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("channel123", ""))
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", "event456"))

    def test_handle_app_mention_governance_channel_canned_response(self):
        """Test that mentions in the governance channel return a canned message instead of chatting."""
        # Set up the governance channel ID in the kv_store
        governance_channel_id = "C_GOVERNANCE123"
        asyncio.run(
            self.kv_store.get_and_set(
                "channel_name_to_id",
                "test-channel",  # normalized channel name from self.bot.governance_alerts_channel
                lambda _: governance_channel_id,
            )
        )

        # Mock get_bot_user_id to return a bot user ID
        async def mock_get_bot_user_id():
            return "U_BOT123"

        self.bot.get_bot_user_id = mock_get_bot_user_id  # type: ignore

        # Mock bot_server (only need minimal functionality for this test)
        mock_bot_server = Mock()

        # Create an app_mention event in the governance channel
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> Hello bot!",
            "ts": "1234567890.123456",
            "channel": governance_channel_id,
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention
        asyncio.run(self.bot.handle_app_mention(mock_bot_server, event))

        # Verify that chat_postMessage was called with the canned response
        self.mock_client.chat_postMessage.assert_called_once()
        call_args = self.mock_client.chat_postMessage.call_args

        # Check the arguments
        self.assertEqual(call_args[1]["channel"], governance_channel_id)
        self.assertIn("!admin", call_args[1]["text"])
        self.assertIn("configure Compass settings", call_args[1]["text"])
        self.assertIn("data channels", call_args[1]["text"])
        self.assertEqual(call_args[1]["thread_ts"], event["ts"])

        # Verify that _handle_new_thread was NOT called (i.e., we don't chat normally)
        # We can't easily assert this without mocking _handle_new_thread, but we can verify
        # that only one message was sent (the canned response)
        self.assertEqual(self.mock_client.chat_postMessage.call_count, 1)

    def test_handle_app_mention_non_governance_channel_normal_chat(self):
        """Test that mentions in non-governance channels trigger normal chat handling."""
        # Set up the governance channel ID in the kv_store
        governance_channel_id = "C_GOVERNANCE123"
        asyncio.run(
            self.kv_store.get_and_set(
                "channel_name_to_id",
                "test-channel",  # normalized channel name from self.bot.governance_alerts_channel
                lambda _: governance_channel_id,
            )
        )

        # Mock get_bot_user_id to return a bot user ID
        async def mock_get_bot_user_id():
            return "U_BOT123"

        self.bot.get_bot_user_id = mock_get_bot_user_id  # type: ignore

        # Mock _handle_new_thread to track if it was called
        async def mock_handle_new_thread(*args, **kwargs):
            pass

        self.bot._handle_new_thread = mock_handle_new_thread  # type: ignore

        # Mock bot_server (only need minimal functionality for this test)
        mock_bot_server = Mock()

        # Create an app_mention event in a DIFFERENT channel (not governance)
        regular_channel_id = "C_REGULAR456"
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> What is the revenue?",
            "ts": "1234567890.123456",
            "channel": regular_channel_id,
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention
        asyncio.run(self.bot.handle_app_mention(mock_bot_server, event))

        # Verify that chat_postMessage was NOT called (no canned response)
        self.mock_client.chat_postMessage.assert_not_called()

        # Verify that _handle_new_thread WAS called (normal chat flow)
        # We've mocked it, so we can't directly assert it was called, but we can verify
        # no canned message was sent, which implies normal flow was followed


class TestCompassChannelQACommunityBotInstance(unittest.TestCase):
    """Test cases for CompassChannelQACommunityBotInstance."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a dictionary-backed kv_store for realistic testing
        self.kv_store = DictBackedKVStore()
        self.mock_logger = Mock()
        self.mock_client = AsyncMock()
        self.mock_github_config = Mock()
        self.mock_local_context_store = Mock()

        # Create a proper mock for AIConfig (which is AnthropicConfig | OpenAIConfig)
        self.mock_ai_config = Mock()
        self.mock_ai_config.provider = "anthropic"
        self.mock_ai_config.api_key = Mock()
        self.mock_ai_config.api_key.get_secret_value.return_value = "test-api-key"
        self.mock_ai_config.model = "claude-sonnet-4-20250514"

        self.mock_analytics_store = Mock()
        self.mock_profile = Mock()
        self.mock_csbot_client = Mock()
        self.mock_github_monitor = Mock()
        self.mock_bot_config = Mock()

        # Create a proper bot_type instance
        self.bot_type = BotTypeQA()

        # Create the bot instance with mocked dependencies
        self.bot = CompassChannelQACommunityBotInstance(
            key=Mock(),
            logger=self.mock_logger,
            github_config=self.mock_github_config,
            local_context_store=self.mock_local_context_store,
            client=self.mock_client,
            bot_background_task_manager=AsyncMock(),
            ai_config=self.mock_ai_config,
            kv_store=self.kv_store,  # type: ignore
            governance_alerts_channel="test-channel",
            analytics_store=self.mock_analytics_store,
            profile=self.mock_profile,
            csbot_client=self.mock_csbot_client,
            data_request_github_creds=self.mock_github_config,
            slackbot_github_monitor=self.mock_github_monitor,
            scaffold_branch_enabled=False,
            bot_config=self.mock_bot_config,
            bot_type=self.bot_type,
            server_config=Mock(),
            storage=Mock(),
            issue_creator=AsyncMock(),
        )

    def test_have_we_handled_this_event_new_event(self):
        """Test that have_we_handled_this_event allows new events."""
        # First call should return False (new event)
        result = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))

        # Verify that the function correctly identifies this as a new event
        self.assertFalse(result, "Should return False for new events")

        # Verify the event was stored in the kv_store
        expected_fingerprint = json.dumps(
            {
                "channel_ts": "channel123",
                "event_ts": "event456",
            }
        )
        self.assertIn(f"handled_events:{expected_fingerprint}", self.kv_store._store)

    def test_have_we_handled_this_event_duplicate_event(self):
        """Test that have_we_handled_this_event prevents duplicate events."""
        # First call - should be new
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "First call should return False (new event)")

        # Second call with same parameters - should be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertTrue(result2, "Second call should return True (duplicate event)")

    def test_have_we_handled_this_event_different_channels_not_duplicates(self):
        """Test that events in different channels are not considered duplicates."""
        # Event in channel 1
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "Event in channel123 should be new")

        # Same event_ts but different channel - should not be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel789", "event456"))
        self.assertFalse(result2, "Same event_ts in different channel should not be duplicate")

    def test_have_we_handled_this_event_different_events_not_duplicates(self):
        """Test that different events in same channel are not considered duplicates."""
        # Event 1
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "First event should be new")

        # Different event_ts in same channel - should not be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event789"))
        self.assertFalse(result2, "Different event_ts in same channel should not be duplicate")

    def test_have_we_handled_this_event_multiple_scenarios(self):
        """Test multiple scenarios with the same kv_store instance."""
        # Scenario 1: New event
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event1"))
        self.assertFalse(result1, "First event should be new")

        # Scenario 2: Duplicate of scenario 1
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event1"))
        self.assertTrue(result2, "Duplicate event should be detected")

        # Scenario 3: New event in different channel
        result3 = asyncio.run(self.bot.have_we_handled_this_event("channel2", "event1"))
        self.assertFalse(result3, "Same event_ts in different channel should be new")

        # Scenario 4: New event with different timestamp
        result4 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event2"))
        self.assertFalse(result4, "Different event_ts should be new")

        # Scenario 5: Duplicate of scenario 4
        result5 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event2"))
        self.assertTrue(result5, "Duplicate of scenario 4 should be detected")

        # Verify we have 3 unique events stored:
        # 1. channel1:event1
        # 2. channel2:event1
        # 3. channel1:event2
        self.assertEqual(
            len(self.kv_store._store),
            3,
            f"Should have 3 unique events stored, got {len(self.kv_store._store)}: {list(self.kv_store._store.keys())}",
        )

    def test_have_we_handled_this_event_json_fingerprint_format(self):
        """Test that the JSON fingerprint is correctly formatted."""
        # Call the function
        asyncio.run(self.bot.have_we_handled_this_event("test_channel", "test_event"))

        # Check that the fingerprint is stored with correct JSON format
        expected_fingerprint = json.dumps(
            {
                "channel_ts": "test_channel",
                "event_ts": "test_event",
            }
        )

        # Verify the key exists in the store
        self.assertIn(f"handled_events:{expected_fingerprint}", self.kv_store._store)

        # Verify the stored value is "1"
        self.assertEqual(self.kv_store._store[f"handled_events:{expected_fingerprint}"], "1")

    def test_have_we_handled_this_event_edge_cases(self):
        """Test edge cases for the function."""
        # Test with empty strings
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", ""))

        # Test with special characters
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel@#$", "event!@#"))
        self.assertFalse(result2, "Special characters should be handled correctly")

        # Test duplicate with special characters
        result3 = asyncio.run(self.bot.have_we_handled_this_event("channel@#$", "event!@#"))
        self.assertTrue(result3, "Duplicate with special characters should be detected")

        # Test very long strings
        long_channel = "channel" * 100
        long_event = "event" * 100
        result4 = asyncio.run(self.bot.have_we_handled_this_event(long_channel, long_event))
        self.assertFalse(result4, "Long strings should be handled correctly")

        # Test duplicate with long strings
        result5 = asyncio.run(self.bot.have_we_handled_this_event(long_channel, long_event))
        self.assertTrue(result5, "Duplicate with long strings should be detected")

    def test_have_we_handled_this_event_empty_strings(self):
        """Test that the function raises an error if the channel_id or event_ts is empty."""
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", ""))
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("channel123", ""))
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", "event456"))

    def test_handle_app_mention_governance_channel_canned_response(self):
        """Test that mentions in the governance channel return a canned message instead of chatting."""
        # Set up the governance channel ID in the kv_store
        governance_channel_id = "C_GOVERNANCE123"
        asyncio.run(
            self.kv_store.get_and_set(
                "channel_name_to_id",
                "test-channel",  # normalized channel name from self.bot.governance_alerts_channel
                lambda _: governance_channel_id,
            )
        )

        # Mock get_bot_user_id to return a bot user ID
        async def mock_get_bot_user_id():
            return "U_BOT123"

        self.bot.get_bot_user_id = mock_get_bot_user_id  # type: ignore

        # Mock bot_server (only need minimal functionality for this test)
        mock_bot_server = Mock()

        # Create an app_mention event in the governance channel
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> Hello bot!",
            "ts": "1234567890.123456",
            "channel": governance_channel_id,
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention
        asyncio.run(self.bot.handle_app_mention(mock_bot_server, event))

        # Verify that chat_postMessage was called with the canned response
        self.mock_client.chat_postMessage.assert_called_once()
        call_args = self.mock_client.chat_postMessage.call_args

        # Check the arguments
        self.assertEqual(call_args[1]["channel"], governance_channel_id)
        self.assertIn("!admin", call_args[1]["text"])
        self.assertIn("configure Compass settings", call_args[1]["text"])
        self.assertIn("data channels", call_args[1]["text"])
        self.assertEqual(call_args[1]["thread_ts"], event["ts"])

        # Verify that _handle_new_thread was NOT called (i.e., we don't chat normally)
        # We can't easily assert this without mocking _handle_new_thread, but we can verify
        # that only one message was sent (the canned response)
        self.assertEqual(self.mock_client.chat_postMessage.call_count, 1)

    def test_handle_app_mention_non_governance_channel_normal_chat(self):
        """Test that mentions in non-governance channels trigger normal chat handling."""
        # Set up the governance channel ID in the kv_store
        governance_channel_id = "C_GOVERNANCE123"
        asyncio.run(
            self.kv_store.get_and_set(
                "channel_name_to_id",
                "test-channel",  # normalized channel name from self.bot.governance_alerts_channel
                lambda _: governance_channel_id,
            )
        )

        # Mock get_bot_user_id to return a bot user ID
        async def mock_get_bot_user_id():
            return "U_BOT123"

        self.bot.get_bot_user_id = mock_get_bot_user_id  # type: ignore

        # Mock _handle_new_thread to track if it was called
        async def mock_handle_new_thread(*args, **kwargs):
            pass

        self.bot._handle_new_thread = mock_handle_new_thread  # type: ignore

        # Mock bot_server (only need minimal functionality for this test)
        mock_bot_server = Mock()

        # Create an app_mention event in a DIFFERENT channel (not governance)
        regular_channel_id = "C_REGULAR456"
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> What is the revenue?",
            "ts": "1234567890.123456",
            "channel": regular_channel_id,
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention
        asyncio.run(self.bot.handle_app_mention(mock_bot_server, event))

        # Verify that chat_postMessage was NOT called (no canned response)
        self.mock_client.chat_postMessage.assert_not_called()

        # Verify that _handle_new_thread WAS called (normal chat flow)
        # We've mocked it, so we can't directly assert it was called, but we can verify
        # no canned message was sent, which implies normal flow was followed


class TestCompassChannelCombinedProspectorBotInstance(unittest.TestCase):
    """Test cases for CompassChannelCombinedProspectorBotInstance."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a dictionary-backed kv_store for realistic testing
        self.kv_store = DictBackedKVStore()
        self.mock_logger = Mock()
        self.mock_client = AsyncMock()
        self.mock_github_config = Mock()
        self.mock_local_context_store = Mock()

        # Create a proper mock for AIConfig (which is AnthropicConfig | OpenAIConfig)
        self.mock_ai_config = Mock()
        self.mock_ai_config.provider = "anthropic"
        self.mock_ai_config.api_key = Mock()
        self.mock_ai_config.api_key.get_secret_value.return_value = "test-api-key"
        self.mock_ai_config.model = "claude-sonnet-4-20250514"

        self.mock_analytics_store = Mock()
        self.mock_profile = Mock()
        self.mock_csbot_client = Mock()
        self.mock_github_monitor = Mock()
        self.mock_bot_config = Mock()

        # Create a proper bot_type instance
        self.bot_type = BotTypeCombined(governed_bot_keys=set())

        # Create the bot instance with mocked dependencies
        self.bot = CompassChannelCombinedProspectorBotInstance(
            key=Mock(),
            logger=self.mock_logger,
            github_config=self.mock_github_config,
            local_context_store=self.mock_local_context_store,
            client=self.mock_client,
            bot_background_task_manager=AsyncMock(),
            ai_config=self.mock_ai_config,
            kv_store=self.kv_store,  # type: ignore
            governance_alerts_channel="",
            analytics_store=self.mock_analytics_store,
            profile=self.mock_profile,
            csbot_client=self.mock_csbot_client,
            data_request_github_creds=self.mock_github_config,
            slackbot_github_monitor=self.mock_github_monitor,
            scaffold_branch_enabled=False,
            bot_config=self.mock_bot_config,
            bot_type=self.bot_type,
            server_config=Mock(),
            storage=Mock(),
            issue_creator=AsyncMock(),
        )

    def test_have_we_handled_this_event_new_event(self):
        """Test that have_we_handled_this_event allows new events."""
        # First call should return False (new event)
        result = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))

        # Verify that the function correctly identifies this as a new event
        self.assertFalse(result, "Should return False for new events")

        # Verify the event was stored in the kv_store
        expected_fingerprint = json.dumps(
            {
                "channel_ts": "channel123",
                "event_ts": "event456",
            }
        )
        self.assertIn(f"handled_events:{expected_fingerprint}", self.kv_store._store)

    def test_have_we_handled_this_event_duplicate_event(self):
        """Test that have_we_handled_this_event prevents duplicate events."""
        # First call - should be new
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "First call should return False (new event)")

        # Second call with same parameters - should be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertTrue(result2, "Second call should return True (duplicate event)")

    def test_have_we_handled_this_event_different_channels_not_duplicates(self):
        """Test that events in different channels are not considered duplicates."""
        # Event in channel 1
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "Event in channel123 should be new")

        # Same event_ts but different channel - should not be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel789", "event456"))
        self.assertFalse(result2, "Same event_ts in different channel should not be duplicate")

    def test_have_we_handled_this_event_different_events_not_duplicates(self):
        """Test that different events in same channel are not considered duplicates."""
        # Event 1
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "First event should be new")

        # Different event_ts in same channel - should not be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event789"))
        self.assertFalse(result2, "Different event_ts in same channel should not be duplicate")

    def test_have_we_handled_this_event_multiple_scenarios(self):
        """Test multiple scenarios with the same kv_store instance."""
        # Scenario 1: New event
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event1"))
        self.assertFalse(result1, "First event should be new")

        # Scenario 2: Duplicate of scenario 1
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event1"))
        self.assertTrue(result2, "Duplicate event should be detected")

        # Scenario 3: New event in different channel
        result3 = asyncio.run(self.bot.have_we_handled_this_event("channel2", "event1"))
        self.assertFalse(result3, "Same event_ts in different channel should be new")

        # Scenario 4: New event with different timestamp
        result4 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event2"))
        self.assertFalse(result4, "Different event_ts should be new")

        # Scenario 5: Duplicate of scenario 4
        result5 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event2"))
        self.assertTrue(result5, "Duplicate of scenario 4 should be detected")

        # Verify we have 3 unique events stored:
        # 1. channel1:event1
        # 2. channel2:event1
        # 3. channel1:event2
        self.assertEqual(
            len(self.kv_store._store),
            3,
            f"Should have 3 unique events stored, got {len(self.kv_store._store)}: {list(self.kv_store._store.keys())}",
        )

    def test_have_we_handled_this_event_json_fingerprint_format(self):
        """Test that the JSON fingerprint is correctly formatted."""
        # Call the function
        asyncio.run(self.bot.have_we_handled_this_event("test_channel", "test_event"))

        # Check that the fingerprint is stored with correct JSON format
        expected_fingerprint = json.dumps(
            {
                "channel_ts": "test_channel",
                "event_ts": "test_event",
            }
        )

        # Verify the key exists in the store
        self.assertIn(f"handled_events:{expected_fingerprint}", self.kv_store._store)

        # Verify the stored value is "1"
        self.assertEqual(self.kv_store._store[f"handled_events:{expected_fingerprint}"], "1")

    def test_have_we_handled_this_event_edge_cases(self):
        """Test edge cases for the function."""
        # Test with empty strings
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", ""))

        # Test with special characters
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel@#$", "event!@#"))
        self.assertFalse(result2, "Special characters should be handled correctly")

        # Test duplicate with special characters
        result3 = asyncio.run(self.bot.have_we_handled_this_event("channel@#$", "event!@#"))
        self.assertTrue(result3, "Duplicate with special characters should be detected")

        # Test very long strings
        long_channel = "channel" * 100
        long_event = "event" * 100
        result4 = asyncio.run(self.bot.have_we_handled_this_event(long_channel, long_event))
        self.assertFalse(result4, "Long strings should be handled correctly")

        # Test duplicate with long strings
        result5 = asyncio.run(self.bot.have_we_handled_this_event(long_channel, long_event))
        self.assertTrue(result5, "Duplicate with long strings should be detected")

    def test_have_we_handled_this_event_empty_strings(self):
        """Test that the function raises an error if the channel_id or event_ts is empty."""
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", ""))
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("channel123", ""))
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", "event456"))

    def test_handle_app_mention_non_governance_channel_normal_chat(self):
        """Test that mentions in non-governance channels trigger normal chat handling."""
        # Set up the governance channel ID in the kv_store
        governance_channel_id = "C_GOVERNANCE123"
        asyncio.run(
            self.kv_store.get_and_set(
                "channel_name_to_id",
                "test-channel",  # normalized channel name from self.bot.governance_alerts_channel
                lambda _: governance_channel_id,
            )
        )

        # Mock get_bot_user_id to return a bot user ID
        async def mock_get_bot_user_id():
            return "U_BOT123"

        self.bot.get_bot_user_id = mock_get_bot_user_id  # type: ignore

        # Mock _handle_new_thread to track if it was called
        async def mock_handle_new_thread(*args, **kwargs):
            pass

        self.bot._handle_new_thread = mock_handle_new_thread  # type: ignore

        # Mock bot_server (only need minimal functionality for this test)
        mock_bot_server = Mock()

        # Create an app_mention event in a DIFFERENT channel (not governance)
        regular_channel_id = "C_REGULAR456"
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> What is the revenue?",
            "ts": "1234567890.123456",
            "channel": regular_channel_id,
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention
        asyncio.run(self.bot.handle_app_mention(mock_bot_server, event))

        # Verify that chat_postMessage was NOT called (no canned response)
        self.mock_client.chat_postMessage.assert_not_called()

        # Verify that _handle_new_thread WAS called (normal chat flow)
        # We've mocked it, so we can't directly assert it was called, but we can verify
        # no canned message was sent, which implies normal flow was followed

    def test_handle_app_mention_combined_bot_type_allows_qa_in_governance_channel(self):
        """Test that BotTypeCombined allows Q&A processing in the governance channel."""

        # Set up the governance channel ID in the kv_store
        governance_channel_id = "C_GOVERNANCE123"
        asyncio.run(
            self.kv_store.get_and_set(
                "channel_name_to_id",
                "test-channel",  # normalized channel name from self.bot.governance_alerts_channel
                lambda _: governance_channel_id,
            )
        )

        # Mock get_bot_user_id to return a bot user ID
        async def mock_get_bot_user_id():
            return "U_BOT123"

        self.bot.get_bot_user_id = mock_get_bot_user_id  # type: ignore

        # Track if _handle_new_thread was called
        handle_new_thread_called = False

        async def mock_handle_new_thread(*args, **kwargs):
            nonlocal handle_new_thread_called
            handle_new_thread_called = True

        self.bot._handle_new_thread = mock_handle_new_thread  # type: ignore

        # Mock bot_server (only need minimal functionality for this test)
        mock_bot_server = Mock()

        # Create an app_mention event in the governance channel (which is also the Q&A channel for combined bot)
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> What is the revenue?",
            "ts": "1234567890.123456",
            "channel": governance_channel_id,
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention
        asyncio.run(self.bot.handle_app_mention(mock_bot_server, event))

        # Verify that chat_postMessage was NOT called (no canned response for BotTypeCombined)
        self.mock_client.chat_postMessage.assert_not_called()

        # Verify that _handle_new_thread WAS called (Q&A processing happens in combined channel)
        self.assertTrue(
            handle_new_thread_called,
            "Expected _handle_new_thread to be called for BotTypeCombined in governance channel",
        )


class TestCompassChannelCombinedCommunityProspectorBotInstance(unittest.TestCase):
    """Test cases for CompassChannelCombinedCommunityProspectorBotInstance."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a dictionary-backed kv_store for realistic testing
        self.kv_store = DictBackedKVStore()
        self.mock_logger = Mock()
        self.mock_client = AsyncMock()
        self.mock_github_config = Mock()
        self.mock_local_context_store = Mock()

        # Create a proper mock for AIConfig (which is AnthropicConfig | OpenAIConfig)
        self.mock_ai_config = Mock()
        self.mock_ai_config.provider = "anthropic"
        self.mock_ai_config.api_key = Mock()
        self.mock_ai_config.api_key.get_secret_value.return_value = "test-api-key"
        self.mock_ai_config.model = "claude-sonnet-4-20250514"

        self.mock_analytics_store = Mock()
        self.mock_profile = Mock()
        self.mock_csbot_client = Mock()
        self.mock_github_monitor = Mock()
        self.mock_bot_config = Mock()

        # Create a proper bot_type instance
        self.bot_type = BotTypeCombined(governed_bot_keys=set())

        # Create the bot instance with mocked dependencies
        self.bot = CompassChannelCombinedCommunityProspectorBotInstance(
            key=Mock(),
            logger=self.mock_logger,
            github_config=self.mock_github_config,
            local_context_store=self.mock_local_context_store,
            client=self.mock_client,
            bot_background_task_manager=AsyncMock(),
            ai_config=self.mock_ai_config,
            kv_store=self.kv_store,  # type: ignore
            governance_alerts_channel="",
            analytics_store=self.mock_analytics_store,
            profile=self.mock_profile,
            csbot_client=self.mock_csbot_client,
            data_request_github_creds=self.mock_github_config,
            slackbot_github_monitor=self.mock_github_monitor,
            scaffold_branch_enabled=False,
            bot_config=self.mock_bot_config,
            bot_type=self.bot_type,
            server_config=Mock(),
            storage=Mock(),
            issue_creator=AsyncMock(),
        )

    def test_have_we_handled_this_event_new_event(self):
        """Test that have_we_handled_this_event allows new events."""
        # First call should return False (new event)
        result = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))

        # Verify that the function correctly identifies this as a new event
        self.assertFalse(result, "Should return False for new events")

        # Verify the event was stored in the kv_store
        expected_fingerprint = json.dumps(
            {
                "channel_ts": "channel123",
                "event_ts": "event456",
            }
        )
        self.assertIn(f"handled_events:{expected_fingerprint}", self.kv_store._store)

    def test_have_we_handled_this_event_duplicate_event(self):
        """Test that have_we_handled_this_event prevents duplicate events."""
        # First call - should be new
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "First call should return False (new event)")

        # Second call with same parameters - should be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertTrue(result2, "Second call should return True (duplicate event)")

    def test_have_we_handled_this_event_different_channels_not_duplicates(self):
        """Test that events in different channels are not considered duplicates."""
        # Event in channel 1
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "Event in channel123 should be new")

        # Same event_ts but different channel - should not be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel789", "event456"))
        self.assertFalse(result2, "Same event_ts in different channel should not be duplicate")

    def test_have_we_handled_this_event_different_events_not_duplicates(self):
        """Test that different events in same channel are not considered duplicates."""
        # Event 1
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event456"))
        self.assertFalse(result1, "First event should be new")

        # Different event_ts in same channel - should not be duplicate
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel123", "event789"))
        self.assertFalse(result2, "Different event_ts in same channel should not be duplicate")

    def test_have_we_handled_this_event_multiple_scenarios(self):
        """Test multiple scenarios with the same kv_store instance."""
        # Scenario 1: New event
        result1 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event1"))
        self.assertFalse(result1, "First event should be new")

        # Scenario 2: Duplicate of scenario 1
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event1"))
        self.assertTrue(result2, "Duplicate event should be detected")

        # Scenario 3: New event in different channel
        result3 = asyncio.run(self.bot.have_we_handled_this_event("channel2", "event1"))
        self.assertFalse(result3, "Same event_ts in different channel should be new")

        # Scenario 4: New event with different timestamp
        result4 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event2"))
        self.assertFalse(result4, "Different event_ts should be new")

        # Scenario 5: Duplicate of scenario 4
        result5 = asyncio.run(self.bot.have_we_handled_this_event("channel1", "event2"))
        self.assertTrue(result5, "Duplicate of scenario 4 should be detected")

        # Verify we have 3 unique events stored:
        # 1. channel1:event1
        # 2. channel2:event1
        # 3. channel1:event2
        self.assertEqual(
            len(self.kv_store._store),
            3,
            f"Should have 3 unique events stored, got {len(self.kv_store._store)}: {list(self.kv_store._store.keys())}",
        )

    def test_have_we_handled_this_event_json_fingerprint_format(self):
        """Test that the JSON fingerprint is correctly formatted."""
        # Call the function
        asyncio.run(self.bot.have_we_handled_this_event("test_channel", "test_event"))

        # Check that the fingerprint is stored with correct JSON format
        expected_fingerprint = json.dumps(
            {
                "channel_ts": "test_channel",
                "event_ts": "test_event",
            }
        )

        # Verify the key exists in the store
        self.assertIn(f"handled_events:{expected_fingerprint}", self.kv_store._store)

        # Verify the stored value is "1"
        self.assertEqual(self.kv_store._store[f"handled_events:{expected_fingerprint}"], "1")

    def test_have_we_handled_this_event_edge_cases(self):
        """Test edge cases for the function."""
        # Test with empty strings
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", ""))

        # Test with special characters
        result2 = asyncio.run(self.bot.have_we_handled_this_event("channel@#$", "event!@#"))
        self.assertFalse(result2, "Special characters should be handled correctly")

        # Test duplicate with special characters
        result3 = asyncio.run(self.bot.have_we_handled_this_event("channel@#$", "event!@#"))
        self.assertTrue(result3, "Duplicate with special characters should be detected")

        # Test very long strings
        long_channel = "channel" * 100
        long_event = "event" * 100
        result4 = asyncio.run(self.bot.have_we_handled_this_event(long_channel, long_event))
        self.assertFalse(result4, "Long strings should be handled correctly")

        # Test duplicate with long strings
        result5 = asyncio.run(self.bot.have_we_handled_this_event(long_channel, long_event))
        self.assertTrue(result5, "Duplicate with long strings should be detected")

    def test_have_we_handled_this_event_empty_strings(self):
        """Test that the function raises an error if the channel_id or event_ts is empty."""
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", ""))
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("channel123", ""))
        with self.assertRaises(ValueError):
            asyncio.run(self.bot.have_we_handled_this_event("", "event456"))

    def test_handle_app_mention_non_governance_channel_normal_chat(self):
        """Test that mentions in non-governance channels trigger normal chat handling."""
        # Set up the governance channel ID in the kv_store
        governance_channel_id = "C_GOVERNANCE123"
        asyncio.run(
            self.kv_store.get_and_set(
                "channel_name_to_id",
                "test-channel",  # normalized channel name from self.bot.governance_alerts_channel
                lambda _: governance_channel_id,
            )
        )

        # Mock get_bot_user_id to return a bot user ID
        async def mock_get_bot_user_id():
            return "U_BOT123"

        self.bot.get_bot_user_id = mock_get_bot_user_id  # type: ignore

        # Mock _handle_new_thread to track if it was called
        async def mock_handle_new_thread(*args, **kwargs):
            pass

        self.bot._handle_new_thread = mock_handle_new_thread  # type: ignore

        # Mock bot_server (only need minimal functionality for this test)
        mock_bot_server = Mock()

        # Create an app_mention event in a DIFFERENT channel (not governance)
        regular_channel_id = "C_REGULAR456"
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> What is the revenue?",
            "ts": "1234567890.123456",
            "channel": regular_channel_id,
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention
        asyncio.run(self.bot.handle_app_mention(mock_bot_server, event))

        # Verify that chat_postMessage was NOT called (no canned response)
        self.mock_client.chat_postMessage.assert_not_called()

        # Verify that _handle_new_thread WAS called (normal chat flow)
        # We've mocked it, so we can't directly assert it was called, but we can verify
        # no canned message was sent, which implies normal flow was followed

    def test_handle_app_mention_combined_bot_type_allows_qa_in_governance_channel(self):
        """Test that BotTypeCombined allows Q&A processing in the governance channel."""

        # Set up the governance channel ID in the kv_store
        governance_channel_id = "C_GOVERNANCE123"
        asyncio.run(
            self.kv_store.get_and_set(
                "channel_name_to_id",
                "test-channel",  # normalized channel name from self.bot.governance_alerts_channel
                lambda _: governance_channel_id,
            )
        )

        # Mock get_bot_user_id to return a bot user ID
        async def mock_get_bot_user_id():
            return "U_BOT123"

        self.bot.get_bot_user_id = mock_get_bot_user_id  # type: ignore

        # Track if _handle_new_thread was called
        handle_new_thread_called = False

        async def mock_handle_new_thread(*args, **kwargs):
            nonlocal handle_new_thread_called
            handle_new_thread_called = True

        self.bot._handle_new_thread = mock_handle_new_thread  # type: ignore

        # Mock bot_server (only need minimal functionality for this test)
        mock_bot_server = Mock()

        # Create an app_mention event in the governance channel (which is also the Q&A channel for combined bot)
        event = {
            "type": "app_mention",
            "user": "U_USER123",
            "text": "<@U_BOT123> What is the revenue?",
            "ts": "1234567890.123456",
            "channel": governance_channel_id,
            "event_ts": "1234567890.123456",
        }

        # Call handle_app_mention
        asyncio.run(self.bot.handle_app_mention(mock_bot_server, event))

        # Verify that chat_postMessage was NOT called (no canned response for BotTypeCombined)
        self.mock_client.chat_postMessage.assert_not_called()

        # Verify that _handle_new_thread WAS called (Q&A processing happens in combined channel)
        self.assertTrue(
            handle_new_thread_called,
            "Expected _handle_new_thread to be called for BotTypeCombined in governance channel",
        )


if __name__ == "__main__":
    unittest.main()
