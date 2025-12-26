"""Shared fixtures for context store integration tests.

This module provides three tiers of fixtures for context store tests:

1. **Full fixtures** (dagsterlabs_v0/v2_2025_09_21): 540KB with 50+ contexts, 23 datasets
   - Used by: V1/V2 equivalence tests, full documentation structure tests, ranking tests
   - Required for: test_manifest_layout_integration.py (all tests)

2. **Medium fixtures** (10 contexts, 4 datasets): ~50KB, programmatically generated
   - Used by: Search tests, retrieval tests, indexing tests
   - Sufficient for: Realistic search behavior, connection filtering, IRIS dataset tests

3. **Minimal fixtures** (3 contexts, 1 dataset): ~5KB, programmatically generated
   - Used by: Configuration tests, file operations tests, edge case tests
   - Sufficient for: Structure validation, error handling, basic operations

Tests that MUST use full fixtures (dagsterlabs_v0/v2_2025_09_21):
- test_manifest_layout_integration.py (8 tests): All V1/V2 equivalence comparison tests
- test_context_store_client_datasets.py (7+ tests):
  - test_dataset_docs_structure_organizations (needs complete ORGANIZATIONS docs)
  - test_search_with_full_documentation (needs complete IRIS docs)
  - test_search_result_ranking (needs many results for ranking)
  - test_large_result_handling (needs many results)
  - test_v1_vs_v2_search_equivalence (needs both full fixtures)
  - test_dataset_docs_structure_iris (needs complete IRIS docs)
  - test_multi_term_search (may need multiple matches)

Session-Scoped Caching:
- Session-scoped fixtures cache parsed stores and built indexes for performance
- Caching is safe because stores are immutable and tests are read-only
- Building Tantivy indexes is expensive (~100-150ms each)
- Session caching reduces index builds significantly
"""

from contextlib import contextmanager
from pathlib import Path

import pytest

from csbot.local_context_store.git.file_tree import FilesystemFileTree


@pytest.fixture(scope="session")
def fixture_root():
    """Path to the test context store fixture (V1)."""
    return Path(__file__).parent.parent / "context_stores" / "dagsterlabs_v0_2025_09_21"


@pytest.fixture(scope="session")
def fixture_root_v1():
    """Path to the test context store fixture (V1 legacy layout)."""
    return Path(__file__).parent.parent / "context_stores" / "dagsterlabs_v0_2025_09_21"


@pytest.fixture(scope="session")
def fixture_root_v2():
    """Path to the test context store fixture (V2 manifest layout)."""
    return Path(__file__).parent.parent / "context_stores" / "dagsterlabs_v2_2025_09_21"


@pytest.fixture
def file_tree(fixture_root):
    """FilesystemFileTree instance for the test fixture (V1)."""
    return FilesystemFileTree(fixture_root)


@pytest.fixture
def file_tree_v1(fixture_root_v1):
    """FilesystemFileTree instance for the V1 test fixture."""
    return FilesystemFileTree(fixture_root_v1)


@pytest.fixture
def file_tree_v2(fixture_root_v2):
    """FilesystemFileTree instance for the V2 test fixture."""
    return FilesystemFileTree(fixture_root_v2)


@pytest.fixture(params=[1, 2])
def versioned_file_tree(request, fixture_root_v1, fixture_root_v2):
    """Parametrized fixture that returns V1 or V2 file tree based on param."""
    if request.param == 1:
        return FilesystemFileTree(fixture_root_v1)
    return FilesystemFileTree(fixture_root_v2)


@pytest.fixture
def stub_agent():
    """Minimal stub agent that returns fixed responses for tests."""

    class StubAgent:
        async def create_completion(self, *args, **kwargs):
            return "SUMMARY: Test summary\nKEYWORDS: test, keywords"

    return StubAgent()


