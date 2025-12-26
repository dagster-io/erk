"""Idle detection for background tasks."""

from datetime import UTC, datetime

from csbot.utils.time import DatetimeNow, system_datetime_now


class IdleDetector:
    """Detects idle state based on activity timestamps and manages polling intervals."""

    def __init__(
        self,
        idle_threshold_seconds: int = 1800,  # 30 minutes
        poll_interval_seconds: int = 900,  # 15 minutes
        datetime_now: DatetimeNow = system_datetime_now,
    ):
        self.datetime_now = datetime_now
        self.idle_threshold_seconds = idle_threshold_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.last_poll_timestamp: datetime | None = None

    def is_idle(self, last_activity_timestamp: datetime | None) -> bool:
        """Check if system is idle based on last activity."""
        if last_activity_timestamp is None:
            return False  # No activity yet means not idle

        # Normalize to timezone-aware
        if last_activity_timestamp.tzinfo is None:
            last_activity_timestamp = last_activity_timestamp.replace(tzinfo=UTC)

        now = self.datetime_now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        time_since_activity = now - last_activity_timestamp
        return time_since_activity.total_seconds() > self.idle_threshold_seconds

    def should_skip_poll(self, is_idle: bool) -> bool:
        """Determine if polling should be skipped based on idle state and last poll time."""
        if not is_idle:
            return False  # Never skip when active

        if self.last_poll_timestamp is None:
            return False  # First poll, don't skip

        now = self.datetime_now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        if self.last_poll_timestamp.tzinfo is None:
            self.last_poll_timestamp = self.last_poll_timestamp.replace(tzinfo=UTC)

        time_since_poll = now - self.last_poll_timestamp
        return time_since_poll.total_seconds() < self.poll_interval_seconds

    def record_poll(self) -> None:
        """Record that a poll was executed."""
        self.last_poll_timestamp = self.datetime_now()

    def get_time_since_last_poll_seconds(self) -> float | None:
        """Get seconds since last poll, or None if no poll yet."""
        if self.last_poll_timestamp is None:
            return None

        now = self.datetime_now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        if self.last_poll_timestamp.tzinfo is None:
            self.last_poll_timestamp = self.last_poll_timestamp.replace(tzinfo=UTC)

        return (now - self.last_poll_timestamp).total_seconds()
