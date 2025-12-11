"""Unit tests for dataset_documentation module - lightweight tests without I/O."""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from csbot.contextengine.contextstore_protocol import Dataset
from csbot.contextengine.loader import _parse_frontmatter_and_summary
from csbot.ctx_admin.dataset_documentation import (
    ColumnAnalysis,
    ColumnDescription,
    TableAnalysis,
    TableFrontmatter,
    TableSchemaAnalysis,
    add_frontmatter_to_markdown,
    truncate,
    truncate_row,
)
from csbot.local_context_store.git.file_tree import create_git_commit_file_tree


class TestGitCommitFileTree:
    """Test create_git_commit_file_tree function."""

    def test_init_with_invalid_repo(self):
        """Test initialization with invalid repository raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(Exception):
                with create_git_commit_file_tree(Path(temp_dir), f"local:{temp_dir}"):
                    pass


class TestDataModels:
    """Test Pydantic data models."""

    def test_column_analysis_model(self):
        """Test ColumnAnalysis model creation and validation."""
        col = ColumnAnalysis(
            name="test_col",
            type="VARCHAR",
            null_percentage=5.0,
            min="a",
            max="z",
            unique_values=["a", "b", "c"],
            unique_values_count=3,
            is_enum=True,
            enum_values=["a", "b", "c"],
            sample_values=["a", "b"],
            column_comment=None,
        )

        assert col.name == "test_col"
        assert col.type == "VARCHAR"
        assert col.null_percentage == 5.0
        assert col.min == "a"
        assert col.max == "z"
        assert col.unique_values == ["a", "b", "c"]
        assert col.unique_values_count == 3
        assert col.is_enum is True
        assert col.enum_values == ["a", "b", "c"]
        assert col.sample_values == ["a", "b"]

    def test_column_analysis_model_minimal(self):
        """Test ColumnAnalysis model with minimal required fields."""
        col = ColumnAnalysis(
            name="test_col", type="VARCHAR", null_percentage=0.0, column_comment=None
        )

        assert col.name == "test_col"
        assert col.type == "VARCHAR"
        assert col.null_percentage == 0.0
        assert col.min is None
        assert col.max is None
        assert col.unique_values is None
        assert col.unique_values_count is None
        assert col.is_enum is None
        assert col.enum_values is None
        assert col.sample_values is None

    def test_table_frontmatter_model(self):
        """Test TableFrontmatter model creation and validation."""
        frontmatter = TableFrontmatter(
            schema_hash="abc123", columns=["col1 (VARCHAR)", "col2 (INT)"]
        )

        assert frontmatter.schema_hash == "abc123"
        assert frontmatter.columns == ["col1 (VARCHAR)", "col2 (INT)"]

    def test_table_frontmatter_model_minimal(self):
        """Test TableFrontmatter model with minimal required fields."""
        frontmatter = TableFrontmatter(schema_hash="abc123")

        assert frontmatter.schema_hash == "abc123"
        assert frontmatter.columns is None

    def test_table_analysis_model(self):
        """Test TableAnalysis model creation and validation."""
        columns = [
            ColumnAnalysis(name="col1", type="VARCHAR", null_percentage=0.0, column_comment=None),
            ColumnAnalysis(name="col2", type="INT", null_percentage=5.0, column_comment=None),
        ]
        sample_rows = [{"col1": "value1", "col2": 123}, {"col1": "value2", "col2": 456}]

        analysis = TableAnalysis(
            table_name="test_table",
            row_count=1000,
            columns=columns,
            sample_rows=sample_rows,
            table_comment=None,
        )

        assert analysis.table_name == "test_table"
        assert analysis.row_count == 1000
        assert len(analysis.columns) == 2
        assert analysis.columns[0].name == "col1"
        assert analysis.columns[1].name == "col2"
        assert len(analysis.sample_rows) == 2
        assert analysis.sample_rows[0]["col1"] == "value1"

    def test_column_description_model(self):
        """Test ColumnDescription model creation and validation."""
        col_desc = ColumnDescription(name="test_col", type="VARCHAR", column_comment=None)

        assert col_desc.name == "test_col"
        assert col_desc.type == "VARCHAR"

    def test_table_schema_analysis_model(self):
        """Test TableSchemaAnalysis model creation and validation."""
        columns = [
            ColumnDescription(name="col1", type="VARCHAR", column_comment=None),
            ColumnDescription(name="col2", type="INT", column_comment=None),
        ]

        schema_analysis = TableSchemaAnalysis(
            table_name="test_table", columns=columns, schema_hash="abc123", table_comment=None
        )

        assert schema_analysis.table_name == "test_table"
        assert len(schema_analysis.columns) == 2
        assert schema_analysis.columns[0].name == "col1"
        assert schema_analysis.columns[1].name == "col2"
        assert schema_analysis.schema_hash == "abc123"

    def test_dataset_to_reconcile_model(self):
        """Test Dataset model creation and validation."""
        dataset = Dataset(table_name="test_table", connection="test_connection")

        assert dataset.table_name == "test_table"
        assert dataset.connection == "test_connection"


class TestFrontmatterFunctions:
    """Test frontmatter parsing and adding functions."""

    def test_parse_frontmatter_valid(self):
        """Test parsing valid frontmatter from markdown."""
        markdown = """---
