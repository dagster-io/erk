"""Integration tests for dataset_documentation module - tests with I/O and git operations."""

import logging
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import yaml

from csbot.contextengine.contextstore_protocol import Dataset, DatasetDocumentation
from csbot.contextengine.loader import get_dataset_schema_hash
from csbot.ctx_admin.dataset_documentation import (
    TableFrontmatter,
    TableSchemaAnalysis,
    update_dataset,
)
from csbot.local_context_store.git.file_tree import FilesystemFileTree, create_git_commit_file_tree
from tests.factories.context_store_factory import context_store_builder


def add_project_file(project_path: Path):
    project_file = project_path / "contextstore_project.yaml"
    with open(str(project_file), "w") as f:
        yaml.safe_dump({"project_name": "test/test"}, f)


class TestGitCommitFileTree:
    """Test create_git_commit_file_tree function with git operations."""

    def test_context_manager_works(self):
        """Test context manager works with valid git repo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_dir = Path(temp_dir) / ".git"
            git_dir.mkdir()

            # Initialize a minimal git repo for testing
            subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True
            )
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True)

            # Create a file and commit it
            (Path(temp_dir) / "test.txt").write_text("test content")
            subprocess.run(["git", "add", "test.txt"], cwd=temp_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)

            with create_git_commit_file_tree(Path(temp_dir), f"local:{temp_dir}") as tree:
                # Should return a FileTree object
                assert hasattr(tree, "get_git_info")
                git_info = tree.get_git_info()
                assert git_info is not None
                assert git_info.repository == f"local:{temp_dir}"


class TestGetDatasetSchemaHash:
    """Test get_dataset_schema_hash function with file I/O."""

    def test_get_dataset_schema_hash_file_exists_with_frontmatter(self):
        """Test getting schema hash when file exists with frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            add_project_file(project_path)
            docs_dir = project_path / "docs" / "test_connection"
            docs_dir.mkdir(parents=True)

            # Create a markdown file with frontmatter
            markdown_content = """---
schema_hash: abc123
columns:
  - col1 (VARCHAR)
---
# Table Documentation"""

            output_file = docs_dir / "test_table.md"
            output_file.write_text(markdown_content)

            dataset = Dataset(table_name="test_table", connection="test_connection")

            tree = FilesystemFileTree(project_path)
            result = get_dataset_schema_hash(tree, dataset)

            assert result == "abc123"

    def test_get_dataset_schema_hash_file_exists_no_frontmatter(self):
        """Test getting schema hash when file exists without frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            add_project_file(project_path)

            docs_dir = project_path / "docs" / "test_connection"
            docs_dir.mkdir(parents=True)

            # Create a markdown file without frontmatter
            markdown_content = "# Table Documentation\n\nContent without frontmatter."

            output_file = docs_dir / "test_table.md"
            output_file.write_text(markdown_content)

            dataset = Dataset(table_name="test_table", connection="test_connection")

            tree = FilesystemFileTree(project_path)
            result = get_dataset_schema_hash(tree, dataset)

            assert result is None


def test_update_dataset():
    logger = logging.getLogger(__name__)
    schema_analysis = TableSchemaAnalysis(
        table_name="t",
        columns=[],
        schema_hash="123",
        table_comment="comment",
    )
    from csbot.ctx_admin.dataset_documentation import TableAnalysis

    table_analysis = TableAnalysis(
        table_name=schema_analysis.table_name,
        table_comment=schema_analysis.table_comment,
        row_count=5,
        columns=[],
        sample_rows=[],
    )
    agent = AsyncMock()
    agent.create_completion.return_value = "summary"
    dataset = Dataset(connection="connection", table_name="table")
    profile = Mock()
    before = (
        context_store_builder()
        .add_dataset(
            "connection",
            "table",
        )
        .build()
    )

    with (
        patch(
            "csbot.ctx_admin.dataset_documentation.analyze_table",
            return_value=table_analysis,
        ),
        patch(
            "csbot.ctx_admin.dataset_documentation.get_sql_client",
        ),
        ThreadPoolExecutor() as t,
    ):
        updated = update_dataset(
            logger,
            before,
            profile,
            dataset,
            schema_analysis,
            agent,
            t,
        )
    assert updated == before.add_or_update_dataset(
        dataset,
        DatasetDocumentation(
            frontmatter=TableFrontmatter(
                schema_hash="123",
                columns=[],
            ),
            summary="summary",
        ),
    )
