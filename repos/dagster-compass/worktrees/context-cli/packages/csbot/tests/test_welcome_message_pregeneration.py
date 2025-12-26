"""Test cases for welcome message pre-generation functionality.

This module tests the welcome message pre-generation flow including:
- Email to user_id lookup
- Welcome message caching in KV store
- Cache retrieval and fallback to fresh generation
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import SecretStr

from csbot.slackbot.channel_bot.bot import (
    CompassChannelQANormalBotInstance,
)
from csbot.slackbot.slack_utils import lookup_user_id_by_email
from csbot.slackbot.slackbot_core import AnthropicConfig


@pytest.fixture
def mock_bot():
    """Create a mock bot instance for testing."""
    mock_key = Mock()
    mock_key.to_bot_id.return_value = "test_bot_id"

    mock_ai_config = AnthropicConfig(
        provider="anthropic",
        api_key=SecretStr("test_api_key"),
        model="claude-sonnet-4-20250514",
    )

    mock_kv_store = AsyncMock()
    mock_client = AsyncMock()
    mock_logger = Mock()

    bot_config = {
        "key": mock_key,
        "logger": mock_logger,
        "github_config": Mock(),
        "local_context_store": Mock(),
        "ai_config": mock_ai_config,
        "kv_store": mock_kv_store,
        "governance_alerts_channel": "governance",
        "profile": Mock(),
        "csbot_client": Mock(),
        "data_request_github_creds": Mock(),
        "slackbot_github_monitor": Mock(),
        "scaffold_branch_enabled": False,
        "bot_type": Mock(),
        "bot_background_task_manager": AsyncMock(),
        "server_config": Mock(),
        "storage": Mock(),
        "client": mock_client,
        "analytics_store": AsyncMock(),
        "bot_config": Mock(),
        "issue_creator": Mock(),
    }

    bot = CompassChannelQANormalBotInstance(**bot_config)
    return {
        "bot": bot,
        "kv_store": mock_kv_store,
        "client": mock_client,
        "logger": mock_logger,
    }


class TestLookupUserIdByEmail:
    """Test cases for lookup_user_id_by_email utility function."""

    @pytest.mark.asyncio
    async def test_successful_lookup(self):
        """Test successful email to user_id resolution."""
        mock_client = AsyncMock()
        mock_logger = Mock()

        mock_client.users_lookupByEmail.return_value = {
            "ok": True,
            "user": {"id": "U123456", "name": "test_user"},
        }

        user_id = await lookup_user_id_by_email(mock_client, "test@example.com", mock_logger)

        assert user_id == "U123456"
        mock_client.users_lookupByEmail.assert_called_once_with(email="test@example.com")
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_lookup_user_not_found(self):
        """Test lookup when user doesn't exist in workspace."""
        mock_client = AsyncMock()
        mock_logger = Mock()

        mock_client.users_lookupByEmail.return_value = {
            "ok": False,
            "error": "users_not_found",
        }

        user_id = await lookup_user_id_by_email(mock_client, "notfound@example.com", mock_logger)

        assert user_id is None
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_lookup_with_exception(self):
        """Test lookup when API call raises exception."""
        mock_client = AsyncMock()
        mock_logger = Mock()

        mock_client.users_lookupByEmail.side_effect = Exception("API error")

        user_id = await lookup_user_id_by_email(mock_client, "error@example.com", mock_logger)

        assert user_id is None
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_lookup_with_no_client(self):
        """Test lookup when client is None."""
        mock_logger = Mock()

        user_id = await lookup_user_id_by_email(None, "test@example.com", mock_logger)

        assert user_id is None
        mock_logger.debug.assert_called()


