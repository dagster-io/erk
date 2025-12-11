"""
Unit tests for user mention resolution functionality.

Tests the resolve_user_mentions_in_message and get_cached_user_info functions
in the personalization module.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from csbot.slackbot.channel_bot.personalization import (
    EnrichedPerson,
    SlackUserInfo,
    get_cached_user_info,
    resolve_user_mentions_in_message,
)


class MockKVStore:
    """Mock KV store for testing."""

    def __init__(self):
        self.cache = {}

    async def get(self, namespace: str, key: str) -> str | None:
        """Get value from cache."""
        return self.cache.get(f"{namespace}:{key}")

    async def set(self, namespace: str, key: str, value: str, ttl: int) -> None:
        """Set value in cache."""
        self.cache[f"{namespace}:{key}"] = value


@pytest.fixture
def kv_store():
    """Create a mock KV store for testing."""
    return MockKVStore()


@pytest.fixture
def mock_client():
    """Create a mock Slack client for testing."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_resolve_user_mentions_no_mentions(kv_store, mock_client):
    """Test that messages without user mentions are unchanged."""
    message = "Hello world, no mentions here!"
    result = await resolve_user_mentions_in_message(mock_client, kv_store, message)
    assert result == message


@pytest.mark.asyncio
async def test_resolve_user_mentions_single_mention(kv_store, mock_client):
    """Test resolution of a single user mention."""
    with patch(
        "csbot.slackbot.channel_bot.personalization.get_person_info_from_slack_user_id"
    ) as mock_get_person_info:
        mock_get_person_info.return_value = EnrichedPerson(
            real_name="John Doe", job_title="Software Engineer", timezone="America/New_York"
        )

        message = "Hello <@U123456>!"
        result = await resolve_user_mentions_in_message(mock_client, kv_store, message)
        expected = "Hello <@U123456> (John Doe, Software Engineer)!"
        assert result == expected


@pytest.mark.asyncio
async def test_resolve_user_mentions_multiple_mentions(kv_store, mock_client):
    """Test resolution of multiple user mentions."""
    with patch(
        "csbot.slackbot.channel_bot.personalization.get_person_info_from_slack_user_id"
    ) as mock_get_person_info:

        def mock_person_info(client, kv_store, user_id):
            users = {
                "U123456": EnrichedPerson(
                    real_name="John Doe", job_title="Software Engineer", timezone="America/New_York"
                ),
                "U789012": EnrichedPerson(
                    real_name="Jane Smith",
                    job_title="Product Manager",
                    timezone="America/Los_Angeles",
                ),
            }
            return users.get(user_id)

        mock_get_person_info.side_effect = mock_person_info

        message = "Hey <@U123456> and <@U789012>!"
        result = await resolve_user_mentions_in_message(mock_client, kv_store, message)
        expected = "Hey <@U123456> (John Doe, Software Engineer) and <@U789012> (Jane Smith, Product Manager)!"
        assert result == expected


@pytest.mark.asyncio
async def test_resolve_user_mentions_fallback_to_cached_user_info(kv_store, mock_client):
    """Test fallback to cached user info when person info is not available."""
    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_person_info_from_slack_user_id"
        ) as mock_get_person_info,
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info"
        ) as mock_get_cached_user_info,
    ):
        mock_get_person_info.return_value = None
        mock_get_cached_user_info.return_value = SlackUserInfo(
            real_name="Bob Johnson",
            username="bob.johnson",
            email=None,
            avatar_url=None,
            timezone=None,
            is_bot=False,
            is_admin=False,
            is_owner=False,
            deleted=False,
            is_restricted=False,
            is_ultra_restricted=False,
        )

        message = "Hello <@U345678>!"
        result = await resolve_user_mentions_in_message(mock_client, kv_store, message)
        expected = "Hello <@U345678> (Bob Johnson)!"
        assert result == expected


@pytest.mark.asyncio
async def test_resolve_user_mentions_user_not_found(kv_store, mock_client):
    """Test handling of users that cannot be resolved."""
    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_person_info_from_slack_user_id"
        ) as mock_get_person_info,
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info"
        ) as mock_get_cached_user_info,
    ):
        mock_get_person_info.return_value = None
        mock_get_cached_user_info.return_value = None

        message = "Hello <@U999999>!"
        result = await resolve_user_mentions_in_message(mock_client, kv_store, message)
        # Should keep original mention when user not found
        assert result == message


@pytest.mark.asyncio
async def test_resolve_user_mentions_duplicate_mentions(kv_store, mock_client):
    """Test resolution of duplicate user mentions."""
    with patch(
        "csbot.slackbot.channel_bot.personalization.get_person_info_from_slack_user_id"
    ) as mock_get_person_info:
        mock_get_person_info.return_value = EnrichedPerson(
            real_name="John Doe", job_title="Software Engineer", timezone="America/New_York"
        )

        message = "Hey <@U123456>, <@U123456> again!"
        result = await resolve_user_mentions_in_message(mock_client, kv_store, message)
        expected = "Hey <@U123456> (John Doe, Software Engineer), <@U123456> (John Doe, Software Engineer) again!"
        assert result == expected


