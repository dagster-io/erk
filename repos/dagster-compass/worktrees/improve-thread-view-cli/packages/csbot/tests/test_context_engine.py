"""Tests for context_engine module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from csbot.contextengine.context_engine import (
    ContextEngine,
    ContextSearcher,
)
from csbot.contextengine.contextstore_protocol import ContextStore
from csbot.contextengine.dataset_documentation import DatasetSearcher
from csbot.local_context_store.github.config import GithubConfig
from csbot.local_context_store.github.context import with_pull_request_context
from csbot.local_context_store.github.types import PullRequestResult
from csbot.local_context_store.local_context_store import (
    setup_fresh_github_repository,
)
from tests.factories import context_store_builder
from tests.fakes.context_store_manager import ContextStoreMutation, FakeContextStoreManager


def create_context_engine(
    store: ContextStore, connections: set[str] | None = None, channel_name: str | None = None
) -> tuple[ContextEngine, list[ContextStoreMutation]]:
    mutations = []
    provider = FakeContextStoreManager(store, mutations)
    mock_agent = AsyncMock()
    engine = ContextEngine(
        provider,
        mock_agent,
        channel_name,
        set() if connections is None else connections,
        None,
    )
    return engine, mutations


class TestDatasetSearcher:
    """Test DatasetSearcher class."""

    def test_searcher_no_docs(self):
        context_store = context_store_builder().build()
        searcher = DatasetSearcher(context_store=context_store, full=False, connections=None)
        results = searcher.search("test query")
        assert results == []

    def test_searcher_with_docs(self):
        """Test DatasetSearcher with dataset documentation."""
        # Use summary without frontmatter (frontmatter is separate now)
        doc_content = """# Users Table

This table contains user profile data including authentication details.

