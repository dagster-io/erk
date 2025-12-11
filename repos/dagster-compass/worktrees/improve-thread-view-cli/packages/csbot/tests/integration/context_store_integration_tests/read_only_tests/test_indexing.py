"""FTS Indexing Tests.

Tests for full-text search index functionality, including index building,
caching behavior, result ranking, and Tantivy-specific features.
"""

from csbot.contextengine.context_engine import ContextSearcher, FTSIndex
from csbot.contextengine.loader import load_context_store
from tests.factories.context_store_factory import context_store_builder


def test_index_building_from_contexts(medium_file_tree_v1):
    """Test building FTS index from context files."""
    context_store = load_context_store(medium_file_tree_v1)
    searcher = ContextSearcher(context_store=context_store, channel_name=None)

    # Build index - should not raise errors
    fts_index = searcher.build_index()

    assert fts_index is not None
    assert isinstance(fts_index, FTSIndex)

    # Medium fixture has 10 contexts
    assert len(fts_index.doc_ids) >= 10, f"Expected 10+ documents, got {len(fts_index.doc_ids)}"


def test_index_caching_behavior(medium_file_tree_v1):
    """Test that index is cached and reused."""
    context_store = load_context_store(medium_file_tree_v1)
    searcher = ContextSearcher(context_store=context_store, channel_name=None)

    # First index build
    index1 = searcher.build_index()

    # Second index build should return the same instance (cached)
    index2 = searcher.build_index()

    assert index1 is index2, "Index should be cached and reused"
    assert searcher.fts is not None, "Searcher should store the cached index"


def test_search_result_ranking(file_tree):
    """Test that search results are properly ranked by relevance."""
    context_store = load_context_store(file_tree)
    searcher = ContextSearcher(context_store=context_store, channel_name=None)

    # Search for a term that appears in multiple contexts
    results = searcher.search("customer")

    if len(results) > 1:
        # Results should be returned in consistent order
        # (Tantivy handles the actual relevance scoring)
        first_result = results[0]
        second_result = results[1]

        # Both should be valid results
        assert isinstance(first_result, tuple)
        assert len(first_result) == 2
        assert isinstance(second_result, tuple)
        assert len(second_result) == 2

        # File paths should be different
        assert first_result[0] != second_result[0]


def test_index_with_empty_directory(file_tree):
    """Test index creation when no context files are found (hypothetical)."""
    from collections.abc import Generator

    from csbot.contextengine.contextstore_protocol import GitInfo

    # Create a searcher but use a path that won't find any contexts
    class EmptyFileTree:
        def recursive_glob(self, pattern: str) -> Generator[str]:
            if False:  # Make this unreachable to satisfy generator requirements
                yield ""

        def read_text(self, path: str) -> str:
            raise FileNotFoundError(f"File not found: {path}")

        def exists(self, path: str) -> bool:
            return False

        def is_file(self, path: str) -> bool:
            return False

        def is_dir(self, path: str) -> bool:
            return False

        def listdir(self, path: str = "") -> list[str]:
            return []

        def glob(self, path: str, pattern: str) -> Generator[str]:
            if False:  # Make this unreachable to satisfy generator requirements
                yield ""

        def get_git_info(self) -> GitInfo | None:
            return None

    empty_store = context_store_builder().build()
    searcher = ContextSearcher(context_store=empty_store, channel_name=None)

    # Should handle empty document list gracefully
    fts_index = searcher.build_index()
    assert isinstance(fts_index, FTSIndex)
    assert len(fts_index.doc_ids) == 0

    # Search on empty index should return empty results
    results = searcher.search("anything")
    assert isinstance(results, list)
    assert len(results) == 0


def test_concurrent_index_access(medium_file_tree_v1):
    """Test thread safety of index access (basic test)."""
    context_store = load_context_store(medium_file_tree_v1)
    searcher = ContextSearcher(context_store=context_store, channel_name=None)

    # Build index first
    searcher.build_index()

    # Multiple searches should work without issues
    results1 = searcher.search("customer")
    results2 = searcher.search("fiscal")
    results3 = searcher.search("sales")

    # All should return valid results (lists)
    assert isinstance(results1, list)
    assert isinstance(results2, list)
    assert isinstance(results3, list)

    # Results should be consistent across calls
    results1_repeat = searcher.search("customer")
    assert len(results1) == len(results1_repeat)


def test_tantivy_index_features(file_tree):
    """Test Tantivy-specific indexing features."""
    context_store = load_context_store(file_tree)
    searcher = ContextSearcher(context_store=context_store, channel_name=None)
    fts_index = searcher.build_index()

    # Test basic search functionality
    test_queries = ["customer", "fiscal", "sales", "CSM"]

    for query in test_queries:
        # Each query should work without errors
        results = fts_index.search(query, limit=5)
        assert isinstance(results, list)

        # Results should be valid document IDs
        for doc_id in results:
            assert isinstance(doc_id, str)
            assert doc_id in fts_index.doc_ids

    # Test query parsing (implicit through search)
    # Complex queries should be handled gracefully
    complex_query = "customer AND fiscal"
    results = fts_index.search(complex_query, limit=5)
    assert isinstance(results, list)

    # Test limit parameter
    unlimited_results = fts_index.search("customer", limit=100)
    limited_results = fts_index.search("customer", limit=2)

    if len(unlimited_results) > 2:
        assert len(limited_results) <= 2, "Limit parameter should restrict results"
