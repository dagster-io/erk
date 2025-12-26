"""Tests for CompositeContextStoreManager.

This module tests the composite context store manager that merges a mutable
user-accessible context store with read-only shared dataset documentation stores.
"""

import pytest

from csbot.contextengine.contextstore_protocol import (
    ChannelContext,
    ContextStore,
    ContextStoreProject,
    Dataset,
    DatasetDocumentation,
    NamedContext,
    ProvidedContext,
    TableFrontmatter,
    UserCronJob,
)
from csbot.local_context_store.composite_context_store_provider import CompositeContextStoreManager
from tests.fakes.context_store_manager import FakeContextStoreManager


@pytest.fixture
def mutable_store() -> ContextStore:
    """Create a mutable context store with org-specific content."""
    return ContextStore(
        project=ContextStoreProject(project_name="test/org", version=2),
        datasets=[
            (
                Dataset(connection="postgres", table_name="users"),
                DatasetDocumentation(
                    frontmatter=TableFrontmatter(schema_hash="abc123", columns=["id", "name"]),
                    summary="User table from mutable store",
                ),
            ),
            (
                Dataset(connection="postgres", table_name="orders"),
                DatasetDocumentation(
                    frontmatter=TableFrontmatter(schema_hash="def456", columns=["id", "user_id"]),
                    summary="Orders table",
                ),
            ),
        ],
        general_context=[
            NamedContext(
                group="business",
                name="revenue_definition",
                context=ProvidedContext(
                    topic="Revenue Calculation",
                    incorrect_understanding="Revenue is just sales",
                    correct_understanding="Revenue includes sales plus fees",
                    search_keywords="revenue money income",
                ),
            )
        ],
        general_cronjobs={
            "daily_report": UserCronJob(
                cron="0 9 * * *", question="Generate daily report", thread="T123456"
            )
        },
        channels={
            "data-team": ChannelContext(
                cron_jobs={},
                context=[
                    NamedContext(
                        group="team",
                        name="workflow",
                        context=ProvidedContext(
                            topic="Team Workflow",
                            incorrect_understanding="Use prod directly",
                            correct_understanding="Always use staging first",
                            search_keywords="workflow process",
                        ),
                    )
                ],
                system_prompt="Data team specific prompt",
            )
        },
        system_prompt="Organization system prompt",
    )


@pytest.fixture
def shared_datasets_store() -> ContextStore:
    """Create a shared context store with only dataset documentation."""
    return ContextStore(
        project=ContextStoreProject(project_name="shared/datasets", version=2),
        datasets=[
            (
                Dataset(connection="bigquery", table_name="analytics_events"),
                DatasetDocumentation(
                    frontmatter=TableFrontmatter(
                        schema_hash="shared123", columns=["event_id", "timestamp", "user_id"]
                    ),
                    summary="Shared analytics events table",
                ),
            ),
            (
                Dataset(connection="bigquery", table_name="user_sessions"),
                DatasetDocumentation(
                    frontmatter=TableFrontmatter(
                        schema_hash="shared456", columns=["session_id", "user_id", "start_time"]
                    ),
                    summary="Shared user sessions table",
                ),
            ),
            (
                Dataset(connection="postgres", table_name="users"),
                DatasetDocumentation(
                    frontmatter=TableFrontmatter(
                        schema_hash="shared789", columns=["id", "name", "email"]
                    ),
                    summary="Shared users table (should be ignored due to mutable override)",
                ),
            ),
        ],
        general_context=[],
        general_cronjobs={},
        channels={},
        system_prompt=None,
    )


@pytest.fixture
def second_shared_store() -> ContextStore:
    """Create a second shared context store for multi-store testing."""
    return ContextStore(
        project=ContextStoreProject(project_name="shared/datasets2", version=2),
        datasets=[
            (
                Dataset(connection="snowflake", table_name="customer_data"),
                DatasetDocumentation(
                    frontmatter=TableFrontmatter(
                        schema_hash="snow123", columns=["customer_id", "name"]
                    ),
                    summary="Customer data from Snowflake",
                ),
            ),
            (
                Dataset(connection="bigquery", table_name="analytics_events"),
                DatasetDocumentation(
                    frontmatter=TableFrontmatter(
                        schema_hash="conflict456", columns=["event_id", "type"]
                    ),
                    summary="Should be ignored - first shared provider takes precedence",
                ),
            ),
        ],
        general_context=[],
        general_cronjobs={},
        channels={},
        system_prompt=None,
    )