class FakeLocalContextStore:
    """Fake LocalContextStore for read-only tests with simplified file tree functionality."""

    def __init__(self, project_path):
        self.project_path = project_path
        self.github_config = None  # Not needed for read-only

    def latest_file_tree(self):
        @contextmanager
        def _latest_file_tree():
            yield FilesystemFileTree(self.project_path)

        return _latest_file_tree()


@pytest.fixture
def fake_local_context_store(fixture_root):
    """Fake LocalContextStore for read-only tests (V1)."""
    return FakeLocalContextStore(fixture_root)


@pytest.fixture
def fake_local_context_store_v1(fixture_root_v1):
    """Fake LocalContextStore for V1 read-only tests."""
    return FakeLocalContextStore(fixture_root_v1)


@pytest.fixture
def fake_local_context_store_v2(fixture_root_v2):
    """Fake LocalContextStore for V2 read-only tests."""
    return FakeLocalContextStore(fixture_root_v2)


# Session-scoped fixtures for caching context stores and search indexes


@pytest.fixture(scope="session")
def context_store_v1(fixture_root_v1):
    """Session-scoped ContextStore for V1 fixture.

    Caches the parsed context store for the entire test session to avoid
    repeated disk I/O and YAML parsing (~50-100ms per load).

    Safe to cache because:
    - ContextStore is a frozen dataclass (immutable)
    - All tests in read_only_tests/ never modify data

    Returns: Parsed ContextStore with ~57 contexts, datasets, cronjobs
    """
    # Import inside fixture to avoid circular imports at module load time
    from csbot.contextengine.loader import load_context_store

    file_tree = FilesystemFileTree(fixture_root_v1)
    return load_context_store(file_tree)


@pytest.fixture(scope="session")
def context_store_v2(fixture_root_v2):
    """Session-scoped ContextStore for V2 fixture.

    Caches the parsed context store for V2 manifest layout testing.
    See context_store_v1 docstring for caching rationale.
    """
    from csbot.contextengine.loader import load_context_store

    file_tree = FilesystemFileTree(fixture_root_v2)
    return load_context_store(file_tree)


@pytest.fixture(scope="session")
def context_store(context_store_v1):
    """Session-scoped ContextStore for default (V1) fixture.

    Alias for tests that don't need to specify V1/V2 explicitly.
    """
    return context_store_v1


@pytest.fixture(scope="session")
def fts_index_v1(context_store_v1):
    """Session-scoped FTS index for V1 contexts.

    Builds Tantivy search index once per session and caches it.
    This is the primary performance optimization - building indexes
    takes ~100-150ms each and was happening for every test.

    Safe to cache because:
    - FTSIndex is read-only after creation (only has search() method)
    - Tantivy searches are thread-safe
    - Temporary directory kept alive for session (cleaned up in __del__)

    Returns: FTSIndex instance with built Tantivy index
    """
    # Import FTSIndex from dedicated module to avoid circular imports
    from csbot.contextengine.fts_index import FTSIndex

    # Build docs list same way ContextSearcher.build_index() does
    NO_CHANNEL_SENTINEL = "__NO_CHANNEL__"
    docs = []

    for named_context in context_store_v1.general_context:
        context = named_context.context
        content = (
            f"{context.topic} {context.incorrect_understanding} "
            f"{context.correct_understanding} {context.search_keywords}"
        )
        docs.append((f"{NO_CHANNEL_SENTINEL}/{named_context.group}/{named_context.name}", content))

    for channel_name, channel_context in context_store_v1.channels.items():
        for named_context in channel_context.context:
            context = named_context.context
            content = (
                f"{context.topic} {context.incorrect_understanding} "
                f"{context.correct_understanding} {context.search_keywords}"
            )
            docs.append((f"{channel_name}/{named_context.group}/{named_context.name}", content))

    return FTSIndex(docs)