class TestWelcomeMessagePregeneration:
    """Test cases for pregenerate_and_store_welcome_message functionality."""

    @pytest.mark.asyncio
    async def test_successful_pregeneration_with_user_id(self, mock_bot):
        """Test successful welcome message pre-generation with user_id."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock get_bot_user_id
        with patch.object(bot, "get_bot_user_id", return_value="UBOT123"):
            # Mock generate_welcome_message_and_follow_up_question
            with patch.object(
                bot,
                "generate_welcome_message_and_follow_up_question",
                return_value=("Welcome message", "Follow-up question"),
            ):
                await bot.pregenerate_and_store_welcome_message("U123456", None)

                # Verify KV store was called with correct data
                kv_store.set.assert_called_once()
                call_args = kv_store.set.call_args
                assert call_args[0][0] == "welcome_message"
                # Cache key format is bot_user_id:user_id
                assert call_args[0][1] == "UBOT123:U123456"

                stored_data = json.loads(call_args[0][2])
                assert stored_data["welcome_message"] == "Welcome message"
                assert stored_data["follow_up_question"] == "Follow-up question"

    @pytest.mark.asyncio
    async def test_successful_pregeneration_with_email_lookup(self, mock_bot):
        """Test successful welcome message pre-generation with email lookup."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock get_bot_user_id
        with patch.object(bot, "get_bot_user_id", return_value="UBOT123"):
            # Mock lookup_user_id_by_email to return a user_id
            # Since it's imported within the function, patch it in slack_utils
            with patch(
                "csbot.slackbot.slack_utils.lookup_user_id_by_email",
                return_value="U123456",
            ):
                # Mock generate_welcome_message_and_follow_up_question
                with patch.object(
                    bot,
                    "generate_welcome_message_and_follow_up_question",
                    return_value=("Welcome message", "Follow-up question"),
                ):
                    await bot.pregenerate_and_store_welcome_message(None, "test@example.com")

                    # Verify KV store was called with resolved user_id
                    kv_store.set.assert_called_once()
                    call_args = kv_store.set.call_args
                    assert call_args[0][1] == "UBOT123:U123456"

    @pytest.mark.asyncio
    async def test_pregeneration_email_lookup_fails_uses_email_key(self, mock_bot):
        """Test pre-generation when email lookup fails - uses email-based cache key."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock get_bot_user_id
        with patch.object(bot, "get_bot_user_id", return_value="UBOT123"):
            # Mock lookup_user_id_by_email to return None
            with patch(
                "csbot.slackbot.slack_utils.lookup_user_id_by_email",
                return_value=None,
            ):
                # Mock generate_welcome_message_and_follow_up_question for email-based generation
                with patch.object(
                    bot,
                    "generate_welcome_message_and_follow_up_question",
                    return_value=("Email-based welcome", "Email-based question"),
                ):
                    await bot.pregenerate_and_store_welcome_message(None, "user@example.com")

                    # Should store welcome message with email-based key (bot_user_id:email)
                    kv_store.set.assert_called_once()
                    call_args = kv_store.set.call_args
                    assert call_args[0][1] == "UBOT123:user@example.com"  # Email-based key format

    @pytest.mark.asyncio
    async def test_pregeneration_no_bot_user_id(self, mock_bot):
        """Test pre-generation when bot_user_id cannot be retrieved."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock get_bot_user_id to return None
        with patch.object(bot, "get_bot_user_id", return_value=None):
            await bot.pregenerate_and_store_welcome_message("U123456", None)

            # Should not attempt to store in KV
            kv_store.set.assert_not_called()


