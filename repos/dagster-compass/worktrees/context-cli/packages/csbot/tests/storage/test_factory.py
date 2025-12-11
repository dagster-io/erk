import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from csbot.slackbot.config import DatabaseConfig, UnsupportedKekConfig
from csbot.slackbot.storage.factory import (
    create_connection_factory,
    create_storage_from_uri,
    get_database_type,
)
from csbot.slackbot.storage.postgresql import PostgresqlConnectionFactory, SlackbotPostgresqlStorage
from csbot.slackbot.storage.sqlite import SlackbotSqliteStorage, SqliteConnectionFactory


class TestCreateConnectionFactory:
    """Test the create_connection_factory function with various URI schemes."""

    @pytest.fixture
    def temp_db_file(self):
        """Create a temporary SQLite database file for testing."""
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)  # Close the file descriptor, keep the file
        yield path
        os.unlink(path)  # Clean up after test

    def test_creates_postgresql_factory_type(self, monkeypatch):
        """Test that PostgreSQL factory is created for postgresql:// URIs."""
        # Mock the PostgresqlConnectionFactory.from_database_url to avoid needing real DB
        mock_factory = Mock(spec=PostgresqlConnectionFactory)

        def mock_from_db_config(cls, config, time_provider=None):
            return mock_factory

        monkeypatch.setattr(
            PostgresqlConnectionFactory, "from_db_config", classmethod(mock_from_db_config)
        )

        factory = create_connection_factory(
            DatabaseConfig(database_uri="postgresql://user:pass@host:5432/db")
        )
        assert factory == mock_factory

    @pytest.mark.parametrize(
        "sqlite_uri,expected_path",
        [
            ("sqlite:///path/to/db.sqlite", "path/to/db.sqlite"),  # triple slash removes one slash
            ("sqlite://path/to/db.sqlite", "path/to/db.sqlite"),  # double slash keeps path as-is
            (
                "sqlite:///absolute/path/with spaces/db.sqlite",
                "absolute/path/with spaces/db.sqlite",
            ),
            ("/absolute/path.sqlite", "/absolute/path.sqlite"),
            ("relative/path.sqlite", "relative/path.sqlite"),
        ],
    )
    def test_sqlite_path_handling(self, sqlite_uri, expected_path, monkeypatch):
        """Test that SQLite URIs are properly converted to file paths."""
        captured_path = None

        def mocked_connect(db_path):
            nonlocal captured_path
            captured_path = db_path
            return Mock()

        with (
            patch(
                "csbot.slackbot.storage.sqlite.sqlite3",
            ) as sqlite3,
            patch("csbot.slackbot.storage.sqlite.SqliteConnectionFactory._initialize_database"),
        ):
            sqlite3.connect.side_effect = mocked_connect

            conn_factory = create_connection_factory(DatabaseConfig(database_uri=sqlite_uri))
            with conn_factory.with_conn():
                pass

        assert captured_path == expected_path


class TestCreateStorage:
    """Test the create_storage function with various URI schemes."""

    @pytest.mark.parametrize(
        "database_uri,expected_storage_type",
        [
            ("postgresql://user:pass@host:5432/db", SlackbotPostgresqlStorage),
            ("sqlite:///path/to/db.sqlite", SlackbotSqliteStorage),
            ("sqlite://path/to/db.sqlite", SlackbotSqliteStorage),
            ("/absolute/path/to/db.sqlite", SlackbotSqliteStorage),
            ("relative/path/to/db.sqlite", SlackbotSqliteStorage),
            ("db.sqlite", SlackbotSqliteStorage),
        ],
    )
    def test_creates_correct_storage_type(self, database_uri, expected_storage_type):
        """Test that the correct storage type is returned based on URI scheme."""
        # Create appropriate mock factory based on expected storage type
        if expected_storage_type == SlackbotPostgresqlStorage:
            mock_factory = Mock(spec=PostgresqlConnectionFactory)
        else:
            mock_factory = Mock(spec=SqliteConnectionFactory)

        with patch(
            "csbot.slackbot.storage.factory.create_connection_factory", return_value=mock_factory
        ):
            storage = create_storage_from_uri(
                database_uri, UnsupportedKekConfig(), seed_database_from=None
            )
            assert isinstance(storage, expected_storage_type)


class TestGetDatabaseType:
    """Test the get_database_type function with various URI schemes."""

    @pytest.mark.parametrize(
        "database_uri,expected_type",
        [
            ("postgresql://user:pass@host:5432/db", "postgresql"),
            ("postgresql://localhost/test", "postgresql"),
            ("sqlite:///path/to/db.sqlite", "sqlite"),
            ("sqlite://path/to/db.sqlite", "sqlite"),
            ("sqlite:///tmp/test.db", "sqlite"),
            ("/absolute/path/to/db.sqlite", "sqlite"),
            ("relative/path/to/db.sqlite", "sqlite"),
            ("db.sqlite", "sqlite"),
            ("test.db", "sqlite"),
            ("", "sqlite"),  # Empty string defaults to sqlite
            ("invalid://scheme", "sqlite"),  # Unknown schemes default to sqlite
            ("mysql://host/db", "sqlite"),  # Unsupported schemes default to sqlite
        ],
    )
    def test_returns_correct_database_type(self, database_uri, expected_type):
        """Test that the correct database type is returned for various URIs."""
        result = get_database_type(database_uri)
        assert result == expected_type

    def test_case_sensitivity(self):
        """Test that scheme comparison handles case correctly (urlparse normalizes to lowercase)."""
        # Standard lowercase schemes should work
        assert get_database_type("postgresql://host/db") == "postgresql"
        assert get_database_type("sqlite:///path/db") == "sqlite"

        # urlparse normalizes schemes to lowercase, so these should work too
        assert get_database_type("POSTGRESQL://host/db") == "postgresql"
        assert get_database_type("SQLITE:///path/db") == "sqlite"