@pytest.fixture(scope="session")
def fts_index_v2(context_store_v2):
    """Session-scoped FTS index for V2 contexts.

    Caches Tantivy index for V2 manifest layout testing.
    See fts_index_v1 docstring for caching rationale.
    """
    # Import FTSIndex from dedicated module to avoid circular imports
    from csbot.contextengine.fts_index import FTSIndex

    # Build docs list same way ContextSearcher.build_index() does
    NO_CHANNEL_SENTINEL = "__NO_CHANNEL__"
    docs = []

    for named_context in context_store_v2.general_context:
        context = named_context.context
        content = (
            f"{context.topic} {context.incorrect_understanding} "
            f"{context.correct_understanding} {context.search_keywords}"
        )
        docs.append((f"{NO_CHANNEL_SENTINEL}/{named_context.group}/{named_context.name}", content))

    for channel_name, channel_context in context_store_v2.channels.items():
        for named_context in channel_context.context:
            context = named_context.context
            content = (
                f"{context.topic} {context.incorrect_understanding} "
                f"{context.correct_understanding} {context.search_keywords}"
            )
            docs.append((f"{channel_name}/{named_context.group}/{named_context.name}", content))

    return FTSIndex(docs)


@pytest.fixture(scope="session")
def fts_index(fts_index_v1):
    """Session-scoped FTS index for default (V1) fixture.

    Alias for tests that don't need to specify V1/V2 explicitly.
    """
    return fts_index_v1


@pytest.fixture(scope="session")
def context_searcher_v1(context_store_v1, fts_index_v1):
    """Session-scoped ContextSearcher for V1 with pre-built index.

    Provides a fully-configured searcher that tests can use directly.
    This is the convenience layer that most tests should use.

    Returns a lightweight wrapper that implements the search() method
    without requiring the full ContextSearcher class (avoids circular imports).
    """
    from csbot.contextengine.contextstore_protocol import ContextIdentifier

    class CachedSearcher:
        """Lightweight search wrapper with pre-built index."""

        def __init__(self, context_store, fts_index):
            self.context_store = context_store
            self.fts = fts_index

        def search(self, query: str):
            """Search contexts using cached FTS index."""
            results = []
            for doc_id in self.fts.search(query, limit=10):
                context_id = ContextIdentifier.from_string(doc_id)
                # Handle NO_CHANNEL_SENTINEL by converting to None
                if context_id.channel == "__NO_CHANNEL__":
                    context_id = ContextIdentifier(
                        channel=None, group=context_id.group, name=context_id.name
                    )
                results.append((doc_id, self.context_store.get_context(context_id)))
            return results

    return CachedSearcher(context_store_v1, fts_index_v1)


@pytest.fixture(scope="session")
def context_searcher_v2(context_store_v2, fts_index_v2):
    """Session-scoped ContextSearcher for V2 with pre-built index.

    See context_searcher_v1 docstring for usage pattern.
    """
    from csbot.contextengine.contextstore_protocol import ContextIdentifier

    class CachedSearcher:
        """Lightweight search wrapper with pre-built index."""

        def __init__(self, context_store, fts_index):
            self.context_store = context_store
            self.fts = fts_index

        def search(self, query: str):
            """Search contexts using cached FTS index."""
            results = []
            for doc_id in self.fts.search(query, limit=10):
                context_id = ContextIdentifier.from_string(doc_id)
                # Handle NO_CHANNEL_SENTINEL by converting to None
                if context_id.channel == "__NO_CHANNEL__":
                    context_id = ContextIdentifier(
                        channel=None, group=context_id.group, name=context_id.name
                    )
                results.append((doc_id, self.context_store.get_context(context_id)))
            return results

    return CachedSearcher(context_store_v2, fts_index_v2)


@pytest.fixture(scope="session")
def context_searcher(context_searcher_v1):
    """Session-scoped ContextSearcher for default (V1) fixture.

    Alias for tests that don't need to specify V1/V2 explicitly.
    """
    return context_searcher_v1