schema_hash: abc123
columns:
  - col1 (VARCHAR)
  - col2 (INT)
---
# Table Documentation

This is the content."""

        frontmatter, summary = _parse_frontmatter_and_summary(markdown)

        assert frontmatter is not None
        assert frontmatter.schema_hash == "abc123"
        assert frontmatter.columns == ["col1 (VARCHAR)", "col2 (INT)"]
        assert summary == "# Table Documentation\n\nThis is the content."

    def test_parse_frontmatter_minimal(self):
        """Test parsing minimal frontmatter from markdown."""
        markdown = """---
schema_hash: abc123
---
# Table Documentation

This is the content."""

        frontmatter, summary = _parse_frontmatter_and_summary(markdown)

        assert frontmatter is not None
        assert frontmatter.schema_hash == "abc123"
        assert frontmatter.columns is None
        assert summary == "# Table Documentation\n\nThis is the content."

    def test_parse_frontmatter_no_frontmatter(self):
        """Test parsing markdown with no frontmatter returns None."""
        markdown = """# Table Documentation

This is the content without frontmatter."""

        frontmatter, summary = _parse_frontmatter_and_summary(markdown)

        assert frontmatter is None
        assert summary == markdown

    def test_parse_frontmatter_invalid_yaml(self):
        """Test parsing markdown with invalid YAML frontmatter."""
        markdown = """---
