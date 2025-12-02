"""Abstract interface for thread persistence."""

from abc import ABC, abstractmethod

from erk.slack.types import ThreadRecord


class ThreadStore(ABC):
    """Abstract interface for thread persistence.

    Implementations store ThreadRecord data to enable conversation
    continuity across bot restarts.
    """

    @abstractmethod
    def get_thread(self, channel: str, thread_ts: str) -> ThreadRecord | None:
        """Get a thread record by channel and thread timestamp.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp

        Returns:
            ThreadRecord if found, None otherwise
        """
        ...

    @abstractmethod
    def upsert_thread(self, record: ThreadRecord) -> None:
        """Insert or update a thread record.

        If a record with the same channel and thread_ts exists,
        it will be updated. Otherwise, a new record is created.

        Args:
            record: The ThreadRecord to insert or update
        """
        ...

    @abstractmethod
    def update_session_id(self, channel: str, thread_ts: str, session_id: str) -> None:
        """Update the session ID for an existing thread.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp
            session_id: The new Claude session ID
        """
        ...

    @abstractmethod
    def has_thread(self, channel: str, thread_ts: str) -> bool:
        """Check if a thread record exists.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp

        Returns:
            True if the thread exists, False otherwise
        """
        ...
