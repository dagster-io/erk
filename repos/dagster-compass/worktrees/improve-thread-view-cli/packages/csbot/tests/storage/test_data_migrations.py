"""Tests for data migration operations."""

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest

if TYPE_CHECKING:
    from csbot.slackbot.storage.data_migrations import DataMigration

from csbot.slackbot.storage.data_migrations import (
    CreateProspectorOrgContextstoreRepos,
    MigrationRunner,
    PopulateBotToConnections,
    PopulateProspectorConnectionsDataDocRepo,
)


class TestPopulateBotToConnections:
    """Test suite for PopulateBotToConnections data migration."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database with test schema."""
        temp_dir = TemporaryDirectory()
        path = Path(temp_dir.name) / "test.sqlite"
        conn = sqlite3.connect(path)

        # Create required tables
        cursor = conn.cursor()

        # Organizations table
        cursor.execute("""
            CREATE TABLE organizations (
                organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_name TEXT NOT NULL,
                organization_industry TEXT,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT
            )
        """)

        # Bot instances table
        cursor.execute("""
            CREATE TABLE bot_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT NOT NULL,
                organization_name TEXT,
                organization_id INTEGER,
                slack_team_id TEXT NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
            )
        """)

        # Connections table
        cursor.execute("""
            CREATE TABLE connections (
                connection_name TEXT NOT NULL,
                bot_instance_id INTEGER NOT NULL,
                organization_id INTEGER,
                connection_type TEXT,
                FOREIGN KEY (bot_instance_id) REFERENCES bot_instances(id),
                FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
            )
        """)

        # Bot to connections table
        cursor.execute("""
            CREATE TABLE bot_to_connections (
                organization_id INTEGER NOT NULL,
                bot_id TEXT NOT NULL,
                connection_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (organization_id, bot_id, connection_name),
                FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
            )
        """)

        conn.commit()
        yield conn
        conn.close()
        temp_dir.cleanup()

    def test_is_needed_empty_bot_to_connections_table(self, temp_db):
        """Test migration is needed when bot_to_connections is empty but connections exist."""
        cursor = temp_db.cursor()

        # Insert test data
        cursor.execute(
            "INSERT INTO organizations (organization_name, organization_industry) VALUES ('Test Org', 'Tech')"
        )
        org_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO bot_instances (channel_name, organization_id, slack_team_id) VALUES ('test-channel', ?, 'T123456')",
            (org_id,),
        )
        bot_instance_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO connections (connection_name, bot_instance_id, organization_id) VALUES ('test-conn', ?, ?)",
            (bot_instance_id, org_id),
        )
        temp_db.commit()

        # Test migration
        migration = PopulateBotToConnections()
        assert migration.is_needed(temp_db) is True

    def test_is_needed_bot_to_connections_has_data(self, temp_db):
        """Test migration is not needed when bot_to_connections already has data."""
        cursor = temp_db.cursor()

        # Insert test data including bot_to_connections
        cursor.execute(
            "INSERT INTO organizations (organization_name, organization_industry) VALUES ('Test Org', 'Tech')"
        )
        org_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO bot_to_connections (organization_id, bot_id, connection_name) VALUES (?, 'T123456-test-channel', 'test-conn')",
            (org_id,),
        )
        temp_db.commit()

        # Test migration
        migration = PopulateBotToConnections()
        assert migration.is_needed(temp_db) is False

    def test_is_needed_no_connections_to_migrate(self, temp_db):
        """Test migration is not needed when no connections exist."""
        migration = PopulateBotToConnections()
        assert migration.is_needed(temp_db) is False

    def test_apply_creates_bot_to_connections_records(self, temp_db):
        """Test migration creates correct bot_to_connections records."""
        cursor = temp_db.cursor()

        # Insert test data
        cursor.execute(
            "INSERT INTO organizations (organization_name, organization_industry) VALUES ('Test Org 1', 'Tech')"
        )
        org_id_1 = cursor.lastrowid

        cursor.execute(
            "INSERT INTO organizations (organization_name, organization_industry) VALUES ('Test Org 2', 'Finance')"
        )
        org_id_2 = cursor.lastrowid

        # Bot instances with different channel name formats
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, organization_id, slack_team_id) VALUES ('test-channel', ?, 'T123456')",
            (org_id_1,),
        )
        bot_instance_id_1 = cursor.lastrowid

        cursor.execute(
            "INSERT INTO bot_instances (channel_name, organization_id, slack_team_id) VALUES ('data_team', ?, 'T789012')",
            (org_id_2,),
        )
        bot_instance_id_2 = cursor.lastrowid

        # Connections
        cursor.execute(
            "INSERT INTO connections (connection_name, bot_instance_id, organization_id) VALUES ('postgres-prod', ?, ?)",
            (bot_instance_id_1, org_id_1),
        )

        cursor.execute(
            "INSERT INTO connections (connection_name, bot_instance_id, organization_id) VALUES ('mysql-analytics', ?, ?)",
            (bot_instance_id_1, org_id_1),
        )

        cursor.execute(
            "INSERT INTO connections (connection_name, bot_instance_id, organization_id) VALUES ('snowflake-main', ?, ?)",
            (bot_instance_id_2, org_id_2),
        )

        temp_db.commit()

        # Apply migration
        migration = PopulateBotToConnections()
        migration.apply(temp_db)

        # Verify bot_to_connections records were created
        cursor.execute(
            "SELECT organization_id, bot_id, connection_name FROM bot_to_connections ORDER BY organization_id, connection_name"
        )
        results = cursor.fetchall()

        expected_results = [
            (org_id_1, "T123456-test-channel", "mysql-analytics"),
            (org_id_1, "T123456-test-channel", "postgres-prod"),
            (org_id_2, "T789012-data_team", "snowflake-main"),
        ]

        assert results == expected_results

    def test_apply_handles_channel_name_normalization(self, temp_db):
        """Test migration properly normalizes channel names in bot_id construction."""
        cursor = temp_db.cursor()

        # Insert test data with channel names that need normalization
        cursor.execute(
            "INSERT INTO organizations (organization_name, organization_industry) VALUES ('Test Org', 'Tech')"
        )
        org_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO bot_instances (channel_name, organization_id, slack_team_id) VALUES ('Test-Channel-Name', ?, 'T123456')",
            (org_id,),
        )
        bot_instance_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO connections (connection_name, bot_instance_id, organization_id) VALUES ('test-conn', ?, ?)",
            (bot_instance_id, org_id),
        )

        temp_db.commit()

        # Apply migration
        migration = PopulateBotToConnections()
        migration.apply(temp_db)

        # Verify the bot_id uses normalized channel name
        cursor.execute("SELECT bot_id FROM bot_to_connections")
        result = cursor.fetchone()

        # The normalize_channel_name function should convert to lowercase
        assert result[0] == "T123456-test-channel-name"

    def test_apply_skips_connections_without_organization_id(self, temp_db):
        """Test migration skips connections that don't have organization_id."""
        cursor = temp_db.cursor()

        # Insert test data
        cursor.execute(
            "INSERT INTO organizations (organization_name, organization_industry) VALUES ('Test Org', 'Tech')"
        )
        org_id = cursor.lastrowid

        # Bot instance without organization_id
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, slack_team_id) VALUES ('orphan-channel', 'T123456')"
        )
        orphan_bot_instance_id = cursor.lastrowid

        # Bot instance with organization_id
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, organization_id, slack_team_id) VALUES ('valid-channel', ?, 'T789012')",
            (org_id,),
        )
        valid_bot_instance_id = cursor.lastrowid

        # Connections - one orphaned, one valid
        cursor.execute(
            "INSERT INTO connections (connection_name, bot_instance_id) VALUES ('orphan-conn', ?)",
            (orphan_bot_instance_id,),
        )

        cursor.execute(
            "INSERT INTO connections (connection_name, bot_instance_id, organization_id) VALUES ('valid-conn', ?, ?)",
            (valid_bot_instance_id, org_id),
        )

        temp_db.commit()

        # Apply migration
        migration = PopulateBotToConnections()
        migration.apply(temp_db)

        # Verify only the valid connection was migrated
        cursor.execute("SELECT organization_id, bot_id, connection_name FROM bot_to_connections")
        results = cursor.fetchall()

        assert len(results) == 1
        assert results[0] == (org_id, "T789012-valid-channel", "valid-conn")

    def test_migration_properties(self):
        """Test migration metadata properties."""
        migration = PopulateBotToConnections()

        assert migration.name == "populate_bot_to_connections"
        assert (
            migration.description == "Populate bot_to_connections table from existing connections"
        )

    def test_sqlite_vs_postgresql_query_handling(self, temp_db):
        """Test that migration handles SQLite-specific query syntax."""
        cursor = temp_db.cursor()

        # Insert minimal test data
        cursor.execute(
            "INSERT INTO organizations (organization_name, organization_industry) VALUES ('Test Org', 'Tech')"
        )
        org_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO bot_instances (channel_name, organization_id, slack_team_id) VALUES ('test-channel', ?, 'T123456')",
            (org_id,),
        )
        bot_instance_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO connections (connection_name, bot_instance_id, organization_id) VALUES ('test-conn', ?, ?)",
            (bot_instance_id, org_id),
        )

        temp_db.commit()

        # Apply migration (should use SQLite path)
        migration = PopulateBotToConnections()
        migration.apply(temp_db)  # Should not raise any exceptions

        # Verify record was created
        cursor.execute("SELECT COUNT(*) FROM bot_to_connections")
        assert cursor.fetchone()[0] == 1