schema_hash: abc123
columns:
  - col1 (VARCHAR
  - col2 (INT)
invalid_syntax: [unclosed bracket
---
# Table Documentation

This is the content."""

        with pytest.raises(yaml.YAMLError):
            _parse_frontmatter_and_summary(markdown)

    def test_add_frontmatter_to_markdown_success(self):
        """Test adding frontmatter to markdown successfully."""
        markdown = "# Table Documentation\n\nThis is the content."
        frontmatter = TableFrontmatter(
            schema_hash="abc123", columns=["col1 (VARCHAR)", "col2 (INT)"]
        )

        result = add_frontmatter_to_markdown(markdown, frontmatter)

        assert result.startswith("---\n")
        assert "schema_hash: abc123" in result
        assert "columns:" in result
        assert "- col1 (VARCHAR)" in result
        assert "- col2 (INT)" in result
        assert result.endswith("---\n# Table Documentation\n\nThis is the content.")

    def test_add_frontmatter_to_markdown_already_exists(self):
        """Test adding frontmatter to markdown that already has frontmatter raises ValueError."""
        markdown = """---
existing: frontmatter
---
# Table Documentation

This is the content."""
        frontmatter = TableFrontmatter(schema_hash="abc123")

        with pytest.raises(ValueError, match="Frontmatter already exists"):
            add_frontmatter_to_markdown(markdown, frontmatter)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_truncate_short_string(self):
        """Test truncate with string shorter than limit."""
        result = truncate("hello", 10)
        assert result == "hello"

    def test_truncate_long_string(self):
        """Test truncate with string longer than limit."""
        result = truncate("hello world this is a long string", 10)
        assert result == "hello worl... (truncated)"

    def test_truncate_exact_length(self):
        """Test truncate with string exactly at limit."""
        result = truncate("hello", 5)
        assert result == "hello"

    def test_truncate_row_with_strings(self):
        """Test truncate_row with dictionary containing strings."""
        row = {
            "short": "hello",
            "long": "this is a very long string that should be truncated",
            "number": 123,
            "none_value": None,
        }

        result = truncate_row(row, 10)

        assert result["short"] == "hello"
        assert result["long"] == "this is a ... (truncated)"
        assert result["number"] == 123
        assert result["none_value"] is None

    def test_truncate_row_no_strings(self):
        """Test truncate_row with dictionary containing no strings."""
        row = {"number": 123, "float": 45.67, "bool": True, "none_value": None}

        result = truncate_row(row, 10)

        assert result == row  # Should be unchanged


class TestAnalyzeTableSchemaHashComputation:
    """Test schema hash computation logic without external dependencies."""

    def test_schema_hash_computation(self):
        """Test that schema hash is computed correctly and consistently."""
        columns = [
            ColumnDescription(name="col_b", type="VARCHAR", column_comment=None),
            ColumnDescription(name="col_a", type="INT", column_comment=None),
            ColumnDescription(name="col_c", type="FLOAT", column_comment=None),
        ]

        # Manually compute expected hash
        sorted_columns = sorted(columns, key=lambda x: x.name)
        column_tuples = [(col.name, col.type) for col in sorted_columns]
        expected_hash = hashlib.sha256(
            json.dumps(column_tuples, sort_keys=True).encode()
        ).hexdigest()

        # Create TableSchemaAnalysis with the expected hash
        schema_analysis = TableSchemaAnalysis(
            table_name="test_table", columns=columns, schema_hash=expected_hash, table_comment=None
        )

        assert schema_analysis.schema_hash == expected_hash

        # Verify the hash is deterministic regardless of input order
        columns_different_order = [
            ColumnDescription(name="col_a", type="INT", column_comment=None),
            ColumnDescription(name="col_c", type="FLOAT", column_comment=None),
            ColumnDescription(name="col_b", type="VARCHAR", column_comment=None),
        ]

        sorted_columns_2 = sorted(columns_different_order, key=lambda x: x.name)
        column_tuples_2 = [(col.name, col.type) for col in sorted_columns_2]
        hash_2 = hashlib.sha256(json.dumps(column_tuples_2, sort_keys=True).encode()).hexdigest()

        assert hash_2 == expected_hash


class TestMockingScenarios:
    """Test scenarios using mocks to avoid external dependencies."""

    @patch("csbot.ctx_admin.dataset_documentation.get_sql_client")
    def test_analyze_table_schema_snowflake(self, mock_get_sql_client):
        """Test analyze_table_schema for Snowflake without external dependencies."""
        # Mock SQL client
        mock_sql_client = Mock()
        mock_sql_client.dialect = "snowflake"
        # Mock both column info and table info queries
        mock_sql_client.run_sql_query.side_effect = [
            [  # First call: DESCRIBE TABLE
                {"name": "col1", "type": "VARCHAR", "comment": None},
                {"name": "col2", "type": "NUMBER", "comment": None},
            ],
            [  # Second call: SHOW TABLES for table comment
                {"name": "test_table", "comment": "Test table comment"}
            ],
            [],  # Third call: SHOW VIEWS for view comment
        ]
        mock_get_sql_client.return_value = mock_sql_client

        # Mock inputs
        logger = Mock()
        profile = Mock()
        dataset = Dataset(table_name="test_schema.test_table", connection="test_connection")

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import analyze_table_schema

        result = analyze_table_schema(logger, profile, dataset)

        assert result.table_name == "test_schema.test_table"
        assert len(result.columns) == 2
        assert result.columns[0].name == "col1"
        assert result.columns[0].type == "VARCHAR"
        assert result.columns[1].name == "col2"
        assert result.columns[1].type == "NUMBER"
        assert isinstance(result.schema_hash, str)
        assert len(result.schema_hash) == 64  # SHA256 hex digest length

    @patch("csbot.ctx_admin.dataset_documentation.get_sql_client")
    def test_analyze_table_schema_bigquery(self, mock_get_sql_client):
        """Test analyze_table_schema for BigQuery without external dependencies."""
        # Mock SQL client
        mock_sql_client = Mock()
        mock_sql_client.dialect = "bigquery"
        # Mock both column info and table options queries
        mock_sql_client.run_sql_query.side_effect = [
            [  # First call: column information
                {"column_name": "col1", "data_type": "STRING", "description": None},
                {"column_name": "col2", "data_type": "INTEGER", "description": None},
            ],
            [],  # Second call: table options (empty for no comment)
        ]
        mock_get_sql_client.return_value = mock_sql_client

        # Mock inputs
        logger = Mock()
        profile = Mock()
        dataset = Dataset(table_name="dataset.test_table", connection="test_connection")

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import analyze_table_schema

        result = analyze_table_schema(logger, profile, dataset)

        assert result.table_name == "dataset.test_table"
        assert len(result.columns) == 2
        assert result.columns[0].name == "col1"
        assert result.columns[0].type == "STRING"
        assert result.columns[1].name == "col2"
        assert result.columns[1].type == "INTEGER"
        assert isinstance(result.schema_hash, str)

    @patch("csbot.ctx_admin.dataset_documentation.get_sql_client")
    def test_analyze_table_schema_duckdb(self, mock_get_sql_client):
        """Test analyze_table_schema for DuckDB without external dependencies."""
        # Mock SQL client
        mock_sql_client = Mock()
        mock_sql_client.dialect = "duckdb"
        # Mock both column info and table comment queries
        mock_sql_client.run_sql_query.side_effect = [
            [  # First call: column information
                {"column_name": "col1", "data_type": "VARCHAR", "comment": None},
                {"column_name": "col2", "data_type": "INTEGER", "comment": None},
            ],
            [],  # Second call: table comment (empty for no comment)
        ]
        mock_get_sql_client.return_value = mock_sql_client

        # Mock inputs
        logger = Mock()
        profile = Mock()
        dataset = Dataset(table_name="test_table", connection="test_connection")

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import analyze_table_schema

        result = analyze_table_schema(logger, profile, dataset)

        assert result.table_name == "test_table"
        assert len(result.columns) == 2
        assert result.columns[0].name == "col1"
        assert result.columns[0].type == "VARCHAR"
        assert result.columns[1].name == "col2"
        assert result.columns[1].type == "INTEGER"
        assert isinstance(result.schema_hash, str)

    @patch("csbot.ctx_admin.dataset_documentation.get_sql_client")
    def test_analyze_table_schema_unsupported_dialect(self, mock_get_sql_client):
        """Test analyze_table_schema with unsupported dialect raises ValueError."""
        # Mock SQL client with unsupported dialect
        mock_sql_client = Mock()
        mock_sql_client.dialect = "mysql"
        mock_get_sql_client.return_value = mock_sql_client

        # Mock inputs
        logger = Mock()
        profile = Mock()
        dataset = Dataset(table_name="test_table", connection="test_connection")

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import analyze_table_schema

        with pytest.raises(ValueError, match="Unsupported dialect: mysql"):
            analyze_table_schema(logger, profile, dataset)

    @patch("csbot.ctx_admin.dataset_documentation.get_sql_client")
    def test_analyze_table_schema_no_columns_found(self, mock_get_sql_client):
        """Test analyze_table_schema when no columns are found raises ValueError."""
        # Mock SQL client returning empty result
        mock_sql_client = Mock()
        mock_sql_client.dialect = "snowflake"
        mock_sql_client.run_sql_query.return_value = []
        mock_get_sql_client.return_value = mock_sql_client

        # Mock inputs
        logger = Mock()
        profile = Mock()
        dataset = Dataset(table_name="test_schema.test_table", connection="test_connection")

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import analyze_table_schema

        with pytest.raises(ValueError, match="No columns found for test_schema.test_table"):
            analyze_table_schema(logger, profile, dataset)

    def test_list_bigquery_table_names_unsupported_dialect(self):
        """Test list_bigquery_table_names with unsupported dialect raises ValueError."""
        # Mock SQL client with unsupported dialect
        mock_sql_client = Mock()
        mock_sql_client.dialect = "snowflake"

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import list_bigquery_table_names

        with pytest.raises(ValueError, match="list_bigquery_table_names only supports BigQuery"):
            list_bigquery_table_names(mock_sql_client, ["dataset1"])

    def test_list_bigquery_table_names_success(self):
        """Test list_bigquery_table_names with successful execution."""
        # Mock SQL client
        mock_sql_client = Mock()
        mock_sql_client.dialect = "bigquery"
        mock_sql_client.run_sql_query.return_value = [
            {"table_name": "table1", "comment": None},
            {"table_name": "table2", "comment": None},
        ]

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import list_bigquery_table_names

        result = list_bigquery_table_names(mock_sql_client, ["dataset1"])

        assert result == ["dataset1.table1", "dataset1.table2"]
        mock_sql_client.run_sql_query.assert_called_once()

    def test_has_recent_data_activity_unsupported_dialect(self):
        """Test has_recent_data_activity with unsupported dialect raises ValueError."""
        # Mock SQL client with unsupported dialect
        mock_sql_client = Mock()
        mock_sql_client.dialect = "snowflake"

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import has_recent_data_activity

        with pytest.raises(ValueError, match="has_recent_data_activity only supports BigQuery"):
            has_recent_data_activity(mock_sql_client, "dataset.table")

    def test_has_recent_data_activity_no_date_columns(self):
        """Test has_recent_data_activity when no date columns are found."""
        # Mock SQL client
        mock_sql_client = Mock()
        mock_sql_client.dialect = "bigquery"
        mock_sql_client.run_sql_query.return_value = []

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import has_recent_data_activity

        result = has_recent_data_activity(mock_sql_client, "dataset.table")

        assert result is True  # Returns True when no date columns found

    def test_has_recent_data_activity_with_recent_data(self):
        """Test has_recent_data_activity when recent data is found."""
        # Mock SQL client
        mock_sql_client = Mock()
        mock_sql_client.dialect = "bigquery"

        # Mock the calls in sequence
        mock_sql_client.run_sql_query.side_effect = [
            [{"column_name": "created_at", "data_type": "TIMESTAMP"}],  # Columns query
            [{"recent_count": 5}],  # Recent data check query
        ]

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import has_recent_data_activity

        result = has_recent_data_activity(mock_sql_client, "dataset.table")

        assert result is True
        assert mock_sql_client.run_sql_query.call_count == 2

    def test_has_recent_data_activity_no_recent_data(self):
        """Test has_recent_data_activity when no recent data is found."""
        # Mock SQL client
        mock_sql_client = Mock()
        mock_sql_client.dialect = "bigquery"

        # Mock the calls in sequence
        mock_sql_client.run_sql_query.side_effect = [
            [{"column_name": "created_at", "data_type": "TIMESTAMP"}],  # Columns query
            [{"recent_count": 0}],  # Recent data check query
        ]

        # Import the function to test
        from csbot.ctx_admin.dataset_documentation import has_recent_data_activity

        result = has_recent_data_activity(mock_sql_client, "dataset.table")

        assert result is False
        assert mock_sql_client.run_sql_query.call_count == 2