## Columns
- id: Primary key
- email: User email address
- created_at: Account creation timestamp
"""

        context_store = (
            context_store_builder()
            .add_dataset("postgres_prod", "users")
            .with_markdown(doc_content)
            .build()
        )

        searcher = DatasetSearcher(context_store=context_store, full=True, connections=None)
        results = searcher.search("users")

        assert len(results) >= 1
        result = results[0]
        assert result.connection == "postgres_prod"
        assert result.table == "users"
        assert result.docs_markdown is not None
        # Should not have frontmatter (summary doesn't include it)
        assert "---" not in result.docs_markdown
        assert "Users Table" in result.docs_markdown

    def test_searcher_connection_filter(self):
        """Test DatasetSearcher with connection filter using connections list."""
        # Create ContextStore with datasets from multiple connections
        context_store = (
            context_store_builder()
            .add_dataset("postgres_prod", "table")
            .with_markdown("# Table for postgres_prod")
            .add_dataset("bigquery_analytics", "table")
            .with_markdown("# Table for bigquery_analytics")
            .build()
        )

        # Search with connection filter - only postgres_prod
        searcher = DatasetSearcher(
            context_store=context_store, full=False, connections=["postgres_prod"]
        )
        index = searcher.build_index()

        # Should only include docs from postgres_prod
        postgres_docs = [doc_id for doc_id, _ in index.docs if "postgres_prod" in doc_id]
        bigquery_docs = [doc_id for doc_id, _ in index.docs if "bigquery_analytics" in doc_id]

        assert len(postgres_docs) > 0
        assert len(bigquery_docs) == 0

    def test_searcher_full_vs_minimal_results(self):
        """Test DatasetSearcher with full vs minimal results."""
        context_store = (
            context_store_builder()
            .add_dataset("warehouse", "orders")
            .with_markdown("# Orders Table\nContains order information")
            .build()
        )

        # Test with full=True
        searcher_full = DatasetSearcher(context_store=context_store, full=True, connections=None)
        results_full = searcher_full.search("orders")

        # Test with full=False
        searcher_minimal = DatasetSearcher(
            context_store=context_store, full=False, connections=None
        )
        results_minimal = searcher_minimal.search("orders")

        if results_full:
            assert results_full[0].docs_markdown is not None
            assert "Orders Table" in results_full[0].docs_markdown

        if results_minimal:
            assert results_minimal[0].docs_markdown is None

    def test_searcher_connections_list_filter(self):
        """Test DatasetSearcher with connections list filter."""
        # Create ContextStore with datasets from multiple connections
        context_store = (
            context_store_builder()
            .add_dataset("postgres_prod", "table")
            .with_markdown("# Table for postgres_prod")
            .add_dataset("bigquery_analytics", "table")
            .with_markdown("# Table for bigquery_analytics")
            .add_dataset("mysql_legacy", "table")
            .with_markdown("# Table for mysql_legacy")
            .add_dataset("snowflake_warehouse", "table")
            .with_markdown("# Table for snowflake_warehouse")
            .build()
        )

        # Search with connections list filter (only allow postgres_prod and bigquery_analytics)
        allowed_connections = ["postgres_prod", "bigquery_analytics"]
        searcher = DatasetSearcher(
            context_store=context_store, full=False, connections=allowed_connections
        )
        index = searcher.build_index()

        # Should only include docs from allowed connections
        postgres_docs = [doc_id for doc_id, _ in index.docs if "postgres_prod" in doc_id]
        bigquery_docs = [doc_id for doc_id, _ in index.docs if "bigquery_analytics" in doc_id]
        mysql_docs = [doc_id for doc_id, _ in index.docs if "mysql_legacy" in doc_id]
        snowflake_docs = [doc_id for doc_id, _ in index.docs if "snowflake_warehouse" in doc_id]

        assert len(postgres_docs) > 0
        assert len(bigquery_docs) > 0
        assert len(mysql_docs) == 0
        assert len(snowflake_docs) == 0

    def test_searcher_connections_none_filter(self):
        """Test DatasetSearcher with connections=None (no filtering)."""
        # Create ContextStore with datasets from multiple connections
        context_store = (
            context_store_builder()
            .add_dataset("postgres_prod", "table")
            .with_markdown("# Table for postgres_prod")
            .add_dataset("bigquery_analytics", "table")
            .with_markdown("# Table for bigquery_analytics")
            .build()
        )

        # Search with connections=None (should include all connections)
        searcher = DatasetSearcher(context_store=context_store, full=False, connections=None)
        index = searcher.build_index()

        # Should include docs from all connections
        postgres_docs = [doc_id for doc_id, _ in index.docs if "postgres_prod" in doc_id]
        bigquery_docs = [doc_id for doc_id, _ in index.docs if "bigquery_analytics" in doc_id]

        assert len(postgres_docs) > 0
        assert len(bigquery_docs) > 0

    def test_searcher_connections_list_with_single_connection(self):
        """Test DatasetSearcher with single connection in connections list."""
        # Create ContextStore with datasets from multiple connections
        context_store = (
            context_store_builder()
            .add_dataset("postgres_prod", "table")
            .with_markdown("# Table for postgres_prod")
            .add_dataset("bigquery_analytics", "table")
            .with_markdown("# Table for bigquery_analytics")
            .add_dataset("mysql_legacy", "table")
            .with_markdown("# Table for mysql_legacy")
            .build()
        )

        # Search with single connection in connections list
        allowed_connections = ["mysql_legacy"]  # Only allow mysql_legacy
        searcher = DatasetSearcher(
            context_store=context_store, full=False, connections=allowed_connections
        )
        index = searcher.build_index()

        # Should only include docs from mysql_legacy
        postgres_docs = [doc_id for doc_id, _ in index.docs if "postgres_prod" in doc_id]
        bigquery_docs = [doc_id for doc_id, _ in index.docs if "bigquery_analytics" in doc_id]
        mysql_docs = [doc_id for doc_id, _ in index.docs if "mysql_legacy" in doc_id]

        assert len(postgres_docs) == 0
        assert len(bigquery_docs) == 0
        assert len(mysql_docs) > 0


class TestGithubWorkingDirFunctions:
    """Test new GitHub working directory standalone functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.github_config = GithubConfig.pat(token="test_token", repo_name="test/repo")

    @patch("csbot.local_context_store.git.repository_operations.pygit2.clone_repository")
    @patch("csbot.local_context_store.git.repository_operations.clean_and_update_repository")
    @patch("csbot.local_context_store.git.repository_operations._fetch_repository")
    @patch(
        "csbot.local_context_store.git.repository_operations._fetch_repository_and_repoint_origin"
    )
    def test_setup_repo(self, mock_fetch_repoint, mock_fetch, mock_clean_update, mock_pygit2_clone):
        """Test setup_repo function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            working_dir = Path(temp_dir)
            repo_path = working_dir / "github-repo"

            # Mock clone_repository to create the directory as a side effect
            def mock_clone_side_effect(url, local_path, depth=None, callbacks=None):
                Path(local_path).mkdir(parents=True, exist_ok=True)

            mock_pygit2_clone.side_effect = mock_clone_side_effect

            setup_fresh_github_repository(self.github_config, repo_path)

            assert repo_path.exists()
            mock_pygit2_clone.assert_called_once()
            # clean_and_update_repository is only called if repo already exists
            mock_clean_update.assert_not_called()

    def test_with_pull_request_context(self):
        """Test with_pull_request_context function."""
        mock_repo_path = Path("/mock/repo")
        mock_repo = Mock()
        mock_repo.temp_repo_path = mock_repo_path
        mock_repo.commit_changes = Mock(return_value="feature-branch")
        mock_repo.create_pull_request = Mock(return_value="https://github.com/test/repo/pull/123")

        from csbot.local_context_store.local_context_store import create_local_context_store

        mock_store = create_local_context_store(self.github_config)

        # Mock the store's isolated_copy method
        with patch.object(mock_store, "isolated_copy") as mock_for_creating:
            mock_pr_cm = Mock()
            mock_pr_cm.__enter__ = Mock(return_value=mock_repo)
            mock_pr_cm.__exit__ = Mock(return_value=None)
            mock_for_creating.return_value = mock_pr_cm

            with with_pull_request_context(
                mock_store, "Test Title", "Test Body", False
            ) as pr_result:
                assert isinstance(pr_result, PullRequestResult)
                assert pr_result.repo_path == mock_repo_path
                assert pr_result.title == "Test Title"
                assert pr_result.body == "Test Body"
                assert pr_result.automerge is False

            # After exiting context, PR should be created
            assert pr_result.pr_url == "https://github.com/test/repo/pull/123"
            mock_repo.commit_changes.assert_called_once_with(
                "Test Title",
                author_name="csbot",
                author_email="csbot@example.com",
            )
            mock_repo.create_pull_request.assert_called_once_with(
                "Test Title", "Test Body", "feature-branch"
            )
            mock_for_creating.assert_called_once()

    def test_with_pull_request_context_automerge(self):
        """Test with_pull_request_context with automerge=True."""
        mock_repo_path = Path("/mock/repo")
        mock_repo = Mock()
        mock_repo.temp_repo_path = mock_repo_path
        mock_repo.commit_changes = Mock(return_value="feature-branch")
        mock_repo.create_and_merge_pull_request = Mock(
            return_value="https://github.com/test/repo/pull/123"
        )

        from csbot.local_context_store.local_context_store import create_local_context_store

        mock_store = create_local_context_store(self.github_config)

        # Mock the store's isolated_copy method
        with patch.object(mock_store, "isolated_copy") as mock_for_creating:
            mock_pr_cm = Mock()
            mock_pr_cm.__enter__ = Mock(return_value=mock_repo)
            mock_pr_cm.__exit__ = Mock(return_value=None)
            mock_for_creating.return_value = mock_pr_cm

            with with_pull_request_context(
                mock_store, "Auto Title", "Auto Body", True
            ) as pr_result:
                assert pr_result.automerge is True

            # Should use create_and_merge_pull_request for automerge
            assert pr_result.pr_url == "https://github.com/test/repo/pull/123"
            mock_repo.commit_changes.assert_called_once_with(
                "Auto Title",
                author_name="csbot",
                author_email="csbot@example.com",
            )
            mock_repo.create_and_merge_pull_request.assert_called_once_with(
                "Auto Title", "Auto Body", "feature-branch"
            )
            mock_for_creating.assert_called_once()


class TestContextEngine:
    @pytest.mark.asyncio
    async def test_search_context_empty(self):
        """Test search_context with no context files."""
        engine, _ = create_context_engine(context_store_builder().build())
        result = await engine.search_context("test query")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_datasets_empty(self):
        """Test search_datasets with no dataset docs."""
        engine, _ = create_context_engine(context_store_builder().build())
        result = await engine.search_datasets("test query", False)
        assert result == []

    @pytest.mark.asyncio
    async def test_search_datasets_all_datasets(self):
        """Test search_datasets with '*' query."""
        engine, _ = create_context_engine(
            context_store_builder()
            .add_dataset("connection1", "table1")
            .add_dataset("connection2", "table2")
            .build(),
            connections={"connection1", "connection2"},
        )

        # Mock doc_ids in the searcher index
        mock_searcher = Mock()
        with patch(
            "csbot.contextengine.context_engine.DatasetSearcher", return_value=mock_searcher
        ):
            result = await engine.search_datasets("*", False)

        assert len(result) == 2
        assert any(r.table == "table1" and r.connection == "connection1" for r in result)
        assert any(r.table == "table2" and r.connection == "connection2" for r in result)

    @pytest.mark.asyncio
    async def test_search_datasets_all_with_full_error(self):
        """Test search_datasets with '*' query and full=True raises error."""
        engine, _ = create_context_engine(context_store_builder().build())
        with pytest.raises(ValueError, match="Cannot search all datasets when full=True"):
            await engine.search_datasets("*", True)

    @pytest.mark.asyncio
    async def test_get_system_prompt_channel_and_main(self):
        engine, _ = create_context_engine(
            context_store_builder()
            .with_system_prompt("Main system prompt content.")
            .new_channel("x")
            .with_channel_system_prompt("Channel-specific system prompt content.")
            .build(),
            channel_name="x",
        )

        result = await engine.get_system_prompt()

        # Should combine both prompts with double newline
        assert result == "Main system prompt content.\n\nChannel-specific system prompt content."

    @pytest.mark.asyncio
    async def test_get_system_prompt_channel_only(self):
        """Test get_system_prompt with only channel system prompt, no main."""
        engine, _ = create_context_engine(
            context_store_builder()
            .new_channel("x")
            .with_channel_system_prompt("Channel-specific system prompt content.")
            .build(),
            channel_name="x",
        )

        result = await engine.get_system_prompt()

        assert result == "Channel-specific system prompt content."

    @pytest.mark.asyncio
    async def test_get_system_prompt_different_channel_and_main(self):
        engine, _ = create_context_engine(
            context_store_builder()
            .with_system_prompt("Main system prompt content.")
            .new_channel("x")
            .with_channel_system_prompt("Channel-specific system prompt content.")
            .build(),
            channel_name="y",
        )
        result = await engine.get_system_prompt()

        expected = "Main system prompt content."
        assert result == expected

    @pytest.mark.asyncio
    async def test_search_datasets_connection_filtering(self):
        # Create engine with specific available connections
        store = (
            context_store_builder()
            .add_dataset("postgres_prod", "users")
            .add_dataset("postgres_prod", "orders")
            .add_dataset("bigquery_analytics", "events")
            .add_dataset("mysql_legacy", "old_table")
            .add_dataset("snowflake_warehouse", "analytics")
            .build()
        )
        engine, _ = create_context_engine(
            store, connections={"postgres_prod", "bigquery_analytics"}
        )
        # Test wildcard search with connection filtering
        results = await engine.search_datasets("*", False)

        # Should only return results from allowed connections
        assert len(results) == 3  # postgres_prod: 2 tables, bigquery_analytics: 1 table
        connection_names = {r.connection for r in results}
        assert connection_names == {"postgres_prod", "bigquery_analytics"}

        # Verify specific results
        table_names = {(r.connection, r.table) for r in results}
        expected_tables = {
            ("postgres_prod", "users"),
            ("postgres_prod", "orders"),
            ("bigquery_analytics", "events"),
        }
        assert table_names == expected_tables

        # Verify excluded connections are not present
        for result in results:
            assert result.connection not in {"mysql_legacy", "snowflake_warehouse"}

    @pytest.mark.asyncio
    async def test_add_context(self):
        initial_context_store = context_store_builder().build()
        engine, mutations = create_context_engine(initial_context_store)

        with (
            patch(
                "csbot.contextengine.context_engine.generate_context_summary",
                new=AsyncMock(return_value=("Test Summary", "test, keywords")),
            ),
            patch(
                "csbot.contextengine.context_engine.categorize_context",
                new=AsyncMock(return_value="test_category"),
            ),
        ):
            result = await engine.add_context(
                topic="Test Topic",
                incorrect_understanding="Wrong assumption",
                correct_understanding="Correct understanding",
                attribution="Test User",
            )

        # Verify the mutator was called
        assert mutations
        mutation = mutations[-1]

        assert mutation.title == "CONTEXT: Test Summary"
        assert "Test User" in mutation.body
        assert mutation.commit is False
        assert mutation.before == initial_context_store
        assert len(mutation.after.general_context) == len(mutation.before.general_context) + 1

        # Get the added context
        new_context = mutation.after.general_context[-1]
        assert new_context.group == "test_category"
        assert new_context.context.topic == "Test Topic"
        assert new_context.context.incorrect_understanding == "Wrong assumption"
        assert new_context.context.correct_understanding == "Correct understanding"
        assert new_context.context.search_keywords == "test, keywords"

        # Verify the result
        assert "Test Summary" in result.context_summary


class TestIntegrationScenarios:
    """Test common integration scenarios using ContextStore."""

    def setup_method(self):
        """Set up integration test fixtures."""
        # Build ContextStore with realistic test data
        self.context_store = self._build_test_context_store()

    def _build_test_context_store(self):
        """Create a realistic ContextStore for integration tests."""
        users_doc = """---
