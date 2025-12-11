from abc import ABC, abstractmethod

import pytest

from csbot.slackbot.storage.interface import SlackbotInstanceStorage, SqlConnectionFactory
from csbot.utils.time import SecondsNow, system_seconds_now


class StorageTestBase(ABC):
    """Abstract base class for testing SlackbotInstanceStorage implementations.

    This class contains comprehensive tests that any storage backend should pass.
    Subclasses need to implement the fixture methods to provide backend-specific
    connection factories and storage instances.
    """

    @pytest.fixture
    @abstractmethod
    def sql_conn_factory(self) -> SqlConnectionFactory:
        """Create a fresh connection factory for each test."""
        pass

    @pytest.fixture
    @abstractmethod
    def storage(self, sql_conn_factory: SqlConnectionFactory) -> SlackbotInstanceStorage:
        """Create a storage instance with a test bot ID."""
        pass

    @pytest.fixture
    @abstractmethod
    def storage2(self, sql_conn_factory: SqlConnectionFactory) -> SlackbotInstanceStorage:
        """Create a second storage instance with a different bot ID for isolation tests."""
        pass

    # Bot ID Isolation Tests
    @pytest.mark.asyncio
    async def test_bot_id_isolation_basic(self, sql_conn_factory):
        """Test that different bot IDs don't interfere with each other."""
        storage1 = self._create_storage(sql_conn_factory, "bot1", system_seconds_now)
        storage2 = self._create_storage(sql_conn_factory, "bot2", system_seconds_now)

        family, key, value1, value2 = "family", "key", "value1", "value2"

        # Set different values in different bots
        await storage1.set(family, key, value1)
        await storage2.set(family, key, value2)

        # Each bot should only see its own value
        assert await storage1.get(family, key) == value1
        assert await storage2.get(family, key) == value2

    @pytest.mark.asyncio
    async def test_bot_id_isolation_exists(self, sql_conn_factory):
        """Test that exists() respects bot ID isolation."""
        storage1 = self._create_storage(sql_conn_factory, "bot1", system_seconds_now)
        storage2 = self._create_storage(sql_conn_factory, "bot2", system_seconds_now)

        family, key, value = "family", "key", "value"

        # Set in bot1 only
        await storage1.set(family, key, value)

        # Bot1 should see it exists, bot2 should not
        assert await storage1.exists(family, key) is True
        assert await storage2.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_bot_id_isolation_delete(self, sql_conn_factory):
        """Test that delete() respects bot ID isolation."""
        storage1 = self._create_storage(sql_conn_factory, "bot1", system_seconds_now)
        storage2 = self._create_storage(sql_conn_factory, "bot2", system_seconds_now)

        family, key, value = "family", "key", "value"

        # Set same key in both bots
        await storage1.set(family, key, value)
        await storage2.set(family, key, value)

        # Delete from bot1 only
        await storage1.delete(family, key)

        # Bot1 should not have it, bot2 should still have it
        assert await storage1.exists(family, key) is False
        assert await storage2.exists(family, key) is True
        assert await storage2.get(family, key) == value

    # Family Isolation Tests
    @pytest.mark.asyncio
    async def test_family_isolation_basic(self, storage):
        """Test that different families don't interfere with each other."""
        family1, family2 = "family1", "family2"
        key, value1, value2 = "key", "value1", "value2"

        # Set different values in different families
        await storage.set(family1, key, value1)
        await storage.set(family2, key, value2)

        # Each family should only see its own value
        assert await storage.get(family1, key) == value1
        assert await storage.get(family2, key) == value2

    @pytest.mark.asyncio
    async def test_family_isolation_exists(self, storage):
        """Test that exists() respects family isolation."""
        family1, family2 = "family1", "family2"
        key, value = "key", "value"

        # Set in family1 only
        await storage.set(family1, key, value)

        # Family1 should see it exists, family2 should not
        assert await storage.exists(family1, key) is True
        assert await storage.exists(family2, key) is False

    @pytest.mark.asyncio
    async def test_family_isolation_delete(self, storage):
        """Test that delete() respects family isolation."""
        family1, family2 = "family1", "family2"
        key, value = "key", "value"

        # Set same key in both families
        await storage.set(family1, key, value)
        await storage.set(family2, key, value)

        # Delete from family1 only
        await storage.delete(family1, key)

        # Family1 should not have it, family2 should still have it
        assert await storage.exists(family1, key) is False
        assert await storage.exists(family2, key) is True
        assert await storage.get(family2, key) == value

    # State Machine Tests - All Operation Orderings
    @pytest.mark.asyncio
    async def test_get_set_get(self, storage):
        """Test: get (missing) → set → get (present)."""
        family, key, value = "family", "key", "value"

        # Start: MISSING state
        assert await storage.get(family, key) is None

        # Transition to PRESENT
        await storage.set(family, key, value)

        # Verify PRESENT state
        assert await storage.get(family, key) == value

    @pytest.mark.asyncio
    async def test_get_set_exists(self, storage):
        """Test: get (missing) → set → exists (true)."""
        family, key, value = "family", "key", "value"

        assert await storage.get(family, key) is None
        await storage.set(family, key, value)
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_get_set_delete(self, storage):
        """Test: get (missing) → set → delete."""
        family, key, value = "family", "key", "value"

        assert await storage.get(family, key) is None
        await storage.set(family, key, value)
        await storage.delete(family, key)
        assert await storage.get(family, key) is None

    @pytest.mark.asyncio
    async def test_get_exists_set(self, storage):
        """Test: get (missing) → exists (false) → set."""
        family, key, value = "family", "key", "value"

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False
        await storage.set(family, key, value)
        assert await storage.get(family, key) == value

    @pytest.mark.asyncio
    async def test_get_exists_delete(self, storage):
        """Test: get (missing) → exists (false) → delete (no-op)."""
        family, key = "family", "key"

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False
        await storage.delete(family, key)  # Should be no-op
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_get_delete_set(self, storage):
        """Test: get (missing) → delete (no-op) → set."""
        family, key, value = "family", "key", "value"

        assert await storage.get(family, key) is None
        await storage.delete(family, key)  # Should be no-op
        await storage.set(family, key, value)
        assert await storage.get(family, key) == value

    @pytest.mark.asyncio
    async def test_set_get_exists(self, storage):
        """Test: set → get → exists."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_set_get_delete(self, storage):
        """Test: set → get → delete."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        assert await storage.get(family, key) == value
        await storage.delete(family, key)
        assert await storage.get(family, key) is None

    @pytest.mark.asyncio
    async def test_set_exists_get(self, storage):
        """Test: set → exists → get."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        assert await storage.exists(family, key) is True
        assert await storage.get(family, key) == value

    @pytest.mark.asyncio
    async def test_set_exists_delete(self, storage):
        """Test: set → exists → delete."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        assert await storage.exists(family, key) is True
        await storage.delete(family, key)
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_set_delete_get(self, storage):
        """Test: set → delete → get (missing)."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        await storage.delete(family, key)
        assert await storage.get(family, key) is None

    @pytest.mark.asyncio
    async def test_set_delete_exists(self, storage):
        """Test: set → delete → exists (false)."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        await storage.delete(family, key)
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_exists_get_set(self, storage):
        """Test: exists (false) → get (missing) → set."""
        family, key, value = "family", "key", "value"

        assert await storage.exists(family, key) is False
        assert await storage.get(family, key) is None
        await storage.set(family, key, value)
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_exists_get_delete(self, storage):
        """Test: exists (false) → get (missing) → delete (no-op)."""
        family, key = "family", "key"

        assert await storage.exists(family, key) is False
        assert await storage.get(family, key) is None
        await storage.delete(family, key)  # Should be no-op
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_exists_set_get(self, storage):
        """Test: exists (false) → set → get."""
        family, key, value = "family", "key", "value"

        assert await storage.exists(family, key) is False
        await storage.set(family, key, value)
        assert await storage.get(family, key) == value

    @pytest.mark.asyncio
    async def test_exists_set_delete(self, storage):
        """Test: exists (false) → set → delete."""
        family, key, value = "family", "key", "value"

        assert await storage.exists(family, key) is False
        await storage.set(family, key, value)
        await storage.delete(family, key)
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_exists_delete_set(self, storage):
        """Test: exists (false) → delete (no-op) → set."""
        family, key, value = "family", "key", "value"

        assert await storage.exists(family, key) is False
        await storage.delete(family, key)  # Should be no-op
        await storage.set(family, key, value)
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_delete_get_set(self, storage):
        """Test: delete (no-op) → get (missing) → set."""
        family, key, value = "family", "key", "value"

        await storage.delete(family, key)  # Should be no-op
        assert await storage.get(family, key) is None
        await storage.set(family, key, value)
        assert await storage.get(family, key) == value

    @pytest.mark.asyncio
    async def test_delete_set_get(self, storage):
        """Test: delete (no-op) → set → get."""
        family, key, value = "family", "key", "value"

        await storage.delete(family, key)  # Should be no-op
        await storage.set(family, key, value)
        assert await storage.get(family, key) == value

    @pytest.mark.asyncio
    async def test_delete_exists_set(self, storage):
        """Test: delete (no-op) → exists (false) → set."""
        family, key, value = "family", "key", "value"

        await storage.delete(family, key)  # Should be no-op
        assert await storage.exists(family, key) is False
        await storage.set(family, key, value)
        assert await storage.exists(family, key) is True

    # Value Update Tests
    @pytest.mark.asyncio
    async def test_set_overwrite_value(self, storage):
        """Test that setting a new value overwrites the old value."""
        family, key, value1, value2 = "family", "key", "value1", "value2"

        await storage.set(family, key, value1)
        assert await storage.get(family, key) == value1

        await storage.set(family, key, value2)
        assert await storage.get(family, key) == value2
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_set_same_value_multiple_times(self, storage):
        """Test that setting the same value multiple times is idempotent."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        await storage.set(family, key, value)
        await storage.set(family, key, value)

        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    # Multiple Delete Tests
    @pytest.mark.asyncio
    async def test_delete_multiple_times(self, storage):
        """Test that deleting the same key multiple times is safe."""
        family, key, value = "family", "key", "value"

        await storage.set(family, key, value)
        await storage.delete(family, key)
        await storage.delete(family, key)  # Should be no-op
        await storage.delete(family, key)  # Should be no-op

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    # Longer State Machine Sequences
    @pytest.mark.asyncio
    async def test_complex_sequence_1(self, storage):
        """Test: set → delete → set → get → exists → delete."""
        family, key, value1, value2 = "family", "key", "value1", "value2"

        await storage.set(family, key, value1)
        await storage.delete(family, key)
        await storage.set(family, key, value2)
        assert await storage.get(family, key) == value2
        assert await storage.exists(family, key) is True
        await storage.delete(family, key)
        assert await storage.get(family, key) is None

    @pytest.mark.asyncio
    async def test_complex_sequence_2(self, storage):
        """Test: get → exists → delete → set → get → set → exists → delete."""
        family, key, value1, value2 = "family", "key", "value1", "value2"

        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False
        await storage.delete(family, key)  # no-op
        await storage.set(family, key, value1)
        assert await storage.get(family, key) == value1
        await storage.set(family, key, value2)
        assert await storage.exists(family, key) is True
        await storage.delete(family, key)
        assert await storage.get(family, key) is None

    # Edge Cases
    @pytest.mark.asyncio
    async def test_empty_string_value(self, storage):
        """Test storage with empty string as value."""
        family, key, value = "family", "key", ""

        await storage.set(family, key, value)
        assert await storage.get(family, key) == ""
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_empty_string_key(self, storage):
        """Test storage with empty string as key."""
        family, key, value = "family", "", "value"

        await storage.set(family, key, value)
        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_empty_string_family(self, storage):
        """Test storage with empty string as family."""
        family, key, value = "", "key", "value"

        await storage.set(family, key, value)
        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_unicode_characters(self, storage):
        """Test storage with Unicode characters."""
        family, key, value = "家族", "键", "值🔑"

        await storage.set(family, key, value)
        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_special_characters(self, storage):
        """Test storage with special characters that might affect SQL."""
        family = "fam'ily"
        key = 'key"with"quotes'
        value = "value\nwith\ttabs"

        await storage.set(family, key, value)
        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_very_long_strings(self, storage):
        """Test storage with very long strings."""
        family = "f" * 1000
        key = "k" * 1000
        value = "v" * 10000

        await storage.set(family, key, value)
        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_whitespace_strings(self, storage):
        """Test storage with whitespace-only strings."""
        family, key, value = "   ", "\t\n", "  \t  "

        await storage.set(family, key, value)
        assert await storage.get(family, key) == value
        assert await storage.exists(family, key) is True

    # Comprehensive Multi-Key Test
    @pytest.mark.asyncio
    async def test_multiple_keys_independence(self, storage):
        """Test that multiple keys in the same family are independent."""
        family = "family"
        key1, key2, key3 = "key1", "key2", "key3"
        value1, value2, value3 = "value1", "value2", "value3"

        # Set all values
        await storage.set(family, key1, value1)
        await storage.set(family, key2, value2)
        await storage.set(family, key3, value3)

        # Verify all are set correctly
        assert await storage.get(family, key1) == value1
        assert await storage.get(family, key2) == value2
        assert await storage.get(family, key3) == value3

        # Delete middle key
        await storage.delete(family, key2)

        # Verify only middle key is deleted
        assert await storage.get(family, key1) == value1
        assert await storage.get(family, key2) is None
        assert await storage.get(family, key3) == value3
        assert await storage.exists(family, key1) is True
        assert await storage.exists(family, key2) is False
        assert await storage.exists(family, key3) is True

    @pytest.mark.asyncio
    async def test_concurrent_bot_and_family_operations(self, sql_conn_factory):
        """Test complex scenario with multiple bots and families."""
        storage1 = self._create_storage(sql_conn_factory, "bot1", system_seconds_now)
        storage2 = self._create_storage(sql_conn_factory, "bot2", system_seconds_now)

        # Set up data in both bots across multiple families
        await storage1.set("family1", "key1", "bot1_family1_value1")
        await storage1.set("family2", "key1", "bot1_family2_value1")
        await storage2.set("family1", "key1", "bot2_family1_value1")
        await storage2.set("family2", "key1", "bot2_family2_value1")

        # Verify isolation
        assert await storage1.get("family1", "key1") == "bot1_family1_value1"
        assert await storage1.get("family2", "key1") == "bot1_family2_value1"
        assert await storage2.get("family1", "key1") == "bot2_family1_value1"
        assert await storage2.get("family2", "key1") == "bot2_family2_value1"

        # Delete from bot1 family1 only
        await storage1.delete("family1", "key1")

        # Verify only the specific entry was deleted
        assert await storage1.get("family1", "key1") is None
        assert await storage1.get("family2", "key1") == "bot1_family2_value1"
        assert await storage2.get("family1", "key1") == "bot2_family1_value1"
        assert await storage2.get("family2", "key1") == "bot2_family2_value1"

    # get_and_set Tests
    @pytest.mark.asyncio
    async def test_get_and_set_key_does_not_exist(self, storage):
        """Test get_and_set when key doesn't exist initially."""
        family, key = "get_and_set_test", "missing_key"

        def value_factory(current_value):
            assert current_value is None
            return "new_value"

        await storage.get_and_set(family, key, value_factory)
        assert await storage.get(family, key) == "new_value"

    @pytest.mark.asyncio
    async def test_get_and_set_key_exists(self, storage):
        """Test get_and_set when key exists."""
        family, key, initial_value = "get_and_set_test", "existing_key", "initial_value"

        # Set up initial state
        await storage.set(family, key, initial_value)

        def value_factory(current_value):
            assert current_value == initial_value
            return "updated_value"

        await storage.get_and_set(family, key, value_factory)
        assert await storage.get(family, key) == "updated_value"

    @pytest.mark.asyncio
    async def test_get_and_set_factory_returns_none_key_exists(self, storage):
        """Test get_and_set when factory returns None and key exists (should delete)."""
        family, key, initial_value = "get_and_set_test", "delete_key", "initial_value"

        # Set up initial state
        await storage.set(family, key, initial_value)
        assert await storage.exists(family, key) is True

        def value_factory(current_value):
            assert current_value == initial_value
            return None

        await storage.get_and_set(family, key, value_factory)
        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_get_and_set_factory_returns_none_key_missing(self, storage):
        """Test get_and_set when factory returns None and key doesn't exist (no-op)."""
        family, key = "get_and_set_test", "no_op_key"

        def value_factory(current_value):
            assert current_value is None
            return None

        await storage.get_and_set(family, key, value_factory)
        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_get_and_set_with_expiry(self, storage):
        """Test get_and_set with expiry_seconds parameter."""
        family, key = "get_and_set_test", "expiry_key"

        def value_factory(current_value):
            assert current_value is None
            return "value_with_expiry"

        await storage.get_and_set(family, key, value_factory, expiry_seconds=3600)
        assert await storage.get(family, key) == "value_with_expiry"
        assert await storage.exists(family, key) is True

    @pytest.mark.asyncio
    async def test_get_and_set_atomicity_no_exception(self, storage):
        """Test get_and_set atomicity - successful operation."""
        family, key, initial_value = "get_and_set_test", "atomicity_key", "initial_value"

        await storage.set(family, key, initial_value)

        call_count = 0

        def value_factory(current_value):
            nonlocal call_count
            call_count += 1
            assert current_value == initial_value
            return f"updated_value_{call_count}"

        await storage.get_and_set(family, key, value_factory)

        # Value factory should be called exactly once
        assert call_count == 1
        assert await storage.get(family, key) == "updated_value_1"

    @pytest.mark.asyncio
    async def test_get_and_set_factory_exception_rollback(self, storage):
        """Test get_and_set rollback when value_factory raises exception."""
        family, key, initial_value = "get_and_set_test", "rollback_key", "initial_value"

        await storage.set(family, key, initial_value)

        def value_factory(current_value):
            assert current_value == initial_value
            raise ValueError("Factory error")

        # Should raise the exception from value_factory
        with pytest.raises(ValueError, match="Factory error"):
            await storage.get_and_set(family, key, value_factory)

        # Original value should be unchanged due to rollback
        assert await storage.get(family, key) == initial_value

    @pytest.mark.asyncio
    async def test_get_and_set_respects_expired_keys(self, sql_conn_factory):
        """Test get_and_set treats expired keys as non-existent."""
        # Import here to avoid import errors if time_provider module doesn't exist
        from csbot.utils.time import SecondsNowFake

        # Use a controlled time provider for precise expiry testing
        time_provider = SecondsNowFake(1000)  # Start at time 1000
        storage = self._create_storage(sql_conn_factory, "test_bot", time_provider)

        family, key, initial_value = "get_and_set_expiry_test", "expiry_test_key", "initial_value"

        # Set with expiry in 100 seconds
        await storage.set(family, key, initial_value, expiry_seconds=100)

        # Advance time past expiry
        time_provider.advance_time(150)

        def value_factory(current_value):
            # Should see None because key is expired
            assert current_value is None
            return "new_value"

        await storage.get_and_set(family, key, value_factory)
        assert await storage.get(family, key) == "new_value"

    @pytest.mark.asyncio
    async def test_get_and_set_bot_id_isolation(self, sql_conn_factory):
        """Test get_and_set respects bot ID isolation."""
        storage1 = self._create_storage(sql_conn_factory, "bot1", system_seconds_now)
        storage2 = self._create_storage(sql_conn_factory, "bot2", system_seconds_now)

        family, key, value1, value2 = "get_and_set_isolation", "isolation_key", "value1", "value2"

        # Set initial values in both bots
        await storage1.set(family, key, value1)
        await storage2.set(family, key, value2)

        def factory1(current_value):
            assert current_value == value1
            return "updated1"

        def factory2(current_value):
            assert current_value == value2
            return "updated2"

        # Update in both bots
        await storage1.get_and_set(family, key, factory1)
        await storage2.get_and_set(family, key, factory2)

        # Each bot should see its own updated value
        assert await storage1.get(family, key) == "updated1"
        assert await storage2.get(family, key) == "updated2"

    @pytest.mark.asyncio
    async def test_get_and_set_family_isolation(self, storage):
        """Test get_and_set respects family isolation."""
        family1, family2 = "get_and_set_family1", "get_and_set_family2"
        key, value1, value2 = "isolation_key", "value1", "value2"

        # Set initial values in both families
        await storage.set(family1, key, value1)
        await storage.set(family2, key, value2)

        def factory1(current_value):
            assert current_value == value1
            return "updated1"

        # Update only family1
        await storage.get_and_set(family1, key, factory1)

        # family1 should be updated, family2 unchanged
        assert await storage.get(family1, key) == "updated1"
        assert await storage.get(family2, key) == value2

    @pytest.mark.asyncio
    async def test_get_and_set_counter_increment(self, storage):
        """Test get_and_set for counter increment use case."""
        family, key = "counters", "page_views"

        # Initialize counter
        def init_counter(current_value):
            return "1" if current_value is None else str(int(current_value) + 1)

        # First call: initialize to 1
        await storage.get_and_set(family, key, init_counter)
        assert await storage.get(family, key) == "1"

        # Subsequent calls: increment
        await storage.get_and_set(family, key, init_counter)
        assert await storage.get(family, key) == "2"

        await storage.get_and_set(family, key, init_counter)
        assert await storage.get(family, key) == "3"

    @pytest.mark.asyncio
    async def test_get_and_set_conditional_update(self, storage):
        """Test get_and_set for conditional update use case."""
        family, key, initial_value = "config", "feature_flag", "disabled"

        await storage.set(family, key, initial_value)

        def conditional_enable(current_value):
            # Only enable if currently disabled
            if current_value == "disabled":
                return "enabled"
            return current_value  # No change if already enabled

        # First call: should enable
        await storage.get_and_set(family, key, conditional_enable)
        assert await storage.get(family, key) == "enabled"

        # Second call: should remain enabled
        await storage.get_and_set(family, key, conditional_enable)
        assert await storage.get(family, key) == "enabled"

    @pytest.mark.asyncio
    async def test_get_and_set_value_transformation(self, storage):
        """Test get_and_set for value transformation."""
        family, key, initial_value = "data", "json_config", '{"count": 5}'

        await storage.set(family, key, initial_value)

        def increment_json_count(current_value):
            if current_value is None:
                return '{"count": 1}'
            # Simple transformation (in real code you'd use json.loads/dumps)
            return current_value.replace('"count": 5', '"count": 6')

        await storage.get_and_set(family, key, increment_json_count)
        assert await storage.get(family, key) == '{"count": 6}'

    @pytest.mark.asyncio
    async def test_get_and_set_cleanup_pattern(self, storage):
        """Test get_and_set for cleanup/garbage collection pattern."""
        family, key, stale_value = "temp", "session_data", "stale_session_data"

        await storage.set(family, key, stale_value)

        def cleanup_if_stale(current_value):
            # Remove stale data
            if current_value and "stale" in current_value:
                return None  # Delete key
            return current_value  # Keep if not stale

        await storage.get_and_set(family, key, cleanup_if_stale)
        assert await storage.get(family, key) is None
        assert await storage.exists(family, key) is False

    @pytest.mark.asyncio
    async def test_get_and_set_empty_string_handling(self, storage):
        """Test get_and_set with empty strings."""
        family, key = "empty_string_test", "empty_key"

        # Test factory that returns empty string
        def return_empty(current_value):
            assert current_value is None
            return ""

        await storage.get_and_set(family, key, return_empty)
        assert await storage.get(family, key) == ""
        assert await storage.exists(family, key) is True

        # Test factory that processes empty string
        def process_empty(current_value):
            assert current_value == ""
            return "processed"

        await storage.get_and_set(family, key, process_empty)
        assert await storage.get(family, key) == "processed"

    @abstractmethod
    def _create_storage(
        self, sql_conn_factory: SqlConnectionFactory, bot_id: str, seconds_now: SecondsNow
    ) -> SlackbotInstanceStorage:
        """Create a storage instance for the given bot ID. Must be implemented by subclasses."""
        pass
