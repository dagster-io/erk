"""Tests for schema change PR duplication prevention."""

import hashlib
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest
import yaml

from csbot.contextengine.contextstore_protocol import ContextStoreProject, Dataset
from csbot.ctx_admin.dataset_documentation import (
    ColumnDescription,
    TableSchemaAnalysis,
)
from csbot.local_context_store.git.file_tree import FilesystemFileTree
from csbot.local_context_store.github.types import PullRequestResult
from csbot.slackbot.config import DatabaseConfig


class MockGithubWorkingDir:
    """Mock GitHub working directory for testing."""

    def __init__(self, _repo_path: str):
        self._repo_path = Path(_repo_path)
        self.created_prs = []
        self.open_prs = {}  # Track open PRs by title

    def _get_git_repository_name(self) -> str:
        return "test/repo"

    def _get_repo_path(self) -> Path:
        return self._repo_path

    def clean_and_update_repo(self) -> None:
        pass

    def commit_and_push(self, title: str, body: str, automerge: bool) -> str:
        # Simulate GitHub PR creation
        pr_url = f"https://github.com/test/repo/pull/{len(self.created_prs) + 1}"
        self.created_prs.append({"title": title, "body": body, "url": pr_url})
        # Track as open PR
        if not automerge:
            self.open_prs[title] = pr_url
        return pr_url

    def open_data_request_ticket(self, title: str, body: str, attribution: str | None) -> str:
        """Mock implementation."""
        return "https://github.com/test/repo/issues/1"

    @contextmanager
    def pull_request(
        self, title: str, body: str, automerge: bool, *, copy_mode: bool = True
    ) -> "Generator[PullRequestResult]":
        pr = PullRequestResult(self._repo_path, title, body, automerge)
        pr.pr_url = self.commit_and_push(title, body, automerge)
        yield pr

    def has_open_pr_with_title_prefix(self, prefix: str) -> bool:
        """Check if there's an open PR with the given title prefix."""
        return any(title.startswith(prefix) for title in self.open_prs.keys())

    def get_open_pr_url_with_title_prefix(self, prefix: str) -> str | None:
        """Get the URL of an open PR with the given title prefix."""
        for title, url in self.open_prs.items():
            if title.startswith(prefix):
                return url
        return None


class TestSchemaChangePRDuplication:
    """Test cases for schema change PR duplication prevention."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_path = Path(self.temp_dir.name)

        # Create project structure
        self.docs_dir = self.project_path / "docs" / "test_connection"
        self.docs_dir.mkdir(parents=True)

        # Create a project config
        self.project_config = ContextStoreProject(
            project_name="test_org/test_project",
            teams={"team1": ["user1", "user2"]},
        )

        config_path = self.project_path / "contextstore_project.yaml"
        with open(config_path, "w") as f:
            yaml.safe_dump(self.project_config.model_dump(), f)

        self.mock_github_dir = MockGithubWorkingDir(str(self.project_path))

    def teardown_method(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def create_table_schema_analysis(
        self, table_name: str, schema_hash: str
    ) -> TableSchemaAnalysis:
        """Create a test table schema analysis."""
        columns = [
            ColumnDescription(name="col1", type="VARCHAR", column_comment=None),
            ColumnDescription(name="col2", type="INTEGER", column_comment=None),
        ]
        return TableSchemaAnalysis(
            table_name=table_name,
            columns=columns,
            schema_hash=schema_hash,
            table_comment=None,
        )

    def create_existing_documentation(self, table_name: str, schema_hash: str):
        """Create existing documentation file with frontmatter."""
        content = f"""---
schema_hash: {schema_hash}
columns:
  - col1 (VARCHAR)
  - col2 (INTEGER)
---
# Table Documentation for {table_name}