# Programmatic minimal fixtures for faster tests


@pytest.fixture
def minimal_context_store_v1():
    """Minimal V1 context store (3 contexts, 1 dataset, 1 cronjob)."""
    from tests.factories import context_store_builder

    return (
        context_store_builder()
        .with_project("test/minimal", version=1)
        .with_system_prompt("Test system prompt for minimal fixture")
        .with_project_teams({"exec": ["Test User <test@example.com>"]})
        .add_dataset("test_connection", "test_table")
        .with_markdown("# Test Table\n\nMinimal test dataset.")
        .with_schema_hash("test123", columns=["id", "name"])
        .add_general_context("org_and_people", "test_org")
        .with_topic("Test Organization Context")
        .with_incorrect("Wrong understanding about org")
        .with_correct("Correct understanding about org")
        .with_keywords("organization test")
        .add_general_context("sales_definitions", "test_sales")
        .with_topic("Test Sales Context")
        .with_incorrect("Wrong sales definition")
        .with_correct("Correct sales definition")
        .with_keywords("sales test CSM")
        .add_general_context("uncategorized", "test_other")
        .with_topic("Test Uncategorized Context")
        .with_incorrect("Wrong understanding")
        .with_correct("Correct understanding")
        .with_keywords("test general")
        .add_general_cronjob("test_daily", "0 9 * * *", "Test daily question?", "test-thread")
        .build()
    )


@pytest.fixture
def minimal_context_store_v2():
    """Minimal V2 context store (3 contexts, 1 dataset, 1 cronjob)."""
    from tests.factories import context_store_builder

    return (
        context_store_builder()
        .with_project("test/minimal", version=2)
        .with_system_prompt("Test system prompt for minimal fixture")
        .with_project_teams({"exec": ["Test User <test@example.com>"]})
        .add_dataset("test_connection", "test_table")
        .with_markdown("# Test Table\n\nMinimal test dataset.")
        .with_schema_hash("test123", columns=["id", "name"])
        .add_general_context("org_and_people", "test_org")
        .with_topic("Test Organization Context")
        .with_incorrect("Wrong understanding about org")
        .with_correct("Correct understanding about org")
        .with_keywords("organization test")
        .add_general_context("sales_definitions", "test_sales")
        .with_topic("Test Sales Context")
        .with_incorrect("Wrong sales definition")
        .with_correct("Correct sales definition")
        .with_keywords("sales test CSM")
        .add_general_context("uncategorized", "test_other")
        .with_topic("Test Uncategorized Context")
        .with_incorrect("Wrong understanding")
        .with_correct("Correct understanding")
        .with_keywords("test general")
        .add_general_cronjob("test_daily", "0 9 * * *", "Test daily question?", "test-thread")
        .build()
    )


@pytest.fixture(params=[1, 2])
def minimal_context_store(request, minimal_context_store_v1, minimal_context_store_v2):
    """Parametrized fixture that returns V1 or V2 minimal context store based on param."""
    if request.param == 1:
        return minimal_context_store_v1
    return minimal_context_store_v2


# Programmatic medium fixtures for search tests


