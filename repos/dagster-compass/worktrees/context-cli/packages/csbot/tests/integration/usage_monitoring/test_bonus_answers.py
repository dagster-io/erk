"""
Test cases for bonus answer usage patterns.

Tests bonus answer grants, consumption tracking, and availability checks
for the streaming_reply_to_thread_with_ai method.
"""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from tests.usage_monitoring_helpers import (
    setup_bonus_answer_consumption_via_bot,
    setup_organization_bonus_answer_grant,
)


class TestBonusAnswerUsage:
    """Test cases for bonus answer usage patterns in streaming_reply_to_thread_with_ai."""

    @pytest.mark.asyncio
    async def test_non_overage_below_limit_uses_regular_answer(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test non-overage plan below limit uses regular answer."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - no overage allowed
        await bot.storage.set_plan_limits(org_id, 10, False, 5, False)

        # Set up initial usage in the database (5 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 5
        )

        # Set up bonus answers in database (shouldn't be used)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 20)

        mock_thread = Mock()

        # Get initial count to verify later
        initial_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )

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

        # Verify regular answer count was incremented in the database
        final_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_count == initial_count + 1

        # Verify bonus answer count was NOT incremented
        bonus_count = await real_analytics_store.get_organization_bonus_answers_consumed(org_id)
        assert bonus_count == 0

        # Verify Claude response was called
        bot._stream_claude_response.assert_called_once()
        # Verify no warnings were sent
        bot._warn_plan_limit_reached_no_overages.assert_not_called()
        bot._possibly_warn_plan_limit_reached_overages.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_overage_at_limit_with_bonus_uses_bonus_answer(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test non-overage plan at limit with bonus available uses bonus answer."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - no overage allowed
        await bot.storage.set_plan_limits(org_id, 10, False, 5, False)

        # Set up usage at limits in the database (10 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 10
        )

        # Set up bonus answers in database (5 available)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 20)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 15
        )  # 20-15 = 5 available

        mock_thread = Mock()

        # Get initial bonus answer consumption to verify later
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )

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

        # Verify bonus answer count was incremented in the database
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed + 1

        # Verify regular answer count was NOT incremented
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count

        # Verify Claude response was called
        bot._stream_claude_response.assert_called_once()
        # Verify no warnings were sent (bonus answer used)
        bot._warn_plan_limit_reached_no_overages.assert_not_called()
        bot._possibly_warn_plan_limit_reached_overages.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_overage_at_limit_no_bonus_blocks_request(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test non-overage plan at limit with no bonus available blocks request."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - no overage allowed
        await bot.storage.set_plan_limits(org_id, 10, False, 5, False)

        # Set up usage at limits in the database (10 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 10
        )

        # Set up bonus answers - all consumed (none available)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 20)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 20
        )  # All 20 consumed

        mock_thread = Mock()

        # Get initial counts to verify they don't change
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )

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

        # Verify no answer counts were incremented (blocked)
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )

        assert final_regular_count == initial_regular_count
        assert final_bonus_consumed == initial_bonus_consumed

        # Verify Claude response was NOT called (blocked)
        bot._stream_claude_response.assert_not_called()
        # Verify warning was sent
        bot._warn_plan_limit_reached_no_overages.assert_called_once_with(
            "C123456789", "1234567890.123456", 10, 10, False
        )

    @pytest.mark.asyncio
    async def test_non_overage_exceeds_limit_no_bonus_blocks_request(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test non-overage plan exceeding limit with no bonus available blocks request."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - no overage allowed
        await bot.storage.set_plan_limits(org_id, 10, False, 5, False)

        # Set up usage exceeding limits in the database (12 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 12
        )

        # Set up bonus answers - all consumed (none available)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 5)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 5
        )  # All 5 consumed

        mock_thread = Mock()

        # Get initial counts to verify they don't change
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )

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

        # Verify no answer counts were incremented (blocked)
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )

        assert final_regular_count == initial_regular_count
        assert final_bonus_consumed == initial_bonus_consumed

        # Verify Claude response was NOT called (blocked)
        bot._stream_claude_response.assert_not_called()
        # Verify warning was sent
        bot._warn_plan_limit_reached_no_overages.assert_called_once_with(
            "C123456789", "1234567890.123456", 10, 12, False
        )

    @pytest.mark.asyncio
    async def test_non_overage_exceeds_limit_with_bonus_uses_bonus_answer(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test non-overage plan exceeding limit with bonus available uses bonus answer."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - no overage allowed
        await bot.storage.set_plan_limits(org_id, 10, False, 5, False)

        # Set up usage exceeding limits in the database (12 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 12
        )

        # Set up bonus answers available (3 remaining: 30-27=3)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 30)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 27
        )

        mock_thread = Mock()

        # Get initial counts to verify changes
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )

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

        # Verify bonus answer count was incremented in the database
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed + 1

        # Verify regular answer count was NOT incremented
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count

        # Verify Claude response was called
        bot._stream_claude_response.assert_called_once()
        # Verify no warnings were sent (bonus answer used)
        bot._warn_plan_limit_reached_no_overages.assert_not_called()
        bot._possibly_warn_plan_limit_reached_overages.assert_not_called()

    @pytest.mark.asyncio
    async def test_overage_below_limit_uses_regular_answer(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test overage plan below limit uses regular answer."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - overage allowed
        await bot.storage.set_plan_limits(org_id, 10, True, 5, True)

        # Set up usage below limits in the database (7 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 7
        )

        # Set up bonus answers available (shouldn't be used)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 50)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 42
        )  # 50-42=8 available

        mock_thread = Mock()

        # Get initial counts
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )

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

        # Verify regular answer count was incremented
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count + 1

        # Verify bonus answer count was NOT incremented
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed

        # Verify Claude response was called
        bot._stream_claude_response.assert_called_once()
        # Verify no warnings were sent
        bot._warn_plan_limit_reached_no_overages.assert_not_called()
        bot._possibly_warn_plan_limit_reached_overages.assert_not_called()

    @pytest.mark.asyncio
    async def test_overage_at_limit_with_bonus_uses_bonus_answer(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test overage plan at limit with bonus available uses bonus answer."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - overage allowed
        await bot.storage.set_plan_limits(org_id, 10, True, 5, True)

        # Set up usage at limits in the database (10 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 10
        )

        # Set up bonus answers available (8 remaining: 25-17=8)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 25)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 17
        )

        mock_thread = Mock()

        # Get initial counts
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )

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

        # Verify bonus answer count was incremented
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed + 1

        # Verify regular answer count was NOT incremented
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count

        # Verify Claude response was called
        bot._stream_claude_response.assert_called_once()
        # Verify no warnings were sent (bonus answer used)
        bot._warn_plan_limit_reached_no_overages.assert_not_called()
        bot._possibly_warn_plan_limit_reached_overages.assert_not_called()

    @pytest.mark.asyncio
    async def test_overage_at_limit_no_bonus_uses_regular_overage(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test overage plan at limit with no bonus available uses regular answer (overage)."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - overage allowed
        await bot.storage.set_plan_limits(org_id, 10, True, 5, True)

        # Set up usage at limits in the database (10 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 10
        )

        # Set up no bonus answers available
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 15)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 15
        )  # All consumed

        mock_thread = Mock()

        # Get initial counts
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )

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

        # Verify regular answer count was incremented (overage)
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count + 1

        # Verify bonus answer count was NOT incremented
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed

        # Verify Claude response was called (overage allowed)
        bot._stream_claude_response.assert_called_once()
        # Verify overage warning was sent
        bot._possibly_warn_plan_limit_reached_overages.assert_called_once_with(
            "C123456789", "1234567890.123456", 10, 10, False
        )

    @pytest.mark.asyncio
    async def test_overage_exceeds_limit_no_bonus_uses_regular_overage(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test overage plan exceeding limit with no bonus available uses regular answer (overage)."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - overage allowed
        await bot.storage.set_plan_limits(org_id, 10, True, 5, True)

        # Set up usage exceeding limits in the database (15 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 15
        )

        # Set up no bonus answers available
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 8)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 8
        )  # All consumed

        mock_thread = Mock()

        # Get initial counts
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )

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

        # Verify regular answer count was incremented (overage)
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count + 1

        # Verify bonus answer count was NOT incremented
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed

        # Verify Claude response was called (overage allowed)
        bot._stream_claude_response.assert_called_once()
        # Verify overage warning was sent
        bot._possibly_warn_plan_limit_reached_overages.assert_called_once_with(
            "C123456789", "1234567890.123456", 10, 15, False
        )

    @pytest.mark.asyncio
    async def test_overage_exceeds_limit_with_bonus_uses_bonus_answer(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test overage plan exceeding limit with bonus available uses bonus answer."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - overage allowed
        await bot.storage.set_plan_limits(org_id, 10, True, 5, True)

        # Set up usage exceeding limits in the database (15 regular answers)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 15
        )

        # Set up bonus answers available (2 remaining: 40-38=2)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 40)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 38
        )

        mock_thread = Mock()

        # Get initial counts
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )

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

        # Verify bonus answer count was incremented
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed + 1

        # Verify regular answer count was NOT incremented
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count

        # Verify Claude response was called
        bot._stream_claude_response.assert_called_once()
        # Verify no warnings were sent (bonus answer used)
        bot._warn_plan_limit_reached_no_overages.assert_not_called()
        bot._possibly_warn_plan_limit_reached_overages.assert_not_called()

    @pytest.mark.asyncio
    async def test_bonus_answer_usage_without_plan_limits(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test that bonus answers are not used when no plan limits are cached."""
        bot, org_id = bonus_test_bot_with_db

        # No plan limits set in storage (real storage returns None)
        # Set up bonus answers available in database (should be irrelevant)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 100)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 50
        )

        mock_thread = Mock()

        # Get initial counts
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )

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

        # Verify regular answer count was incremented (no limits to enforce)
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count + 1

        # Verify bonus answer count was NOT incremented
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed

        # Verify Claude response was called (no limits blocking)
        bot._stream_claude_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_first_time_at_limit_with_bonus_answer_usage(
        self, bonus_test_bot_with_db, real_analytics_store, sql_conn_factory_transactional
    ):
        """Test governance warning when reaching limit for first time using bonus answer."""
        bot, org_id = bonus_test_bot_with_db

        # Set up real plan limits in storage - no overage allowed
        await bot.storage.set_plan_limits(org_id, 10, False, 5, False)

        # Set up current usage exactly at limits (10 regular answers - first time)
        current_month = datetime.now(UTC).month
        current_year = datetime.now(UTC).year
        await real_analytics_store.insert_usage_tracking_data(
            "test-bot_bonus", current_month, current_year, 10
        )

        # Set up bonus answers available (5 remaining: 25-20=5)
        await setup_organization_bonus_answer_grant(sql_conn_factory_transactional, org_id, 25)
        await setup_bonus_answer_consumption_via_bot(
            sql_conn_factory_transactional, "test-bot_bonus", 20
        )

        mock_thread = Mock()

        # Get initial counts to verify changes
        initial_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        initial_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )

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

        # Verify bonus answer count was incremented (used bonus instead of blocking)
        final_bonus_consumed = await real_analytics_store.get_organization_bonus_answers_consumed(
            org_id
        )
        assert final_bonus_consumed == initial_bonus_consumed + 1

        # Verify regular answer count was NOT incremented
        final_regular_count = await real_analytics_store.get_usage_tracking_data_for_month(
            "test-bot_bonus", current_month, current_year, include_bonus_answers=False
        )
        assert final_regular_count == initial_regular_count

        # Verify Claude response was called (bonus allowed processing)
        bot._stream_claude_response.assert_called_once()

        # Note: The actual governance warning logic would be tested in the helper method tests
        # This test verifies that the bonus answer path is taken when at limit with bonus available


class TestBonusAnswerAvailabilityChecks:
    """Test cases for bonus answer availability checking logic."""

    @pytest.mark.asyncio
    async def test_has_remaining_bonus_answers_with_grants_and_no_usage(
        self, compass_bot_instance, mock_analytics_store, mock_bot_config
    ):
        """Test has_remaining_bonus_answers returns True with grants and no consumption."""
        # Configure bot config organization_id
        mock_bot_config.organization_id = 789

        # Mock organization has bonus answer grants, no consumption
        mock_analytics_store.get_organization_bonus_answer_grants.return_value = 50
        mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 0

        result = await compass_bot_instance.has_remaining_bonus_answers()

        assert result is True
        mock_analytics_store.get_organization_bonus_answer_grants.assert_called_once_with(789)
        mock_analytics_store.get_organization_bonus_answers_consumed.assert_called_once_with(789)

    @pytest.mark.asyncio
    async def test_has_remaining_bonus_answers_with_partial_consumption(
        self, compass_bot_instance, mock_analytics_store, mock_bot_config
    ):
        """Test has_remaining_bonus_answers returns True with partial consumption."""
        # Configure bot config organization_id
        mock_bot_config.organization_id = 789

        # Mock organization has bonus answer grants, partial consumption
        mock_analytics_store.get_organization_bonus_answer_grants.return_value = 100
        mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 75

        result = await compass_bot_instance.has_remaining_bonus_answers()

        assert result is True  # 100 - 75 = 25 remaining

    @pytest.mark.asyncio
    async def test_has_remaining_bonus_answers_fully_consumed(
        self, compass_bot_instance, mock_analytics_store, mock_bot_config
    ):
        """Test has_remaining_bonus_answers returns False when fully consumed."""
        # Configure bot config organization_id
        mock_bot_config.organization_id = 789

        # Mock organization has bonus answer grants, fully consumed
        mock_analytics_store.get_organization_bonus_answer_grants.return_value = 30
        mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 30

        result = await compass_bot_instance.has_remaining_bonus_answers()

        assert result is False  # 30 - 30 = 0 remaining

    @pytest.mark.asyncio
    async def test_has_remaining_bonus_answers_over_consumed(
        self, compass_bot_instance, mock_analytics_store, mock_bot_config
    ):
        """Test has_remaining_bonus_answers returns False when over-consumed."""
        # Configure bot config organization_id
        mock_bot_config.organization_id = 789

        # Mock organization has consumed more than granted (edge case)
        mock_analytics_store.get_organization_bonus_answer_grants.return_value = 20
        mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 25

        result = await compass_bot_instance.has_remaining_bonus_answers()

        assert result is False  # 20 - 25 = -5 remaining (treated as 0)

    @pytest.mark.asyncio
    async def test_has_remaining_bonus_answers_no_grants(
        self, compass_bot_instance, mock_analytics_store, mock_bot_config
    ):
        """Test has_remaining_bonus_answers returns False with no grants."""
        # Configure bot config organization_id
        mock_bot_config.organization_id = 789

        # Mock organization has no bonus answer grants
        mock_analytics_store.get_organization_bonus_answer_grants.return_value = 0
        mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 0

        result = await compass_bot_instance.has_remaining_bonus_answers()

        assert result is False  # 0 - 0 = 0 remaining

    @pytest.mark.asyncio
    async def test_has_remaining_bonus_answers_edge_case_one_remaining(
        self, compass_bot_instance, mock_analytics_store, mock_bot_config
    ):
        """Test has_remaining_bonus_answers returns True with exactly one remaining."""
        # Configure bot config organization_id
        mock_bot_config.organization_id = 789

        # Mock organization has exactly one bonus answer remaining
        mock_analytics_store.get_organization_bonus_answer_grants.return_value = 100
        mock_analytics_store.get_organization_bonus_answers_consumed.return_value = 99

        result = await compass_bot_instance.has_remaining_bonus_answers()

        assert result is True  # 100 - 99 = 1 remaining
