"""Tests for IdleDetector class."""

from datetime import datetime

import pytest

from csbot.slackbot.storage.idle_detector import IdleDetector
from csbot.utils.time import DatetimeNowFake


@pytest.fixture
def datetime_now_fake():
    return DatetimeNowFake(initial_time_seconds=1000000)


@pytest.fixture
def detector(datetime_now_fake):
    return IdleDetector(
        datetime_now=datetime_now_fake,
        idle_threshold_seconds=1800,  # 30 minutes
        poll_interval_seconds=900,  # 15 minutes
    )


class TestIdleDetector:
    def test_not_idle_with_recent_activity(self, detector, datetime_now_fake):
        """Test that recent activity means not idle."""
        # Activity 10 minutes ago
        activity_time = datetime_now_fake()
        datetime_now_fake.advance_time(600)  # 10 minutes

        assert not detector.is_idle(activity_time)

    def test_idle_with_old_activity(self, detector, datetime_now_fake):
        """Test that old activity means idle."""
        # Activity 31 minutes ago
        activity_time = datetime_now_fake()
        datetime_now_fake.advance_time(1860)  # 31 minutes

        assert detector.is_idle(activity_time)

    def test_not_idle_with_no_activity(self, detector):
        """Test that no activity timestamp means not idle."""
        assert not detector.is_idle(None)

    def test_timezone_naive_handling(self, detector, datetime_now_fake):
        """Test handling of naive datetime objects."""
        # Create a naive datetime (no timezone)
        # Use a fixed timestamp for naive datetime test
        naive_time = datetime.fromtimestamp(1000000)
        datetime_now_fake.advance_time(1860)  # 31 minutes

        # Should handle naive datetime gracefully
        assert detector.is_idle(naive_time)

    def test_activity_at_exact_threshold(self, detector, datetime_now_fake):
        """Test boundary condition at exact idle threshold."""
        activity_time = datetime_now_fake()
        datetime_now_fake.advance_time(1800)  # Exactly 30 minutes

        # Should not be idle at exact threshold
        assert not detector.is_idle(activity_time)

        # One second past threshold should be idle
        datetime_now_fake.advance_time(1)
        assert detector.is_idle(activity_time)

    def test_never_skip_when_active(self, detector):
        """Test that polling is never skipped when not idle."""
        detector.record_poll()
        assert not detector.should_skip_poll(is_idle=False)

        # Even with very recent poll
        detector.record_poll()
        assert not detector.should_skip_poll(is_idle=False)

    def test_skip_when_idle_and_recent_poll(self, detector, datetime_now_fake):
        """Test that polling is skipped when idle with recent poll."""
        detector.record_poll()
        datetime_now_fake.advance_time(300)  # 5 minutes

        assert detector.should_skip_poll(is_idle=True)

    def test_no_skip_when_idle_and_old_poll(self, detector, datetime_now_fake):
        """Test that polling happens when idle but poll is old."""
        detector.record_poll()
        datetime_now_fake.advance_time(960)  # 16 minutes

        assert not detector.should_skip_poll(is_idle=True)

    def test_no_skip_on_first_poll(self, detector):
        """Test that first poll is never skipped."""
        # No poll recorded yet
        assert not detector.should_skip_poll(is_idle=True)

    def test_poll_at_exact_interval_threshold(self, detector, datetime_now_fake):
        """Test boundary condition at exact poll interval."""
        detector.record_poll()
        datetime_now_fake.advance_time(900)  # Exactly 15 minutes

        # Should not skip at exact threshold
        assert not detector.should_skip_poll(is_idle=True)

        # Reset and test just before threshold
        detector.record_poll()
        datetime_now_fake.advance_time(899)  # 1 second before 15 minutes

        # Should skip just before threshold
        assert detector.should_skip_poll(is_idle=True)

    def test_record_poll_updates_timestamp(self, detector, datetime_now_fake):
        """Test that recording a poll updates the timestamp."""
        assert detector.last_poll_timestamp is None

        detector.record_poll()
        first_poll = detector.last_poll_timestamp
        assert first_poll is not None

        datetime_now_fake.advance_time(100)
        detector.record_poll()
        second_poll = detector.last_poll_timestamp

        assert second_poll > first_poll

    def test_get_time_since_last_poll(self, detector, datetime_now_fake):
        """Test getting time since last poll."""
        assert detector.get_time_since_last_poll_seconds() is None

        detector.record_poll()
        assert detector.get_time_since_last_poll_seconds() == 0

        datetime_now_fake.advance_time(300)
        assert detector.get_time_since_last_poll_seconds() == 300

        datetime_now_fake.advance_time(600)
        assert detector.get_time_since_last_poll_seconds() == 900

    def test_custom_thresholds(self, datetime_now_fake):
        """Test IdleDetector with custom thresholds."""
        # Create detector with custom values
        custom_detector = IdleDetector(
            datetime_now=datetime_now_fake,
            idle_threshold_seconds=60,  # 1 minute
            poll_interval_seconds=30,  # 30 seconds
        )

        activity_time = datetime_now_fake()

        # Not idle at 59 seconds
        datetime_now_fake.advance_time(59)
        assert not custom_detector.is_idle(activity_time)

        # Idle at 61 seconds
        datetime_now_fake.advance_time(2)
        assert custom_detector.is_idle(activity_time)

        # Test poll interval
        custom_detector.record_poll()
        datetime_now_fake.advance_time(29)  # 29 seconds
        assert custom_detector.should_skip_poll(is_idle=True)

        datetime_now_fake.advance_time(2)  # 31 seconds total
        assert not custom_detector.should_skip_poll(is_idle=True)

    def test_multiple_poll_cycles(self, detector, datetime_now_fake):
        """Test multiple poll cycles in idle mode."""
        # Record initial poll
        detector.record_poll()

        # Should skip polls for next 14 minutes (test at specific intervals)
        test_times = [60, 300, 600, 840]  # 1, 5, 10, 14 minutes
        for seconds in test_times:
            datetime_now_fake.set_time(1000000 + seconds)  # Set absolute time
            assert detector.should_skip_poll(is_idle=True), (
                f"Should skip at {seconds / 60:.0f} minutes"
            )

        # After 15 minutes, should allow poll
        datetime_now_fake.set_time(1000000 + 900)  # 15 minutes
        assert not detector.should_skip_poll(is_idle=True)

        # Record new poll and repeat
        detector.record_poll()
        datetime_now_fake.advance_time(300)  # 5 minutes
        assert detector.should_skip_poll(is_idle=True)