@pytest.fixture
def medium_context_store_v1():
    """Medium V1 context store (10 contexts, 4 datasets, 3 cronjobs)."""
    from tests.factories import context_store_builder

    return (
        context_store_builder()
        .with_project("test/medium", version=1)
        .with_system_prompt("Test system prompt for medium fixture")
        .with_project_teams({"exec": ["Test User <test@example.com>"]})
        # Dataset 1: IRIS (BigQuery) - required by test_dataset_docs_structure_iris
        .add_dataset("dev_bigquery", "IRIS")
        .with_markdown("# IRIS Dataset\n\nClassic iris flower dataset with measurements.")
        .with_schema_hash(
            "iris_hash",
            columns=["sepal_length", "sepal_width", "petal_length", "petal_width", "species"],
        )
        # Dataset 2: Snowflake users table
        .add_dataset("purina_snowflake", "users")
        .with_markdown("# Users Table\n\nUser account information.")
        .with_schema_hash("users_hash", columns=["id", "email", "created_at"])
        # Dataset 3: Snowflake orders table
        .add_dataset("purina_snowflake", "orders")
        .with_markdown("# Orders Table\n\nCustomer orders and transactions.")
        .with_schema_hash("orders_hash", columns=["id", "user_id", "total", "order_date"])
        # Dataset 4: Snowflake products table
        .add_dataset("purina_snowflake", "products")
        .with_markdown("# Products Table\n\nProduct catalog.")
        .with_schema_hash("products_hash", columns=["id", "name", "price"])
        # Org contexts (4)
        .add_general_context("org_and_people", "company_structure")
        .with_topic("Company organizational structure")
        .with_incorrect("We have 3 departments")
        .with_correct("We have 5 departments: Engineering, Sales, Marketing, Finance, Operations")
        .with_keywords("organization structure departments teams")
        .add_general_context("org_and_people", "leadership")
        .with_topic("Company leadership team")
        .with_incorrect("CEO reports to board")
        .with_correct("CEO leads executive team with 5 direct reports")
        .with_keywords("leadership executive management CEO")
        .add_general_context("org_and_people", "fiscal_calendar")
        .with_topic("Fiscal quarters and reporting periods")
        .with_incorrect("Calendar year quarters")
        .with_correct("Fiscal year starts Feb 1, quarters align with Feb/May/Aug/Nov")
        .with_keywords("fiscal quarters calendar year reporting")
        .add_general_context("org_and_people", "office_locations")
        .with_topic("Office locations and timezones")
        .with_incorrect("Single office location")
        .with_correct("Three offices: SF (PST), NYC (EST), London (GMT)")
        .with_keywords("offices locations timezones geography")
        # Sales contexts (3)
        .add_general_context("sales_definitions", "customer_segments")
        .with_topic("Customer segmentation model")
        .with_incorrect("Two customer types")
        .with_correct("Four segments: Enterprise, Mid-Market, SMB, Startup")
        .with_keywords("customer segments enterprise SMB CSM")
        .add_general_context("sales_definitions", "pipeline_stages")
        .with_topic("Sales pipeline stages")
        .with_incorrect("Three pipeline stages")
        .with_correct("Five stages: Lead, Qualified, Proposal, Negotiation, Closed")
        .with_keywords("sales pipeline stages deals")
        .add_general_context("sales_definitions", "commission_structure")
        .with_topic("Sales commission calculations")
        .with_incorrect("Flat commission rate")
        .with_correct("Tiered commission: 5% base, 7% over quota, 10% over 150%")
        .with_keywords("sales commission quota compensation")
        # Uncategorized contexts (3)
        .add_general_context("uncategorized", "engineering_practices")
        .with_topic("Engineering development practices")
        .with_incorrect("Waterfall development")
        .with_correct("Two-week sprints with daily standups and weekly demos")
        .with_keywords("engineering development agile sprints")
        .add_general_context("uncategorized", "product_roadmap")
        .with_topic("Product development roadmap")
        .with_incorrect("Annual planning cycle")
        .with_correct("Quarterly roadmap planning with monthly adjustments")
        .with_keywords("product roadmap planning quarterly")
        .add_general_context("uncategorized", "support_sla")
        .with_topic("Customer support SLA commitments")
        .with_incorrect("24-hour response time")
        .with_correct("Enterprise: 2hr response, Mid-Market: 8hr, SMB: 24hr")
        .with_keywords("support SLA response time customer")
        # Cronjobs (3)
        .add_general_cronjob(
            "daily_metrics", "0 9 * * *", "What were yesterday's key metrics?", "daily-metrics"
        )
        .add_general_cronjob(
            "weekly_sales", "0 10 * * 1", "What deals closed last week?", "weekly-sales"
        )
        .add_general_cronjob(
            "monthly_review",
            "0 9 1 * *",
            "What were last month's highlights?",
            "monthly-review",
        )
        .build()
    )


