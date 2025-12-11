"""Integration tests for manifest layout using real test fixtures."""

from csbot.contextengine.dataset_documentation import DatasetSearcher
from csbot.contextengine.loader import load_context_store, load_project_from_tree


class TestManifestLayoutIntegration:
    """Integration tests using V1 and V2 test fixtures."""

    def test_v1_fixture_behavior(self, file_tree_v1):
        """Test V1 fixture has correct legacy behavior."""
        # Load project and verify it's version 1
        project = load_project_from_tree(file_tree_v1)
        assert project.version == 1

        # Create searcher and verify it works with legacy layout

        context_store = load_context_store(file_tree_v1)
        searcher = DatasetSearcher(context_store=context_store, full=False, connections=None)

        # Should find some results
        results = searcher.search("ACCOUNTS")
        assert len(results) > 0

    def test_v2_fixture_behavior(self, file_tree_v2):
        """Test V2 fixture has correct manifest behavior."""
        # Load project and verify it's version 2
        project = load_project_from_tree(file_tree_v2)
        assert project.version == 2

        # Create searcher and verify it works with manifest layout
        context_store = load_context_store(file_tree_v2)
        searcher = DatasetSearcher(context_store=context_store, full=False, connections=None)

        # Should find some results
        results = searcher.search("ACCOUNTS")
        assert len(results) > 0

        # Results should have object_id (V2 behavior)
        for result in results:
            assert result.object_id is not None
            # Verify object_id format
            assert result.connection in result.object_id
            assert result.table in result.object_id

    def test_v1_vs_v2_search_equivalence(self, file_tree_v1, file_tree_v2):
        """Test that V1 and V2 find equivalent content after migration."""
        # Create searchers
        context_v1 = load_context_store(file_tree_v1)
        searcher_v1 = DatasetSearcher(
            context_store=context_v1,
            full=True,
            connections=None,
        )
        context_v2 = load_context_store(file_tree_v2)
        searcher_v2 = DatasetSearcher(
            context_store=context_v2,
            full=True,
            connections=None,
        )

        # Search for the same term
        results_v1 = searcher_v1.search("ACCOUNTS")
        results_v2 = searcher_v2.search("ACCOUNTS")

        # Should find same number of results
        assert len(results_v1) == len(results_v2)

        # Content should be equivalent (same docs_markdown)
        # Sort by connection/table for comparison
        results_v1_sorted = sorted(results_v1, key=lambda r: (r.connection, r.table))
        results_v2_sorted = sorted(results_v2, key=lambda r: (r.connection, r.table))

        for r1, r2 in zip(results_v1_sorted, results_v2_sorted):
            assert r1.connection == r2.connection
            assert r1.table == r2.table
            # Content should be the same after migration
            assert r1.docs_markdown == r2.docs_markdown

    def test_v2_object_id_structure(self, file_tree_v2):
        """Test V2 object IDs have correct structure."""
        context_store = load_context_store(file_tree_v2)
        searcher = DatasetSearcher(context_store=context_store, full=False, connections=None)

        # Search for all results
        results = searcher.search("REPORTING")  # Should match many tables

        for result in results:
            object_id = result.object_id
            assert object_id is not None

            # Parse object ID parts
            parts = object_id.split("/")

            # Should have at least connection and table name
            assert len(parts) >= 2

            # First part should be connection
            assert parts[0] == result.connection

            # Last part should be table name
            assert parts[-1] == result.table

            # If more than 2 parts, middle parts are namespace
            if len(parts) > 2:
                namespace_parts = parts[1:-1]
                assert len(namespace_parts) > 0

    def test_v1_connection_filtering(self, file_tree_v1):
        """Test connection filtering works correctly in V1."""
        context_store = load_context_store(file_tree_v1)

        # Test with specific connection filter
        searcher_filtered = DatasetSearcher(
            context_store=context_store,
            full=False,
            connections=["purina_snowflake"],
        )

        results_filtered = searcher_filtered.search("REPORTING")

        # All results should be from the filtered connection
        for result in results_filtered:
            assert result.connection == "purina_snowflake"

    def test_v2_connection_filtering(self, file_tree_v2):
        """Test connection filtering works correctly in V2."""
        context_store = load_context_store(file_tree_v2)

        # Test with specific connection filter
        searcher_filtered = DatasetSearcher(
            context_store=context_store,
            full=False,
            connections=["purina_snowflake"],
        )

        results_filtered = searcher_filtered.search("REPORTING")

        # All results should be from the filtered connection
        for result in results_filtered:
            assert result.connection == "purina_snowflake"
            # V2 should still have object_id
            assert result.object_id is not None
            assert result.object_id.startswith("purina_snowflake/")

    def test_v1_docs_structure_validation(self, file_tree_v1):
        """Test V1 fixture has expected legacy structure."""
        # Check that legacy .md files exist directly in connection directories
        assert file_tree_v1.exists("docs/purina_snowflake")

        # Look for some legacy files
        files = list(file_tree_v1.glob("docs/purina_snowflake", "*.md"))
        assert len(files) > 0

        # Should not have any artifacts directories
        artifacts_dirs = list(file_tree_v1.glob("docs/purina_snowflake", "**/artifacts"))
        assert len(artifacts_dirs) == 0

    def test_v2_docs_structure_validation(self, file_tree_v2):
        """Test V2 fixture has expected manifest structure."""
        # Check that manifest structure exists
        assert file_tree_v2.exists("docs/purina_snowflake")

        # Look for context directories
        # This searches for all summary.md files in context directories
        summary_files = []
        for connection_dir in file_tree_v2.listdir("docs"):
            if file_tree_v2.is_dir(f"docs/{connection_dir}"):
                for item in file_tree_v2.listdir(f"docs/{connection_dir}"):
                    if file_tree_v2.is_dir(f"docs/{connection_dir}/{item}"):
                        context_dir = f"docs/{connection_dir}/{item}/context"
                        summary_file = f"{context_dir}/summary.md"
                        if file_tree_v2.exists(summary_file):
                            summary_files.append(summary_file)

        assert len(summary_files) > 0

        # Should not have any legacy .md files directly in connection directories
        for connection_dir in file_tree_v2.listdir("docs"):
            if file_tree_v2.is_dir(f"docs/{connection_dir}"):
                legacy_files = list(file_tree_v2.glob(f"docs/{connection_dir}", "*.md"))
                assert len(legacy_files) == 0, f"Found legacy files in V2 fixture: {legacy_files}"
