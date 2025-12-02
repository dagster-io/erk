"""SQLite implementation of ThreadStore for production persistence."""

import sqlite3
from datetime import datetime
from pathlib import Path

from erk.slack.thread_store.abc import ThreadStore
from erk.slack.types import ThreadRecord


class SQLiteThreadStore(ThreadStore):
    """SQLite implementation of ThreadStore for production use.

    Stores thread records in a SQLite database for persistence
    across bot restarts.

    Attributes:
        db_path: Path to the SQLite database file
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize with database path and create schema if needed.

        Args:
            db_path: Path to the SQLite database file
        """
        self._db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the threads table if it doesn't exist."""
        # Ensure parent directory exists
        if not self._db_path.parent.exists():
            self._db_path.parent.mkdir(parents=True)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    channel TEXT NOT NULL,
                    thread_ts TEXT NOT NULL,
                    session_id TEXT,
                    last_message_ts TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (channel, thread_ts)
                )
            """)
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection.

        Returns:
            sqlite3.Connection to the database
        """
        return sqlite3.connect(self._db_path)

    def get_thread(self, channel: str, thread_ts: str) -> ThreadRecord | None:
        """Get a thread record from the database.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp

        Returns:
            ThreadRecord if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT channel, thread_ts, session_id, last_message_ts, created_at, updated_at
                FROM threads
                WHERE channel = ? AND thread_ts = ?
                """,
                (channel, thread_ts),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return ThreadRecord(
                channel=row[0],
                thread_ts=row[1],
                session_id=row[2],
                last_message_ts=row[3],
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5]),
            )

    def upsert_thread(self, record: ThreadRecord) -> None:
        """Insert or update a thread record in the database.

        Args:
            record: The ThreadRecord to store
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO threads (
                    channel, thread_ts, session_id,
                    last_message_ts, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(channel, thread_ts) DO UPDATE SET
                    session_id = excluded.session_id,
                    last_message_ts = excluded.last_message_ts,
                    updated_at = excluded.updated_at
                """,
                (
                    record.channel,
                    record.thread_ts,
                    record.session_id,
                    record.last_message_ts,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            conn.commit()

    def update_session_id(self, channel: str, thread_ts: str, session_id: str) -> None:
        """Update the session ID for an existing thread.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp
            session_id: The new Claude session ID
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE threads
                SET session_id = ?, updated_at = ?
                WHERE channel = ? AND thread_ts = ?
                """,
                (session_id, datetime.now().isoformat(), channel, thread_ts),
            )
            conn.commit()

    def has_thread(self, channel: str, thread_ts: str) -> bool:
        """Check if a thread record exists in the database.

        Args:
            channel: The Slack channel ID
            thread_ts: The thread timestamp

        Returns:
            True if the thread exists, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT 1 FROM threads
                WHERE channel = ? AND thread_ts = ?
                """,
                (channel, thread_ts),
            )
            return cursor.fetchone() is not None