class TestMigrationRunner:
    """Test suite for MigrationRunner."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_conn.commit = Mock()
        mock_conn.rollback = Mock()
        return mock_conn

    def test_run_migration_not_needed(self, mock_connection):
        """Test running migration that is not needed."""
        # Create a mock migration that says it's not needed
        mock_migration = Mock()
        mock_migration.is_needed.return_value = False
        mock_migration.name = "test_migration"

        runner = MigrationRunner(mock_connection)
        result = runner.run_migration(mock_migration)

        assert result is False
        mock_migration.is_needed.assert_called_once_with(mock_connection)
        mock_migration.apply.assert_not_called()
        mock_connection.commit.assert_not_called()

    def test_run_migration_needed_and_applied(self, mock_connection):
        """Test running migration that is needed and successfully applied."""
        # Create a mock migration that needs to be applied
        mock_migration = Mock()
        mock_migration.is_needed.return_value = True
        mock_migration.name = "test_migration"

        runner = MigrationRunner(mock_connection)
        result = runner.run_migration(mock_migration)

        assert result is True
        mock_migration.is_needed.assert_called_once_with(mock_connection)
        mock_migration.apply.assert_called_once_with(mock_connection, None)
        mock_connection.commit.assert_called_once()

    def test_run_migration_dry_run_needed(self, mock_connection):
        """Test dry run for migration that would be applied."""
        # Create a mock migration that says it's needed
        mock_migration = Mock()
        mock_migration.is_needed.return_value = True
        mock_migration.name = "test_migration"

        runner = MigrationRunner(mock_connection)
        result = runner.run_migration(mock_migration, dry_run=True)

        assert result is True
        mock_migration.is_needed.assert_called_once_with(mock_connection)
        mock_migration.apply.assert_not_called()  # Should not apply in dry run
        mock_connection.commit.assert_not_called()

    def test_run_migration_dry_run_not_needed(self, mock_connection):
        """Test dry run for migration that is not needed."""
        # Create a mock migration that says it's not needed
        mock_migration = Mock()
        mock_migration.is_needed.return_value = False
        mock_migration.name = "test_migration"

        runner = MigrationRunner(mock_connection)
        result = runner.run_migration(mock_migration, dry_run=True)

        assert result is False
        mock_migration.is_needed.assert_called_once_with(mock_connection)
        mock_migration.apply.assert_not_called()

    def test_run_migration_with_exception_rollsback(self, mock_connection):
        """Test that migration failures trigger rollback."""
        # Create a mock migration that raises an exception during apply
        mock_migration = Mock()
        mock_migration.is_needed.return_value = True
        mock_migration.apply.side_effect = Exception("Migration failed")
        mock_migration.name = "failing_migration"

        runner = MigrationRunner(mock_connection)

        with pytest.raises(Exception, match="Migration failed"):
            runner.run_migration(mock_migration)

        mock_connection.rollback.assert_called_once()
        mock_connection.commit.assert_not_called()

    def test_run_migrations_multiple(self, mock_connection):
        """Test running multiple migrations."""
        # Create mock migrations with different needs
        migration1 = Mock()
        migration1.is_needed.return_value = True
        migration1.name = "migration1"

        migration2 = Mock()
        migration2.is_needed.return_value = False
        migration2.name = "migration2"

        migration3 = Mock()
        migration3.is_needed.return_value = True
        migration3.name = "migration3"

        migrations = cast("list[DataMigration]", [migration1, migration2, migration3])

        runner = MigrationRunner(mock_connection)
        results = runner.run_migrations(migrations)

        expected_results = {
            "migration1": True,
            "migration2": False,
            "migration3": True,
        }

        assert results == expected_results

        # Verify apply was called for needed migrations
        migration1.apply.assert_called_once_with(mock_connection, None)
        migration2.apply.assert_not_called()
        migration3.apply.assert_called_once_with(mock_connection, None)

    def test_get_all_migrations_returns_correct_order(self):
        """Test that get_all_migrations returns migrations in dependency order."""
        migrations = MigrationRunner.get_all_migrations()

        # Verify we get the expected migrations in the right order
        migration_names = [m.name for m in migrations]
        expected_names = [
            "populate_organizations_from_bot_instances",
            "populate_connections_organization_id",
            "populate_bot_to_connections",
            "populate_organization_contextstore_repo",
            "populate_prospector_connections_data_doc_repo",
            "create_prospector_org_contextstore_repos",
        ]

        assert migration_names == expected_names

        # Verify they are all DataMigration instances
        for migration in migrations:
            assert hasattr(migration, "is_needed")
            assert hasattr(migration, "apply")
            assert hasattr(migration, "name")
            assert hasattr(migration, "description")


class TestPopulateProspectorConnectionsDataDocRepo:
    """Test suite for PopulateProspectorConnectionsDataDocRepo data migration."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database with test schema."""
        temp_dir = TemporaryDirectory()
        path = Path(temp_dir.name) / "test.sqlite"
        conn = sqlite3.connect(path)

        cursor = conn.cursor()

        # Organizations table
        cursor.execute("""
            CREATE TABLE organizations (
                organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_name TEXT NOT NULL,
                contextstore_github_repo TEXT
            )
        """)

        # Bot instances table with instance_type
        cursor.execute("""
            CREATE TABLE bot_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT NOT NULL,
                slack_team_id TEXT NOT NULL,
                organization_id INTEGER NOT NULL,
                instance_type TEXT DEFAULT 'standard',
                FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
            )
        """)

        # Connections table with data_documentation_contextstore_github_repo
        cursor.execute("""
            CREATE TABLE connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_name TEXT NOT NULL,
                organization_id INTEGER NOT NULL,
                data_documentation_contextstore_github_repo TEXT,
                FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
            )
        """)

        # Bot to connections mapping
        cursor.execute("""
            CREATE TABLE bot_to_connections (
                organization_id INTEGER NOT NULL,
                bot_id TEXT NOT NULL,
                connection_name TEXT NOT NULL,
                PRIMARY KEY (organization_id, bot_id, connection_name)
            )
        """)

        conn.commit()
        yield conn
        conn.close()
        temp_dir.cleanup()

    def test_apply_sets_data_doc_repo_on_prospector_connections(self, temp_db):
        """Test migration sets data_documentation_contextstore_github_repo from org contextstore on prospector connections."""
        cursor = temp_db.cursor()

        # Create prospector org with contextstore repo
        cursor.execute(
            "INSERT INTO organizations (organization_name, contextstore_github_repo) VALUES ('Prospector Org', 'org/prospector-context')"
        )
        prospector_org_id = cursor.lastrowid

        # Create standard org
        cursor.execute(
            "INSERT INTO organizations (organization_name, contextstore_github_repo) VALUES ('Standard Org', 'org/standard-context')"
        )
        standard_org_id = cursor.lastrowid

        # Create prospector bot instance
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, slack_team_id, organization_id, instance_type) VALUES ('recruiting-channel', 'T789012', ?, 'prospector')",
            (prospector_org_id,),
        )

        # Create community_prospector bot instance
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, slack_team_id, organization_id, instance_type) VALUES ('community-channel', 'T555555', ?, 'community_prospector')",
            (prospector_org_id,),
        )

        # Create standard bot instance
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, slack_team_id, organization_id, instance_type) VALUES ('data-channel', 'T111111', ?, 'standard')",
            (standard_org_id,),
        )

        # Create connections for prospector bots (should be updated)
        cursor.execute(
            "INSERT INTO connections (connection_name, organization_id) VALUES ('prospector-conn1', ?)",
            (prospector_org_id,),
        )
        cursor.execute(
            "INSERT INTO connections (connection_name, organization_id) VALUES ('prospector-conn2', ?)",
            (prospector_org_id,),
        )

        # Create connection for standard bot (should NOT be updated)
        cursor.execute(
            "INSERT INTO connections (connection_name, organization_id) VALUES ('standard-conn', ?)",
            (standard_org_id,),
        )

        # Create bot_to_connections mappings
        cursor.execute(
            "INSERT INTO bot_to_connections (organization_id, bot_id, connection_name) VALUES (?, 'T789012-recruiting-channel', 'prospector-conn1')",
            (prospector_org_id,),
        )
        cursor.execute(
            "INSERT INTO bot_to_connections (organization_id, bot_id, connection_name) VALUES (?, 'T555555-community-channel', 'prospector-conn2')",
            (prospector_org_id,),
        )
        cursor.execute(
            "INSERT INTO bot_to_connections (organization_id, bot_id, connection_name) VALUES (?, 'T111111-data-channel', 'standard-conn')",
            (standard_org_id,),
        )

        temp_db.commit()

        # Apply migration
        migration = PopulateProspectorConnectionsDataDocRepo()
        migration.apply(temp_db)

        # Verify prospector connections were updated with org contextstore
        cursor.execute(
            "SELECT connection_name, data_documentation_contextstore_github_repo FROM connections WHERE organization_id = ? ORDER BY connection_name",
            (prospector_org_id,),
        )
        prospector_results = cursor.fetchall()

        assert len(prospector_results) == 2
        assert prospector_results[0] == ("prospector-conn1", "org/prospector-context")
        assert prospector_results[1] == ("prospector-conn2", "org/prospector-context")

        # Verify standard connection was NOT updated
        cursor.execute(
            "SELECT data_documentation_contextstore_github_repo FROM connections WHERE connection_name = 'standard-conn'"
        )
        standard_result = cursor.fetchone()
        assert standard_result[0] is None