@pytest.mark.asyncio
async def test_resolve_user_mentions_mixed_resolution(kv_store, mock_client):
    """Test resolution with some users found and some not found."""
    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_person_info_from_slack_user_id"
        ) as mock_get_person_info,
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info"
        ) as mock_get_cached_user_info,
    ):

        def mock_person_info(client, kv_store, user_id):
            if user_id == "U123456":
                return EnrichedPerson(
                    real_name="John Doe", job_title="Software Engineer", timezone="America/New_York"
                )
            return None

        def mock_cached_user_info(client, kv_store, user_id):
            if user_id == "U789012":
                return SlackUserInfo(
                    real_name="Jane Smith",
                    username="jane.smith",
                    email=None,
                    avatar_url=None,
                    timezone=None,
                    is_bot=False,
                    is_admin=False,
                    is_owner=False,
                    deleted=False,
                    is_restricted=False,
                    is_ultra_restricted=False,
                )
            return None

        mock_get_person_info.side_effect = mock_person_info
        mock_get_cached_user_info.side_effect = mock_cached_user_info

        message = "Hey <@U123456>, <@U789012>, and <@U999999>!"
        result = await resolve_user_mentions_in_message(mock_client, kv_store, message)
        expected = (
            "Hey <@U123456> (John Doe, Software Engineer), <@U789012> (Jane Smith), and <@U999999>!"
        )
        assert result == expected


@pytest.mark.asyncio
async def test_get_cached_user_info_cache_hit(kv_store, mock_client):
    """Test get_cached_user_info with cache hit."""
    # Pre-populate cache
    user_info = {
        "real_name": "John Doe",
        "name": "john.doe",
        "profile": {"email": "john@example.com", "image_72": "http://example.com/avatar.jpg"},
        "tz": "America/New_York",
        "is_bot": False,
        "is_admin": False,
        "is_owner": False,
        "deleted": False,
        "is_restricted": False,
        "is_ultra_restricted": False,
    }
    await kv_store.set("user_info", "U123456", json.dumps({"value": user_info}), 3600)

    result = await get_cached_user_info(mock_client, kv_store, "U123456")
    expected = SlackUserInfo(
        real_name="John Doe",
        username="john.doe",
        email="john@example.com",
        avatar_url="http://example.com/avatar.jpg",
        timezone="America/New_York",
        is_bot=False,
        is_admin=False,
        is_owner=False,
        deleted=False,
        is_restricted=False,
        is_ultra_restricted=False,
    )
    assert result == expected
    # Should not call the API
    mock_client.users_info.assert_not_called()


@pytest.mark.asyncio
async def test_get_cached_user_info_cache_miss(kv_store, mock_client):
    """Test get_cached_user_info with cache miss."""
    # Mock API response
    mock_client.users_info.return_value = {
        "ok": True,
        "user": {
            "real_name": "John Doe",
            "name": "john.doe",
            "profile": {"email": "john@example.com", "image_48": "http://example.com/avatar.jpg"},
            "tz": "America/New_York",
            "is_bot": False,
            "is_admin": False,
            "is_owner": False,
            "deleted": False,
            "is_restricted": False,
            "is_ultra_restricted": False,
        },
    }

    result = await get_cached_user_info(mock_client, kv_store, "U123456")
    expected = SlackUserInfo(
        real_name="John Doe",
        username="john.doe",
        email="john@example.com",
        avatar_url="http://example.com/avatar.jpg",
        timezone="America/New_York",
        is_bot=False,
        is_admin=False,
        is_owner=False,
        deleted=False,
        is_restricted=False,
        is_ultra_restricted=False,
    )
    assert result == expected

    # Should call the API
    mock_client.users_info.assert_called_once_with(user="U123456", include_locale=True)

    # Should cache the result
    cached = await kv_store.get("user_info", "U123456")
    assert cached is not None


@pytest.mark.asyncio
async def test_get_cached_user_info_api_failure(kv_store, mock_client):
    """Test get_cached_user_info when API call fails."""
    # Mock API failure
    mock_client.users_info.return_value = {"ok": False, "user": None}

    result = await get_cached_user_info(mock_client, kv_store, "U123456")
    assert result is None


@pytest.mark.asyncio
async def test_parallel_resolution_performance(kv_store, mock_client):
    """Test that parallel resolution is faster than sequential."""

    # Mock slow API calls
    async def slow_person_info(client, kv_store, user_id):
        await asyncio.sleep(0.1)  # Simulate API delay
        users = {
            "U123456": EnrichedPerson(
                real_name="John Doe", job_title="Software Engineer", timezone="America/New_York"
            ),
            "U789012": EnrichedPerson(
                real_name="Jane Smith", job_title="Product Manager", timezone="America/Los_Angeles"
            ),
            "U345678": EnrichedPerson(real_name="Bob Johnson", job_title=None, timezone=None),
        }
        return users.get(user_id)

    with patch(
        "csbot.slackbot.channel_bot.personalization.get_person_info_from_slack_user_id"
    ) as mock_get_person_info:
        mock_get_person_info.side_effect = slow_person_info

        message = "Hey <@U123456>, <@U789012>, and <@U345678>!"

        start_time = time.time()
        result = await resolve_user_mentions_in_message(mock_client, kv_store, message)
        end_time = time.time()

        # Should complete in less than 0.2 seconds (parallel execution)
        # vs 0.3 seconds (sequential execution)
        assert end_time - start_time < 0.2

        expected = "Hey <@U123456> (John Doe, Software Engineer), <@U789012> (Jane Smith, Product Manager), and <@U345678> (Bob Johnson)!"
        assert result == expected
