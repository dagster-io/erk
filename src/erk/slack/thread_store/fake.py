"""Fake implementation of ThreadStore for testing."""

from erk.slack.thread_store.abc import ThreadStore
from erk.slack.types import ThreadRecord


class FakeThreadStore(ThreadStore):
    """In-memory implementation of ThreadStore for testing.

    Stores thread records in a dictionary keyed by (channel, thread_ts).
    Provides mutation tracking for test assertions.

    Example:
        >>> store = FakeThreadStore()
        >>> store.upsert_thread(record)
        >>> assert store.has_thread("C123", "1234.5678")
        >>> assert len(store.records_upserted) == 1
    """

    def __init__(self) -> None:
        """Initialize with empty storage."""
        self._threads: dict[tuple[str, str], ThreadRecord] = {}
        self._upserted: list[ThreadRecord] = []
        self._session_updates: list[tuple[str, str, str]] = []

    def get_thread(self, channel: str, thread_ts: str) -> ThreadRecord | None:
        """Get a thread record from in-memory storage.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp

        Returns:
            ThreadRecord if found, None otherwise
        """
        key = (channel, thread_ts)
        if key not in self._threads:
            return None
        return self._threads[key]

    def upsert_thread(self, record: ThreadRecord) -> None:
        """Insert or update a thread record in memory.

        Args:
            record: The ThreadRecord to store
        """
        key = (record.channel, record.thread_ts)
        self._threads[key] = record
        self._upserted.append(record)

    def update_session_id(self, channel: str, thread_ts: str, session_id: str) -> None:
        """Update the session ID for an existing thread.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp
            session_id: The new Claude session ID
        """
        key = (channel, thread_ts)
        if key in self._threads:
            old_record = self._threads[key]
            # Create new record with updated session_id (frozen dataclass)
            new_record = ThreadRecord(
                channel=old_record.channel,
                thread_ts=old_record.thread_ts,
                session_id=session_id,
                last_message_ts=old_record.last_message_ts,
                created_at=old_record.created_at,
                updated_at=old_record.updated_at,
            )
            self._threads[key] = new_record
        self._session_updates.append((channel, thread_ts, session_id))

    def has_thread(self, channel: str, thread_ts: str) -> bool:
        """Check if a thread record exists in memory.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp

        Returns:
            True if the thread exists, False otherwise
        """
        key = (channel, thread_ts)
        return key in self._threads

    @property
    def records_upserted(self) -> list[ThreadRecord]:
        """Read-only access to records that were upserted.

        Returns:
            Copy of the upserted records list
        """
        return list(self._upserted)

    @property
    def session_updates(self) -> list[tuple[str, str, str]]:
        """Read-only access to session ID updates.

        Returns:
            List of (channel, thread_ts, session_id) tuples
        """
        return list(self._session_updates)

    @property
    def all_threads(self) -> dict[tuple[str, str], ThreadRecord]:
        """Read-only access to all stored threads.

        Returns:
            Copy of the threads dictionary
        """
        return dict(self._threads)
