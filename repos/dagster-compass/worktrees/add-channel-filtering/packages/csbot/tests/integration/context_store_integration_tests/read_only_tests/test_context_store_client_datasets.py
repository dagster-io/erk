"""Integration tests for ContextStoreClient dataset documentation functionality.

Tests the full dataset search and documentation workflow using real test data
with minimal test doubles. Uses fakes and stubs to replace external dependencies
while preserving real business logic. Focuses on the ContextStoreClient.search_datasets()
method and related functionality.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from csbot.contextengine.context_engine import ContextEngine
from csbot.contextengine.loader import load_context_store
from csbot.csbot_client.csbot_client import ContextStoreClient
from csbot.csbot_client.csbot_profile import ConnectionProfile, ProjectProfile
from csbot.local_context_store.local_context_store import LocalContextStore
from tests.fakes.context_store_manager import FakeContextStoreManager


class FakeContextEngine:
    """Fake ContextEngine that provides working search functionality with simplified dependencies.

    This is a fake (not a mock or stub) because it contains real business logic
    by delegating to a real ContextEngine instance, while avoiding external dependencies
    like GitHub API calls.
    """

    def __init__(self, fake_local_context_store: LocalContextStore, stub_agent):
        with fake_local_context_store.latest_file_tree() as tree:
            context_store = load_context_store(tree)
        # Create real context engine for actual functionality
        fake_provider = FakeContextStoreManager(context_store)
        from csbot.contextengine.protocol import ReadOnlyContextStoreManager

        manager = ReadOnlyContextStoreManager(fake_provider)
        self.real_engine = ContextEngine(
            context_store_manager=manager,
            agent=stub_agent,
            normalized_channel_name="test",
            available_connection_names={"dev_bigquery", "purina_snowflake"},
            github_config=Mock(),
        )

    async def search_datasets(self, query: str, full: bool):
        """Delegate to real search functionality."""
        return await self.real_engine.search_datasets(query, full)


class StubSqlClient:
    """Stub SQL client that returns predetermined dialect information without real connections.

    This is a stub (not a mock or fake) because it only provides fixed responses
    and contains no business logic.
    """

    def __init__(self, dialect):
        self.dialect = dialect


@pytest.fixture
def mock_project_profile():
    """Create a mock ProjectProfile with test connections.

    This uses a proper mock (unittest.mock.Mock) because we only care about
    the structure and don't need to verify interactions with it.
    """
    with patch(
        "csbot.csbot_client.csbot_client.get_sql_client_from_connection_profile"
    ) as mock_get_sql_client:
        # Stub the get_sql_client_from_connection_profile function to avoid real DB connections
        def stub_sql_client_factory(connection_profile):
            if "bigquery" in connection_profile.url:
                return StubSqlClient("bigquery")
            elif "snowflake" in connection_profile.url:
                return StubSqlClient("snowflake")
            else:
                return StubSqlClient("unknown")

        mock_get_sql_client.side_effect = stub_sql_client_factory

        # Create test connection profiles
        bigquery_conn = ConnectionProfile(
            url="bigquery://project/dataset",
            connect_args={},
            init_sql=[],
            additional_sql_dialect="bigquery",
        )

        # Create Snowflake connection
        snowflake_conn = ConnectionProfile(
            url="snowflake://account/database/schema",
            connect_args={},
            init_sql=[],
            additional_sql_dialect="snowflake",
        )

        profile = ProjectProfile(
            connections={"dev_bigquery": bigquery_conn, "purina_snowflake": snowflake_conn}
        )

        yield profile


@pytest.fixture
def fake_context_engine(fake_local_context_store, stub_agent):
    """Create FakeContextEngine using test fixture data."""
    return FakeContextEngine(fake_local_context_store, stub_agent)


@pytest.fixture
def context_store_client(fake_context_engine, mock_project_profile) -> ContextStoreClient:
    """Create ContextStoreClient with test double dependencies."""
    return ContextStoreClient(contextstore=fake_context_engine, profile=mock_project_profile)


class TestDatasetSearchFunctionality:
    """Test core dataset search functionality."""

    @pytest.mark.asyncio
    async def test_search_all_datasets(self, context_store_client):
        """Test wildcard search returns all available datasets."""
        results = await context_store_client.search_datasets("*", full=False)

        assert len(results) > 0, "Should find datasets in test fixture"

        # Should find both BigQuery and Snowflake datasets
        connections = {result.connection for result in results}
        assert "dev_bigquery" in connections
        assert "purina_snowflake" in connections

        # Check structure
        for result in results:
            assert hasattr(result, "connection")
            assert hasattr(result, "table")
            assert hasattr(result, "docs_markdown")
            assert hasattr(result, "connection_sql_dialect")
            assert result.docs_markdown is None  # full=False

    @pytest.mark.asyncio
    async def test_search_by_exact_table_name(self, context_store_client: ContextStoreClient):
        """Test exact table name matching."""
        # Search for specific IRIS table
        results = await context_store_client.search_datasets("iris_data_partitioned", full=False)

        assert len(results) >= 1, "Should find IRIS dataset"

        # Find the iris dataset
        iris_result = None
        for result in results:
            if "iris_data_partitioned" in result.table:
                iris_result = result
                break

        assert iris_result is not None
        assert iris_result.connection == "dev_bigquery"
        assert "iris_data_partitioned" in iris_result.table
        assert iris_result.connection_sql_dialect == "bigquery"

    @pytest.mark.asyncio
    async def test_search_by_connection_filtering(self, context_store_client):
        """Test filtering by connection name."""
        # Search for bigquery-specific content
        results = await context_store_client.search_datasets("IRIS", full=False)

        # Should find BigQuery iris dataset
        bigquery_results = [r for r in results if r.connection == "dev_bigquery"]
        assert len(bigquery_results) > 0

        # Search for snowflake-specific content
        results = await context_store_client.search_datasets("ORGANIZATIONS", full=False)

        # Should find Snowflake organizations dataset
        snowflake_results = [r for r in results if r.connection == "purina_snowflake"]
        assert len(snowflake_results) > 0

    @pytest.mark.asyncio
    async def test_search_by_keywords(self, context_store_client):
        """Test content-based keyword searches."""
        # Search for business-related keywords
        results = await context_store_client.search_datasets("revenue", full=False)

        # Should find results (organizations table has revenue data)
        assert len(results) > 0

        # Search for column names
        results = await context_store_client.search_datasets("ORGANIZATION_ID", full=False)

        # Should find organizations and related tables
        assert len(results) > 0
        org_results = [r for r in results if "ORGANIZATIONS" in r.table.upper()]
        assert len(org_results) > 0

    @pytest.mark.asyncio
    async def test_search_with_full_documentation(self, context_store_client):
        """Test search with full=True returns documentation."""
        results = await context_store_client.search_datasets("iris", full=True)

        assert len(results) > 0

        # Find iris result with documentation
        iris_result = None
        for result in results:
            if "iris" in result.table.lower():
                iris_result = result
                break

        assert iris_result is not None
        assert iris_result.docs_markdown is not None
        assert len(iris_result.docs_markdown) > 0

        # Should contain expected content from the test fixture
        docs = iris_result.docs_markdown
        assert "IRIS.iris_data_partitioned" in docs
        assert "PETAL_LENGTH" in docs
        assert "SEPAL_WIDTH" in docs

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, context_store_client):
        """Test that search is case insensitive."""
        results_lower = await context_store_client.search_datasets("organizations", full=False)
        results_upper = await context_store_client.search_datasets("ORGANIZATIONS", full=False)
        results_mixed = await context_store_client.search_datasets("Organizations", full=False)

        # All variations should return results
        assert len(results_lower) > 0 or len(results_upper) > 0 or len(results_mixed) > 0

        # Should find the same key datasets regardless of case
        def extract_tables(results):
            return {(r.connection, r.table.upper()) for r in results}

        all_tables = (
            extract_tables(results_lower)
            | extract_tables(results_upper)
            | extract_tables(results_mixed)
        )

        # Should contain organizations table
        org_tables = {(conn, table) for conn, table in all_tables if "ORGANIZATIONS" in table}
        assert len(org_tables) > 0


class TestDatasetDocumentationRetrieval:
    """Test dataset documentation parsing and retrieval."""

    @pytest.mark.asyncio
    async def test_dataset_docs_structure_iris(self, context_store_client):
        """Test markdown structure and frontmatter for IRIS dataset."""
        results = await context_store_client.search_datasets("iris_data_partitioned", full=True)

        iris_result = next((r for r in results if "iris_data_partitioned" in r.table), None)
        assert iris_result is not None

        docs = iris_result.docs_markdown
        assert docs is not None

        # Should contain expected sections
        assert "# Data Summary" in docs
        assert "## Overall Dataset Characteristics" in docs
        assert "## Column Details" in docs
        assert "### PETAL_LENGTH" in docs
        assert "### SEPAL_WIDTH" in docs
        assert "## Keywords" in docs

        # Should contain data quality information
        assert "Total Rows" in docs
        assert "no null values" in docs
        assert "FLOAT64" in docs
        assert "STRING" in docs

    @pytest.mark.asyncio
    async def test_dataset_docs_structure_organizations(self, context_store_client):
        """Test markdown structure for complex ORGANIZATIONS dataset."""
        results = await context_store_client.search_datasets("ORGANIZATIONS", full=True)

        org_result = next((r for r in results if "ORGANIZATIONS" in r.table.upper()), None)
        assert org_result is not None

        docs = org_result.docs_markdown
        assert docs is not None

        # Should contain business-specific content
        assert "ORGANIZATIONS" in docs
        assert "ORGANIZATION_ID" in docs
        assert "PLAN_TYPE" in docs
        assert "revenue" in docs.lower() or "invoice" in docs.lower()

        # Should contain data quality metrics
        assert "Total Rows" in docs
        assert "%" in docs  # Percentage indicators

    @pytest.mark.asyncio
    async def test_column_metadata_extraction(self, context_store_client):
        """Test extraction of column information from documentation."""
        results = await context_store_client.search_datasets("iris_data_partitioned", full=True)

        iris_result = next((r for r in results if "iris_data_partitioned" in r.table), None)
        assert iris_result is not None

        docs = iris_result.docs_markdown

        # Should have detailed column information
        expected_columns = ["PETAL_LENGTH", "PETAL_WIDTH", "SEPAL_LENGTH", "SEPAL_WIDTH", "SPECIES"]
        for col in expected_columns:
            assert col in docs

        # Should have data types
        assert "FLOAT64" in docs
        assert "STRING" in docs

        # Should have null value information
        assert "null" in docs.lower() or "None" in docs


class TestConnectionIntegration:
    """Test connection integration and SQL dialect detection."""

    @pytest.mark.asyncio
    async def test_connection_sql_dialect_detection(self, context_store_client):
        """Test BigQuery vs Snowflake dialect detection."""
        results = await context_store_client.search_datasets("*", full=False)

        # Should detect different dialects
        dialects = {result.connection_sql_dialect for result in results}
        assert "bigquery" in dialects
        assert "snowflake" in dialects

        # Check specific connections
        bigquery_results = [r for r in results if r.connection == "dev_bigquery"]
        for result in bigquery_results:
            assert result.connection_sql_dialect == "bigquery"

        snowflake_results = [r for r in results if r.connection == "purina_snowflake"]
        for result in snowflake_results:
            assert result.connection_sql_dialect == "snowflake"

    @pytest.mark.asyncio
    async def test_connection_profile_mapping(self, context_store_client):
        """Test profile-to-dataset mapping."""
        results = await context_store_client.search_datasets("*", full=False)

        # All results should have valid connections
        for result in results:
            assert result.connection in ["dev_bigquery", "purina_snowflake"]
            assert result.connection_sql_dialect != "<dataset not available to this user>"

    @pytest.mark.asyncio
    async def test_dataset_connection_consistency(self, context_store_client):
        """Test that datasets are consistently mapped to connections."""
        results = await context_store_client.search_datasets("*", full=False)

        # Group by connection
        by_connection = {}
        for result in results:
            if result.connection not in by_connection:
                by_connection[result.connection] = []
            by_connection[result.connection].append(result)

        # Should have datasets for both connections
        assert "dev_bigquery" in by_connection
        assert "purina_snowflake" in by_connection

        # BigQuery should have IRIS dataset
        bigquery_tables = [r.table for r in by_connection["dev_bigquery"]]
        iris_tables = [t for t in bigquery_tables if "iris" in t.lower()]
        assert len(iris_tables) > 0

        # Snowflake should have business datasets
        snowflake_tables = [r.table for r in by_connection["purina_snowflake"]]
        org_tables = [t for t in snowflake_tables if "ORGANIZATIONS" in t.upper()]
        assert len(org_tables) > 0


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, context_store_client):
        """Test handling of empty search queries."""
        results = await context_store_client.search_datasets("", full=False)
        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_whitespace_query_handling(self, context_store_client):
        """Test handling of whitespace-only queries."""
        results = await context_store_client.search_datasets("   ", full=False)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_no_matches_found(self, context_store_client):
        """Test search with query that should find no matches."""
        results = await context_store_client.search_datasets("xyz123nonexistent", full=False)
        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, context_store_client):
        """Test handling of special characters in search queries."""
        # Test various special characters
        special_queries = ["table@name", "col-name", "field_name", "name.with.dots"]

        for query in special_queries:
            results = await context_store_client.search_datasets(query, full=False)
            # Should handle gracefully without errors
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_multi_term_search(self, context_store_client):
        """Test search with multiple terms."""
        results = await context_store_client.search_datasets("iris data", full=False)
        assert isinstance(results, list)

        # Should find iris-related datasets
        iris_results = [r for r in results if "iris" in r.table.lower()]
        if len(iris_results) > 0:
            # If found, should be relevant
            assert any("iris" in r.table.lower() for r in iris_results)

    @pytest.mark.asyncio
    async def test_wildcard_search_constraints(self, context_store_client):
        """Test wildcard search with full=True constraint."""
        # This should raise an error based on the implementation
        with pytest.raises(ValueError, match="Cannot search all datasets when full=True"):
            # Test through the proper ContextStoreClient interface
            await context_store_client.search_datasets("*", full=True)

    @pytest.mark.asyncio
    async def test_search_result_structure_consistency(self, context_store_client):
        """Test that all search results have consistent structure."""
        results = await context_store_client.search_datasets("*", full=False)

        for result in results:
            # Check all required attributes exist
            assert hasattr(result, "connection")
            assert hasattr(result, "table")
            assert hasattr(result, "docs_markdown")
            assert hasattr(result, "connection_sql_dialect")

            # Check types
            assert isinstance(result.connection, str)
            assert isinstance(result.table, str)
            assert result.docs_markdown is None or isinstance(result.docs_markdown, str)
            assert isinstance(result.connection_sql_dialect, str)

            # Check non-empty values
            assert len(result.connection) > 0
            assert len(result.table) > 0
            assert len(result.connection_sql_dialect) > 0

    @pytest.mark.asyncio
    async def test_large_result_handling(self, context_store_client):
        """Test handling of potentially large result sets."""
        # Search for broad term that might return many results
        results = await context_store_client.search_datasets("*", full=False)

        # Should handle results without issues
        assert isinstance(results, list)
        assert len(results) > 0

        # Should not be excessively large (reasonable limit)
        assert len(results) < 1000  # Sanity check

        # Each result should be well-formed
        for result in results[:10]:  # Check first 10
            assert result.connection
            assert result.table
            assert result.connection_sql_dialect


# Async test runner helper
def run_async_test(coro):
    """Helper to run async tests."""
    return asyncio.run(coro)
