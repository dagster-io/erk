"""Integration tests for SQLiteThreadStore."""

from datetime import datetime
from pathlib import Path

from erk.slack.thread_store.sqlite import SQLiteThreadStore
from erk.slack.types import ThreadRecord


class TestSQLiteThreadStore:
    """Integration tests for SQLiteThreadStore with real SQLite."""

    def test_creates_database_file(self, tmp_path: Path) -> None:
        """SQLiteThreadStore creates database file on init."""
        db_path = tmp_path / "slack_threads.db"

        SQLiteThreadStore(db_path=db_path)

        assert db_path.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """SQLiteThreadStore creates parent directories if needed."""
        db_path = tmp_path / "subdir" / "nested" / "slack_threads.db"

        SQLiteThreadStore(db_path=db_path)

        assert db_path.exists()

    def test_get_thread_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """get_thread returns None for non-existent thread."""
        store = SQLiteThreadStore(db_path=tmp_path / "slack_threads.db")

        result = store.get_thread("C12345", "1234567890.123456")

        assert result is None

    def test_has_thread_returns_false_when_not_found(self, tmp_path: Path) -> None:
        """has_thread returns False for non-existent thread."""
        store = SQLiteThreadStore(db_path=tmp_path / "slack_threads.db")

        result = store.has_thread("C12345", "1234567890.123456")

        assert result is False

    def test_upsert_and_get_thread(self, tmp_path: Path) -> None:
        """upsert_thread stores record that can be retrieved."""
        store = SQLiteThreadStore(db_path=tmp_path / "slack_threads.db")
        now = datetime(2024, 1, 15, 10, 30, 0)
        record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id="session-abc-123",
            last_message_ts="1234567890.123456",
            created_at=now,
            updated_at=now,
        )

        store.upsert_thread(record)
        result = store.get_thread("C12345", "1234567890.123456")

        assert result is not None
        assert result.channel == "C12345"
        assert result.thread_ts == "1234567890.123456"
        assert result.session_id == "session-abc-123"
        assert result.last_message_ts == "1234567890.123456"
        assert result.created_at == now
        assert result.updated_at == now

    def test_has_thread_returns_true_after_upsert(self, tmp_path: Path) -> None:
        """has_thread returns True for existing thread."""
        store = SQLiteThreadStore(db_path=tmp_path / "slack_threads.db")
        now = datetime.now()
        record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id="session-abc-123",
            last_message_ts="1234567890.123456",
            created_at=now,
            updated_at=now,
        )

        store.upsert_thread(record)
        result = store.has_thread("C12345", "1234567890.123456")

        assert result is True

    def test_upsert_updates_existing_record(self, tmp_path: Path) -> None:
        """upsert_thread updates existing record with same key."""
        store = SQLiteThreadStore(db_path=tmp_path / "slack_threads.db")
        now = datetime(2024, 1, 15, 10, 30, 0)
        later = datetime(2024, 1, 15, 11, 0, 0)

        record1 = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id="session-old",
            last_message_ts="1234567890.123456",
            created_at=now,
            updated_at=now,
        )
        record2 = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id="session-new",
            last_message_ts="1234567890.234567",
            created_at=now,
            updated_at=later,
        )

        store.upsert_thread(record1)
        store.upsert_thread(record2)
        result = store.get_thread("C12345", "1234567890.123456")

        assert result is not None
        assert result.session_id == "session-new"
        assert result.last_message_ts == "1234567890.234567"
        assert result.updated_at == later

    def test_update_session_id_updates_existing(self, tmp_path: Path) -> None:
        """update_session_id changes session_id for existing thread."""
        store = SQLiteThreadStore(db_path=tmp_path / "slack_threads.db")
        now = datetime.now()
        record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id="session-old",
            last_message_ts="1234567890.123456",
            created_at=now,
            updated_at=now,
        )

        store.upsert_thread(record)
        store.update_session_id("C12345", "1234567890.123456", "session-new")
        result = store.get_thread("C12345", "1234567890.123456")

        assert result is not None
        assert result.session_id == "session-new"

    def test_stores_null_session_id(self, tmp_path: Path) -> None:
        """ThreadRecord with None session_id is stored correctly."""
        store = SQLiteThreadStore(db_path=tmp_path / "slack_threads.db")
        now = datetime.now()
        record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id=None,
            last_message_ts="1234567890.123456",
            created_at=now,
            updated_at=now,
        )

        store.upsert_thread(record)
        result = store.get_thread("C12345", "1234567890.123456")

        assert result is not None
        assert result.session_id is None

    def test_multiple_threads_different_channels(self, tmp_path: Path) -> None:
        """Can store and retrieve threads from different channels."""
        store = SQLiteThreadStore(db_path=tmp_path / "slack_threads.db")
        now = datetime.now()

        record1 = ThreadRecord(
            channel="C11111",
            thread_ts="1234567890.000001",
            session_id="session-1",
            last_message_ts="1234567890.000001",
            created_at=now,
            updated_at=now,
        )
        record2 = ThreadRecord(
            channel="C22222",
            thread_ts="1234567890.000002",
            session_id="session-2",
            last_message_ts="1234567890.000002",
            created_at=now,
            updated_at=now,
        )

        store.upsert_thread(record1)
        store.upsert_thread(record2)

        result1 = store.get_thread("C11111", "1234567890.000001")
        result2 = store.get_thread("C22222", "1234567890.000002")

        assert result1 is not None
        assert result1.session_id == "session-1"
        assert result2 is not None
        assert result2.session_id == "session-2"

    def test_persists_across_instances(self, tmp_path: Path) -> None:
        """Data persists when creating new SQLiteThreadStore instance."""
        db_path = tmp_path / "slack_threads.db"
        now = datetime.now()
        record = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.123456",
            session_id="session-abc-123",
            last_message_ts="1234567890.123456",
            created_at=now,
            updated_at=now,
        )

        # First instance writes
        store1 = SQLiteThreadStore(db_path=db_path)
        store1.upsert_thread(record)

        # Second instance reads
        store2 = SQLiteThreadStore(db_path=db_path)
        result = store2.get_thread("C12345", "1234567890.123456")

        assert result is not None
        assert result.session_id == "session-abc-123"