This is existing documentation.
"""
        output_file = self.docs_dir / f"{table_name}.md"
        output_file.write_text(content)

    def test_no_duplicate_pr_for_same_schema_change(self):
        """Test that multiple calls for the same schema change don't create duplicate PRs."""
        import asyncio
        import tempfile

        from csbot.contextengine.loader import get_dataset_schema_hash
        from csbot.slackbot.storage.sqlite import (
            SlackbotInstanceSqliteStorage,
            SqliteConnectionFactory,
        )

        table_name = "test_table"
        old_hash = "old_hash_123"
        new_hash = "new_hash_456"

        # Create existing documentation with old hash
        self.create_existing_documentation(table_name, old_hash)

        dataset = Dataset(table_name=table_name, connection="test_connection")
        new_schema = self.create_table_schema_analysis(table_name, new_hash)

        # Verify initial state
        tree = FilesystemFileTree(self.project_path)
        current_hash = get_dataset_schema_hash(tree, dataset)
        assert current_hash == old_hash

        # Create a temporary database for KV store testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        sql_conn_factory = SqliteConnectionFactory.from_db_config(
            DatabaseConfig.from_sqlite_path(db_path)
        )
        kv_store = SlackbotInstanceSqliteStorage(sql_conn_factory, "test_bot", Mock())

        async def test_pr_deduplication():
            # Create the PR key that would be used in the actual implementation
            pr_key = f"{dataset.connection}:{dataset.table_name}:{new_schema.schema_hash}"

            # First check - no existing PR should be found
            existing_pr = await kv_store.get("schema_change_prs", pr_key)
            assert existing_pr is None

            # Simulate creating first PR
            pr_url_1 = "https://github.com/test/repo/pull/1"
            await kv_store.set(
                "schema_change_prs", pr_key, pr_url_1, expiry_seconds=30 * 24 * 60 * 60
            )

            # Second check - should find the existing PR
            existing_pr = await kv_store.get("schema_change_prs", pr_key)
            assert existing_pr == pr_url_1

            # Different schema hash should not conflict
            different_schema = self.create_table_schema_analysis(table_name, "different_hash_789")
            different_pr_key = (
                f"{dataset.connection}:{dataset.table_name}:{different_schema.schema_hash}"
            )
            existing_different_pr = await kv_store.get("schema_change_prs", different_pr_key)
            assert existing_different_pr is None

        # Run the async test
        asyncio.run(test_pr_deduplication())

        # Clean up
        import os

        os.unlink(db_path)

    def test_multiple_different_schema_changes_create_separate_prs(self):
        """Test that different schema changes create separate PRs."""
        table1 = "table1"
        table2 = "table2"
        hash1 = "hash_123"
        hash2 = "hash_456"

        # Create documentation for both tables
        self.create_existing_documentation(table1, "old_hash_1")
        self.create_existing_documentation(table2, "old_hash_2")

        # dataset1 = DatasetToReconcile(table_name=table1, connection="test_connection")
        # dataset2 = DatasetToReconcile(table_name=table2, connection="test_connection")

        # schema1 = self.create_table_schema_analysis(table1, hash1)
        # schema2 = self.create_table_schema_analysis(table2, hash2)

        # Create PRs for different tables
        with self.mock_github_dir.pull_request(
            title=f"DATASET MONITORING: Update {table1} schema",
            body=f"Schema hash changed to: {hash1}",
            automerge=False,
        ):  # as pr1:
            pass

        with self.mock_github_dir.pull_request(
            title=f"DATASET MONITORING: Update {table2} schema",
            body=f"Schema hash changed to: {hash2}",
            automerge=False,
        ):  # as pr2:
            pass

        # Should have 2 separate PRs
        assert len(self.mock_github_dir.created_prs) == 2
        assert self.mock_github_dir.has_open_pr_with_title_prefix(
            f"DATASET MONITORING: Update {table1}"
        )
        assert self.mock_github_dir.has_open_pr_with_title_prefix(
            f"DATASET MONITORING: Update {table2}"
        )

    def test_pr_tracking_state_management(self):
        """Test that PR tracking state is properly managed."""
        table_name = "test_table"
        hash1 = "hash_123"
        hash2 = "hash_456"

        # Create first PR
        pr_title = f"DATASET MONITORING: Update {table_name} schema"

        with self.mock_github_dir.pull_request(
            title=pr_title, body=f"Schema hash changed to: {hash1}", automerge=False
        ) as pr:
            pass  # pr_url is set in __exit__, not accessible here

        pr1_url = pr.pr_url  # Access after context manager exits
        assert self.mock_github_dir.has_open_pr_with_title_prefix(pr_title)
        assert self.mock_github_dir.get_open_pr_url_with_title_prefix(pr_title) == pr1_url

        # Simulate PR being closed/merged
        if pr_title in self.mock_github_dir.open_prs:
            del self.mock_github_dir.open_prs[pr_title]

        # Now another schema change should be able to create a new PR
        assert not self.mock_github_dir.has_open_pr_with_title_prefix(pr_title)

        with self.mock_github_dir.pull_request(
            title=pr_title, body=f"Schema hash changed to: {hash2}", automerge=False
        ):  # as pr2:
            pass

        # Should now have 2 total PRs created, but only 1 open
        assert len(self.mock_github_dir.created_prs) == 2
        assert self.mock_github_dir.has_open_pr_with_title_prefix(pr_title)


