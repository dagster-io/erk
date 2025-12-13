"""
Test cases for plan limit checking and enforcement.

Tests PlanLimits objects and plan enforcement logic.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from csbot.slackbot.storage.interface import PlanLimits


@pytest.mark.asyncio
async def test_streaming_reply_respects_plan_limits_no_overage_allowed(
    compass_bot_instance,
    mock_analytics_store,
):
    """Test that bot stops responding when plan limits exceeded and no overage allowed."""
    bot = compass_bot_instance

    # Mock plan limits - no overage allowed
    plan_limits = PlanLimits(
        base_num_answers=10,
        allow_overage=False,
        num_channels=5,
        allow_additional_channels=False,
    )
    bot.storage.get_plan_limits.return_value = plan_limits

    # Mock current usage exceeding limits
    mock_analytics_store.get_usage_tracking_data_for_month.return_value = 15
    # Mock no bonus answers available
    mock_analytics_store.get_organization_bonus_answer_grants.return_value = 0
    mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 0

    mock_thread = Mock()

    # Call streaming_reply_to_thread_with_ai
    await bot.streaming_reply_to_thread_with_ai(
        message="Test message",
        message_ts="1234567890.123456",
        thread=mock_thread,
        channel="C123456789",
        thread_ts="1234567890.123456",
        user="U123456789",
        pr_url=None,
        collapse_thinking_steps=True,
        is_automated_message=False,
    )

    # Verify plan limits were checked
    bot.storage.get_plan_limits.assert_called_once_with(123)

    # Verify usage was checked for current month
    current_month = datetime.now(UTC).month
    current_year = datetime.now(UTC).year
    mock_analytics_store.get_usage_tracking_data_for_month.assert_called_once_with(
        "test-bot", current_month, current_year, include_bonus_answers=False
    )

    # Verify warning method was called
    bot._warn_plan_limit_reached_no_overages.assert_called_once_with(
        "C123456789", "1234567890.123456", 10, 15, False
    )

    # Verify answer count was NOT incremented (stopped before processing)
    mock_analytics_store.increment_answer_count.assert_not_called()

    # Verify Claude response was NOT called
    bot._stream_claude_response.assert_not_called()


@pytest.mark.asyncio
async def test_streaming_reply_respects_plan_limits_with_overage_allowed(
    compass_bot_instance,
    mock_analytics_store,
):
    """Test that bot continues but warns when plan limits exceeded with overage allowed."""
    bot = compass_bot_instance

    # Mock plan limits - overage allowed
    plan_limits = PlanLimits(
        base_num_answers=10,
        allow_overage=True,
        num_channels=5,
        allow_additional_channels=True,
    )
    bot.storage.get_plan_limits.return_value = plan_limits

    # Mock current usage exceeding limits
    mock_analytics_store.get_usage_tracking_data_for_month.return_value = 15
    # Mock no bonus answers available
    mock_analytics_store.get_organization_bonus_answer_grants.return_value = 0
    mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 0

    mock_thread = Mock()

    # Call streaming_reply_to_thread_with_ai
    await bot.streaming_reply_to_thread_with_ai(
        message="Test message",
        message_ts="1234567890.123456",
        thread=mock_thread,
        channel="C123456789",
        thread_ts="1234567890.123456",
        user="U123456789",
        pr_url=None,
        collapse_thinking_steps=True,
        is_automated_message=False,
    )

    # Verify warning method was called
    bot._possibly_warn_plan_limit_reached_overages.assert_called_once_with(
        "C123456789", "1234567890.123456", 10, 15, False
    )

    # Verify answer count WAS incremented (processing continued)
    mock_analytics_store.increment_answer_count.assert_called_once_with("test-bot")

    # Verify Claude response WAS called
    bot._stream_claude_response.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_reply_under_plan_limits(
    compass_bot_instance,
    mock_analytics_store,
):
    """Test that bot works normally when under plan limits."""
    bot = compass_bot_instance

    # Mock plan limits
    plan_limits = PlanLimits(
        base_num_answers=10,
        allow_overage=False,
        num_channels=5,
        allow_additional_channels=False,
    )
    bot.storage.get_plan_limits.return_value = plan_limits

    # Mock current usage under limits
    mock_analytics_store.get_usage_tracking_data_for_month.return_value = 5

    mock_thread = Mock()

    # Call streaming_reply_to_thread_with_ai
    await bot.streaming_reply_to_thread_with_ai(
        message="Test message",
        message_ts="1234567890.123456",
        thread=mock_thread,
        channel="C123456789",
        thread_ts="1234567890.123456",
        user="U123456789",
        pr_url=None,
        collapse_thinking_steps=True,
        is_automated_message=False,
    )

    # Verify no warning methods were called
    bot._warn_plan_limit_reached_no_overages.assert_not_called()
    bot._possibly_warn_plan_limit_reached_overages.assert_not_called()

    # Verify answer count WAS incremented
    mock_analytics_store.increment_answer_count.assert_called_once_with("test-bot")

    # Verify Claude response WAS called
    bot._stream_claude_response.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_reply_no_plan_limits_cached(
    compass_bot_instance,
    mock_analytics_store,
):
    """Test that bot works normally when no plan limits are cached."""
    bot = compass_bot_instance

    # Mock no plan limits cached
    bot.storage.get_plan_limits.return_value = None

    mock_thread = Mock()

    # Call streaming_reply_to_thread_with_ai
    await bot.streaming_reply_to_thread_with_ai(
        message="Test message",
        message_ts="1234567890.123456",
        thread=mock_thread,
        channel="C123456789",
        thread_ts="1234567890.123456",
        user="U123456789",
        pr_url=None,
        collapse_thinking_steps=True,
        is_automated_message=False,
    )

    # Verify plan limits were checked
    bot.storage.get_plan_limits.assert_called_once_with(123)

    # Verify usage was NOT checked (since no plan limits)
    mock_analytics_store.get_usage_tracking_data_for_month.assert_not_called()

    # Verify no warning methods were called
    bot._warn_plan_limit_reached_no_overages.assert_not_called()
    bot._possibly_warn_plan_limit_reached_overages.assert_not_called()

    # Verify answer count WAS incremented
    mock_analytics_store.increment_answer_count.assert_called_once_with("test-bot")

    # Verify Claude response WAS called
    bot._stream_claude_response.assert_called_once()


@pytest.mark.asyncio
async def test_streaming_reply_first_time_at_limit_no_overages(
    compass_bot_instance,
    mock_analytics_store,
):
    """Test governance warning when reaching limit for first time with no overages."""
    bot = compass_bot_instance

    # Mock plan limits - no overage allowed
    plan_limits = PlanLimits(
        base_num_answers=10,
        allow_overage=False,
        num_channels=5,
        allow_additional_channels=False,
    )
    bot.storage.get_plan_limits.return_value = plan_limits

    # Mock current usage exactly at limits (first time)
    mock_analytics_store.get_usage_tracking_data_for_month.return_value = 10
    # Mock no bonus answers available
    mock_analytics_store.get_organization_bonus_answer_grants.return_value = 0
    mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 0

    mock_thread = Mock()

    # Call streaming_reply_to_thread_with_ai
    await bot.streaming_reply_to_thread_with_ai(
        message="Test message",
        message_ts="1234567890.123456",
        thread=mock_thread,
        channel="C123456789",
        thread_ts="1234567890.123456",
        user="U123456789",
        pr_url=None,
        collapse_thinking_steps=True,
        is_automated_message=False,
    )

    # Verify warning method was called
    bot._warn_plan_limit_reached_no_overages.assert_called_once_with(
        "C123456789", "1234567890.123456", 10, 10, False
    )

    # Since we're mocking the helper method, it won't actually call the governance warning
    # But in a real scenario, it would detect is_first_time_at_limit = True (10 == 10)


@pytest.mark.asyncio
async def test_streaming_reply_first_time_at_limit_with_overages(
    compass_bot_instance,
    mock_analytics_store,
):
    """Test governance warning when reaching limit for first time with overages allowed."""
    bot = compass_bot_instance

    # Mock plan limits - overage allowed
    plan_limits = PlanLimits(
        base_num_answers=10,
        allow_overage=True,
        num_channels=5,
        allow_additional_channels=True,
    )
    bot.storage.get_plan_limits.return_value = plan_limits

    # Mock current usage exactly at limits (first time)
    mock_analytics_store.get_usage_tracking_data_for_month.return_value = 10
    # Mock no bonus answers available
    mock_analytics_store.get_organization_bonus_answer_grants.return_value = 0
    mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 0

    mock_thread = Mock()

    # Call streaming_reply_to_thread_with_ai
    await bot.streaming_reply_to_thread_with_ai(
        message="Test message",
        message_ts="1234567890.123456",
        thread=mock_thread,
        channel="C123456789",
        thread_ts="1234567890.123456",
        user="U123456789",
        pr_url=None,
        collapse_thinking_steps=True,
        is_automated_message=False,
    )

    # Verify warning method was called
    bot._possibly_warn_plan_limit_reached_overages.assert_called_once_with(
        "C123456789", "1234567890.123456", 10, 10, False
    )

    # Since we're mocking the helper method, it won't actually call the governance warning
    # But in a real scenario, it would detect is_first_time_at_limit = True (10 == 10)
