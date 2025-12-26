import asyncio
import base64
import json
import os
from typing import Any

import pytest
from cryptography.fernet import Fernet
from testcontainers.postgres import PostgresContainer

from csbot.config.database_instance_loader import DatabaseBotInstanceLoader
from csbot.slackbot.config import DatabaseConfig, UnsupportedKekConfig
from csbot.slackbot.storage.factory import create_storage as base_create_storage
from csbot.slackbot.storage.interface import SqlConnectionFactory
from csbot.slackbot.storage.postgresql import PostgresqlConnectionFactory
from csbot.slackbot.storage.schema_changes import SchemaManager

pytest_plugins = ("pytest_asyncio",)

# Skip all tests if psycopg is not available
psycopg = pytest.importorskip("psycopg")


def create_storage(conn_factory: SqlConnectionFactory):
    return base_create_storage(conn_factory, UnsupportedKekConfig())


@pytest.fixture(scope="session")
def encryption_setup():
    """Set up encryption key for all tests in this session."""
    # Generate a test encryption key
    key = Fernet.generate_key()
    encoded_key = base64.urlsafe_b64encode(key).decode()

    # Set the environment variable
    os.environ["SECRET_ENCRYPTION_KEY"] = encoded_key

    # Create a Fernet instance for tests to use
    fernet = Fernet(key)

    yield fernet

    # Clean up
    if "SECRET_ENCRYPTION_KEY" in os.environ:
        del os.environ["SECRET_ENCRYPTION_KEY"]


@pytest.fixture
def encrypted_tokens(encryption_setup):
    """Create encrypted tokens for testing."""
    fernet = encryption_setup

    tokens = {
        "SLACK_BOT_TOKEN_T1234567890": fernet.encrypt(b"xoxb-test-token-123").decode(),
        "SLACK_BOT_TOKEN_T1111111111": fernet.encrypt(b"xoxb-test-token-111").decode(),
        "SLACK_BOT_TOKEN_T2222222222": fernet.encrypt(b"xoxb-test-token-222").decode(),
    }

    # Set the encrypted tokens as environment variables
    for env_var, encrypted_value in tokens.items():
        os.environ[env_var] = encrypted_value

    yield tokens

    # Clean up
    for env_var in tokens:
        if env_var in os.environ:
            del os.environ[env_var]


@pytest.fixture(scope="session")
def postgres_container():
    """Session-scoped PostgreSQL container for testing."""
    # Use environment variable if available (for CI/CD environments)
    if test_db_url := os.environ.get("TEST_DATABASE_URL"):
        if test_db_url.startswith("postgresql://"):
            yield test_db_url
            return

    # Otherwise, spin up a test container
    with PostgresContainer(
        image="public.ecr.aws/docker/library/postgres:16-alpine3.21",
        username="test",
        password="test",
        dbname="test_db",
        driver="psycopg",
    ) as postgres:
        database_url = postgres.get_connection_url()
        # Set environment variable for any code that might need it
        os.environ["TEST_DATABASE_URL"] = database_url
        yield database_url


@pytest.fixture
def sql_conn_factory(postgres_container):
    """Create a PostgreSQL connection factory for testing."""
    database_url = postgres_container
    return PostgresqlConnectionFactory.from_db_config(DatabaseConfig.from_uri(database_url))


@pytest.fixture
def test_schema(sql_conn_factory):
    """Create test schema using SchemaManager for DatabaseBotInstanceLoader testing."""
    with sql_conn_factory.with_conn() as conn:
        # Apply all schema changes using the SchemaManager
        schema_manager = SchemaManager()
        schema_manager.apply_all_changes(conn)
        conn.commit()

        yield

        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
        conn.commit()