class TestCreateProspectorOrgContextstoreRepos:
    """Test suite for CreateProspectorOrgContextstoreRepos data migration."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database with test schema."""
        temp_dir = TemporaryDirectory()
        path = Path(temp_dir.name) / "test.sqlite"
        conn = sqlite3.connect(path)

        cursor = conn.cursor()

        # Organizations table
        cursor.execute("""
            CREATE TABLE organizations (
                organization_id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_name TEXT NOT NULL,
                contextstore_github_repo TEXT
            )
        """)

        # Bot instances table
        cursor.execute("""
            CREATE TABLE bot_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT NOT NULL,
                slack_team_id TEXT NOT NULL,
                organization_id INTEGER NOT NULL,
                instance_type TEXT DEFAULT 'standard',
                FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
            )
        """)

        # TOS records table
        cursor.execute("""
            CREATE TABLE tos_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        yield conn
        conn.close()
        temp_dir.cleanup()

    def test_apply_requires_bot_config(self, temp_db):
        """Test migration requires bot_config and would create repos for prospector orgs without contextstore."""
        cursor = temp_db.cursor()

        # Create prospector org without contextstore repo (should need migration)
        cursor.execute("INSERT INTO organizations (organization_name) VALUES ('Prospector Org')")
        prospector_org_id = cursor.lastrowid

        # Create standard org without contextstore repo (should NOT get contextstore)
        cursor.execute("INSERT INTO organizations (organization_name) VALUES ('Standard Org')")
        standard_org_id = cursor.lastrowid

        # Create prospector org WITH contextstore repo (should be skipped)
        cursor.execute(
            "INSERT INTO organizations (organization_name, contextstore_github_repo) VALUES ('Existing Prospector', 'org/existing-context')"
        )
        existing_prospector_org_id = cursor.lastrowid

        # Create bot instances
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, slack_team_id, organization_id, instance_type) VALUES ('recruiting', 'T123456', ?, 'prospector')",
            (prospector_org_id,),
        )
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, slack_team_id, organization_id, instance_type) VALUES ('data-team', 'T789012', ?, 'standard')",
            (standard_org_id,),
        )
        cursor.execute(
            "INSERT INTO bot_instances (channel_name, slack_team_id, organization_id, instance_type) VALUES ('old-recruiting', 'T555555', ?, 'prospector')",
            (existing_prospector_org_id,),
        )

        temp_db.commit()

        migration = CreateProspectorOrgContextstoreRepos()

        # Test that migration is needed for prospector org without contextstore
        assert migration.is_needed(temp_db) is True

        # Test that migration requires bot_config
        with pytest.raises(Exception, match="bot_config is required"):
            migration.apply(temp_db, bot_config=None)
