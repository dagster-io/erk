"""
Test cases for streaming reply usage logging.

Tests usage count increments during streaming_reply_to_thread_with_ai calls.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.asyncio
@patch("csbot.slackbot.channel_bot.streaming_response.stream_claude_response")
async def test_streaming_reply_increments_usage_count(
    mock_stream_claude_response, compass_bot_instance, mock_analytics_store, mock_bot_key
):
    """Test that streaming_reply_to_thread_with_ai increments usage count."""
    mock_bot_key.to_bot_id.return_value = "test_bot_streaming"
    mock_stream_claude_response.return_value = AsyncMock()

    # Create mock thread
    mock_thread = Mock()

    # Call streaming_reply_to_thread_with_ai
    await compass_bot_instance.streaming_reply_to_thread_with_ai(
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

    # Verify that increment_answer_count was called
    mock_analytics_store.increment_answer_count.assert_called_once_with("test_bot_streaming")


@pytest.mark.asyncio
async def test_streaming_reply_logs_usage_even_on_error(
    compass_bot_instance, mock_analytics_store, mock_bot_key
):
    """Test that usage is logged even if the streaming response fails."""
    mock_bot_key.to_bot_id.return_value = "test_bot_streaming"

    # Create mock thread
    mock_thread = Mock()

    # Mock streaming function to raise an exception
    with patch(
        "csbot.slackbot.channel_bot.streaming_response.stream_claude_response",
        side_effect=Exception("Claude API error"),
    ):
        # Call streaming_reply_to_thread_with_ai (should handle exception)
        await compass_bot_instance.streaming_reply_to_thread_with_ai(
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

    # Verify that increment_answer_count was still called
    mock_analytics_store.increment_answer_count.assert_called_once_with("test_bot_streaming")


@pytest.mark.asyncio
async def test_streaming_reply_with_pr_url(
    compass_bot_instance, mock_analytics_store, mock_bot_key
):
    """Test that usage is logged for PR threads."""
    mock_bot_key.to_bot_id.return_value = "test_bot_streaming"

    # Mock github monitor methods for PR handling
    compass_bot_instance.github_monitor.get_pr_system_prompt = AsyncMock(return_value="PR prompt")
    compass_bot_instance.github_monitor.get_pr_tools = AsyncMock(return_value={})

    mock_thread = Mock()

    # Call with PR URL
    await compass_bot_instance.streaming_reply_to_thread_with_ai(
        message="Test PR message",
        message_ts="1234567890.123456",
        thread=mock_thread,
        channel="C123456789",
        thread_ts="1234567890.123456",
        user="U123456789",
        pr_url="https://github.com/org/repo/pull/123",
        collapse_thinking_steps=True,
        is_automated_message=False,
    )

    # Verify usage count increment
    mock_analytics_store.increment_answer_count.assert_called_once_with("test_bot_streaming")