@pytest.fixture
def medium_context_store_v2():
    """Medium V2 context store (10 contexts, 4 datasets, 3 cronjobs)."""
    from tests.factories import context_store_builder

    return (
        context_store_builder()
        .with_project("test/medium", version=2)
        .with_system_prompt("Test system prompt for medium fixture")
        .with_project_teams({"exec": ["Test User <test@example.com>"]})
        # Dataset 1: IRIS (BigQuery) - required by test_dataset_docs_structure_iris
        .add_dataset("dev_bigquery", "IRIS")
        .with_markdown("# IRIS Dataset\n\nClassic iris flower dataset with measurements.")
        .with_schema_hash(
            "iris_hash",
            columns=["sepal_length", "sepal_width", "petal_length", "petal_width", "species"],
        )
        # Dataset 2: Snowflake users table
        .add_dataset("purina_snowflake", "users")
        .with_markdown("# Users Table\n\nUser account information.")
        .with_schema_hash("users_hash", columns=["id", "email", "created_at"])
        # Dataset 3: Snowflake orders table
        .add_dataset("purina_snowflake", "orders")
        .with_markdown("# Orders Table\n\nCustomer orders and transactions.")
        .with_schema_hash("orders_hash", columns=["id", "user_id", "total", "order_date"])
        # Dataset 4: Snowflake products table
        .add_dataset("purina_snowflake", "products")
        .with_markdown("# Products Table\n\nProduct catalog.")
        .with_schema_hash("products_hash", columns=["id", "name", "price"])
        # Org contexts (4)
        .add_general_context("org_and_people", "company_structure")
        .with_topic("Company organizational structure")
        .with_incorrect("We have 3 departments")
        .with_correct("We have 5 departments: Engineering, Sales, Marketing, Finance, Operations")
        .with_keywords("organization structure departments teams")
        .add_general_context("org_and_people", "leadership")
        .with_topic("Company leadership team")
        .with_incorrect("CEO reports to board")
        .with_correct("CEO leads executive team with 5 direct reports")
        .with_keywords("leadership executive management CEO")
        .add_general_context("org_and_people", "fiscal_calendar")
        .with_topic("Fiscal quarters and reporting periods")
        .with_incorrect("Calendar year quarters")
        .with_correct("Fiscal year starts Feb 1, quarters align with Feb/May/Aug/Nov")
        .with_keywords("fiscal quarters calendar year reporting")
        .add_general_context("org_and_people", "office_locations")
        .with_topic("Office locations and timezones")
        .with_incorrect("Single office location")
        .with_correct("Three offices: SF (PST), NYC (EST), London (GMT)")
        .with_keywords("offices locations timezones geography")
        # Sales contexts (3)
        .add_general_context("sales_definitions", "customer_segments")
        .with_topic("Customer segmentation model")
        .with_incorrect("Two customer types")
        .with_correct("Four segments: Enterprise, Mid-Market, SMB, Startup")
        .with_keywords("customer segments enterprise SMB CSM")
        .add_general_context("sales_definitions", "pipeline_stages")
        .with_topic("Sales pipeline stages")
        .with_incorrect("Three pipeline stages")
        .with_correct("Five stages: Lead, Qualified, Proposal, Negotiation, Closed")
        .with_keywords("sales pipeline stages deals")
        .add_general_context("sales_definitions", "commission_structure")
        .with_topic("Sales commission calculations")
        .with_incorrect("Flat commission rate")
        .with_correct("Tiered commission: 5% base, 7% over quota, 10% over 150%")
        .with_keywords("sales commission quota compensation")
        # Uncategorized contexts (3)
        .add_general_context("uncategorized", "engineering_practices")
        .with_topic("Engineering development practices")
        .with_incorrect("Waterfall development")
        .with_correct("Two-week sprints with daily standups and weekly demos")
        .with_keywords("engineering development agile sprints")
        .add_general_context("uncategorized", "product_roadmap")
        .with_topic("Product development roadmap")
        .with_incorrect("Annual planning cycle")
        .with_correct("Quarterly roadmap planning with monthly adjustments")
        .with_keywords("product roadmap planning quarterly")
        .add_general_context("uncategorized", "support_sla")
        .with_topic("Customer support SLA commitments")
        .with_incorrect("24-hour response time")
        .with_correct("Enterprise: 2hr response, Mid-Market: 8hr, SMB: 24hr")
        .with_keywords("support SLA response time customer")
        # Cronjobs (3)
        .add_general_cronjob(
            "daily_metrics", "0 9 * * *", "What were yesterday's key metrics?", "daily-metrics"
        )
        .add_general_cronjob(
            "weekly_sales", "0 10 * * 1", "What deals closed last week?", "weekly-sales"
        )
        .add_general_cronjob(
            "monthly_review",
            "0 9 1 * *",
            "What were last month's highlights?",
            "monthly-review",
        )
        .build()
    )