title: Users Table
description: Core user accounts and authentication
---

# Users Table

Primary table for user account management.

## Schema
- id (bigint): Primary key
- email (varchar): Unique email address
- created_at (timestamp): Account creation time
"""

        orders_doc = """---
title: Orders Table
description: E-commerce order tracking
---

# Orders Table

Tracks customer orders and fulfillment status.

## Schema
- order_id (bigint): Primary key
- user_id (bigint): Foreign key to users
- total_amount (decimal): Order total
- status (varchar): Order status
"""

        return (
            context_store_builder()
            .with_project("analytics/platform")
            .with_project_teams(
                {
                    "data": ["alice", "bob"],
                    "engineering": ["charlie", "diana"],
                }
            )
            .add_general_context("database", "db_context_0")
            .with_topic("Connection Pooling")
            .with_incorrect("More connections are always better")
            .with_correct("Connection pools should be sized based on workload")
            .with_keywords("database, connections, performance")
            .add_general_context("database", "db_context_1")
            .with_topic("Query Optimization")
            .with_incorrect("Indexes solve all performance problems")
            .with_correct("Indexes must be balanced with write performance")
            .with_keywords("database, queries, indexes, optimization")
            .add_general_context("api", "rate_limiting")
            .with_topic("Rate Limiting")
            .with_incorrect("Rate limits are per user account")
            .with_correct("Rate limits are per API key and endpoint")
            .with_keywords("api, rate limiting, throttling")
            .add_dataset("postgres_prod", "users")
            .with_markdown(users_doc)
            .add_dataset("postgres_prod", "orders")
            .with_markdown(orders_doc)
            .build()
        )

    def test_full_text_search_across_contexts(self):
        """Test full-text search works across all context categories."""
        searcher = ContextSearcher(context_store=self.context_store, channel_name=None)

        # Search for "database" should find contexts in database category
        results = searcher.search("database")
        assert len(results) >= 2

        # All results should be related to database
        for file_path, context in results:
            assert "database" in context.search_keywords.lower()

    def test_dataset_search_cross_connections(self):
        """Test dataset search works across multiple connections."""
        searcher = DatasetSearcher(context_store=self.context_store, full=False, connections=None)

        # Search for "user" should find users table
        results = searcher.search("user")

        assert len(results) > 0
        user_result = next((r for r in results if r.table == "users"), None)
        assert user_result is not None
        assert user_result.connection == "postgres_prod"

    def test_project_loading_integration(self):
        """Test project configuration from ContextStore."""
        project = self.context_store.project

        assert project.project_name == "analytics/platform"
        assert len(project.teams) == 2
        assert "alice" in project.teams["data"]
        assert "charlie" in project.teams["engineering"]