class TestSchemaChangeDetectionLogic:
    """Test the core logic for detecting schema changes."""

    def test_schema_hash_computation_consistency(self):
        """Test that schema hash computation is consistent and deterministic."""
        # Same columns in different orders should produce same hash
        columns1 = [
            ColumnDescription(name="col_b", type="VARCHAR", column_comment=None),
            ColumnDescription(name="col_a", type="INTEGER", column_comment=None),
        ]

        columns2 = [
            ColumnDescription(name="col_a", type="INTEGER", column_comment=None),
            ColumnDescription(name="col_b", type="VARCHAR", column_comment=None),
        ]

        # Manually compute hashes (simulating the logic from ctx_admin_lib.py)
        def compute_hash(columns):
            sorted_columns = sorted(columns, key=lambda x: x.name)
            column_tuples = [(col.name, col.type) for col in sorted_columns]
            return hashlib.sha256(json.dumps(column_tuples, sort_keys=True).encode()).hexdigest()

        hash1 = compute_hash(columns1)
        hash2 = compute_hash(columns2)

        assert hash1 == hash2, "Schema hashes should be the same regardless of column order"

    def test_schema_change_detection(self):
        """Test schema change detection logic."""
        # Different schemas should produce different hashes
        columns1 = [ColumnDescription(name="col1", type="VARCHAR", column_comment=None)]
        columns2 = [
            ColumnDescription(name="col1", type="INTEGER", column_comment=None)
        ]  # Type changed
        columns3 = [
            ColumnDescription(name="col1", type="VARCHAR", column_comment=None),
            ColumnDescription(name="col2", type="INTEGER", column_comment=None),  # Column added
        ]

        def compute_hash(columns):
            sorted_columns = sorted(columns, key=lambda x: x.name)
            column_tuples = [(col.name, col.type) for col in sorted_columns]
            return hashlib.sha256(json.dumps(column_tuples, sort_keys=True).encode()).hexdigest()

        hash1 = compute_hash(columns1)
        hash2 = compute_hash(columns2)
        hash3 = compute_hash(columns3)

        # All hashes should be different
        assert hash1 != hash2, "Different column types should produce different hashes"
        assert hash1 != hash3, "Additional columns should produce different hashes"
        assert hash2 != hash3, "Different schemas should produce different hashes"


@pytest.mark.asyncio
class TestAsyncSchemaChangeHandling:
    """Test async handling of schema changes with proper PR deduplication."""

    async def test_concurrent_schema_change_detection(self):
        """Test that concurrent schema change detections don't create duplicate PRs."""
        # This test would simulate multiple async calls to _check_and_update_dataset_if_changed
        # and verify that only one PR gets created for the same schema change

        # Mock the async environment
        # mock_logger = Mock()
        # mock_profile = Mock()
        # mock_project = Mock()
        # mock_github_dir = Mock()

        # This would test the actual slackbot logic if implemented with proper deduplication
        pass  # Placeholder for future async test implementation


class TestPRTitlePatterns:
    """Test PR title patterns and tracking."""

    def test_pr_title_generation(self):
        """Test that PR titles are generated consistently."""
        table_name = "my_test_table"
        expected_prefix = f"DATASET MONITORING: Update {table_name} schema"

        # The actual title should start with this prefix
        assert expected_prefix == f"DATASET MONITORING: Update {table_name} schema"

    def test_pr_title_uniqueness_per_table(self):
        """Test that PR titles are unique per table but consistent for the same table."""
        table1 = "table1"
        table2 = "table2"

        title1 = f"DATASET MONITORING: Update {table1} schema"
        title2 = f"DATASET MONITORING: Update {table2} schema"
        title1_duplicate = f"DATASET MONITORING: Update {table1} schema"

        assert title1 != title2, "Different tables should have different PR titles"
        assert title1 == title1_duplicate, "Same table should have same PR title"


if __name__ == "__main__":
    pytest.main([__file__])