@pytest.fixture(params=[1, 2])
def medium_context_store(request, medium_context_store_v1, medium_context_store_v2):
    """Parametrized fixture that returns V1 or V2 medium context store based on param."""
    if request.param == 1:
        return medium_context_store_v1
    return medium_context_store_v2


# Helper fixtures that wrap programmatic stores for tests expecting file-based interfaces


@pytest.fixture
def minimal_file_tree_v1(minimal_context_store_v1, tmp_path):
    """FileTree wrapper for minimal V1 store."""
    from csbot.contextengine.serializer import serialize_context_store

    fixture_path = tmp_path / "minimal_v1"
    serialize_context_store(minimal_context_store_v1, fixture_path)
    return FilesystemFileTree(fixture_path)


@pytest.fixture
def minimal_file_tree_v2(minimal_context_store_v2, tmp_path):
    """FileTree wrapper for minimal V2 store."""
    from csbot.contextengine.serializer import serialize_context_store

    fixture_path = tmp_path / "minimal_v2"
    serialize_context_store(minimal_context_store_v2, fixture_path)
    return FilesystemFileTree(fixture_path)


@pytest.fixture
def minimal_context_store_client(minimal_context_store_v1, tmp_path):
    """ContextStoreClient wrapper for minimal store."""
    from csbot.contextengine.serializer import serialize_context_store

    fixture_path = tmp_path / "minimal_client"
    serialize_context_store(minimal_context_store_v1, fixture_path)
    return FakeLocalContextStore(fixture_path)


@pytest.fixture
def medium_file_tree_v1(medium_context_store_v1, tmp_path):
    """FileTree wrapper for medium V1 store."""
    from csbot.contextengine.serializer import serialize_context_store

    fixture_path = tmp_path / "medium_v1"
    serialize_context_store(medium_context_store_v1, fixture_path)
    return FilesystemFileTree(fixture_path)


@pytest.fixture
def medium_file_tree_v2(medium_context_store_v2, tmp_path):
    """FileTree wrapper for medium V2 store."""
    from csbot.contextengine.serializer import serialize_context_store

    fixture_path = tmp_path / "medium_v2"
    serialize_context_store(medium_context_store_v2, fixture_path)
    return FilesystemFileTree(fixture_path)


@pytest.fixture
def medium_context_store_client(medium_context_store_v1, tmp_path):
    """ContextStoreClient wrapper for medium store."""
    from csbot.contextengine.serializer import serialize_context_store

    fixture_path = tmp_path / "medium_client"
    serialize_context_store(medium_context_store_v1, fixture_path)
    return FakeLocalContextStore(fixture_path)