class TestCompositeContextStoreManager:
    """Test suite for CompositeContextStoreManager."""

    @pytest.mark.asyncio
    async def test_get_context_store_merges_datasets_correctly(
        self,
        mutable_store: ContextStore,
        shared_datasets_store: ContextStore,
        second_shared_store: ContextStore,
    ):
        """Test comprehensive dataset merging behavior including precedence and sorting.

        This test verifies:
        - Datasets from mutable and shared stores are merged
        - Mutable store datasets take precedence over shared
        - First shared store takes precedence over later shared stores
        - Non-dataset fields (context, channels, etc.) come only from mutable store
        - Merged datasets are sorted by (connection, table_name)
        - Works correctly with empty stores
        """
        # Test basic merge with single shared store
        mutable_manager = FakeContextStoreManager(mutable_store)
        shared_store = FakeContextStoreManager(shared_datasets_store)
        composite = CompositeContextStoreManager(mutable_manager, [shared_store])

        result = await composite.get_context_store()

        # Should have 4 datasets: 2 from mutable + 2 new from shared
        # (postgres.users from mutable takes precedence over shared)
        assert len(result.datasets) == 4
        dataset_keys = {(ds.connection, ds.table_name) for ds, _ in result.datasets}
        assert dataset_keys == {
            ("postgres", "users"),
            ("postgres", "orders"),
            ("bigquery", "analytics_events"),
            ("bigquery", "user_sessions"),
        }

        # Verify mutable dataset takes precedence
        users_doc = next(
            doc
            for ds, doc in result.datasets
            if ds.connection == "postgres" and ds.table_name == "users"
        )
        assert users_doc.summary == "User table from mutable store"
        assert users_doc.frontmatter is not None
        assert users_doc.frontmatter.schema_hash == "abc123"

        # Verify non-dataset fields come only from mutable store
        assert result.project.project_name == "test/org"
        assert result.system_prompt == "Organization system prompt"
        assert len(result.general_context) == 1
        assert result.general_context[0].name == "revenue_definition"
        assert len(result.general_cronjobs) == 1
        assert "daily_report" in result.general_cronjobs
        assert len(result.channels) == 1
        assert "data-team" in result.channels
        assert result.channels["data-team"].system_prompt == "Data team specific prompt"

        # Verify sorting
        dataset_order = [(ds.connection, ds.table_name) for ds, _ in result.datasets]
        assert dataset_order == sorted(dataset_order)

        # Test with multiple shared stores
        shared_store2 = FakeContextStoreManager(second_shared_store)
        composite_multi = CompositeContextStoreManager(
            mutable_manager, [shared_store, shared_store2]
        )
        result_multi = await composite_multi.get_context_store()

        # Should have 5 datasets: 2 mutable + 2 from first shared + 1 from second shared
        # (first shared's analytics_events takes precedence over second shared)
        assert len(result_multi.datasets) == 5
        dataset_keys_multi = {(ds.connection, ds.table_name) for ds, _ in result_multi.datasets}
        assert ("snowflake", "customer_data") in dataset_keys_multi

        # Verify first shared provider's analytics_events is used
        analytics_doc = next(
            doc
            for ds, doc in result_multi.datasets
            if ds.connection == "bigquery" and ds.table_name == "analytics_events"
        )
        assert analytics_doc.summary == "Shared analytics events table"
        assert analytics_doc.frontmatter is not None
        assert analytics_doc.frontmatter.schema_hash == "shared123"

        # Test with empty shared store
        empty_shared = ContextStore(
            project=ContextStoreProject(project_name="shared/empty", version=2),
            datasets=[],
            general_context=[],
            general_cronjobs={},
            channels={},
            system_prompt=None,
        )
        composite_empty = CompositeContextStoreManager(
            mutable_manager, [FakeContextStoreManager(empty_shared)]
        )
        result_empty = await composite_empty.get_context_store()
        assert len(result_empty.datasets) == 2  # Only mutable datasets

        # Test with empty mutable store
        empty_mutable = ContextStore(
            project=ContextStoreProject(project_name="test/empty", version=2),
            datasets=[],
            general_context=[],
            general_cronjobs={},
            channels={},
            system_prompt=None,
        )
        composite_empty_mut = CompositeContextStoreManager(
            FakeContextStoreManager(empty_mutable), [shared_store]
        )
        result_empty_mut = await composite_empty_mut.get_context_store()
        assert len(result_empty_mut.datasets) == 3  # All shared datasets
        assert len(result_empty_mut.general_context) == 0
        assert len(result_empty_mut.channels) == 0

    @pytest.mark.asyncio
    async def test_mutate_filters_shared_datasets_and_preserves_mutable_changes(
        self, mutable_store: ContextStore, shared_datasets_store: ContextStore
    ):
        """Test that mutate() filters shared datasets and preserves mutable changes.

        This test verifies:
        - Shared datasets are filtered out before writing to mutable store
        - Changes to mutable datasets are preserved
        - Changes to non-dataset fields are preserved
        - Mutation is delegated correctly to the mutable manager
        """
        mutable_manager = FakeContextStoreManager(mutable_store)
        shared_store = FakeContextStoreManager(shared_datasets_store)
        composite = CompositeContextStoreManager(mutable_manager, [shared_store])

        merged_before = await composite.get_context_store()

        # Add a new mutable dataset and modify non-dataset fields
        new_dataset = (
            Dataset(connection="postgres", table_name="new_table"),
            DatasetDocumentation(
                frontmatter=TableFrontmatter(schema_hash="new123", columns=["id"]),
                summary="New table",
            ),
        )
        new_context = NamedContext(
            group="test",
            name="new_context",
            context=ProvidedContext(
                topic="Test Topic",
                incorrect_understanding="Wrong",
                correct_understanding="Right",
                search_keywords="test",
            ),
        )
        merged_after = merged_before.model_copy(
            update={
                "datasets": list(merged_before.datasets) + [new_dataset],
                "general_context": list(merged_before.general_context) + [new_context],
                "system_prompt": "Updated system prompt",
            }
        )

        # Mutate
        pr_url = await composite.mutate(
            "Add new table", "Adding new table", False, merged_before, merged_after
        )

        # Verify mutation was delegated correctly
        assert pr_url == "https://github.com/test/repo/pull/123"
        mutation = mutable_manager.get_last_mutation()

        # The filtered before/after should only contain mutable datasets
        # Before: postgres.orders (postgres.users exists in shared, so filtered out)
        # After: postgres.orders + postgres.new_table
        assert len(mutation.before.datasets) == 1
        assert len(mutation.after.datasets) == 2

        # Verify no shared datasets in the mutation
        shared_dataset_keys = {
            (ds.connection, ds.table_name) for ds, _ in shared_datasets_store.datasets
        }
        for ds, _ in mutation.before.datasets:
            assert (ds.connection, ds.table_name) not in shared_dataset_keys
        for ds, _ in mutation.after.datasets:
            assert (ds.connection, ds.table_name) not in shared_dataset_keys

        # Verify non-dataset changes are preserved
        assert len(mutation.after.general_context) == 2
        assert mutation.after.system_prompt == "Updated system prompt"

    @pytest.mark.asyncio
    async def test_mutate_raises_errors_when_modifying_shared_datasets(
        self, mutable_store: ContextStore, shared_datasets_store: ContextStore
    ):
        """Test that mutate() raises errors when shared datasets are added, removed, or modified.

        This test verifies:
        - Error raised when modifying shared dataset documentation
        - Error raised when removing shared dataset
        - Error raised when adding new entry for shared dataset key
        - Error messages include dataset connection and table name
        """
        mutable_manager = FakeContextStoreManager(mutable_store)
        shared_store = FakeContextStoreManager(shared_datasets_store)
        composite = CompositeContextStoreManager(mutable_manager, [shared_store])

        merged_before = await composite.get_context_store()

        # Test modifying shared dataset
        modified_datasets = []
        for ds, doc in merged_before.datasets:
            if ds.connection == "bigquery" and ds.table_name == "analytics_events":
                modified_doc = doc.model_copy(update={"summary": "Modified summary"})
                modified_datasets.append((ds, modified_doc))
            else:
                modified_datasets.append((ds, doc))

        merged_after_modified = merged_before.model_copy(update={"datasets": modified_datasets})

        with pytest.raises(ValueError, match="Cannot modify shared.*analytics_events.*modified"):
            await composite.mutate(
                "Try to modify shared", "Should fail", False, merged_before, merged_after_modified
            )

        # Test removing shared dataset
        filtered_datasets = [
            (ds, doc)
            for ds, doc in merged_before.datasets
            if not (ds.connection == "bigquery" and ds.table_name == "analytics_events")
        ]
        merged_after_removed = merged_before.model_copy(update={"datasets": filtered_datasets})

        with pytest.raises(ValueError, match="Cannot modify shared.*analytics_events.*removed"):
            await composite.mutate(
                "Try to remove shared", "Should fail", False, merged_before, merged_after_removed
            )

        # Test adding shared dataset (simulating it wasn't in before)
        before_without_shared = [
            (ds, doc)
            for ds, doc in merged_before.datasets
            if not (ds.connection == "bigquery" and ds.table_name == "analytics_events")
        ]
        modified_before = merged_before.model_copy(update={"datasets": before_without_shared})

        with pytest.raises(ValueError, match="Cannot modify shared.*analytics_events.*added"):
            await composite.mutate(
                "Try to add shared", "Should fail", False, modified_before, merged_before
            )
