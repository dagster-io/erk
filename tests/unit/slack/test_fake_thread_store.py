"""Tests for FakeThreadStore."""

from datetime import datetime

from erk.slack.thread_store.fake import FakeThreadStore
from erk.slack.types import ThreadRecord


class TestFakeThreadStore:
    """Tests for FakeThreadStore."""

    def test_get_thread_returns_none_when_not_found(self) -> None:
        """get_thread returns None for non-existent thread."""
        store = FakeThreadStore()

        result = store.get_thread("C12345", "1234567890.123456")

        assert result is None

    def test_has_thread_returns_false_when_not_found(self) -> None:
        """has_thread returns False for non-existent thread."""
        store = FakeThreadStore()

        result = store.has_thread("C12345", "1234567890.123456")

        assert result is False

    def test_upsert_and_get_thread(self) -> None:
        """upsert_thread stores record that can be retrieved."""
        store = FakeThreadStore()
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

        assert result == record

    def test_has_thread_returns_true_after_upsert(self) -> None:
        """has_thread returns True for existing thread."""
        store = FakeThreadStore()
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

    def test_upsert_updates_existing_record(self) -> None:
        """upsert_thread replaces existing record with same key."""
        store = FakeThreadStore()
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
        assert result.updated_at == later

    def test_update_session_id_updates_existing(self) -> None:
        """update_session_id changes session_id for existing thread."""
        store = FakeThreadStore()
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

    def test_records_upserted_tracks_all_upserts(self) -> None:
        """records_upserted contains all records that were upserted."""
        store = FakeThreadStore()
        now = datetime.now()
        record1 = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.000001",
            session_id=None,
            last_message_ts="1234567890.000001",
            created_at=now,
            updated_at=now,
        )
        record2 = ThreadRecord(
            channel="C12345",
            thread_ts="1234567890.000002",
            session_id=None,
            last_message_ts="1234567890.000002",
            created_at=now,
            updated_at=now,
        )

        store.upsert_thread(record1)
        store.upsert_thread(record2)

        assert len(store.records_upserted) == 2
        assert store.records_upserted[0] == record1
        assert store.records_upserted[1] == record2

    def test_session_updates_tracks_all_updates(self) -> None:
        """session_updates contains all session ID updates."""
        store = FakeThreadStore()
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
        store.update_session_id("C12345", "1234567890.123456", "session-1")
        store.update_session_id("C12345", "1234567890.123456", "session-2")

        assert len(store.session_updates) == 2
        assert store.session_updates[0] == ("C12345", "1234567890.123456", "session-1")
        assert store.session_updates[1] == ("C12345", "1234567890.123456", "session-2")

    def test_all_threads_returns_copy(self) -> None:
        """all_threads returns a copy of the internal dict."""
        store = FakeThreadStore()
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
        threads_copy = store.all_threads
        threads_copy.clear()

        assert len(store.all_threads) == 1
