"""Comprehensive tests for SlackbotInstanceSqliteStorage expiry and soft delete behavior."""

import asyncio
from unittest.mock import Mock

import pytest

from csbot.slackbot.storage.sqlite import SlackbotInstanceSqliteStorage, SqliteConnectionFactory
from csbot.utils.time import SecondsNowFake


class TestSlackbotStorageExpiry:
    """Test suite for expiry and soft delete functionality."""

    @pytest.fixture
    def time_provider(self):
        """Create a controllable time provider starting at timestamp 1000."""
        return SecondsNowFake(1000)

    @pytest.fixture
    def sql_conn_factory(self, time_provider):
        """Create a fresh in-memory SQLite connection factory with test time provider."""
        return SqliteConnectionFactory.temporary_for_testing(time_provider)

    @pytest.fixture
    def storage(self, sql_conn_factory, time_provider):
        """Create a storage instance with test time provider."""
        return SlackbotInstanceSqliteStorage(sql_conn_factory, "test_bot_id", Mock(), time_provider)

    # Basic Expiry Tests
    @pytest.mark.asyncio
    async def test_set_with_expiry_get_before_expiry(self, storage, time_provider):
        """Test that values can be retrieved before they expire."""
        family, key, value = "family", "key", "value"
        expiry_seconds = 100

        await storage.set(family, key, value, expiry_seconds)

        # Advance time but not past expiry
        time_provider.advance_time(50)

        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_set_with_expiry_get_after_expiry(self, storage, time_provider):
        """Test that values return None after they expire."""
        family, key, value = "family", "key", "value"
        expiry_seconds = 100

        await storage.set(family, key, value, expiry_seconds)

        # Advance time past expiry
        time_provider.advance_time(150)

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_set_with_expiry_exact_boundary(self, storage, time_provider):
        """Test behavior exactly at expiry boundary."""
        family, key, value = "family", "key", "value"
        expiry_seconds = 100

        await storage.set(family, key, value, expiry_seconds)

        # Advance time to exactly the expiry time
        time_provider.advance_time(100)

        # At exactly expiry_time, the value should be considered expired
        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_set_with_expiry_one_second_before(self, storage, time_provider):
        """Test behavior one second before expiry."""
        family, key, value = "family", "key", "value"
        expiry_seconds = 100

        await storage.set(family, key, value, expiry_seconds)

        # Advance time to one second before expiry
        time_provider.advance_time(99)

        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_set_without_expiry_never_expires(self, storage, time_provider):
        """Test that values without expiry never expire."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)  # No expiry

        # Advance time significantly
        time_provider.advance_time(10000)

        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_set_with_zero_expiry_never_expires(self, storage, time_provider):
        """Test that expiry_seconds=0 means no expiry."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value, expiry_seconds=0)

        # Advance time significantly
        time_provider.advance_time(10000)

        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_set_with_negative_expiry_never_expires(self, storage, time_provider):
        """Test that negative expiry_seconds means no expiry."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value, expiry_seconds=-1)

        # Advance time significantly
        time_provider.advance_time(10000)

        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    # Expiry Edge Cases
    @pytest.mark.asyncio
    async def test_update_expiry_extends_life(self, storage, time_provider):
        """Test that updating a value with new expiry extends its life."""
        family, key, value1, value2 = "family", "key", "value1", "value2"

        # Set with short expiry
        await storage.set(family, key, value1, expiry_seconds=50)

        # Advance time close to expiry
        time_provider.advance_time(40)

        # Update with longer expiry
        await storage.set(family, key, value2, expiry_seconds=100)

        # Advance past original expiry but within new expiry
        time_provider.advance_time(30)  # Total: 70 seconds

        assert await storage.get(family, key) == value2
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_update_expiry_shortens_life(self, storage, time_provider):
        """Test that updating a value with shorter expiry shortens its life."""
        family, key, value1, value2 = "family", "key", "value1", "value2"

        # Set with long expiry
        await storage.set(family, key, value1, expiry_seconds=200)

        # Advance time
        time_provider.advance_time(50)

        # Update with shorter expiry
        await storage.set(family, key, value2, expiry_seconds=30)

        # Advance past new expiry but within original expiry
        time_provider.advance_time(40)  # Total: 90 seconds

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_update_to_no_expiry(self, storage, time_provider):
        """Test that updating a value to no expiry removes expiry."""
        family, key, value1, value2 = "family", "key", "value1", "value2"

        # Set with expiry
        await storage.set(family, key, value1, expiry_seconds=50)

        # Advance time close to expiry
        time_provider.advance_time(40)

        # Update with no expiry
        await storage.set(family, key, value2)

        # Advance past original expiry
        time_provider.advance_time(50)

        assert await storage.get(family, key) == value2
        assert await storage.exists(family, key) is True

    # Soft Delete Tests
    @pytest.mark.asyncio
    async def test_delete_marks_as_deleted(self, storage, time_provider):
        """Test that delete() soft deletes entries."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        await storage.delete(family, key)

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key_is_noop(self, storage, time_provider):
        """Test that deleting a nonexistent key is a no-op."""
        family, key = "family", "nonexistent"

        await storage.delete(family, key)  # Should not raise error

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_delete_already_deleted_key_is_noop(self, storage, time_provider):
        """Test that deleting an already deleted key is a no-op."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        await storage.delete(family, key)
        await storage.delete(family, key)  # Second delete should be no-op

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_set_after_delete_resurrects_key(self, storage, time_provider):
        """Test that setting a value after deletion resurrects the key."""
        family, key, value1, value2 = "family", "key", "value1", "value2"

        await storage.set(family, key, value1)
        await storage.delete(family, key)
        await storage.set(family, key, value2)

        assert await storage.get(family, key) == value2
        assert await storage.exists(family, key) is True

    # Combined Expiry and Soft Delete Tests
    @pytest.mark.asyncio
    async def test_expired_entry_gets_soft_deleted(self, storage, time_provider):
        """Test that accessing an expired entry triggers soft deletion."""
        family, key, value = "family", "key", "value"
        expiry_seconds = 100

        await storage.set(family, key, value, expiry_seconds)

        # Advance time past expiry
        time_provider.advance_time(150)

        # Access should trigger soft deletion
        assert await storage.get(family, key) is None

        # Second access should still return None (not find the expired entry)
        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_delete_before_expiry(self, storage, time_provider):
        """Test deleting a key before it expires."""
        family, key, value = "family", "key", "value"
        expiry_seconds = 100

        await storage.set(family, key, value, expiry_seconds)

        # Delete before expiry
        time_provider.advance_time(50)
        await storage.delete(family, key)

        # Should be deleted regardless of expiry
        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

        # Even after expiry time, should still be None
        time_provider.advance_time(100)
        assert await storage.get(family, key) is None

    @pytest.mark.asyncio
    async def test_set_with_expiry_after_soft_delete(self, storage, time_provider):
        """Test setting a new value with expiry after soft deletion."""
        family, key, value1, value2 = "family", "key", "value1", "value2"

        await storage.set(family, key, value1)
        await storage.delete(family, key)
        await storage.set(family, key, value2, expiry_seconds=50)

        # Should be accessible before expiry
        time_provider.advance_time(30)
        assert await storage.get(family, key) == value2

        # Should expire after expiry time
        time_provider.advance_time(30)
        assert await storage.get(family, key) is None

    # Database Cleanup Tests
    def test_initialization_cleans_up_expired_entries(self, time_provider):
        """Test that database initialization removes expired entries."""
        # Create storage and add expired entry
        factory1 = SqliteConnectionFactory.temporary_for_testing(time_provider)
        storage1 = SlackbotInstanceSqliteStorage(factory1, "test_bot_id", Mock(), time_provider)

        asyncio.run(storage1.set("family", "key", "value", expiry_seconds=50))

        # Advance time past expiry
        time_provider.advance_time(100)

        # Create new storage with same connection (simulates restart)
        storage2 = SlackbotInstanceSqliteStorage(factory1, "test_bot_id", Mock(), time_provider)

        # Expired entry should not be accessible
        assert asyncio.run(storage2.get("family", "key")) is None
        assert asyncio.run(storage2.exists("family", "key")) is False

    # Multiple Keys and Families with Expiry
    @pytest.mark.asyncio
    async def test_mixed_expiry_states(self, storage, time_provider):
        """Test multiple keys with different expiry states."""
        # Set various keys with different expiry times
        await storage.set("family", "key1", "value1", expiry_seconds=50)
        await storage.set("family", "key2", "value2", expiry_seconds=100)
        await storage.set("family", "key3", "value3")  # No expiry
        await storage.set("family", "key4", "value4", expiry_seconds=25)

        # Advance time to expire some but not all
        time_provider.advance_time(75)

        # key1 and key4 should be expired, key2 and key3 should remain
        assert await storage.get("family", "key1") is None
        assert await storage.get("family", "key2") == "value2"
        assert await storage.get("family", "key3") == "value3"
        assert await storage.get("family", "key4") is None

        assert await storage.exists("family", "key1") is False
        assert await storage.exists("family", "key2") is True
        assert await storage.exists("family", "key3") is True
        assert await storage.exists("family", "key4") is False

    @pytest.mark.asyncio
    async def test_expiry_isolation_across_families(self, storage, time_provider):
        """Test that expiry works independently across families."""
        await storage.set("family1", "key", "value1", expiry_seconds=50)
        await storage.set("family2", "key", "value2", expiry_seconds=100)

        # Advance time to expire family1 but not family2
        time_provider.advance_time(75)

        assert await storage.get("family1", "key") is None
        assert await storage.get("family2", "key") == "value2"
        assert await storage.exists("family1", "key") is False
        assert await storage.exists("family2", "key") is True

    @pytest.mark.asyncio
    async def test_expiry_isolation_across_bots(self, sql_conn_factory, time_provider):
        """Test that expiry works independently across bot IDs."""
        storage1 = SlackbotInstanceSqliteStorage(sql_conn_factory, "bot1", Mock(), time_provider)
        storage2 = SlackbotInstanceSqliteStorage(sql_conn_factory, "bot2", Mock(), time_provider)

        await storage1.set("family", "key", "value1", expiry_seconds=50)
        await storage2.set("family", "key", "value2", expiry_seconds=100)

        # Advance time to expire bot1 but not bot2
        time_provider.advance_time(75)

        assert await storage1.get("family", "key") is None
        assert await storage2.get("family", "key") == "value2"
        assert await storage1.exists("family", "key") is False
        assert await storage2.exists("family", "key") is True

    # Stress Tests
    @pytest.mark.asyncio
    async def test_rapid_expiry_cycles(self, storage, time_provider):
        """Test rapid cycles of set/expire for the same key."""
        family, key = "family", "key"

        for i in range(10):
            value = f"value{i}"
            await storage.set(family, key, value, expiry_seconds=10)

            # Verify it's there
            assert await storage.get(family, key) == value

            # Expire it
            time_provider.advance_time(15)
            assert await storage.get(family, key) is None

    @pytest.mark.asyncio
    async def test_large_number_of_expired_keys(self, storage, time_provider):
        """Test behavior with many expired keys."""
        family = "family"

        # Set many keys with short expiry
        for i in range(100):
            await storage.set(family, f"key{i}", f"value{i}", expiry_seconds=10)

        # Expire all
        time_provider.advance_time(15)

        # All should be expired
        for i in range(100):
            assert await storage.get(family, f"key{i}") is None
            assert await storage.exists(family, f"key{i}") is False

    # Time Provider Edge Cases
    @pytest.mark.asyncio
    async def test_time_going_backwards_edge_case(self, storage, time_provider):
        """Test edge case where time appears to go backwards."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value, expiry_seconds=100)

        # Advance time
        time_provider.advance_time(50)
        assert await storage.get(family, key) == value

        # Set time backwards (edge case)
        time_provider.set_time(900)  # Earlier than initial time of 1000

        # Value should still be accessible (expiry is absolute timestamp)
        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_very_large_expiry_times(self, storage, time_provider):
        """Test with very large expiry times."""
        family, key, value = "family", "key", "value"

        # Set with very large expiry (1 million seconds)
        await storage.set(family, key, value, expiry_seconds=1_000_000)

        # Advance time significantly but not past expiry
        time_provider.advance_time(500_000)

        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

        # Advance past expiry
        time_provider.advance_time(600_000)

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_atomic_expiry_operations_no_race_condition(self, storage, time_provider):
        """Test that concurrent access to expired keys doesn't cause race conditions."""
        family, key, value = "family", "key", "value"
        expiry_seconds = 100

        await storage.set(family, key, value, expiry_seconds)

        # Advance time past expiry
        time_provider.advance_time(150)

        # Multiple concurrent calls to get() and exists() should be safe
        # (In a real concurrent scenario, these would run in parallel)
        results = []
        for _ in range(5):
            results.append(await storage.get(family, key))
            results.append(await storage.exists(family, key))

        # All results should be None/False
        assert all(result is None or result is False for result in results)

        # Key should remain soft-deleted after all operations
        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False
