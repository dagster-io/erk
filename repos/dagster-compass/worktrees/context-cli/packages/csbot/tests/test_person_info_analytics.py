"""
Unit tests for analytics-specific person enrichment functionality.

Tests the get_person_info_from_slack_user_id function to ensure proper behavior
for analytics tracking, including bot detection and handling users without email.
"""

from unittest.mock import AsyncMock, patch

import pytest

from csbot.slackbot.channel_bot.personalization import (
    get_person_info_from_slack_user_id,
)


@pytest.fixture
def mock_client():
    """Create a mock Slack client for testing."""
    return AsyncMock()


@pytest.fixture
def mock_kv_store():
    """Create a mock KV store for testing."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_analytics_person_info_with_full_profile(mock_client, mock_kv_store):
    """Test analytics enrichment with complete user profile including email."""
    from csbot.slackbot.channel_bot.personalization import SlackUserInfo

    # Mock cache miss - no previous data
    mock_kv_store.get.return_value = None

    # Mock SlackUserInfo with complete user profile
    mock_user_info = SlackUserInfo(
        real_name="John Doe",
        username="john.doe",
        email="john.doe@example.com",
        avatar_url=None,
        timezone="America/New_York",
        is_bot=False,
        is_admin=False,
        is_owner=False,
        deleted=False,
        is_restricted=False,
        is_ultra_restricted=False,
    )

    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info",
            return_value=mock_user_info,
        ),
        patch("csbot.slackbot.channel_bot.personalization.enrich_person") as mock_enrich,
    ):
        mock_enrich.return_value = {"job_title": "Software Engineer"}

        result = await get_person_info_from_slack_user_id(mock_client, mock_kv_store, "U123456")

        assert result is not None
        assert result.real_name == "John Doe"
        assert result.email == "john.doe@example.com"
        assert result.timezone == "America/New_York"
        assert result.job_title == "Software Engineer"

        # Verify enrich_person was called with email
        mock_enrich.assert_called_once_with({"name": "John Doe", "email": "john.doe@example.com"})

        # Verify cache was set
        mock_kv_store.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_analytics_person_info_without_email(mock_client, mock_kv_store):
    """Test analytics enrichment for user without email access."""
    from csbot.slackbot.channel_bot.personalization import SlackUserInfo

    # Mock cache miss - no previous data
    mock_kv_store.get.return_value = None

    # Mock SlackUserInfo without email
    mock_user_info = SlackUserInfo(
        real_name="Jane Smith",
        username="jane.smith",
        email=None,
        avatar_url=None,
        timezone="America/Los_Angeles",
        is_bot=False,
        is_admin=False,
        is_owner=False,
        deleted=False,
        is_restricted=False,
        is_ultra_restricted=False,
    )

    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info",
            return_value=mock_user_info,
        ),
        patch("csbot.slackbot.channel_bot.personalization.enrich_person") as mock_enrich,
    ):
        result = await get_person_info_from_slack_user_id(mock_client, mock_kv_store, "U123456")

        # Should return EnrichedPerson with available data, email=None
        assert result is not None
        assert result.real_name == "Jane Smith"
        assert result.email is None
        assert result.timezone == "America/Los_Angeles"
        assert result.job_title is None

        # Should NOT call enrich_person when email is missing
        mock_enrich.assert_not_called()

        # Verify cache was set
        mock_kv_store.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_analytics_person_info_bot_user(mock_client, mock_kv_store):
    """Test that bot users are properly detected and return None."""
    # Mock cache miss - no previous data
    mock_kv_store.get.return_value = None

    mock_client.users_info.return_value = {
        "user": {
            "id": "B123456",
            "is_bot": True,
            "profile": {
                "real_name": "Bot User",
                "email": "bot@example.com",
            },
            "tz": "UTC",
        }
    }

    with patch("csbot.slackbot.channel_bot.personalization.enrich_person"):
        result = await get_person_info_from_slack_user_id(mock_client, mock_kv_store, "B123456")

        # Should return None for bots
        assert result is None


@pytest.mark.asyncio
async def test_get_analytics_person_info_missing_user_info(mock_client, mock_kv_store):
    """Test handling of missing user info from Slack API."""
    # Mock cache miss - no previous data
    mock_kv_store.get.return_value = None

    mock_client.users_info.return_value = {"user": None}

    with patch("csbot.slackbot.channel_bot.personalization.enrich_person"):
        result = await get_person_info_from_slack_user_id(mock_client, mock_kv_store, "U123456")

        assert result is None


@pytest.mark.asyncio
async def test_get_analytics_person_info_empty_profile(mock_client, mock_kv_store):
    """Test handling of user with empty profile fields."""
    from csbot.slackbot.channel_bot.personalization import SlackUserInfo

    # Mock cache miss - no previous data
    mock_kv_store.get.return_value = None

    # Mock SlackUserInfo with empty fields
    mock_user_info = SlackUserInfo(
        real_name="",
        username="",
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

    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info",
            return_value=mock_user_info,
        ),
        patch("csbot.slackbot.channel_bot.personalization.enrich_person"),
    ):
        result = await get_person_info_from_slack_user_id(mock_client, mock_kv_store, "U123456")

        # Should return EnrichedPerson with empty/None fields
        assert result is not None
        assert result.real_name == ""
        assert result.email is None
        assert result.timezone is None
        assert result.job_title is None


@pytest.mark.asyncio
async def test_get_analytics_person_info_enrichment_failure(mock_client, mock_kv_store):
    """Test graceful handling when PeopleDataLabs enrichment fails."""
    from csbot.slackbot.channel_bot.personalization import SlackUserInfo

    # Mock cache miss - no previous data
    mock_kv_store.get.return_value = None

    # Mock SlackUserInfo
    mock_user_info = SlackUserInfo(
        real_name="Bob Johnson",
        username="bob.johnson",
        email="bob@example.com",
        avatar_url=None,
        timezone="America/Chicago",
        is_bot=False,
        is_admin=False,
        is_owner=False,
        deleted=False,
        is_restricted=False,
        is_ultra_restricted=False,
    )

    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info",
            return_value=mock_user_info,
        ),
        patch("csbot.slackbot.channel_bot.personalization.enrich_person") as mock_enrich,
    ):
        # Simulate enrichment failure
        mock_enrich.return_value = None

        result = await get_person_info_from_slack_user_id(mock_client, mock_kv_store, "U123456")

        # Should still return EnrichedPerson with basic info
        assert result is not None
        assert result.real_name == "Bob Johnson"
        assert result.email == "bob@example.com"
        assert result.timezone == "America/Chicago"
        assert result.job_title is None  # No enrichment data


@pytest.mark.asyncio
async def test_get_analytics_person_info_enrichment_missing_job_title(mock_client, mock_kv_store):
    """Test handling when enrichment returns data but no job_title."""
    from csbot.slackbot.channel_bot.personalization import SlackUserInfo

    # Mock cache miss - no previous data
    mock_kv_store.get.return_value = None

    # Mock SlackUserInfo
    mock_user_info = SlackUserInfo(
        real_name="Alice Williams",
        username="alice.williams",
        email="alice@example.com",
        avatar_url=None,
        timezone="Europe/London",
        is_bot=False,
        is_admin=False,
        is_owner=False,
        deleted=False,
        is_restricted=False,
        is_ultra_restricted=False,
    )

    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info",
            return_value=mock_user_info,
        ),
        patch("csbot.slackbot.channel_bot.personalization.enrich_person") as mock_enrich,
    ):
        # Enrichment returns data but without job_title
        mock_enrich.return_value = {"some_other_field": "value"}

        result = await get_person_info_from_slack_user_id(mock_client, mock_kv_store, "U123456")

        assert result is not None
        assert result.real_name == "Alice Williams"
        assert result.email == "alice@example.com"
        assert result.timezone == "Europe/London"
        assert result.job_title is None


@pytest.mark.asyncio
async def test_get_analytics_person_info_user_without_email_has_name_and_timezone(
    mock_client, mock_kv_store
):
    """Test that analytics can track users with name and timezone but no email."""
    from csbot.slackbot.channel_bot.personalization import SlackUserInfo

    # Mock cache miss - no previous data
    mock_kv_store.get.return_value = None

    # Mock SlackUserInfo without email
    mock_user_info = SlackUserInfo(
        real_name="Privacy User",
        username="privacy.user",
        email=None,
        avatar_url=None,
        timezone="Asia/Tokyo",
        is_bot=False,
        is_admin=False,
        is_owner=False,
        deleted=False,
        is_restricted=False,
        is_ultra_restricted=False,
    )

    with (
        patch(
            "csbot.slackbot.channel_bot.personalization.get_cached_user_info",
            return_value=mock_user_info,
        ),
        patch("csbot.slackbot.channel_bot.personalization.enrich_person"),
    ):
        result = await get_person_info_from_slack_user_id(mock_client, mock_kv_store, "U789012")

        # This is the key test - we should get useful analytics data
        assert result is not None
        assert result.real_name == "Privacy User"
        assert result.timezone == "Asia/Tokyo"
        assert result.email is None
        assert result.job_title is None