class TestWelcomeMessageRetrieval:
    """Test cases for get_welcome_message_and_follow_up_question functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit(self, mock_bot):
        """Test retrieving welcome message from cache."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock cached data
        cached_data = json.dumps(
            {
                "welcome_message": "Cached welcome",
                "follow_up_question": "Cached question",
            }
        )
        kv_store.get.return_value = cached_data

        welcome_msg, follow_up = await bot.get_welcome_message_and_follow_up_question(
            "UBOT123", "U123456"
        )

        assert welcome_msg == "Cached welcome"
        assert follow_up == "Cached question"

        # Verify cache was checked with correct key format (bot_user_id:user_id)
        kv_store.get.assert_called_once_with("welcome_message", "UBOT123:U123456")
        kv_store.delete.assert_called_once_with("welcome_message", "UBOT123:U123456")

    @pytest.mark.asyncio
    async def test_cache_hit_email_based(self, mock_bot):
        """Test retrieving email-based welcome message when personalized not available."""
        from csbot.slackbot.channel_bot.personalization import EnrichedPerson

        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock cached email-based data (personalized returns None, email-based returns data)
        cached_data = json.dumps(
            {
                "welcome_message": "Email-based welcome",
                "follow_up_question": "Email-based question",
            }
        )

        def get_side_effect(family, key):
            if key == "UBOT123:U123456":
                return None  # No personalized message
            elif key == "UBOT123:user@example.com":
                return cached_data  # Email-based message exists
            return None

        kv_store.get.side_effect = get_side_effect

        # Mock get_enriched_person to return person with email
        mock_person = EnrichedPerson(
            real_name="Test User", email="user@example.com", job_title="Engineer", timezone="UTC"
        )
        with patch.object(bot, "get_enriched_person", return_value=mock_person):
            welcome_msg, follow_up = await bot.get_welcome_message_and_follow_up_question(
                "UBOT123", "U123456"
            )

            assert welcome_msg == "Email-based welcome"
            assert follow_up == "Email-based question"

            # Verify email-based cache was found and deleted
            kv_store.delete.assert_called_once_with("welcome_message", "UBOT123:user@example.com")

    @pytest.mark.asyncio
    async def test_cache_miss_no_email_generates_fresh(self, mock_bot):
        """Test generating fresh message when no cached message and user has no email."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock cache miss for all lookups
        kv_store.get.return_value = None

        # Mock get_enriched_person to return person without email
        with patch.object(bot, "get_enriched_person", return_value=None):
            # Mock fresh generation
            with patch.object(
                bot,
                "generate_welcome_message_and_follow_up_question",
                return_value=("Fresh welcome", "Fresh question"),
            ):
                welcome_msg, follow_up = await bot.get_welcome_message_and_follow_up_question(
                    "UBOT123", "U123456"
                )

                assert welcome_msg == "Fresh welcome"
                assert follow_up == "Fresh question"

                # Verify cache was checked once (personalized only, no email to check)
                assert kv_store.get.call_count == 1  # Only personalized check since no email
                kv_store.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_with_email_generates_fresh(self, mock_bot):
        """Test generating fresh welcome message when cache misses for user with email."""
        from csbot.slackbot.channel_bot.personalization import EnrichedPerson

        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock cache miss for all lookups (personalized, email-based)
        kv_store.get.return_value = None

        # Mock get_enriched_person to return person with email
        mock_person = EnrichedPerson(
            real_name="Test User", email="user@example.com", job_title="Engineer", timezone="UTC"
        )

        with patch.object(bot, "get_enriched_person", return_value=mock_person):
            # Mock fresh generation
            with patch.object(
                bot,
                "generate_welcome_message_and_follow_up_question",
                return_value=("Fresh welcome", "Fresh question"),
            ):
                welcome_msg, follow_up = await bot.get_welcome_message_and_follow_up_question(
                    "UBOT123", "U123456"
                )

                assert welcome_msg == "Fresh welcome"
                assert follow_up == "Fresh question"

                # Verify cache was checked twice (personalized, email-based) but not deleted
                assert kv_store.get.call_count == 2
                kv_store.get.assert_any_call("welcome_message", "UBOT123:U123456")  # Personalized
                kv_store.get.assert_any_call(
                    "welcome_message", "UBOT123:user@example.com"
                )  # Email-based
                kv_store.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_corrupt_falls_back_to_fresh(self, mock_bot):
        """Test fallback to fresh generation when cached data is corrupt."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock corrupted cached data
        kv_store.get.return_value = "invalid json"

        # Mock fresh generation
        with patch.object(
            bot,
            "generate_welcome_message_and_follow_up_question",
            return_value=("Fresh welcome", "Fresh question"),
        ):
            welcome_msg, follow_up = await bot.get_welcome_message_and_follow_up_question(
                "UBOT123", "U123456"
            )

            assert welcome_msg == "Fresh welcome"
            assert follow_up == "Fresh question"

            # Verify cache was checked but not deleted (parse failed)
            kv_store.get.assert_called_once()
            kv_store.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_missing_fields_falls_back(self, mock_bot):
        """Test fallback when cached data is missing required fields."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]

        # Mock cached data with missing field
        cached_data = json.dumps({"welcome_message": "Cached welcome"})
        kv_store.get.return_value = cached_data

        # Mock fresh generation
        with patch.object(
            bot,
            "generate_welcome_message_and_follow_up_question",
            return_value=("Fresh welcome", "Fresh question"),
        ):
            welcome_msg, follow_up = await bot.get_welcome_message_and_follow_up_question(
                "UBOT123", "U123456"
            )

            assert welcome_msg == "Fresh welcome"
            assert follow_up == "Fresh question"


class TestSendWelcomeMessage:
    """Test cases for _send_welcome_message using cached content."""

    @pytest.mark.asyncio
    async def test_send_uses_cached_message(self, mock_bot):
        """Test that _send_welcome_message uses cached content when available."""
        bot = mock_bot["bot"]
        kv_store = mock_bot["kv_store"]
        client = mock_bot["client"]

        # Mock cached data
        cached_data = json.dumps(
            {
                "welcome_message": "Cached welcome",
                "follow_up_question": "Cached question",
            }
        )
        kv_store.get.return_value = cached_data

        # Mock bot user ID
        with patch.object(bot, "get_bot_user_id", return_value="UBOT123"):
            # Mock Slack API response
            client.chat_postEphemeral.return_value = {"ok": True, "ts": "123.456"}

            await bot._send_welcome_message("C123456", "U123456")

            # Verify ephemeral message was sent
            client.chat_postEphemeral.assert_called_once()
            call_args = client.chat_postEphemeral.call_args
            assert call_args[1]["channel"] == "C123456"
            assert call_args[1]["user"] == "U123456"
            assert "Cached welcome" in call_args[1]["text"]

            # Verify cache was used
            kv_store.get.assert_called_once()
            kv_store.delete.assert_called_once()