class TestDatabaseBotInstanceLoader:
    """Test suite for DatabaseBotInstanceLoader."""

    @staticmethod
    def _create_mock_get_template_context_for_org(template_context: dict[str, Any]):
        """Create a mock function that returns the provided template context plus org_id."""

        def mock_get_template_context_for_org(org_id: int) -> dict[str, Any]:
            return {**template_context, "org_id": org_id}

        return mock_get_template_context_for_org

    def test_init(self, sql_conn_factory):
        """Test DatabaseBotInstanceLoader initialization."""
        template_context = {"env": "test", "api_key": "secret123"}
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        assert loader._storage == storage
        assert loader._template_context == template_context

    @pytest.mark.asyncio
    async def test_load_bot_instances_empty_database(self, sql_conn_factory, test_schema):
        """Test loading bot instances from empty database returns empty dict."""
        template_context = {"env": "test"}
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        result = await loader.load_bot_instances()

        assert result == {}

    def test_load_bot_instances_single_bot_minimal(
        self, sql_conn_factory, test_schema, encrypted_tokens
    ):
        """Test loading a single bot instance with minimal configuration."""

        # Insert test data
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organization first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology", "user/repo"),
            )
            org_id = cursor.fetchone()[0]

            # Insert bot token first
            cursor.execute(
                """
                INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name)
                VALUES (%s, %s)
            """,
                ("T1234567890", "SLACK_BOT_TOKEN_T1234567890"),
            )

            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s)
            """,
                (
                    "test-channel",
                    "bot@example.com",
                    "alerts-channel",
                    "T1234567890",
                    org_id,
                ),
            )
            conn.commit()

        template_context = {"env": "test"}
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        result = asyncio.run(loader.load_bot_instances())

        assert len(result) == 1
        assert "T1234567890-test-channel" in result

        bot_config = result["T1234567890-test-channel"]
        assert bot_config.bot_email == "bot@example.com"
        assert bot_config.contextstore_github_repo == "user/repo"
        assert bot_config.governance_alerts_channel == "alerts-channel"
        assert bot_config.connections == {}

    def test_load_bot_instances_with_connections(
        self, sql_conn_factory, test_schema, encrypted_tokens
    ):
        """Test loading bot instances with database connections."""

        # Insert test data
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organization first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology", "user/repo"),
            )
            org_id = cursor.fetchone()[0]

            # Insert bot token first
            cursor.execute(
                """
                INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name)
                VALUES (%s, %s)
            """,
                ("T1234567890", "SLACK_BOT_TOKEN_T1234567890"),
            )

            # Insert bot instance
            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
                (
                    "test-channel",
                    "bot@example.com",
                    "alerts-channel",
                    "T1234567890",
                    org_id,
                ),
            )
            _ = cursor.fetchone()[0]  # bot_instance_id no longer needed

            # Insert connections (using organization_id instead of bot_instance_id)
            cursor.execute(
                """
                INSERT INTO connections (organization_id, connection_name, url, init_sql)
                VALUES (%s, %s, %s, %s)
            """,
                (
                    org_id,
                    "prod_db",
                    "postgresql://user:pass@host:5432/db",
                    '["SET search_path = public;"]',
                ),
            )

            cursor.execute(
                """
                INSERT INTO connections (organization_id, connection_name, url, init_sql)
                VALUES (%s, %s, %s, %s)
            """,
                (org_id, "warehouse", "bigquery://project/dataset", '["SELECT 1;", "SELECT 2;"]'),
            )

            # Create bot_to_connections mappings
            # Construct bot_id using the same logic as BotKey.to_bot_id()
            from csbot.utils.misc import normalize_channel_name

            normalized_channel_name = normalize_channel_name("test-channel")
            bot_id_str = f"T1234567890-{normalized_channel_name}"

            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
            """,
                (org_id, bot_id_str, "prod_db"),
            )

            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
            """,
                (org_id, bot_id_str, "warehouse"),
            )

            conn.commit()

        template_context = {"env": "production"}
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        result = asyncio.run(loader.load_bot_instances())

        assert len(result) == 1
        bot_config = result["T1234567890-test-channel"]

        # Check connections
        assert len(bot_config.connections) == 2
        assert "prod_db" in bot_config.connections
        assert "warehouse" in bot_config.connections

        prod_db = bot_config.connections["prod_db"]
        assert prod_db.url == "postgresql://user:pass@host:5432/db"
        assert prod_db.init_sql == ["SET search_path = public;"]

        warehouse = bot_config.connections["warehouse"]
        assert warehouse.url == "bigquery://project/dataset"
        assert warehouse.init_sql == ["SELECT 1;", "SELECT 2;"]

    def test_jinja2_template_processing(self, sql_conn_factory, test_schema, encrypted_tokens):
        """Test Jinja2 template processing for connections and MCP server configurations."""

        # Insert test data with templates
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organization first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology", "user/repo"),
            )
            org_id = cursor.fetchone()[0]

            # Insert bot token first
            cursor.execute(
                """
                INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name)
                VALUES (%s, %s)
            """,
                ("T1234567890", "SLACK_BOT_TOKEN_T1234567890"),
            )

            # Insert bot instance
            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
                (
                    "test-channel",
                    "bot@example.com",
                    "alerts-channel",
                    "T1234567890",
                    org_id,
                ),
            )

            # Insert connection with template variables (using organization_id instead of bot_instance_id)
            cursor.execute(
                """
                INSERT INTO connections (organization_id, connection_name, url, init_sql)
                VALUES (%s, %s, %s, %s)
            """,
                (
                    org_id,
                    "templated_db",
                    "postgresql://{{db_user}}:{{db_password}}@{{db_host}}:5432/{{db_name}}",
                    '["SET search_path = {{schema}};", "SELECT * FROM {{table}};"]',
                ),
            )

            # Create bot_to_connections mapping
            # Construct bot_id using the same logic as BotKey.to_bot_id()
            from csbot.utils.misc import normalize_channel_name

            normalized_channel_name = normalize_channel_name("test-channel")
            bot_id_str = f"T1234567890-{normalized_channel_name}"

            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
            """,
                (org_id, bot_id_str, "templated_db"),
            )

            conn.commit()

        template_context = {
            "db_user": "testuser",
            "db_password": "testpass",
            "db_host": "localhost",
            "db_name": "testdb",
            "schema": "public",
            "table": "users",
            "mcp_protocol": "https",
            "mcp_host": "mcp.example.com",
            "mcp_port": "8443",
            "api_token": "secret-token-123",
            "env": "production",
        }
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        result = asyncio.run(loader.load_bot_instances())

        bot_config = result["T1234567890-test-channel"]

        # Check connection templating
        templated_db = bot_config.connections["templated_db"]
        assert templated_db.url == "postgresql://testuser:testpass@localhost:5432/testdb"
        assert templated_db.init_sql == ["SET search_path = public;", "SELECT * FROM users;"]

    def test_multiple_bot_instances(self, sql_conn_factory, test_schema, encrypted_tokens):
        """Test loading multiple bot instances."""

        # Insert multiple test bots
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organizations first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization 1", "Technology", "user/repo1"),
            )
            org1_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization 2", "Healthcare", "user/repo2"),
            )
            org2_id = cursor.fetchone()[0]

            # Insert bot tokens first
            cursor.execute(
                """
                INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name)
                VALUES (%s, %s)
            """,
                ("T1111111111", "SLACK_BOT_TOKEN_T1111111111"),
            )
            cursor.execute(
                """
                INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name)
                VALUES (%s, %s)
            """,
                ("T2222222222", "SLACK_BOT_TOKEN_T2222222222"),
            )

            # Insert first bot
            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
                ("channel-1", "bot1@example.com", "alerts-1", "T1111111111", org1_id),
            )
            _ = cursor.fetchone()[0]  # bot_instance_id no longer needed

            # Insert second bot
            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
                ("channel-2", "bot2@example.com", "alerts-2", "T2222222222", org2_id),
            )
            _ = cursor.fetchone()[0]  # bot_instance_id no longer needed

            # Add connections for each bot (using organization_id instead of bot_instance_id)
            cursor.execute(
                """
                INSERT INTO connections (organization_id, connection_name, url, init_sql)
                VALUES (%s, %s, %s, %s)
            """,
                (org1_id, "db1", "postgresql://host1:5432/db1", '["SELECT 1;"]'),
            )

            cursor.execute(
                """
                INSERT INTO connections (organization_id, connection_name, url, init_sql)
                VALUES (%s, %s, %s, %s)
            """,
                (org2_id, "db2", "postgresql://host2:5432/db2", '["SELECT 2;"]'),
            )

            # Create bot_to_connections mappings
            # Construct bot_ids using the same logic as BotKey.to_bot_id()
            from csbot.utils.misc import normalize_channel_name

            bot1_id_str = f"T1111111111-{normalize_channel_name('channel-1')}"
            bot2_id_str = f"T2222222222-{normalize_channel_name('channel-2')}"

            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
            """,
                (org1_id, bot1_id_str, "db1"),
            )

            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
            """,
                (org2_id, bot2_id_str, "db2"),
            )

            conn.commit()

        template_context = {"env": "test"}
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        result = asyncio.run(loader.load_bot_instances())

        assert len(result) == 2
        assert "T1111111111-channel-1" in result
        assert "T2222222222-channel-2" in result

        # Check bot 1
        bot1 = result["T1111111111-channel-1"]
        assert bot1.bot_email == "bot1@example.com"
        assert bot1.contextstore_github_repo == "user/repo1"
        assert "db1" in bot1.connections
        assert bot1.connections["db1"].url == "postgresql://host1:5432/db1"

        # Check bot 2
        bot2 = result["T2222222222-channel-2"]
        assert bot2.bot_email == "bot2@example.com"
        assert bot2.contextstore_github_repo == "user/repo2"
        assert "db2" in bot2.connections
        assert bot2.connections["db2"].url == "postgresql://host2:5432/db2"

    def test_jinja2_template_error_handling(self, sql_conn_factory, test_schema, encrypted_tokens):
        """Test error handling for malformed Jinja2 templates."""
        # Insert test data with invalid template
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organization first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology", "user/repo"),
            )
            org_id = cursor.fetchone()[0]

            # Insert bot token first
            cursor.execute(
                """
                INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name)
                VALUES (%s, %s)
            """,
                ("T1234567890", "SLACK_BOT_TOKEN_T1234567890"),
            )

            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
                (
                    "test-channel",
                    "bot@example.com",
                    "alerts-channel",
                    "T1234567890",
                    org_id,
                ),
            )
            _ = cursor.fetchone()[0]  # bot_instance_id no longer needed

            # Invalid template with undefined variable (using organization_id instead of bot_instance_id)
            cursor.execute(
                """
                INSERT INTO connections (organization_id, connection_name, url, init_sql)
                VALUES (%s, %s, %s, %s)
            """,
                (org_id, "bad_template", "postgresql://{{undefined_var}}:5432/db", '["SELECT 1;"]'),
            )

            # Create bot_to_connections mapping
            # Construct bot_id using the same logic as BotKey.to_bot_id()
            from csbot.utils.misc import normalize_channel_name

            normalized_channel_name = normalize_channel_name("test-channel")
            bot_id_str = f"T1234567890-{normalized_channel_name}"

            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
            """,
                (org_id, bot_id_str, "bad_template"),
            )

            conn.commit()

        template_context = {"defined_var": "value"}  # Missing 'undefined_var'
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        # Should raise an exception due to undefined variable in strict mode
        with pytest.raises(Exception):
            asyncio.run(loader.load_bot_instances())

    def test_invalid_json_in_init_sql(self, sql_conn_factory, test_schema, encrypted_tokens):
        """Test error handling for invalid JSON in init_sql field."""
        # Insert test data with invalid JSON
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organization first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology", "user/repo"),
            )
            org_id = cursor.fetchone()[0]

            # Insert bot token first
            cursor.execute(
                """
                INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name)
                VALUES (%s, %s)
            """,
                ("T1234567890", "SLACK_BOT_TOKEN_T1234567890"),
            )

            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
                (
                    "test-channel",
                    "bot@example.com",
                    "alerts-channel",
                    "T1234567890",
                    org_id,
                ),
            )
            _ = cursor.fetchone()[0]  # bot_instance_id no longer needed

            # Invalid JSON in init_sql (using organization_id instead of bot_instance_id)
            cursor.execute(
                """
                INSERT INTO connections (organization_id, connection_name, url, init_sql)
                VALUES (%s, %s, %s, %s)
            """,
                (org_id, "bad_json", "postgresql://localhost:5432/db", "invalid json"),
            )

            # Create bot_to_connections mapping
            # Construct bot_id using the same logic as BotKey.to_bot_id()
            from csbot.utils.misc import normalize_channel_name

            normalized_channel_name = normalize_channel_name("test-channel")
            bot_id_str = f"T1234567890-{normalized_channel_name}"

            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
            """,
                (org_id, bot_id_str, "bad_json"),
            )

            conn.commit()

        template_context = {"env": "test"}
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        # Should raise a JSON decode error
        with pytest.raises(json.JSONDecodeError):
            asyncio.run(loader.load_bot_instances())

    def test_load_bot_instances_no_bot_token_fallback(self, sql_conn_factory, test_schema):
        """Test loading bot instances without bot token falls back to None."""

        # Insert test data without bot token
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organization first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology", "user/repo"),
            )
            org_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s)
            """,
                (
                    "test-channel",
                    "bot@example.com",
                    "alerts-channel",
                    "T9999999999",
                    org_id,
                ),
            )
            conn.commit()

        template_context = {"env": "test"}
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        result = asyncio.run(loader.load_bot_instances())

        assert len(result) == 1
        assert "T9999999999-test-channel" in result

        bot_config = result["T9999999999-test-channel"]
        assert bot_config.bot_email == "bot@example.com"
        assert bot_config.contextstore_github_repo == "user/repo"
        assert bot_config.governance_alerts_channel == "alerts-channel"
        assert bot_config.connections == {}

    def test_load_bot_instances_with_hash_prefixed_channel_name(
        self, sql_conn_factory, test_schema, encrypted_tokens
    ):
        """Test loading bot instances where channel name erroneously starts with #."""

        # Insert test data with # prefix in channel name
        with sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert organization first
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, contextstore_github_repo)
                VALUES (%s, %s, %s) RETURNING organization_id
            """,
                ("Test Organization", "Technology", "user/repo"),
            )
            org_id = cursor.fetchone()[0]

            # Insert bot token first
            cursor.execute(
                """
                INSERT INTO slack_bot_tokens (slack_team_id, bot_token_env_var_name)
                VALUES (%s, %s)
            """,
                ("T1234567890", "SLACK_BOT_TOKEN_T1234567890"),
            )

            # Insert bot instance with # prefix in channel name (erroneous data)
            cursor.execute(
                """
                INSERT INTO bot_instances (
                    channel_name, bot_email,
                    governance_alerts_channel, slack_team_id, organization_id
                )
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
                (
                    "#test-channel",  # Erroneously starts with #
                    "bot@example.com",
                    "alerts-channel",
                    "T1234567890",
                    org_id,
                ),
            )
            cursor.fetchone()[0]

            # Insert connection for this bot
            cursor.execute(
                """
                INSERT INTO connections (organization_id, connection_name, url, init_sql)
                VALUES (%s, %s, %s, %s)
            """,
                (
                    org_id,
                    "test_db",
                    "postgresql://user:pass@host:5432/db",
                    '["SELECT 1;"]',
                ),
            )

            # Create bot_to_connections mapping - the bot_id should be constructed
            # using normalized channel name (without #)
            from csbot.utils.misc import normalize_channel_name

            normalized_channel_name = normalize_channel_name("#test-channel")  # Should remove #
            bot_id_str = f"T1234567890-{normalized_channel_name}"

            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
            """,
                (org_id, bot_id_str, "test_db"),
            )

            conn.commit()

        template_context = {"env": "test"}
        get_template_context_for_org = self._create_mock_get_template_context_for_org(
            template_context
        )

        storage = create_storage(sql_conn_factory)
        loader = DatabaseBotInstanceLoader(storage, template_context, get_template_context_for_org)

        result = asyncio.run(loader.load_bot_instances())

        # Should successfully load the bot instance, normalizing the # prefix
        assert len(result) == 1
        bot_config = next(iter(result.values()))
        # Connection should be loaded properly despite # prefix in database
        assert len(bot_config.connections) == 1
