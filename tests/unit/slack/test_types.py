"""Tests for Slack types."""

from datetime import datetime

from erk.slack.types import SlackEvent, SlackMessage, ThreadRecord


class TestSlackMessage:
    """Tests for SlackMessage dataclass."""

    def test_creates_message_with_all_fields(self) -> None:
        """SlackMessage stores all fields correctly."""
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts="1234567890.000000",
            user="U12345",
            text="Hello, bot!",
        )

        assert msg.channel == "C12345"
        assert msg.ts == "1234567890.123456"
        assert msg.thread_ts == "1234567890.000000"
        assert msg.user == "U12345"
        assert msg.text == "Hello, bot!"

    def test_creates_message_without_thread_ts(self) -> None:
        """SlackMessage can have None thread_ts for root messages."""
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="Root message",
        )

        assert msg.thread_ts is None

    def test_message_is_frozen(self) -> None:
        """SlackMessage is immutable."""
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="Test",
        )

        # Should raise FrozenInstanceError
        try:
            msg.text = "Modified"  # type: ignore[misc]
            raise AssertionError("Should have raised")  # noqa: TRY301
        except AttributeError:
            pass  # Expected - frozen dataclass


class TestSlackEvent:
    """Tests for SlackEvent dataclass."""

    def test_creates_event_with_message(self) -> None:
        """SlackEvent stores event_type and message."""
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="@bot help",
        )
        event = SlackEvent(event_type="app_mention", message=msg)

        assert event.event_type == "app_mention"
        assert event.message == msg

    def test_event_is_frozen(self) -> None:
        """SlackEvent is immutable."""
        msg = SlackMessage(
            channel="C12345",
            ts="1234567890.123456",
            thread_ts=None,
            user="U12345",
            text="Test",
        )
        event = SlackEvent(event_type="app_mention", message=msg)

        try:
            event.event_type = "message"  # type: ignore[misc]
            raise AssertionError("Should have raised")  # noqa: TRY301
        except AttributeError:
            pass  # Expected


class TestThreadRecord:
    """Tests for ThreadRecord dataclass."""

    def test_creates_record_with_all_fields(self) -> None:
        """ThreadRecord stores all fields correctly."""
        now = datetime(2024, 1, 15, 10, 30, 0)
        record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id="session-abc-123",
            last_message_ts="1234567890.123456",
            created_at=now,
            updated_at=now,
        )

        assert record.channel == "C12345"
        assert record.thread_ts == "1234567890.123456"
        assert record.session_id == "session-abc-123"
        assert record.last_message_ts == "1234567890.123456"
        assert record.created_at == now
        assert record.updated_at == now

    def test_creates_record_without_session_id(self) -> None:
        """ThreadRecord can have None session_id for new threads."""
        now = datetime.now()
        record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id=None,
            last_message_ts="1234567890.123456",
            created_at=now,
            updated_at=now,
        )

        assert record.session_id is None
