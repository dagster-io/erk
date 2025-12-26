"""Tests for manifest layout implementation (V1 and V2 behavior)."""

import tempfile
from pathlib import Path

import yaml

from csbot.contextengine.loader import load_context_store
from csbot.local_context_store.git.file_tree import FilesystemFileTree


class TestFileTreeDatasetSearcherVersions:
    """Test FileTreeDatasetSearcher version-aware behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def _create_v1_project(self):
        """Create a V1 project with legacy layout."""
        # Create project config (V1 - no version field)
        config = {"project_name": "test/project", "teams": {"data": ["user@example.com"]}}
        with open(self.project_path / "contextstore_project.yaml", "w") as f:
            yaml.dump(config, f)

        # Create legacy docs structure
        docs_dir = self.project_path / "docs" / "snowflake_prod"
        docs_dir.mkdir(parents=True)

        with open(docs_dir / "customers.md", "w") as f:
            f.write("---\nschema_hash: abc123\n---\n# Customers Table\nCustomer data")

        with open(docs_dir / "orders.md", "w") as f:
            f.write("---\nschema_hash: def456\n---\n# Orders Table\nOrder information")

    def _create_v2_project(self):
        """Create a V2 project with manifest layout."""
        # Create project config (V2)
        config = {
            "project_name": "test/project",
            "teams": {"data": ["user@example.com"]},
            "version": 2,
        }
        with open(self.project_path / "contextstore_project.yaml", "w") as f:
            yaml.dump(config, f)

        # Create manifest docs structure
        customers_dir = self.project_path / "docs" / "snowflake_prod" / "dim_customers" / "context"
        customers_dir.mkdir(parents=True)
        with open(customers_dir / "summary.md", "w") as f:
            f.write("---\nschema_hash: abc123\n---\n# Customers Table\nCustomer data")

        orders_dir = (
            self.project_path / "docs" / "snowflake_prod" / "sales" / "fact_orders" / "context"
        )
        orders_dir.mkdir(parents=True)
        with open(orders_dir / "summary.md", "w") as f:
            f.write("---\nschema_hash: def456\n---\n# Orders Table\nOrder information")

    def test_v1_project_search_legacy_layout(self):
        """Test V1 project correctly searches legacy layout."""
        self._create_v1_project()

        tree = FilesystemFileTree(self.project_path)
        context_store = load_context_store(tree)
        dataset, documentation = next(
            iter(d for d in context_store.datasets if d[0].table_name == "customers")
        )

        assert dataset.connection == "snowflake_prod"
        assert dataset.table_name == "customers"
        assert documentation.summary and "Customer data" in documentation.summary

    def test_v2_project_search_manifest_layout(self):
        """Test V2 project correctly searches manifest layout."""
        self._create_v2_project()

        tree = FilesystemFileTree(self.project_path)
        context_store = load_context_store(tree)

        dataset, documentation = next(
            iter(d for d in context_store.datasets if d[0].table_name == "dim_customers")
        )

        assert dataset.connection == "snowflake_prod"
        assert dataset.table_name == "dim_customers"
        assert documentation.summary and "Customer data" in documentation.summary
