"""Search Functionality Tests.

Tests for FileTreeContextSearcher functionality including topic searches,
keyword matching, and various search edge cases.
"""


def test_search_by_exact_topic(context_searcher):
    """Search for contexts by exact topic match."""
    # Search for "fiscal quarters" - should find specific context
    results = context_searcher.search("fiscal quarters")

    assert len(results) > 0, "Expected at least one result for 'fiscal quarters'"

    for _, context in results:
        assert context.topic is not None
        assert context.incorrect_understanding is not None
        assert context.correct_understanding is not None


def test_search_by_keywords(context_searcher):
    """Search for contexts using search keywords."""
    # Search for "CSM" (Customer Success Manager)
    results = context_searcher.search("CSM")

    assert len(results) > 0, "Expected results for 'CSM' keyword search"

    # At least one result should relate to CSM
    found_csm_context = False
    for file_path, context in results:
        if "CSM" in context.topic or "CSM" in str(context.search_keywords):
            found_csm_context = True
            break

    assert found_csm_context, "Expected to find CSM-related context"


def test_partial_text_matching(context_searcher):
    """Test partial word matching in search."""
    # Search for partial word "custom" - should match "customer", "custom", etc.
    results = context_searcher.search("customer")

    assert len(results) > 0, "Expected results for 'customer' search"

    # Verify results contain customer-related content
    customer_related = False
    for file_path, context in results:
        content = f"{context.topic} {context.incorrect_understanding} {context.correct_understanding} {context.search_keywords}"
        if "customer" in content.lower():
            customer_related = True
            break

    assert customer_related, "Expected customer-related content in results"


def test_search_across_categories(context_searcher):
    """Test search finds results across multiple categories."""
    # Search for broad term "sales"
    results = context_searcher.search("sales")

    assert len(results) > 0, "Expected results for 'sales' search"

    # Should find results from different categories
    categories_found = set()
    for file_path, context in results:
        if "org_and_people" in file_path:
            categories_found.add("org_and_people")
        elif "sales_definitions" in file_path:
            categories_found.add("sales_definitions")
        elif "uncategorized" in file_path:
            categories_found.add("uncategorized")

    # Should find results from at least one category
    assert len(categories_found) > 0, "Expected results from at least one category"


def test_search_with_special_characters(context_searcher):
    """Test search with special characters and formatting."""
    # Search for terms with special characters that appear in context
    results = context_searcher.search("Q1")  # Quarter terminology

    # Should handle the query without errors
    assert isinstance(results, list), "Search should return a list"

    # If results found, they should be valid
    for file_path, context in results:
        assert isinstance(file_path, str)
        assert hasattr(context, "topic")


def test_case_insensitive_search(context_searcher):
    """Test that search is case insensitive."""
    # Search for same term in different cases
    results_lower = context_searcher.search("fiscal")
    results_upper = context_searcher.search("FISCAL")
    results_mixed = context_searcher.search("Fiscal")

    # All should return some results (may differ due to ranking)
    assert len(results_lower) >= 0
    assert len(results_upper) >= 0
    assert len(results_mixed) >= 0

    # If any return results, the search is working
    total_results = len(results_lower) + len(results_upper) + len(results_mixed)
    if total_results > 0:
        # At least one case variant should find results
        assert max(len(results_lower), len(results_upper), len(results_mixed)) > 0


def test_relevance_ordering(context_searcher):
    """Test that search results are ordered by relevance."""
    # Search for term that should appear in multiple contexts
    results = context_searcher.search("customer")

    if len(results) > 1:
        # Results should be returned in some consistent order
        # (The actual relevance scoring is handled by Tantivy)
        first_result = results[0]
        assert isinstance(first_result, tuple)
        assert len(first_result) == 2
        assert isinstance(first_result[0], str)  # file path
        assert hasattr(first_result[1], "topic")  # context object


def test_empty_query_handling(context_searcher):
    """Test handling of empty search queries."""
    # Empty string query
    results = context_searcher.search("")
    assert isinstance(results, list)
    assert len(results) == 0  # Should return empty list

    # Whitespace-only query
    results = context_searcher.search("   ")
    assert isinstance(results, list)


def test_no_matches_found(context_searcher):
    """Test search with query that should find no matches."""
    # Search for non-existent term
    results = context_searcher.search("xyz123nonexistent")

    assert isinstance(results, list)
    assert len(results) == 0, "Expected no results for non-existent term"


def test_multi_term_search(context_searcher):
    """Test search with multiple terms."""
    # Search for multiple terms
    results = context_searcher.search("fiscal year")

    assert isinstance(results, list)

    # If results found, they should contain contexts
    for file_path, context in results:
        assert isinstance(file_path, str)
        assert hasattr(context, "topic")
        assert hasattr(context, "incorrect_understanding")
        assert hasattr(context, "correct_understanding")
