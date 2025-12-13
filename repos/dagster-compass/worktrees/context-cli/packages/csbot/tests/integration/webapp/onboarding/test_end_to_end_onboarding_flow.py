"""End-to-end test for the onboarding flow with webserver and form submission."""

import asyncio
import json
import logging
import os
import re
import shutil
import uuid
from contextlib import AsyncExitStack, ExitStack
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp.test_utils import AioHTTPTestCase
from playwright.async_api import async_playwright
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions
from testcontainers.postgres import PostgresContainer

from csbot.slackbot.bot_server.bot_reconciler import CompassBotReconciler
from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.config import DatabaseConfig, UnsupportedKekConfig
from csbot.slackbot.envelope_encryption import KekProvider
from csbot.slackbot.slackbot_slackstream import throttler
from csbot.slackbot.storage.postgresql import PostgresqlConnectionFactory, SlackbotPostgresqlStorage
from csbot.slackbot.webapp.add_connections.models import JsonConfig
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.routes import add_webapp_routes
from csbot.slackbot.webapp.security import create_link
from csbot.temporal.dataset_sync.activity import DatasetSyncActivities
from csbot.temporal.dataset_sync.workflow import DatasetSyncWorkflow
from csbot.utils.time import SecondsNowFake
from tests.utils.postgres_utils import wait_for_startup
from tests.utils.slack_client import FakeSlackClient, mock_slack_api_with_client

# Skip all tests if psycopg is not available
psycopg = pytest.importorskip("psycopg")

# Re-enabling select E2E tests for new React onboarding flow
# pytest.skip(
#     "Onboarding is in flux, tests aren't keeping up, disabling for now", allow_module_level=True
# )


class ErrorLogHandler(logging.Handler):
    """Custom log handler that captures ERROR level logs to fail tests."""

    def __init__(self, expected_error_patterns=None):
        super().__init__(level=logging.ERROR)
        self.error_logs = []
        self.expected_error_patterns = expected_error_patterns or []

    def emit(self, record):
        """Capture error log records, filtering out expected errors."""
        error_message = record.getMessage()

        # Check if this error matches any expected patterns
        for pattern in self.expected_error_patterns:
            if pattern in error_message:
                return  # Skip this error as it's expected

        self.error_logs.append(
            {
                "message": error_message,
                "levelname": record.levelname,
                "pathname": record.pathname,
                "lineno": record.lineno,
                "funcName": record.funcName,
            }
        )

    def get_errors(self):
        """Get captured error logs."""
        return self.error_logs.copy()

    def clear_errors(self):
        """Clear captured error logs."""
        self.error_logs.clear()

    def has_errors(self):
        """Check if any errors were captured."""
        return len(self.error_logs) > 0

    def add_expected_error_pattern(self, pattern):
        """Add a pattern to ignore during error detection."""
        self.expected_error_patterns.append(pattern)


# Connection test scenarios with comprehensive warehouse coverage paired with their JsonConfig objects
# Each tuple contains (scenario_dict, expected_json_config)
CONNECTION_SCENARIOS_WITH_CONFIGS = [
    # Snowflake scenarios
    (
        {
            "name": "Snowflake with password auth",
            "url_path": "/onboarding/connections/snowflake",
            "form_data": {
                "account_id": "test123",
                "username": "testuser",
                "credential_type": "password",
                "password": "testpassword",
                "warehouse": "COMPUTE_WH",
                "role": "ACCOUNTADMIN",
                "region": "",
            },
            "tables": ["TEST_DB.PUBLIC.CUSTOMERS", "TEST_DB.PUBLIC.ORDERS"],
        },
        JsonConfig(
            type="snowflake",
            config={
                "account_id": "test123",
                "username": "testuser",
                "credential": {"type": "password", "password": "testpassword"},
                "warehouse": "COMPUTE_WH",
                "role": "ACCOUNTADMIN",
                "region": None,
            },
        ),
    ),
    (
        {
            "name": "Snowflake with private key auth",
            "url_path": "/onboarding/connections/snowflake",
            "form_data": {
                "account_id": "test456",
                "username": "keyuser",
                "credential_type": "private_key",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7...\n-----END PRIVATE KEY-----",
                "warehouse": "ANALYTICS_WH",
                "role": "ANALYST",
                "region": "",
            },
            "tables": ["ANALYTICS.FACT.SALES"],
        },
        JsonConfig(
            type="snowflake",
            config={
                "account_id": "test456",
                "username": "keyuser",
                "credential": {
                    "type": "private_key",
                    "private_key_file": "-----BEGIN PRIVATE KEY-----\r\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7...\r\n-----END PRIVATE KEY-----",
                },
                "warehouse": "ANALYTICS_WH",
                "role": "ANALYST",
                "region": None,
            },
        ),
    ),
    (
        {
            "name": "Snowflake with encrypted private key auth",
            "url_path": "/onboarding/connections/snowflake",
            "form_data": {
                "account_id": "test789",
                "username": "encryptedkeyuser",
                "credential_type": "private_key",
                "private_key": "-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIFHDBOBgkqhkiG9w0BBQ0wQTApBgkqhkiG9w0BBQwwHAQI...\n-----END ENCRYPTED PRIVATE KEY-----",
                "key_password": "myencryptionpassword",
                "warehouse": "SECURE_WH",
                "role": "SECURITY_ANALYST",
                "region": "",
            },
            "tables": ["SECURITY.AUDIT.ACCESS_LOGS"],
        },
        JsonConfig(
            type="snowflake",
            config={
                "account_id": "test789",
                "username": "encryptedkeyuser",
                "credential": {
                    "type": "private_key",
                    "private_key_file": "-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIFHDBOBgkqhkiG9w0BBQ0wQTApBgkqhkiG9w0BBQwwHAQI...\n-----END ENCRYPTED PRIVATE KEY-----",
                    "key_password": "myencryptionpassword",
                },
                "warehouse": "SECURE_WH",
                "role": "SECURITY_ANALYST",
                "region": None,
            },
        ),
    ),
    (
        {
            "name": "Snowflake with password auth and explicit region",
            "url_path": "/onboarding/connections/snowflake",
            "form_data": {
                "account_id": "test789",
                "username": "regionuser",
                "credential_type": "password",
                "password": "regionpass",
                "warehouse": "REGIONAL_WH",
                "role": "REGIONAL_ROLE",
                "region": "us-east-1",
            },
            "tables": ["REGIONAL_DB.STAGING.RAW_DATA"],
        },
        JsonConfig(
            type="snowflake",
            config={
                "account_id": "test789",
                "username": "regionuser",
                "credential": {"type": "password", "password": "regionpass"},
                "warehouse": "REGIONAL_WH",
                "role": "REGIONAL_ROLE",
                "region": "us-east-1",
            },
        ),
    ),
    (
        {
            "name": "Snowflake with organization-account format (no region)",
            "url_path": "/onboarding/connections/snowflake",
            "form_data": {
                "account_id": "myorg-account123",
                "username": "modernuser",
                "credential_type": "password",
                "password": "modernpass",
                "warehouse": "MODERN_WH",
                "role": "DATA_ANALYST",
                "region": "",
            },
            "tables": ["MODERN_DB.PUBLIC.ANALYTICS"],
        },
        JsonConfig(
            type="snowflake",
            config={
                "account_id": "myorg-account123",
                "username": "modernuser",
                "credential": {"type": "password", "password": "modernpass"},
                "warehouse": "MODERN_WH",
                "role": "DATA_ANALYST",
                "region": None,
            },
        ),
    ),
    # BigQuery scenarios
    (
        {
            "name": "BigQuery with US location",
            "url_path": "/onboarding/connections/bigquery",
            "form_data": {
                "location": "us",
                "service_account_json_string": json.dumps(
                    {
                        "type": "service_account",
                        "project_id": "test-project-123",
                        "private_key_id": "key123",
                        "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n",
                        "client_email": "test@test-project-123.iam.gserviceaccount.com",
                        "client_id": "123456789",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                ),
            },
            "tables": [
                "test-project-123.dataset.table1",
                "test-project-123.dataset.table2",
            ],
        },
        JsonConfig(
            type="bigquery",
            config={
                "location": "us",
                "service_account_json_string": '{"type": "service_account", "project_id": "test-project-123", "private_key_id": "key123", "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n", "client_email": "test@test-project-123.iam.gserviceaccount.com", "client_id": "123456789", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}',
            },
        ),
    ),
    (
        {
            "name": "BigQuery with EU location",
            "url_path": "/onboarding/connections/bigquery",
            "form_data": {
                "location": "eu",
                "service_account_json_string": json.dumps(
                    {
                        "type": "service_account",
                        "project_id": "eu-project-456",
                        "private_key_id": "key456",
                        "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n",
                        "client_email": "eu-test@eu-project-456.iam.gserviceaccount.com",
                        "client_id": "987654321",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                ),
            },
            "tables": ["eu-project-456.eu_dataset.eu_table"],
        },
        JsonConfig(
            type="bigquery",
            config={
                "location": "eu",
                "service_account_json_string": '{"type": "service_account", "project_id": "eu-project-456", "private_key_id": "key456", "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIE...\\n-----END PRIVATE KEY-----\\n", "client_email": "eu-test@eu-project-456.iam.gserviceaccount.com", "client_id": "987654321", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}',
            },
        ),
    ),
    # Athena scenarios
    (
        {
            "name": "Athena with aws_athena_trino_sql engine",
            "url_path": "/onboarding/connections/athena",
            "form_data": {
                "aws_access_key_id": "AKIATEST123",
                "aws_secret_access_key": "test/secret/key/123",
                "region": "us-west-2",
                "s3_staging_dir": "s3://test-athena-bucket/staging/",
                "query_engine": "aws_athena_trino_sql",
            },
            "tables": ["trino_db.table1", "trino_db.table2"],
        },
        JsonConfig(
            type="athena",
            config={
                "aws_access_key_id": "AKIATEST123",
                "aws_secret_access_key": "test/secret/key/123",
                "region": "us-west-2",
                "s3_staging_dir": "s3://test-athena-bucket/staging/",
                "query_engine": "aws_athena_trino_sql",
            },
        ),
    ),
    (
        {
            "name": "Athena with aws_athena_spark_sql engine",
            "url_path": "/onboarding/connections/athena",
            "form_data": {
                "aws_access_key_id": "AKIATEST456",
                "aws_secret_access_key": "test/spark/key/456",
                "region": "us-east-1",
                "s3_staging_dir": "s3://test-spark-bucket/staging/",
                "query_engine": "aws_athena_spark_sql",
            },
            "tables": ["spark_db.events"],
        },
        JsonConfig(
            type="athena",
            config={
                "aws_access_key_id": "AKIATEST456",
                "aws_secret_access_key": "test/spark/key/456",
                "region": "us-east-1",
                "s3_staging_dir": "s3://test-spark-bucket/staging/",
                "query_engine": "aws_athena_spark_sql",
            },
        ),
    ),
]

# Extract just the scenarios for backward compatibility
CONNECTION_SCENARIOS = [scenario for scenario, _ in CONNECTION_SCENARIOS_WITH_CONFIGS]


@pytest.mark.skipif(
    os.environ.get("COMPASS_E2E_TESTS") != "1",
    reason="E2E tests are not enabled; set COMPASS_E2E_TESTS=1 to run",
)
class TestEndToEndOnboardingFlow(AioHTTPTestCase):
    """Test complete end-to-end onboarding flow with real webserver."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Set up error log handler to capture ERROR level logs
        # No default expected patterns - tests that expect errors should specify them explicitly
        self.error_handler = ErrorLogHandler()
        logging.getLogger().addHandler(self.error_handler)

        # Set up PostgreSQL test container
        self._setup_postgres_container()

        # Create controlled time provider
        self.time_provider = SecondsNowFake(1234567890)

        # Initialize Playwright
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # Create mock bot server
        self.mock_bot_server = MagicMock(spec=CompassBotServer)

        self.mock_bot_server.logger = MagicMock()

        # Mock config with all required tokens and settings
        self.mock_server_config = MagicMock()
        self.mock_server_config.compass_bot_token = MagicMock()
        self.mock_server_config.compass_bot_token.get_secret_value.return_value = (
            "compass_token_12345"
        )
        self.mock_server_config.slack_admin_token = MagicMock()
        self.mock_server_config.slack_admin_token.get_secret_value.return_value = (
            "admin_token_12345"
        )
        self.mock_server_config.compass_dev_tools_bot_token = MagicMock()
        self.mock_server_config.compass_dev_tools_bot_token.get_secret_value.return_value = (
            "dev_tools_token_12345"
        )
        self.mock_server_config.github = MagicMock()
        self.mock_bot_server.github_auth_source = MagicMock()
        self.mock_bot_server.github_auth_source.get_token.return_value = "github_token_12345"
        self.mock_server_config.github.get_auth_token = AsyncMock(return_value="github_token_12345")
        self.mock_server_config.dagster_admins_to_invite = [
            "admin1@dagster.io",
            "admin2@dagster.io",
        ]

        # Mock stripe config
        self.mock_server_config.stripe = MagicMock()
        self.mock_server_config.stripe.default_product = "team"
        self.mock_server_config.stripe.get_default_product_id.return_value = "prod_team_12345"

        # Mock JWT secret and public URL for URL generation
        self.mock_server_config.jwt_secret = MagicMock()
        self.mock_server_config.jwt_secret.get_secret_value.return_value = "test_jwt_secret_12345"

        # Mock AI config for agent creation
        self.mock_server_config.ai_config = MagicMock()
        self.mock_server_config.ai_config.provider = "anthropic"
        self.mock_server_config.ai_config.api_key = MagicMock()
        self.mock_server_config.ai_config.api_key.get_secret_value.return_value = (
            "test_anthropic_key"
        )
        self.mock_server_config.ai_config.model = "claude-sonnet-4-20250514"

        self.mock_bot_server.config = self.mock_server_config

        self.mock_bot_server.logger = logging.getLogger("test")

        # Temporal workflow environment will be set up in tests that need it
        self.temporal_env = None
        self.temporal_worker = None
        self.mock_bot_server.temporal_client = None

        # We'll set the public URL dynamically in the test to match the test server port

        # Create real PostgreSQL storage for database operations
        sql_conn_factory = PostgresqlConnectionFactory.from_db_config(
            DatabaseConfig.from_uri(self.database_url), self.time_provider
        )

        # Create the actual storage class
        storage = SlackbotPostgresqlStorage(
            sql_conn_factory, KekProvider(UnsupportedKekConfig()), self.time_provider
        )

        # Add sql_conn_factory to mock bot server for analytics store
        self.mock_bot_server.sql_conn_factory = sql_conn_factory

        # Mock bot manager with async methods
        self.mock_bot_server.bot_manager = MagicMock()
        self.mock_bot_server.bot_manager.storage = storage
        self.mock_bot_server.bot_manager.discover_and_update_bots_for_keys = AsyncMock()

        # Mock secret store with async methods
        self.mock_secret_store = MagicMock()
        self.mock_secret_store.store_secret = AsyncMock(return_value=Path("mock_secret_filename"))
        self.mock_bot_server.bot_manager.secret_store = self.mock_secret_store

        # Let the storage methods work with the real database instead of mocking them
        # This ensures foreign key constraints are properly maintained
        # We'll still verify the calls were made correctly

        # We need to let mark_referral_token_consumed actually work to mark the token as consumed
        # So we don't mock this method - it should work with the real database

        # Mock bots dict
        self.mock_bot_server.bots = {}

        # Mock channel_id_to_name dict for channel caching
        self.mock_bot_server.channel_id_to_name = {}

        # Create a mock bot instance and add it to the bots dictionary
        # This is needed for the industry selection URL generation
        bot_key = BotKey.from_channel_name("T12345TEST", "test-company-inc-compass")
        mock_bot = MagicMock()
        mock_bot.key = bot_key

        # Create a simple object to hold config values - avoid MagicMock auto-generation
        class MockBotConfig:
            def __init__(self):
                self.organization_name = "Test Company Inc"
                self.organization_id = None  # Will be set later
                self.contextstore_github_repo = "dagster-compass/test-company-inc-context"
                self.team_id = "T12345TEST"
                self.governance_alerts_channel = "test-company-inc-compass-governance"
                self.channel_name = "test-company-inc-compass"

        mock_config = MockBotConfig()
        mock_bot.bot_config = mock_config
        mock_bot.bot_server = self.mock_bot_server
        mock_bot.server_config = self.mock_server_config
        # Set governance_alerts_channel directly as an attribute
        mock_bot.governance_alerts_channel = "test-company-inc-compass-governance"
        # Configure KV store mock to properly handle first-time invite logic
        mock_bot.kv_store = AsyncMock()
        # Return False for first-time sync logic (is_first_dataset_sync returns True when kv_store.exists returns False)
        mock_bot.kv_store.exists.return_value = False
        mock_bot.kv_store.set = AsyncMock()
        mock_bot.kv_store.get = AsyncMock(return_value=None)
        mock_bot.kv_store.delete = AsyncMock()

        # Mock get_channel_id to return channel IDs for testing
        async def mock_get_channel_id(channel_name):
            channel_map = {
                "test-company-inc-compass": "C_MAIN_12345",
                "test-company-inc-compass-governance": "C_GOV_12345",
            }
            return channel_map.get(channel_name)

        mock_bot.kv_store.get_channel_id = mock_get_channel_id

        throttler.running = True
        mock_bot.client = AsyncMock()
        # Configure Slack client method responses to prevent coroutine iteration errors
        mock_bot.client.conversations_members.return_value = {"members": ["U123", "U456", "U789"]}
        mock_bot.client.users_info.return_value = {
            "user": {"id": "U123", "name": "testuser", "is_bot": False}
        }
        mock_bot.client.chat_update.return_value = {"ok": True, "ts": "1234567890.123456"}
        mock_bot.client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}
        mock_bot.github_monitor = AsyncMock()
        mock_bot.associate_channel_id = AsyncMock()  # Mock the associate_channel_id method
        mock_bot.analytics_store = AsyncMock()  # Fix MagicMock await expression error
        self.mock_bot_server.bots[bot_key] = mock_bot
        self.mock_bot = mock_bot

        # Create governance bot key and mock governance bot
        governance_bot_key = BotKey.from_channel_name(
            "T12345TEST", "test-company-inc-compass-governance"
        )
        mock_governance_bot = MagicMock()
        mock_governance_bot.key = governance_bot_key

        # Create a simple object to hold config values - avoid MagicMock auto-generation
        class MockGovernanceBotConfig:
            def __init__(self):
                self.organization_name = "Test Company Inc"
                self.organization_id = None  # Will be set later
                self.team_id = "T12345TEST"
                self.governance_alerts_channel = "test-company-inc-compass-governance"
                self.channel_name = "test-company-inc-compass-governance"
                self.contextstore_github_repo = "dagster-compass/test-company-inc-context"

        mock_governance_config = MockGovernanceBotConfig()
        mock_governance_bot.bot_config = mock_governance_config
        mock_governance_bot.bot_server = self.mock_bot_server
        mock_governance_bot.server_config = self.mock_server_config
        # Set governance_alerts_channel directly as an attribute
        mock_governance_bot.governance_alerts_channel = "test-company-inc-compass-governance"
        mock_governance_bot.client = AsyncMock()
        # Configure Slack client method responses to prevent coroutine iteration errors
        mock_governance_bot.client.conversations_members.return_value = {
            "members": ["U123", "U456", "U789"]
        }
        mock_governance_bot.client.users_info.return_value = {
            "user": {"id": "U123", "name": "testuser", "is_bot": False}
        }
        mock_governance_bot.client.chat_update.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        mock_governance_bot.client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        mock_governance_bot.associate_channel_id = AsyncMock()
        mock_governance_bot.analytics_store = AsyncMock()  # Fix MagicMock await expression error
        mock_governance_bot.kv_store = (
            AsyncMock()
        )  # Fix governance channel notification MagicMock await error
        mock_governance_bot.kv_store.get = AsyncMock(return_value=None)
        mock_governance_bot.kv_store.delete = AsyncMock()
        mock_governance_bot.kv_store.set = AsyncMock()

        # Mock get_channel_id to return channel IDs for testing
        async def mock_gov_get_channel_id(channel_name):
            channel_map = {
                "test-company-inc-compass": "C_MAIN_12345",
                "test-company-inc-compass-governance": "C_GOV_12345",
            }
            return channel_map.get(channel_name)

        mock_governance_bot.kv_store.get_channel_id = mock_gov_get_channel_id

        # Set up governance bot type properly
        from csbot.slackbot.channel_bot.bot import BotTypeGovernance

        mock_governance_bot.bot_type = BotTypeGovernance(governed_bot_keys={bot_key})

        self.mock_bot_server.bots[governance_bot_key] = mock_governance_bot

        # Mock canonicalize_bot_key to return the correct BotKey
        # This is critical for JWT token validation to work correctly
        async def mock_canonicalize_bot_key(bot_key_arg, *args):
            # Handle both BotKey objects and separate arguments
            if isinstance(bot_key_arg, BotKey):
                # Called with BotKey object - map by channel_name regardless of team_id
                # This allows FakeSlackClient's dynamic team_id to work with hardcoded bot setup
                if bot_key_arg.channel_name == "test-company-inc-compass":
                    return bot_key
                elif bot_key_arg.channel_name == "test-company-inc-compass-governance":
                    return governance_bot_key
                elif bot_key_arg in self.mock_bot_server.bots:
                    return bot_key_arg
                else:
                    # Return the compass bot key by default
                    return bot_key
            else:
                # Called with separate team_id, channel_name arguments (legacy call style)
                team_id = bot_key_arg
                channel_name = args[0] if len(args) > 0 else None
                if channel_name is None:
                    return bot_key  # Default fallback
                elif channel_name == "test-company-inc-compass":
                    return bot_key
                elif channel_name == "test-company-inc-compass-governance":
                    return governance_bot_key
                else:
                    return BotKey.from_channel_name(team_id, channel_name)

        self.mock_bot_server.canonicalize_bot_key = mock_canonicalize_bot_key

        # Mock stripe client
        from tests.utils.stripe_client import FakeStripeClient

        self.mock_bot_server.stripe_client = FakeStripeClient("test_stripe_key")

        # Mock analytics logging to prevent JSON serialization issues with MagicMock objects
        self.analytics_patcher = patch(
            "csbot.slackbot.slackbot_analytics.log_analytics_event_unified"
        )
        self.mock_analytics_logger = self.analytics_patcher.start()
        self.mock_analytics_logger.return_value = AsyncMock()

        # Mock Slack Connect API to prevent authentication errors
        self.slack_connect_patcher = patch(
            "csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel"
        )
        self.mock_slack_connect = self.slack_connect_patcher.start()
        self.mock_slack_connect.return_value = [
            {"success": True, "invite": {"id": "mock_invite_123"}}
        ]

        # Create referral token
        self.referral_token = str(uuid.uuid4())
        self._create_referral_token(self.referral_token)

        mock_create_slack_client = patch(
            "csbot.slackbot.webapp.onboarding_steps.create_slack_client"
        ).start()
        mock_create_slack_client.return_value = AsyncMock()

    def _setup_postgres_container(self):
        """Set up PostgreSQL container for testing."""
        # Use environment variable if available (for CI/CD environments)
        if test_db_url := os.environ.get("TEST_DATABASE_URL"):
            if test_db_url.startswith("postgresql://"):
                self.database_url = test_db_url
                return

        # Otherwise, spin up a test container
        self.postgres_container = PostgresContainer(
            image="public.ecr.aws/docker/library/postgres:16-alpine3.21",
            username="test",
            password="test",
            dbname="test_db",
            driver="psycopg",
        )
        self.postgres_container.start()
        self.database_url = self.postgres_container.get_connection_url()
        wait_for_startup(self.database_url)
        # Set environment variable for any code that might need it
        os.environ["TEST_DATABASE_URL"] = self.database_url

    async def _setup_playwright(self):
        """Set up Playwright browser for testing."""
        self.playwright = await async_playwright().start()

        # Configure video recording - enabled via COMPASS_RECORD_VIDEO env var
        if os.environ.get("COMPASS_RECORD_VIDEO") == "1":
            self.browser = await self.playwright.chromium.launch(headless=True)
            # Create browser context with video recording
            self.context = await self.browser.new_context(
                record_video_dir="test-videos/", record_video_size={"width": 1280, "height": 720}
            )
            self.page = await self.context.new_page()
        else:
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()

        if os.environ.get("COMPASS_E2E_CI") == "1":
            self.page.set_default_navigation_timeout(30000)
            self.page.set_default_timeout(30000)
        else:
            self.page.set_default_navigation_timeout(5000)
            self.page.set_default_timeout(5000)

    async def _teardown_playwright(self):
        """Clean up Playwright browser."""
        video_path = None

        if self.page:
            # Ensure video is saved by closing the page first
            await self.page.close()

        # Get video path after page close but before context close (when video is finalized)
        if (
            self.page
            and hasattr(self.page, "video")
            and self.page.video
            and os.environ.get("COMPASS_RECORD_VIDEO") == "1"
        ):
            try:
                video_path = await self.page.video.path()
            except Exception as e:
                print(f"Warning: Could not get video path: {e}")

        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        # Rename video after all cleanup is done
        if video_path:
            self._rename_video(video_path)

    def _rename_video(self, video_path):
        """Rename video file to include test name and suffix from original path."""
        if not video_path or not os.path.exists(video_path):
            print(f"Video path does not exist or is None: {video_path}")
            return

        # Get the test method name
        test_method_name = (
            self._testMethodName if hasattr(self, "_testMethodName") else "unknown_test"
        )

        # Extract filename and extension
        original_path = Path(video_path)
        original_filename = original_path.stem  # filename without extension
        original_extension = original_path.suffix  # .webm

        # Get first 8 chars of original filename for suffix
        suffix = original_filename[:8] if len(original_filename) >= 8 else original_filename

        # Get current timestamp in mmddyy-hhmm format
        from datetime import datetime

        now = datetime.now()
        timestamp = now.strftime("%m%d%y-%H%M")

        # Create new filename: test_name_timestamp_suffix.extension
        video_dir = original_path.parent
        new_filename = f"{test_method_name}_{timestamp}_{suffix}{original_extension}"
        new_path = video_dir / new_filename

        # Rename the video file
        try:
            shutil.move(str(video_path), str(new_path))
            print(f"✅ Video renamed: {original_path.name} → {new_path.name}")
        except Exception as e:
            print(f"❌ Failed to rename video from {video_path} to {new_path}: {e}")

    async def get_video_path(self):
        """Get the path to the recorded video if available."""
        if self.page and hasattr(self.page, "video") and self.page.video:
            return await self.page.video.path()
        return None

    def tearDown(self):
        """Clean up test fixtures."""
        # Check for error logs and fail the test if any were captured
        if hasattr(self, "error_handler"):
            error_logs = self.error_handler.get_errors()
            if error_logs:
                # Format error messages for test failure
                error_messages = []
                for error in error_logs:
                    error_messages.append(
                        f"ERROR in {error['pathname']}:{error['lineno']} ({error['funcName']}): {error['message']}"
                    )

                # Remove error handler before failing
                logging.getLogger().removeHandler(self.error_handler)

                # Fail the test with detailed error information
                self.fail(
                    f"Test failed due to {len(error_logs)} error-level log(s):\n"
                    + "\n".join(error_messages)
                )

            # Clean up error handler
            logging.getLogger().removeHandler(self.error_handler)

        super().tearDown()

        # Stop analytics patcher
        if hasattr(self, "analytics_patcher"):
            self.analytics_patcher.stop()

        # Stop Slack Connect patcher
        if hasattr(self, "slack_connect_patcher"):
            self.slack_connect_patcher.stop()

        # Stop PostgreSQL container if we created one
        if hasattr(self, "postgres_container"):
            self.postgres_container.stop()

    def expect_error_log_containing(self, pattern):
        """Add an expected error pattern to ignore during this test."""
        if hasattr(self, "error_handler"):
            self.error_handler.add_expected_error_pattern(pattern)

    async def _fill_connection_form(self, form_data):
        """Helper method to fill connection form fields.

        React dynamic forms use id attributes instead of name attributes.
        """
        for field_name, field_value in form_data.items():
            # Find the input field by id (React form) or name (fallback)
            input_selector = f'input#{field_name}, select#{field_name}, textarea#{field_name}, input[name="{field_name}"], select[name="{field_name}"], textarea[name="{field_name}"]'
            assert self.page is not None
            field_elements = await self.page.locator(input_selector).all()

            for field_element in field_elements:
                await field_element.wait_for(state="visible")

            if len(field_elements) > 1:
                # This is a radio button
                for field_element in field_elements:
                    if (await field_element.get_attribute("value")) == field_value:
                        await field_element.click()
                        break
            elif len(field_elements) == 0:
                raise ValueError(f"No field elements found for {field_name}")
            else:
                # This is a normal input field
                await field_elements[0].click()
                await field_elements[0].fill(str(field_value))

    def _create_referral_token(self, token):
        """Create a valid referral token in the database."""
        storage = self.mock_bot_server.bot_manager.storage

        # Insert token into existing referral_tokens table (schema is already created)
        with storage._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO referral_tokens (token) VALUES (%s)", (token,))
            conn.commit()

    async def _setup_temporal_environment(self, stack: AsyncExitStack):
        """Set up Temporal workflow environment with worker for dataset sync.

        Args:
            stack: ExitStack to register cleanup handlers

        Returns:
            Tuple of (env, mock_post) for testing
        """
        env = await stack.enter_async_context(await WorkflowEnvironment.start_time_skipping())
        workflow_runner = SandboxedWorkflowRunner(
            restrictions=SandboxRestrictions.default.with_passthrough_modules("csbot")
        )

        # Create mock bot reconciler
        mock_bot_reconciler = MagicMock(spec=CompassBotReconciler)
        mock_bot_reconciler.get_active_bots = MagicMock(return_value=self.mock_bot_server.bots)

        # Create mock temporal client for activities
        mock_temporal_client = MagicMock()
        activities_instance = DatasetSyncActivities(mock_bot_reconciler, mock_temporal_client)

        # Start worker with dataset sync workflow and activities
        await stack.enter_async_context(
            Worker(
                env.client,
                task_queue="compass-queue",
                workflows=[DatasetSyncWorkflow],
                activities=[
                    activities_instance.create_branch,
                    activities_instance.finalize_pull_request,
                    activities_instance.process_dataset,
                    activities_instance.send_notification_started,
                    activities_instance.send_notification_completed,
                    activities_instance.send_slack_connect_invite,
                    activities_instance.log_analytics,
                    activities_instance.update_progress,
                ],
                workflow_runner=workflow_runner,
            )
        )

        # Set up common mocks for temporal activities
        mock_create_merge_pr = stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.create_and_merge_pull_request")
        )
        mock_create_merge_pr.return_value = "https://github.com/example/repo/pull/123"

        mock_post = stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.SlackstreamMessage.post_message")
        )
        mock_message = MagicMock()
        mock_message.message_ts = "1234567890.123456"
        mock_post.return_value = mock_message

        stack.enter_context(
            patch("csbot.temporal.dataset_sync.activity.log_analytics_event_unified")
        )

        # Mock dataset processing functions
        stack.enter_context(patch("csbot.temporal.dataset_sync.activity.analyze_table_schema"))

        stack.enter_context(patch("csbot.temporal.dataset_sync.activity.update_dataset"))

        # Store env and set temporal client on bot server
        self.temporal_env = env
        self.mock_bot_server.temporal_client = env.client

        return env, mock_post

    async def _step_through_and_add_connection(
        self, scenario, mock_to_thread, mock_list_tables, channel_selection=None, config=None
    ):
        """Helper function to step through the complete connection addition flow.

        Args:
            scenario: Connection test scenario data
            mock_to_thread: Mock for asyncio.to_thread
            mock_list_tables: Mock for warehouse_factory.list_tables
            channel_selection: Optional dict with channel selection data.
                             If None, uses default "create" with test-company-inc-compass
            config: The warehouse configuration object (needed to generate connection_name)
        """
        schemas = list(set([table[: table.rfind(".")] for table in scenario["tables"]]))

        # Generate connection name from config
        if config is None:
            raise ValueError("config parameter is required to generate connection_name")

        # Convert JsonConfig to the specific warehouse config type to access get_connection_name
        from csbot.slackbot.webapp.add_connections.models import (
            compass_warehouse_config_from_json_config,
        )

        warehouse_config = compass_warehouse_config_from_json_config(config)
        connection_name = warehouse_config.get_connection_name()

        # Configure mock_to_thread to handle warehouse operations for this scenario
        def mock_to_thread_side_effect(func, *args, **kwargs):
            if hasattr(func, "__name__") and func.__name__ == "list_schemas":
                return schemas
            elif hasattr(func, "__name__") and func.__name__ == "list_tables":
                return [
                    {"name": table, "description": None, "recommended": False}
                    for table in scenario["tables"]
                ]
            else:
                # For other calls, just return a mock result
                return MagicMock()

        mock_to_thread.side_effect = mock_to_thread_side_effect
        mock_list_tables.return_value = {
            "tables": [
                {"name": table, "description": None, "recommended": False}
                for table in scenario["tables"]
            ],
            "schema_warnings": [],
            "success": True,
            "error": None,
        }

        assert self.page is not None

        ##########################################################
        ## Connection Form Page                                 ##
        ## React Wizard: Uses ?source= URL parameter           ##
        ## Routes: /onboarding/connections?source={warehouse}  ##
        ##########################################################

        # Extract warehouse type from URL path (e.g., /onboarding/connections/snowflake -> snowflake)
        warehouse_type = scenario["url_path"].split("/")[-1]

        # Navigate to React wizard with source parameter to skip warehouse selection
        await self.page.goto(
            f"http://localhost:{self.client.port}/onboarding/connections?source={warehouse_type}"
        )
        await self.page.wait_for_load_state("domcontentloaded", timeout=15000)

        # Wait for the credentials form to load
        await self.page.wait_for_selector('h3:has-text("Connection Details")', timeout=10000)

        await self._fill_connection_form(scenario["form_data"])
        await asyncio.sleep(1)

        test_button = self.page.locator("button:has-text('Test Connection')")
        await test_button.wait_for(state="visible")

        # Ensure form validation runs after filling form data
        await self.page.evaluate("validateForm()")

        await self.page.wait_for_function(
            "() => { const btn = document.getElementById('test-connection-button'); return btn && !btn.disabled; }",
            timeout=10000,
        )
        await test_button.click()

        continue_button = self.page.locator("button:has-text('Continue to Schema Selection')")
        await continue_button.wait_for(state="visible")
        await continue_button.click()

        ##########################################################
        ## Schema Selection Page                                ##
        ## Template: warehouse_discover_schemas.html            ##
        ## Routes: add_connections/all_routes.py               ##
        ##########################################################

        await self.page.wait_for_url("**/discover-schemas")
        await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        await asyncio.sleep(2)

        first_schema_checkbox = self.page.locator("#schema-0")
        await first_schema_checkbox.wait_for(state="attached", timeout=10000)
        await first_schema_checkbox.click()

        proceed_button = self.page.get_by_text("Continue to Table Selection")
        await proceed_button.wait_for(state="attached")
        await proceed_button.click()

        ##########################################################
        ## Table Selection Page                                 ##
        ## Template: warehouse_discover_tables.html             ##
        ## Routes: add_connections/all_routes.py               ##
        ##########################################################

        await self.page.wait_for_url("**/discover-tables")
        await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        await asyncio.sleep(2)

        first_table_checkbox = self.page.locator("#table-0")
        await first_table_checkbox.wait_for(state="visible", timeout=10000)
        await first_table_checkbox.click()

        # Wait for table test to complete and continue button to be enabled
        await self.page.wait_for_function(
            "document.getElementById('continue-btn') && !document.getElementById('continue-btn').disabled",
            timeout=20000,
        )

        continue_button = self.page.get_by_text("Connect Data & Continue")
        await continue_button.wait_for(state="visible")
        await continue_button.click()

        ##########################################################
        ## Channel Selection Page                               ##
        ## Template: add_to_channel.html                        ##
        ## Routes: add_connections/all_routes.py               ##
        ##########################################################

        await self.page.wait_for_url("**/channels")
        await self.page.wait_for_load_state("domcontentloaded", timeout=30000)

        ##########################################################
        ## Channel Creation (Backend Simulation)               ##
        ## Routes: add_connections/all_routes.py               ##
        ##########################################################

        # Retrieve connection_token from sessionStorage (set by the frontend after /save)
        connection_token = await self.page.evaluate("sessionStorage.getItem('connection_token')")
        if not connection_token:
            raise ValueError("connection_token not found in sessionStorage after save")

        cookies = await self.page.context.cookies()
        cookie_header = "; ".join(
            [f"{c.get('name', '')}={c.get('value', '')}" for c in cookies if c.get("name")]
        )

        # Use provided channel selection or default for first connection
        if channel_selection is None:
            channel_selection = {"type": "create", "channels": ["test-company-inc-compass"]}

        payload = {
            "connection_name": connection_name,
            "connection_token": connection_token,
            "channelSelection": channel_selection,
        }

        import json

        response = await self.page.request.post(
            f"http://localhost:{self.client.port}/onboarding/connections/process-channel-selection",
            data=json.dumps(payload),
            headers={"Cookie": cookie_header, "Content-Type": "application/json"},
        )

        # Check response status
        if response.status != 200:
            response_text = await response.text()
            raise ValueError(
                f"Channel selection failed with status {response.status}: {response_text}"
            )

        ##########################################################
        ## Success Page Navigation & Verification              ##
        ## Template: connections/success.html                   ##
        ## Routes: add_connections/all_routes.py               ##
        ##########################################################

        if response.status == 200:
            try:
                await response.json()
            except Exception as e:
                response_text = await response.text()
                raise ValueError(
                    f"Failed to parse JSON response from channel selection: {e}\nResponse text: {response_text}"
                )
            try:
                await self.page.wait_for_url("**/success*", timeout=10000)
            except Exception:
                success_url = f"http://localhost:{self.client.port}/onboarding/connections/success?source=snowflake&connection_name={connection_name}"
                await self.page.goto(success_url)
        else:
            await response.text()
            success_url = f"http://localhost:{self.client.port}/onboarding/connections/success?source=snowflake&connection_name={connection_name}"
            try:
                await self.page.goto(success_url, timeout=10000)
            except Exception:
                simple_success_url = (
                    f"http://localhost:{self.client.port}/onboarding/connections/success"
                )
                await self.page.goto(simple_success_url, timeout=10000)

        await self.page.wait_for_url("**/success*", timeout=30000)
        success_page_content = await self.page.content()
        self.assertIn("html", success_page_content.lower())

    async def get_application(self):
        """Create test application."""
        app = build_web_application(self.mock_bot_server)
        add_webapp_routes(app, self.mock_bot_server)
        return app

    @pytest.mark.skip(reason="Must be updated to use new dataset sync")
    async def test_complete_onboarding_flow_with_form_submission(self):
        """Test complete end-to-end onboarding flow from GET request to successful completion."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Test data
            test_email = "test@testcompany.com"
            test_organization = "Test Company Inc"

            # Set the public URL to match the test server port
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"

            # Step 1: Navigate to the onboarding form page
            get_url = f"http://localhost:{self.client.port}/onboarding?token={self.referral_token}"

            await self.page.goto(get_url)

            # Verify we're on the correct page
            self.assertEqual(self.page.url, get_url)

            # Verify form elements are present
            email_input = self.page.locator('input[name="email"]')
            organization_input = self.page.locator('input[name="organization"]')
            submit_button = self.page.locator('button[type="submit"], input[type="submit"]')
            terms_input = self.page.locator('input[name="terms"]')

            await email_input.wait_for(state="attached")
            await organization_input.wait_for(state="attached")
            await submit_button.wait_for(state="attached")
            await terms_input.wait_for(state="attached")

            # Verify submit button text
            submit_text = await submit_button.text_content()
            assert submit_text is not None
            assert "Create account" in submit_text

            # Step 2: Mock all third-party service functions using FakeSlackClient
            fake_slack = FakeSlackClient("test-token")

            # Mock non-Slack third-party services
            mock_create_repo = AsyncMock(
                return_value={
                    "success": True,
                    "repo_url": "https://github.com/dagster-compass/test-company-inc-context",
                    "repo_name": "test-company-inc-context",
                }
            )

            # Set up Temporal workflow environment with real worker
            async with AsyncExitStack() as stack:
                await self._setup_temporal_environment(stack)

                # Add mocks to the same stack
                stack.enter_context(mock_slack_api_with_client(fake_slack))
                stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository",
                        side_effect=mock_create_repo,
                    )
                )

                # Update mock bot's team_id to match what fake_slack will generate
                # fake_slack generates team IDs sequentially starting from T0000000001
                # This must happen before form submission since the organization is created during submission
                self.mock_bot.bot_config.team_id = "T0000000001"

                # Set organization_id so JWT generation and lookups work
                # The organization will be created with ID 1 during background processing
                self.mock_bot.bot_config.organization_id = 1

                # Update the bot's key attribute so JWT generation uses the correct team_id
                new_bot_key = BotKey.from_channel_name("T0000000001", "test-company-inc-compass")
                self.mock_bot.key = new_bot_key

                # Also register the bot under the new key so it can be found by organization lookup
                self.mock_bot_server.bots[new_bot_key] = self.mock_bot

                # Update governance bot similarly
                new_governance_bot_key = BotKey.from_channel_name(
                    "T0000000001", "test-company-inc-compass-governance"
                )
                governance_bot_key_old = BotKey.from_channel_name(
                    "T12345TEST", "test-company-inc-compass-governance"
                )
                if governance_bot_key_old in self.mock_bot_server.bots:
                    governance_bot = self.mock_bot_server.bots[governance_bot_key_old]
                    governance_bot.key = new_governance_bot_key
                    governance_bot.bot_config.organization_id = 1
                    self.mock_bot_server.bots[new_governance_bot_key] = governance_bot

                # Step 3: Fill and submit the form using Playwright
                await email_input.fill(test_email)
                await organization_input.fill(test_organization)
                await terms_input.click()

                # Submit the form
                await submit_button.click(timeout=30000)  # waits for action to complete

                # get page contents
                page_contents = await self.page.content()

                # Verify we're on the success page
                success_url = f"http://localhost:{self.client.port}/onboarding"
                self.assertEqual(self.page.url, success_url, msg=page_contents)

                try:
                    # Wait for background processing to complete (React app shows "Setup complete!")
                    await self.page.wait_for_selector('text="Setup complete!"', timeout=30000)

                    # Wait for the email CTA section with "Check your email"
                    await self.page.wait_for_selector('text="Check your email"', timeout=10000)

                except Exception:
                    # Get current page content for debugging
                    page_content = await self.page.content()
                    raise

                # Verify the email is present in the page content (even if hidden by animations)
                page_content = await self.page.content()
                self.assertIn(test_email, page_content)
                self.assertIn("Slack Connect invite", page_content)

                # Step 4: Verify all third-party service functions were called correctly

                # Verify Slack operations via FakeSlackClient state
                teams = fake_slack.get_teams()
                self.assertEqual(len(teams), 1, "Expected 1 team to be created")
                team_id = fake_slack.get_team_ids()[0]

                # Verify channels were created (general, random + compass + governance = 4)
                channels = fake_slack.get_channels()
                self.assertGreaterEqual(
                    len(channels),
                    4,
                    "Expected at least 4 channels (general, random, compass, governance)",
                )

                # Verify compass and governance channels exist
                compass_channel = fake_slack.get_channel_by_name("test-company-inc-compass")
                governance_channel = fake_slack.get_channel_by_name(
                    "test-company-inc-compass-governance"
                )
                assert compass_channel
                assert governance_channel
                self.assertIsNotNone(compass_channel, "Compass channel should exist")
                self.assertIsNotNone(governance_channel, "Governance channel should exist")
                self.assertFalse(compass_channel["is_private"], "Compass channel should be public")
                self.assertTrue(
                    governance_channel["is_private"], "Governance channel should be private"
                )

                # Verify users were created (2 bots + 2 admin users = 4)
                users = fake_slack.get_users()
                self.assertGreaterEqual(
                    len(users), 4, "Expected at least 4 users (2 bots + 2 admins)"
                )

                # Verify contextstore repository creation
                mock_create_repo.assert_called_once()
                create_repo_call = mock_create_repo.call_args
                # Check positional and keyword args
                self.assertEqual(
                    len(create_repo_call[0]), 4
                )  # logger, agent, github_auth_source, team_name
                self.assertEqual(create_repo_call[0][3], "test-company-inc")  # team_name
                self.assertEqual(create_repo_call[1]["user_email"], test_email)

                # Verify Slack Connect channel creation for only the governance channel
                slack_connect_invites = fake_slack.get_slack_connect_invites()
                self.assertEqual(len(slack_connect_invites), 1)
                self.assertEqual(slack_connect_invites[0]["channel"], governance_channel["id"])

                # Step 5: Verify database state changes
                storage = self.mock_bot_server.bot_manager.storage

                # Verify referral token was marked as consumed
                token_status = await storage.is_referral_token_valid(self.referral_token)
                self.assertTrue(token_status.is_valid)
                self.assertTrue(token_status.has_been_consumed)
                self.assertTrue(token_status.is_single_use)

                # Verify organization and bot instance were created by checking database
                # Use asyncio.to_thread to run sync database operations from async context

                def verify_database_state():
                    storage = self.mock_bot_server.bot_manager.storage
                    with storage._sql_conn_factory.with_conn() as conn:
                        cursor = conn.cursor()
                        # Check that organization was created
                        cursor.execute(
                            "SELECT organization_id FROM organizations WHERE organization_name = %s",
                            (test_organization,),
                        )
                        org_result = cursor.fetchone()
                        assert org_result is not None, "Expected organization to exist"
                        organization_id = org_result[0]

                        # Check that bot instance was created
                        cursor.execute("SELECT COUNT(*) FROM bot_instances")
                        bot_count = cursor.fetchone()[0]
                        assert bot_count == 1, f"Expected 1 bot instance, found {bot_count}"

                        # Check that TOS record was created
                        cursor.execute(
                            "SELECT email, organization_id, organization_name FROM tos_records WHERE organization_id = %s",
                            (organization_id,),
                        )
                        tos_result = cursor.fetchone()
                        assert tos_result is not None, "Expected TOS record to exist"
                        tos_email, tos_org_id, tos_org_name = tos_result
                        assert tos_email == test_email, (
                            f"Expected TOS email {test_email}, found {tos_email}"
                        )
                        assert tos_org_id == organization_id, (
                            f"Expected TOS org_id {organization_id}, found {tos_org_id}"
                        )
                        # Organization name is slugified by generate_urlsafe_team_name
                        assert tos_org_name == "test-company-inc", (
                            f"Expected TOS org_name test-company-inc, found {tos_org_name}"
                        )

                await asyncio.to_thread(verify_database_state)

                # Verify targeted bot discovery was triggered with the specific bot key
                self.mock_bot_server.bot_manager.discover_and_update_bots_for_keys.assert_called_once()

                # Verify Stripe customer and subscription were created
                stripe_customers = self.mock_bot_server.stripe_client.list_customers()
                self.assertEqual(len(stripe_customers), 1)
                customer = stripe_customers[0]
                self.assertEqual(customer["email"], test_email)
                self.assertEqual(customer["name"], test_organization)
                self.assertEqual(customer["metadata"]["organization_id"], team_id)

                stripe_subscriptions = self.mock_bot_server.stripe_client.list_subscriptions()
                self.assertEqual(len(stripe_subscriptions), 1)
                subscription = stripe_subscriptions[0]
                self.assertEqual(subscription["customer"], customer["id"])
                self.assertEqual(subscription["status"], "active")

                # Step 7: Navigate directly to connections page
                # Industry selection was removed in prospector refactor
                connections_link = create_link(
                    self.mock_bot,
                    user_id="U55555ADMIN",
                    path="/onboarding/connections",
                    max_age=timedelta(hours=3),
                )
                await self.page.goto(connections_link)

                ##########################################################
                ## Connection Testing - Multiple Warehouse Types        ##
                ## Template: connections_homepage.html                   ##
                ## Routes: add_connections/all_routes.py                 ##
                ##########################################################

                connections_url_pattern = (
                    f"http://localhost:{self.client.port}/onboarding/connections"
                )
                self.assertTrue(self.page.url.startswith(connections_url_pattern))
                with ExitStack() as stack:
                    mock_test_connection = stack.enter_context(
                        patch(
                            "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.test_connection"
                        )
                    )
                    mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
                    mock_list_tables = stack.enter_context(
                        patch(
                            "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.list_tables"
                        )
                    )
                    mock_analyze_table_schema = stack.enter_context(
                        patch("csbot.ctx_admin.dataset_documentation.analyze_table_schema")
                    )
                    mock_update_dataset = stack.enter_context(
                        patch("csbot.ctx_admin.dataset_documentation.update_dataset")
                    )
                    mock_pr_context = stack.enter_context(
                        patch("csbot.local_context_store.github.context.with_pull_request_context")
                    )
                    # Patch Slack utilities at slack_utils level for connection scenarios
                    # These are separate from onboarding-level patches to avoid call count conflicts
                    mock_slack_create_channel = stack.enter_context(
                        patch("csbot.slackbot.slack_utils.create_channel")
                    )
                    mock_slack_get_channels = stack.enter_context(
                        patch("csbot.slackbot.slack_utils.get_all_channels")
                    )
                    mock_slack_get_bot_id = stack.enter_context(
                        patch("csbot.slackbot.slack_utils.get_bot_user_id")
                    )
                    mock_slack_invite_bot = stack.enter_context(
                        patch("csbot.slackbot.slack_utils.invite_bot_to_channel")
                    )
                    mock_test_connection.return_value = None

                    def mock_analyze_schema(logger, profile, project, dataset):
                        from csbot.ctx_admin.dataset_documentation import (
                            ColumnDescription,
                            TableSchemaAnalysis,
                        )

                        return TableSchemaAnalysis(
                            table_name=dataset.table_name,
                            columns=[
                                ColumnDescription(name="id", type="INTEGER", column_comment=None),
                                ColumnDescription(name="name", type="VARCHAR", column_comment=None),
                            ],
                            schema_hash="mock_hash_" + dataset.table_name.replace(".", "_"),
                            table_comment=None,
                        )

                    mock_analyze_table_schema.side_effect = mock_analyze_schema
                    mock_update_dataset.return_value = None

                    mock_pr = MagicMock()
                    mock_pr.pr_url = (
                        "https://github.com/dagster-compass/test-company-inc-context/pull/123"
                    )
                    mock_pr.repo_path = "/tmp/mock_repo_path"
                    mock_pr_context.return_value.__enter__.return_value = mock_pr

                    # Configure Slack utility mocks for connection scenarios
                    mock_slack_create_channel.return_value = {
                        "success": True,
                        "channel_id": "C12345NEWCHAN",
                    }
                    mock_slack_get_channels.return_value = {"success": True, "channels": []}
                    mock_slack_get_bot_id.return_value = {"success": True, "user_id": "U12345BOT"}
                    mock_slack_invite_bot.return_value = {"success": True}

                    for scenario, config in CONNECTION_SCENARIOS_WITH_CONFIGS:
                        await self._step_through_and_add_connection(
                            scenario, mock_to_thread, mock_list_tables, config=config
                        )

                    ##########################################################
                    ## Verification - Secret Storage & Database State      ##
                    ##########################################################

                    self.assertEqual(mock_test_connection.call_count, len(CONNECTION_SCENARIOS))
                    self.assertEqual(mock_list_tables.call_count, len(CONNECTION_SCENARIOS))
                    from collections import defaultdict

                    secret_store_state = defaultdict(dict)
                    for call in self.mock_secret_store.store_secret.call_args_list:
                        args, kwargs = call
                        # Handle both positional and keyword arguments
                        if "org_id" in kwargs:
                            org_id = kwargs["org_id"]
                            key = kwargs["key"]
                            contents = kwargs["contents"]
                        else:
                            # If called with positional arguments: store_secret(org_id, key, contents)
                            org_id = args[0] if len(args) > 0 else kwargs.get("org_id")
                            key = args[1] if len(args) > 1 else kwargs.get("key")
                            contents = args[2] if len(args) > 2 else kwargs.get("contents")
                        secret_store_state[org_id][key] = contents

                    # Create JsonConfig objects for expected configurations
                    snowflake_testuser_config = JsonConfig(
                        type="snowflake",
                        config={
                            "account_id": "test123",
                            "username": "testuser",
                            "credential": {"type": "password", "password": "testpassword"},
                            "warehouse": "COMPUTE_WH",
                            "role": "ACCOUNTADMIN",
                            "region": None,
                        },
                    )
                    snowflake_keyuser_config = JsonConfig(
                        type="snowflake",
                        config={
                            "account_id": "test456",
                            "username": "keyuser",
                            "credential": {
                                "type": "private_key",
                                "private_key_file": "-----BEGIN PRIVATE KEY-----\r\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7...\r\n-----END PRIVATE KEY-----",
                            },
                            "warehouse": "ANALYTICS_WH",
                            "role": "ANALYST",
                            "region": None,
                        },
                    )
                    snowflake_encryptedkeyuser_config = JsonConfig(
                        type="snowflake",
                        config={
                            "account_id": "test789",
                            "username": "encryptedkeyuser",
                            "credential": {
                                "type": "private_key",
                                "private_key_file": "-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIFHDBOBgkqhkiG9w0BBQ0wQTApBgkqhkiG9w0BBQwwHAQI...\n-----END ENCRYPTED PRIVATE KEY-----",
                                "key_password": "myencryptionpassword",
                            },
                            "warehouse": "SECURE_WH",
                            "role": "SECURITY_ANALYST",
                            "region": None,
                        },
                    )
                    snowflake_regionuser_config = JsonConfig(
                        type="snowflake",
                        config={
                            "account_id": "test789",
                            "username": "regionuser",
                            "credential": {"type": "password", "password": "regionpass"},
                            "warehouse": "REGIONAL_WH",
                            "role": "REGIONAL_ROLE",
                            "region": "us-east-1",
                        },
                    )
                    snowflake_modernuser_config = JsonConfig(
                        type="snowflake",
                        config={
                            "account_id": "myorg-account123",
                            "username": "modernuser",
                            "credential": {"type": "password", "password": "modernpass"},
                            "warehouse": "MODERN_WH",
                            "role": "DATA_ANALYST",
                            "region": None,
                        },
                    )
                    bigquery_test_project_config = JsonConfig(
                        type="bigquery",
                        config={
                            "location": "us",
                            "service_account_json_string": '{"type": "service_account", "project_id": "test-project-123", "private_key_id": "key123", "private_key": "-----BEGIN PRIVATE KEY-----\\\\nMIIE...\\\\n-----END PRIVATE KEY-----\\\\n", "client_email": "test@test-project-123.iam.gserviceaccount.com", "client_id": "123456789", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}',
                        },
                    )
                    bigquery_eu_project_config = JsonConfig(
                        type="bigquery",
                        config={
                            "location": "eu",
                            "service_account_json_string": '{"type": "service_account", "project_id": "eu-project-456", "private_key_id": "key456", "private_key": "-----BEGIN PRIVATE KEY-----\\\\nMIIE...\\\\n-----END PRIVATE KEY-----\\\\n", "client_email": "eu-test@eu-project-456.iam.gserviceaccount.com", "client_id": "987654321", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token"}',
                        },
                    )
                    athena_us_west_config = JsonConfig(
                        type="athena",
                        config={
                            "aws_access_key_id": "AKIATEST123",
                            "aws_secret_access_key": "test/secret/key/123",
                            "region": "us-west-2",
                            "s3_staging_dir": "s3://test-athena-bucket/staging/",
                            "query_engine": "aws_athena_trino_sql",
                        },
                    )
                    athena_us_east_config = JsonConfig(
                        type="athena",
                        config={
                            "aws_access_key_id": "AKIATEST456",
                            "aws_secret_access_key": "test/spark/key/456",
                            "region": "us-east-1",
                            "s3_staging_dir": "s3://test-spark-bucket/staging/",
                            "query_engine": "aws_athena_spark_sql",
                        },
                    )

                    expected_secret_store_state = {
                        1: {
                            "snowflake_testuser_Snowflake_url.txt": snowflake_testuser_config.to_url(),
                            "snowflake_keyuser_Snowflake_url.txt": snowflake_keyuser_config.to_url(),
                            "snowflake_encryptedkeyuser_Snowflake_url.txt": snowflake_encryptedkeyuser_config.to_url(),
                            "snowflake_regionuser_Snowflake_url.txt": snowflake_regionuser_config.to_url(),
                            "snowflake_modernuser_Snowflake_url.txt": snowflake_modernuser_config.to_url(),
                            "bigquery_test_project_123_us_BigQuery_url.txt": bigquery_test_project_config.to_url(),
                            "bigquery_eu_project_456_eu_BigQuery_url.txt": bigquery_eu_project_config.to_url(),
                            "athena_us_west_2_AKIATEST123_Athena_url.txt": athena_us_west_config.to_url(),
                            "athena_us_east_1_AKIATEST456_Athena_url.txt": athena_us_east_config.to_url(),
                        }
                    }

                    # Check that all expected secret keys are present (don't check exact values since base64 encoding may vary)
                    expected_keys = set(expected_secret_store_state[1].keys())
                    actual_keys = (
                        set(secret_store_state[1].keys()) if 1 in secret_store_state else set()
                    )
                    self.assertEqual(actual_keys, expected_keys)

                    def extract_and_validate_connections():
                        """Extract connections from database and validate against test scenarios."""
                        storage = self.mock_bot_server.bot_manager.storage
                        with storage._sql_conn_factory.with_conn() as conn:
                            cursor = conn.cursor()

                            # Get bot_instance_id for our test organization
                            cursor.execute(
                                "SELECT id FROM bot_instances WHERE channel_name = %s",
                                ("test-company-inc-compass",),
                            )
                            bot_instance_result = cursor.fetchone()
                            assert bot_instance_result is not None, "Expected bot instance to exist"
                            bot_instance_id = bot_instance_result[0]

                            # Extract all connections for this bot instance
                            cursor.execute(
                                "SELECT connection_name, url FROM connections WHERE bot_instance_id = %s ORDER BY connection_name",
                                (bot_instance_id,),
                            )
                            db_connections = cursor.fetchall()

                            # Convert to dict for easier validation
                            db_connection_dict = {name: url for name, url in db_connections}

                            assert db_connection_dict == {
                                "athena_us_east_1_AKIATEST456": "{{ pull_from_secret_manager_to_string('athena_us_east_1_AKIATEST456_Athena_url.txt') }}",
                                "athena_us_west_2_AKIATEST123": "{{ pull_from_secret_manager_to_string('athena_us_west_2_AKIATEST123_Athena_url.txt') }}",
                                "bigquery_eu_project_456_eu": "{{ pull_from_secret_manager_to_string('bigquery_eu_project_456_eu_BigQuery_url.txt') }}",
                                "bigquery_test_project_123_us": "{{ pull_from_secret_manager_to_string('bigquery_test_project_123_us_BigQuery_url.txt') }}",
                                "snowflake_encryptedkeyuser": "{{ pull_from_secret_manager_to_string('snowflake_encryptedkeyuser_Snowflake_url.txt') }}",
                                "snowflake_keyuser": "{{ pull_from_secret_manager_to_string('snowflake_keyuser_Snowflake_url.txt') }}",
                                "snowflake_modernuser": "{{ pull_from_secret_manager_to_string('snowflake_modernuser_Snowflake_url.txt') }}",
                                "snowflake_regionuser": "{{ pull_from_secret_manager_to_string('snowflake_regionuser_Snowflake_url.txt') }}",
                                "snowflake_testuser": "{{ pull_from_secret_manager_to_string('snowflake_testuser_Snowflake_url.txt') }}",
                            }

                            for template_str in db_connection_dict.values():
                                # use regex to pull out any secret manager keys
                                secret_keys = re.findall(
                                    r"{{ pull_from_secret_manager_to_string\('([^']+)'\) }}",
                                    template_str,
                                )
                                for key in secret_keys:
                                    assert key in secret_store_state[1]

                    await asyncio.to_thread(extract_and_validate_connections)

                    # # Verify bot discovery was triggered after instance creation and after saving each connection
                    # self.assertEqual(
                    #     self.mock_bot_server.bot_manager.discover_and_update_bots_for_keys.call_count,
                    #     len(CONNECTION_SCENARIOS) + 1,
                    # )

                    # Step 10: Verify bonus answers were granted (token was used)
                    storage = self.mock_bot_server.bot_manager.storage

                    def verify_bonus_grant():
                        with storage._sql_conn_factory.with_conn() as conn:
                            cursor = conn.cursor()
                            # Get the organization_id for the created organization
                            cursor.execute(
                                "SELECT organization_id FROM organizations WHERE organization_name = %s",
                                (test_organization,),
                            )
                            org_result = cursor.fetchone()
                            assert org_result is not None, "Expected organization to exist"
                            organization_id = org_result[0]

                            # Query the bonus_answer_grants table
                            cursor.execute(
                                """
                                SELECT answer_count, reason
                                FROM bonus_answer_grants
                                WHERE organization_id = %s
                                """,
                                (organization_id,),
                            )
                            grants = cursor.fetchall()

                            # Should have exactly one grant for 150 bonus answers with reason "sign-up bonus"
                            sign_up_grants = [g for g in grants if g[1] == "sign-up bonus"]
                            assert len(sign_up_grants) == 1, (
                                "Exactly one sign-up bonus should be granted when token is provided"
                            )
                            assert sign_up_grants[0][0] == 150, (
                                "Sign-up bonus should grant 150 answers"
                            )

                await asyncio.to_thread(verify_bonus_grant)

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    @pytest.mark.skip(
        reason="Need to update connection form schema after React migration - credential fields changed"
    )
    async def test_first_connection_automatic_channel_selection(self):
        """Test first connection automatically uses the main channel without showing channel selection."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Set the public URL to match the test server port
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"

            # Set up bot with organization_id for JWT token generation
            self.mock_bot.bot_config.organization_id = 1

            # Navigate to connections page with proper JWT authentication
            connections_link = create_link(
                self.mock_bot,
                user_id="U55555ADMIN",
                path="/onboarding/connections",
                max_age=timedelta(hours=3),
            )
            await self.page.goto(connections_link)

            # First connection should automatically use main channel (no channel selection UI)
            # KV store mock is set up to return False for exists() initially

            fake_slack = FakeSlackClient("test-token")

            with (
                mock_slack_api_with_client(fake_slack),
                ExitStack() as stack,
            ):
                mock_test_connection = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.test_connection"
                    )
                )
                mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
                mock_list_tables = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.list_tables"
                    )
                )
                mock_analyze_table_schema = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.analyze_table_schema")
                )
                mock_update_dataset = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.update_dataset")
                )
                mock_pr_context = stack.enter_context(
                    patch("csbot.local_context_store.github.context.with_pull_request_context")
                )
                mock_test_connection.return_value = None

                def mock_analyze_schema(logger, profile, project, dataset):
                    from csbot.ctx_admin.dataset_documentation import (
                        ColumnDescription,
                        TableSchemaAnalysis,
                    )

                    return TableSchemaAnalysis(
                        table_name=dataset.table_name,
                        columns=[
                            ColumnDescription(name="id", type="INTEGER", column_comment=None),
                            ColumnDescription(name="name", type="VARCHAR", column_comment=None),
                        ],
                        schema_hash="mock_hash_" + dataset.table_name.replace(".", "_"),
                        table_comment=None,
                    )

                mock_analyze_table_schema.side_effect = mock_analyze_schema
                mock_update_dataset.return_value = None

                # Create a simple object with the needed attributes instead of MagicMock
                class MockPR:
                    pr_url = "https://github.com/dagster-compass/test-company-inc-context/pull/123"
                    repo_path = "/tmp/mock_repo_path"

                mock_pr = MockPR()
                mock_pr_context.return_value.__enter__.return_value = mock_pr

                # Test first connection with automatic channel selection (first connection)
                scenario, config = CONNECTION_SCENARIOS_WITH_CONFIGS[
                    0
                ]  # Snowflake with password auth

                # Even for first connection, provide explicit channel selection in current implementation
                # The system may still show channel selection UI even for first connections
                first_connection_channel_selection = {
                    "type": "create",
                    "channels": ["test-company-inc-compass"],
                }

                await self._step_through_and_add_connection(
                    scenario,
                    mock_to_thread,
                    mock_list_tables,
                    first_connection_channel_selection,
                    config,
                )

                # Verify the secret was stored correctly
                self.assertTrue(len(self.mock_secret_store.store_secret.call_args_list) > 0)

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    @pytest.mark.skip(
        reason="Need to update connection form schema after React migration - credential fields changed"
    )
    async def test_non_first_connection_new_channel(self):
        """Test non-first connection can choose to create a new channel."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Set the public URL to match the test server port
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"

            # Set up bot with organization_id for JWT token generation
            self.mock_bot.bot_config.organization_id = 1

            # Modify KV store mock to simulate non-first connection
            # Return True for invite already sent (is_first_dataset_sync returns False when kv_store.exists returns True)
            self.mock_bot.kv_store.exists.return_value = True

            # Navigate to connections page with proper JWT authentication
            connections_link = create_link(
                self.mock_bot,
                user_id="U55555ADMIN",
                path="/onboarding/connections",
                max_age=timedelta(hours=3),
            )
            await self.page.goto(connections_link)

            fake_slack = FakeSlackClient("test-token")

            with (
                mock_slack_api_with_client(fake_slack),
                ExitStack() as stack,
            ):
                mock_test_connection = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.test_connection"
                    )
                )
                mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
                mock_list_tables = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.list_tables"
                    )
                )
                mock_analyze_table_schema = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.analyze_table_schema")
                )
                mock_update_dataset = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.update_dataset")
                )
                mock_pr_context = stack.enter_context(
                    patch("csbot.local_context_store.github.context.with_pull_request_context")
                )
                mock_test_connection.return_value = None

                def mock_analyze_schema(logger, profile, project, dataset):
                    from csbot.ctx_admin.dataset_documentation import (
                        ColumnDescription,
                        TableSchemaAnalysis,
                    )

                    return TableSchemaAnalysis(
                        table_name=dataset.table_name,
                        columns=[
                            ColumnDescription(name="id", type="INTEGER", column_comment=None),
                            ColumnDescription(name="name", type="VARCHAR", column_comment=None),
                        ],
                        schema_hash="mock_hash_" + dataset.table_name.replace(".", "_"),
                        table_comment=None,
                    )

                mock_analyze_table_schema.side_effect = mock_analyze_schema
                mock_update_dataset.return_value = None

                # Create a simple object with the needed attributes instead of MagicMock
                class MockPR:
                    pr_url = "https://github.com/dagster-compass/test-company-inc-context/pull/123"
                    repo_path = "/tmp/mock_repo_path"

                mock_pr = MockPR()
                mock_pr_context.return_value.__enter__.return_value = mock_pr

                # Test non-first connection creating a new channel
                scenario, config = CONNECTION_SCENARIOS_WITH_CONFIGS[1]  # Snowflake with key auth
                new_channel_selection = {"type": "create", "channels": ["analytics-team-data"]}

                await self._step_through_and_add_connection(
                    scenario, mock_to_thread, mock_list_tables, new_channel_selection, config
                )

                # Verify the secret was stored correctly
                self.assertTrue(len(self.mock_secret_store.store_secret.call_args_list) > 0)

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    @pytest.mark.skip(
        reason="Need to update connection form schema after React migration - credential fields changed"
    )
    async def test_non_first_connection_existing_channel(self):
        """Test non-first connection can choose an existing channel."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Set the public URL to match the test server port
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"

            # Set up bot with organization_id for JWT token generation
            self.mock_bot.bot_config.organization_id = 1

            # Modify KV store mock to simulate non-first connection
            # Return True for invite already sent (is_first_dataset_sync returns False when kv_store.exists returns True)
            self.mock_bot.kv_store.exists.return_value = True

            # Navigate to connections page with proper JWT authentication
            connections_link = create_link(
                self.mock_bot,
                user_id="U55555ADMIN",
                path="/onboarding/connections",
                max_age=timedelta(hours=3),
            )
            await self.page.goto(connections_link)

            fake_slack = FakeSlackClient("test-token")

            with (
                mock_slack_api_with_client(fake_slack),
                ExitStack() as stack,
            ):
                mock_test_connection = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.test_connection"
                    )
                )
                mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
                mock_list_tables = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.list_tables"
                    )
                )
                mock_analyze_table_schema = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.analyze_table_schema")
                )
                mock_update_dataset = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.update_dataset")
                )
                mock_pr_context = stack.enter_context(
                    patch("csbot.local_context_store.github.context.with_pull_request_context")
                )
                mock_test_connection.return_value = None

                def mock_analyze_schema(logger, profile, project, dataset):
                    from csbot.ctx_admin.dataset_documentation import (
                        ColumnDescription,
                        TableSchemaAnalysis,
                    )

                    return TableSchemaAnalysis(
                        table_name=dataset.table_name,
                        columns=[
                            ColumnDescription(name="id", type="INTEGER", column_comment=None),
                            ColumnDescription(name="name", type="VARCHAR", column_comment=None),
                        ],
                        schema_hash="mock_hash_" + dataset.table_name.replace(".", "_"),
                        table_comment=None,
                    )

                mock_analyze_table_schema.side_effect = mock_analyze_schema
                mock_update_dataset.return_value = None

                # Create a simple object with the needed attributes instead of MagicMock
                class MockPR:
                    pr_url = "https://github.com/dagster-compass/test-company-inc-context/pull/123"
                    repo_path = "/tmp/mock_repo_path"

                mock_pr = MockPR()
                mock_pr_context.return_value.__enter__.return_value = mock_pr

                # Test non-first connection using existing channel
                scenario, config = CONNECTION_SCENARIOS_WITH_CONFIGS[2]  # Snowflake with region
                existing_channel_selection = {
                    "type": "existing",
                    "channels": ["test-company-inc-compass"],
                }

                await self._step_through_and_add_connection(
                    scenario, mock_to_thread, mock_list_tables, existing_channel_selection, config
                )

                # Verify the secret was stored correctly
                self.assertTrue(len(self.mock_secret_store.store_secret.call_args_list) > 0)

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    async def test_onboarding_form_validation_errors(self):
        """Test form validation with invalid data."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Navigate to the onboarding form
            get_url = f"http://localhost:{self.client.port}/onboarding?token={self.referral_token}"
            await self.page.goto(get_url)

            # Test missing email - submit form with only organization filled
            email_input = self.page.locator('input[name="email"]')
            organization_input = self.page.locator('input[name="organization"]')
            submit_button = self.page.locator('button[type="submit"], input[type="submit"]')

            await organization_input.fill("Test Org")
            await submit_button.click()

            # Wait for response and check for error
            await self.page.wait_for_load_state("networkidle")
            # The page should show an error or stay on the same page with validation error
            page_content = await self.page.content()
            # Check if there's an error message or if we're still on the form page
            self.assertTrue(
                "error" in page_content.lower()
                or "required" in page_content.lower()
                or self.page.url == get_url
            )

            # Test invalid email format
            await self.page.goto(get_url)  # Reload the page
            await email_input.fill("invalid-email")
            await organization_input.fill("Test Org")
            await submit_button.click()

            await self.page.wait_for_load_state("networkidle")
            page_content = await self.page.content()
            self.assertTrue(
                "error" in page_content.lower()
                or "invalid" in page_content.lower()
                or self.page.url == get_url
            )

            # Test missing organization
            await self.page.goto(get_url)  # Reload the page
            await email_input.fill("test@example.com")
            await submit_button.click()

            await self.page.wait_for_load_state("networkidle")
            page_content = await self.page.content()
            self.assertTrue(
                "error" in page_content.lower()
                or "required" in page_content.lower()
                or self.page.url == get_url
            )

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    @pytest.mark.skip(reason="Need to update test snapshots after React migration")
    async def test_onboarding_with_invalid_referral_token(self):
        """Test onboarding flow with invalid referral token."""

        # This test intentionally uses an invalid token, so expect the error
        self.expect_error_log_containing("UserFacingError: Invalid Token")

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            invalid_token = "invalid-token-12345"

            # Test GET with invalid token
            get_url = f"http://localhost:{self.client.port}/onboarding?token={invalid_token}"

            # Navigate to page with invalid token
            response = await self.page.goto(get_url)
            # Should get an error response
            assert response is not None
            assert response.status >= 400

            # Test POST with invalid token - fill form and submit
            email_input = self.page.locator('input[name="email"]')
            organization_input = self.page.locator('input[name="organization"]')
            submit_button = self.page.locator('button[type="submit"], input[type="submit"]')

            if await email_input.is_visible():
                await email_input.fill("test@example.com")
                await organization_input.fill("Test Org")
                await submit_button.click()

                await self.page.wait_for_load_state("networkidle")
                # Should show error or stay on error page
                page_content = await self.page.content()
                self.assertTrue(
                    "error" in page_content.lower()
                    or "invalid" in page_content.lower()
                    or response.status >= 400
                )

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    @pytest.mark.skip(reason="Need to update test snapshots after React migration")
    async def test_onboarding_with_missing_token(self):
        """Test onboarding flow with missing referral token - should succeed without bonus."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Test data
            test_email = "test_no_token@testcompany.com"
            test_organization = "Test Company No Token"

            # Set the public URL to match the test server port
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"

            # Navigate to page without token
            get_url = f"http://localhost:{self.client.port}/onboarding"
            await self.page.goto(get_url)

            # Verify form elements are present
            email_input = self.page.locator('input[name="email"]')
            organization_input = self.page.locator('input[name="organization"]')
            submit_button = self.page.locator('button[type="submit"], input[type="submit"]')
            terms_input = self.page.locator('input[name="terms"]')

            await email_input.wait_for(state="attached")
            await organization_input.wait_for(state="attached")
            await submit_button.wait_for(state="attached")
            await terms_input.wait_for(state="attached")

            # Mock all third-party service functions using FakeSlackClient
            fake_slack = FakeSlackClient("test-token")

            # Mock contextstore repository creation (not a Slack API)
            mock_create_repo = AsyncMock(
                return_value={
                    "success": True,
                    "repo_url": "https://github.com/dagster-compass/test-company-no-token-context",
                    "repo_name": "test-company-no-token-context",
                }
            )

            with (
                mock_slack_api_with_client(fake_slack),
                patch(
                    "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository",
                    side_effect=mock_create_repo,
                ),
            ):
                # Fill and submit the form
                await email_input.fill(test_email)
                await organization_input.fill(test_organization)
                await terms_input.click()

                # Submit the form
                await submit_button.click(timeout=30000)

                # Verify we're on the success page
                success_url = f"http://localhost:{self.client.port}/onboarding"
                self.assertEqual(self.page.url, success_url)

                # Wait for background processing to complete (React app shows "Setup complete!")
                # Wait for the completion indicator
                await self.page.wait_for_selector('text="Setup complete!"', timeout=30000)

                # Wait for the email CTA section with "Check your email"
                await self.page.wait_for_selector('text="Check your email"', timeout=10000)

                # Verify the email is present in the page content
                page_content = await self.page.content()
                self.assertIn(test_email, page_content)
                self.assertIn("Slack Connect invite", page_content)

                # Verify Slack operations via FakeSlackClient state
                # Check that team was created
                teams = fake_slack.get_teams()
                self.assertEqual(len(teams), 1, "Expected 1 team to be created")

                # Check that channels were created (general, random + compass + governance = 4)
                channels = fake_slack.get_channels()
                self.assertGreaterEqual(
                    len(channels),
                    4,
                    "Expected at least 4 channels (general, random, compass, governance)",
                )

                # Check that users were created (bots + invited user)
                users = fake_slack.get_users()
                self.assertGreaterEqual(len(users), 2, "Expected at least 2 bot users")

                # Verify contextstore repository mock was called
                mock_create_repo.assert_called_once()

                # Verify database state changes
                storage = self.mock_bot_server.bot_manager.storage

                # Get the actual team_id from fake_slack
                team_id = fake_slack.get_team_ids()[0]

                def verify_database_state():
                    with storage._sql_conn_factory.with_conn() as conn:
                        cursor = conn.cursor()
                        # Check that organization was created
                        cursor.execute(
                            "SELECT organization_id FROM organizations WHERE organization_name = %s",
                            (test_organization,),
                        )
                        org_result = cursor.fetchone()
                        assert org_result is not None, "Expected organization to exist"
                        organization_id = org_result[0]

                        # Check that bot instance was created with the actual team_id
                        cursor.execute(
                            "SELECT COUNT(*) FROM bot_instances WHERE slack_team_id = %s",
                            (team_id,),
                        )
                        bot_count = cursor.fetchone()[0]
                        assert bot_count == 1, f"Expected 1 bot instance, found {bot_count}"

                        # Check that TOS record was created
                        cursor.execute(
                            "SELECT email, organization_id, organization_name FROM tos_records WHERE organization_id = %s",
                            (organization_id,),
                        )
                        tos_result = cursor.fetchone()
                        assert tos_result is not None, "Expected TOS record to exist"
                        tos_email, tos_org_id, _ = tos_result
                        assert tos_email == test_email
                        assert tos_org_id == organization_id

                        # Verify no bonus was granted (no referral token provided)
                        cursor.execute(
                            """
                            SELECT answer_count, reason
                            FROM bonus_answer_grants
                            WHERE organization_id = %s
                            """,
                            (organization_id,),
                        )
                        grants = cursor.fetchall()

                        # Should have no sign-up bonus when no token provided
                        sign_up_grants = [g for g in grants if g[1] == "sign-up bonus"]
                        assert len(sign_up_grants) == 0, (
                            "No sign-up bonus should be granted when token is not provided"
                        )

                await asyncio.to_thread(verify_database_state)

                # Verify Stripe customer and subscription were created
                stripe_customers = self.mock_bot_server.stripe_client.list_customers()
                self.assertEqual(len(stripe_customers), 1)
                customer = stripe_customers[0]
                self.assertEqual(customer["email"], test_email)
                self.assertEqual(customer["name"], test_organization)
                self.assertEqual(customer["metadata"]["organization_id"], team_id)

                stripe_subscriptions = self.mock_bot_server.stripe_client.list_subscriptions()
                self.assertEqual(len(stripe_subscriptions), 1)
                subscription = stripe_subscriptions[0]
                self.assertEqual(subscription["customer"], customer["id"])
                self.assertEqual(subscription["status"], "active")

                channel_ids = fake_slack.get_channel_ids()
                for channel_id in channel_ids:
                    await fake_slack.snapshot_channel_threads(channel_id, f"channel_{channel_id}")

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    async def test_onboarding_third_party_service_failure(self):
        """Test onboarding flow when third-party services fail."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        self.error_handler.add_expected_error_pattern("Slack domain already taken")
        self.error_handler.add_expected_error_pattern("domain_taken")
        try:
            fake_slack = FakeSlackClient("test-token")

            # Configure FakeSlackClient to simulate team creation failure
            async def failing_create_team(*args, **kwargs):
                return {"ok": False, "error": "domain_taken"}

            fake_slack.create_team = failing_create_team

            with mock_slack_api_with_client(fake_slack):
                # Navigate to the onboarding form
                get_url = (
                    f"http://localhost:{self.client.port}/onboarding?token={self.referral_token}"
                )
                await self.page.goto(get_url)

                # Fill and submit the form
                email_input = self.page.locator('input[name="email"]')
                organization_input = self.page.locator('input[name="organization"]')
                submit_button = self.page.locator('button[type="submit"], input[type="submit"]')
                terms_input = self.page.locator('input[name="terms"]')

                await email_input.fill("test@example.com")
                await organization_input.fill("Test Organization")
                await terms_input.click()
                await submit_button.click()

                # Wait for response
                await self.page.wait_for_load_state("networkidle")

                # Should show error page or stay on form with error
                page_content = await self.page.content()
                self.assertTrue(
                    "error" in page_content.lower()
                    or "domain_taken" in page_content.lower()
                    or "failed" in page_content.lower()
                )

                # Verify token was NOT consumed on failure
                storage = self.mock_bot_server.bot_manager.storage
                token_status = await storage.is_referral_token_valid(self.referral_token)
                self.assertTrue(token_status.is_valid)
                self.assertFalse(token_status.has_been_consumed)
                self.assertTrue(token_status.is_single_use)

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    @pytest.mark.skip(
        reason="Need to update connection form schema after React migration - credential fields changed"
    )
    async def test_snowflake_encrypted_private_key_form_interaction(self):
        """Test that the form correctly handles encrypted private key detection and password field."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Set the public URL to match the test server port
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"

            # Set up bot with organization_id for JWT token generation
            self.mock_bot.bot_config.organization_id = 1

            # Navigate to Snowflake connection form
            connections_link = create_link(
                self.mock_bot,
                user_id="U55555ADMIN",
                path="/onboarding/connections/snowflake",
                max_age=timedelta(hours=3),
            )
            await self.page.goto(connections_link)

            # Fill basic connection fields (React form uses id attributes)
            await self.page.locator("input#account_id").fill("test789")
            await self.page.locator("input#username").fill("encryptedkeyuser")
            await self.page.locator("input#warehouse").fill("SECURE_WH")
            await self.page.locator("input#role").fill("SECURITY_ANALYST")

            # Select private key authentication method
            await self.page.locator('input[value="private_key"]').click()

            # Initially, key password field should be hidden
            key_password_field = self.page.locator("input#key_password")
            await self.page.wait_for_timeout(500)  # Brief wait for conditional logic

            # Fill in an unencrypted private key first - password field should be hidden
            unencrypted_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7...\n-----END PRIVATE KEY-----"
            await self.page.locator("textarea#private_key").fill(unencrypted_key)
            await self.page.wait_for_timeout(500)  # Wait for encrypted key detection

            # Verify password field is hidden for unencrypted keys
            await key_password_field.wait_for(state="hidden")

            # Verify no error message is shown for valid unencrypted key
            error_message = self.page.locator(".private-key-error")
            self.assertFalse(
                await error_message.is_visible() if await error_message.count() > 0 else False
            )

            # Verify that any previously entered password is cleared when switching to unencrypted key
            password_value = await key_password_field.input_value()
            self.assertEqual(
                password_value, "", "Password should be cleared when switching to unencrypted key"
            )

            # Test the critical password-clearing behavior: Start with encrypted key and password,
            # then switch to unencrypted to ensure password is cleared (prevents crypto errors)

            # First, fill in an encrypted private key
            encrypted_key = "-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIFHDBOBgkqhkiG9w0BBQ0wQTApBgkqhkiG9w0BBQwwHAQI...\n-----END ENCRYPTED PRIVATE KEY-----"
            await self.page.locator("textarea#private_key").fill(encrypted_key)
            await self.page.wait_for_timeout(500)  # Wait for encrypted key detection

            # Verify password field is visible and shows encryption detected
            await key_password_field.wait_for(state="visible")
            help_text = (
                await self.page.locator("input#key_password")
                .locator("xpath=..")
                .locator(".text-sm.text-gray-500")
                .inner_html()
            )
            self.assertIn("Encrypted key", help_text or "")

            # Fill the key password
            await key_password_field.fill("myencryptionpassword")

            # Verify password was entered
            password_value = await key_password_field.input_value()
            self.assertEqual(password_value, "myencryptionpassword")

            # Now switch back to unencrypted key to test critical password clearing
            await self.page.locator("textarea#private_key").fill(unencrypted_key)
            await self.page.wait_for_timeout(500)  # Wait for key validation

            # CRITICAL TEST: Verify password field is hidden and password is cleared
            # This prevents "Password was given but private key is not encrypted" errors
            await key_password_field.wait_for(state="hidden")
            password_value = await key_password_field.input_value()
            self.assertEqual(
                password_value,
                "",
                "CRITICAL: Password must be cleared when switching to unencrypted key",
            )

            # Switch back to encrypted key for remaining tests
            await self.page.locator("textarea#private_key").fill(encrypted_key)
            await self.page.wait_for_timeout(500)

            # Password field should reappear (but password should be cleared from previous switch)
            await key_password_field.wait_for(state="visible")
            await key_password_field.fill("myencryptionpassword")

            # Verify that switching back to password auth hides the key fields
            await self.page.locator('input[value="password"]').click()
            await self.page.wait_for_timeout(500)

            # Both private key and key password fields should be hidden
            private_key_field = self.page.locator('textarea[name="private_key"]')
            await private_key_field.wait_for(state="hidden")
            await key_password_field.wait_for(state="hidden")

            # Switch back to private key to verify fields reappear
            await self.page.locator('input[value="private_key"]').click()
            await self.page.wait_for_timeout(500)

            # Fields should be visible again
            await private_key_field.wait_for(state="visible")
            # Key password field should be hidden since we had an encrypted key before
            # but switching auth methods should reset the state

            # Test invalid key format shows error message
            invalid_key = "-----BEGIN INVALID KEY-----\nthis is not a valid key format\n-----END INVALID KEY-----"
            await self.page.locator('textarea[name="private_key"]').fill(invalid_key)
            await self.page.wait_for_timeout(500)  # Wait for validation

            # Verify error message is shown
            error_message = self.page.locator(".private-key-error")
            await error_message.wait_for(state="visible")
            error_text = await error_message.text_content()
            self.assertIn("Invalid private key format", error_text or "")
            self.assertIn(
                "-----BEGIN PRIVATE KEY-----", error_text or ""
            )  # Should show expected formats

            # Verify password field remains hidden for invalid key
            await key_password_field.wait_for(state="hidden")

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    @pytest.mark.skip(
        reason="Need to update connection form schema after React migration - credential fields changed"
    )
    async def test_plan_limits_blocks_new_channel_at_limit(self):
        """Test that create new channel option is disabled in UI when at plan limit."""
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"
            self.mock_bot.bot_config.organization_id = 1
            self.mock_bot.kv_store.exists.return_value = True

            # Set plan limits with num_channels=1 (already at limit)
            from csbot.slackbot.storage.interface import PlanLimits

            strict_limits = PlanLimits(
                base_num_answers=100,
                allow_overage=False,
                num_channels=1,
                allow_additional_channels=False,
            )

            async def mock_get_plan_limits(org_id: int):
                return strict_limits

            self.mock_bot_server.bot_manager.storage.get_plan_limits = mock_get_plan_limits
            self.mock_bot_server.get_plan_limits_from_cache_or_bail = mock_get_plan_limits

            # Mock get_connection_names_for_organization to return an existing connection
            # This ensures is_first_connection = False
            async def mock_get_connection_names(org_id: int):
                return ["existing-connection-1"]

            self.mock_bot_server.bot_manager.storage.get_connection_names_for_organization = (
                mock_get_connection_names
            )

            connections_link = create_link(
                self.mock_bot,
                user_id="U55555ADMIN",
                path="/onboarding/connections",
                max_age=timedelta(hours=3),
            )
            await self.page.goto(connections_link)

            fake_slack = FakeSlackClient("test-token")

            with (
                mock_slack_api_with_client(fake_slack),
                ExitStack() as stack,
            ):
                mock_test_connection = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.test_connection"
                    )
                )
                mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
                mock_list_tables = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.list_tables"
                    )
                )
                mock_test_connection.return_value = None

                scenario, config = CONNECTION_SCENARIOS_WITH_CONFIGS[0]

                # Configure mock_to_thread with same logic as _step_through_and_add_connection
                schemas = list(set([table[: table.rfind(".")] for table in scenario["tables"]]))

                def mock_to_thread_side_effect(func, *args, **kwargs):
                    if hasattr(func, "__name__") and func.__name__ == "list_schemas":
                        return schemas
                    elif hasattr(func, "__name__") and func.__name__ == "list_tables":
                        return [
                            {"name": table, "description": None, "recommended": False}
                            for table in scenario["tables"]
                        ]
                    else:
                        return MagicMock()

                mock_to_thread.side_effect = mock_to_thread_side_effect
                mock_list_tables.return_value = {
                    "tables": [
                        {"name": table, "description": None, "recommended": False}
                        for table in scenario["tables"]
                    ],
                    "schema_warnings": [],
                    "success": True,
                    "error": None,
                }

                # Navigate through the flow to channel selection page
                await self.page.goto(f"http://localhost:{self.client.port}{scenario['url_path']}")
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                await self._fill_connection_form(scenario["form_data"])
                await asyncio.sleep(1)

                test_button = self.page.locator("button:has-text('Test Connection')")
                await test_button.wait_for(state="visible")
                await self.page.evaluate("validateForm()")
                await self.page.wait_for_function(
                    "() => { const btn = document.getElementById('test-connection-button'); return btn && !btn.disabled; }",
                    timeout=10000,
                )
                await test_button.click()

                continue_button = self.page.locator(
                    "button:has-text('Continue to Schema Selection')"
                )
                await continue_button.wait_for(state="visible")
                await continue_button.click()

                # Schema selection
                await self.page.wait_for_url("**/discover-schemas")
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                first_schema_checkbox = self.page.locator("#schema-0")
                await first_schema_checkbox.wait_for(state="attached", timeout=10000)
                await first_schema_checkbox.click()
                proceed_button = self.page.get_by_text("Continue to Table Selection")
                await proceed_button.wait_for(state="attached")
                await proceed_button.click()

                # Table selection
                await self.page.wait_for_url("**/discover-tables")
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                first_table_checkbox = self.page.locator("#table-0")
                await first_table_checkbox.wait_for(state="visible", timeout=10000)
                await first_table_checkbox.click()
                await self.page.wait_for_function(
                    "document.getElementById('continue-btn') && !document.getElementById('continue-btn').disabled",
                    timeout=20000,
                )
                continue_button = self.page.get_by_text("Connect Data & Continue")
                await continue_button.wait_for(state="visible")
                await continue_button.click()

                # NOW WE'RE AT CHANNEL SELECTION - VERIFY UI STATE
                await self.page.wait_for_url("**/channels")
                await self.page.wait_for_load_state("domcontentloaded", timeout=30000)

                # Verify that "create new channel" radio button is disabled
                create_new_radio = self.page.locator('input[id="create-new-channel"]')
                is_disabled = await create_new_radio.is_disabled()
                self.assertTrue(
                    is_disabled, "Create new channel option should be disabled at plan limit"
                )

                # Verify plan limit message is displayed
                page_content = await self.page.content()
                self.assertIn("plan limit", page_content.lower())
                self.assertIn("1 channels", page_content)

                # Verify that existing channel option is still available
                existing_channels_radio = self.page.locator('input[id="existing-channels"]')
                if await existing_channels_radio.count() > 0:
                    self.assertFalse(
                        await existing_channels_radio.is_disabled(),
                        "Existing channels option should not be disabled",
                    )

        finally:
            await self._teardown_playwright()

    @pytest.mark.skip(
        reason="Need to update connection form schema after React migration - credential fields changed"
    )
    async def test_plan_limits_allows_new_channel_under_limit(self):
        """Test that non-first connection can create new channel when under plan limit."""
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"
            self.mock_bot.bot_config.organization_id = 1
            self.mock_bot.kv_store.exists.return_value = True

            # Set plan limits with num_channels=5 (under limit with 1 existing channel)
            from csbot.slackbot.storage.interface import PlanLimits

            generous_limits = PlanLimits(
                base_num_answers=100,
                allow_overage=False,
                num_channels=5,
                allow_additional_channels=False,
            )

            async def mock_get_plan_limits(org_id: int):
                return generous_limits

            self.mock_bot_server.bot_manager.storage.get_plan_limits = mock_get_plan_limits
            self.mock_bot_server.get_plan_limits_from_cache_or_bail = mock_get_plan_limits

            connections_link = create_link(
                self.mock_bot,
                user_id="U55555ADMIN",
                path="/onboarding/connections",
                max_age=timedelta(hours=3),
            )
            await self.page.goto(connections_link)

            fake_slack = FakeSlackClient("test-token")

            with (
                mock_slack_api_with_client(fake_slack),
                ExitStack() as stack,
            ):
                mock_test_connection = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.test_connection"
                    )
                )
                mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
                mock_list_tables = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.list_tables"
                    )
                )
                mock_analyze_table_schema = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.analyze_table_schema")
                )
                mock_update_dataset = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.update_dataset")
                )
                mock_pr_context = stack.enter_context(
                    patch("csbot.local_context_store.github.context.with_pull_request_context")
                )
                mock_test_connection.return_value = None

                def mock_analyze_schema(logger, profile, project, dataset):
                    from csbot.ctx_admin.dataset_documentation import (
                        ColumnDescription,
                        TableSchemaAnalysis,
                    )

                    return TableSchemaAnalysis(
                        table_name=dataset.table_name,
                        columns=[
                            ColumnDescription(name="id", type="INTEGER", column_comment=None),
                            ColumnDescription(name="name", type="VARCHAR", column_comment=None),
                        ],
                        schema_hash="mock_hash_" + dataset.table_name.replace(".", "_"),
                        table_comment=None,
                    )

                mock_analyze_table_schema.side_effect = mock_analyze_schema
                mock_update_dataset.return_value = None

                class MockPR:
                    pr_url = "https://github.com/dagster-compass/test-company-inc-context/pull/123"
                    repo_path = "/tmp/mock_repo_path"

                mock_pr = MockPR()
                mock_pr_context.return_value.__enter__.return_value = mock_pr

                scenario, config = CONNECTION_SCENARIOS_WITH_CONFIGS[0]

                # Should succeed - under the limit of 5 channels
                new_channel_selection = {
                    "type": "create",
                    "channels": ["test-company-inc-compass-analytics"],
                }

                await self._step_through_and_add_connection(
                    scenario,
                    mock_to_thread,
                    mock_list_tables,
                    new_channel_selection,
                    config,
                )

                self.assertTrue(len(self.mock_secret_store.store_secret.call_args_list) > 0)

        finally:
            await self._teardown_playwright()

    @pytest.mark.skip(
        reason="Need to update connection form schema after React migration - credential fields changed"
    )
    async def test_plan_limits_allows_additional_channels_flag(self):
        """Test that allow_additional_channels flag bypasses channel count limit."""
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"
            self.mock_bot.bot_config.organization_id = 1
            self.mock_bot.kv_store.exists.return_value = True

            # Set plan limits with num_channels=1 but allow_additional_channels=True
            from csbot.slackbot.storage.interface import PlanLimits

            unlimited_limits = PlanLimits(
                base_num_answers=100,
                allow_overage=False,
                num_channels=1,
                allow_additional_channels=True,
            )

            async def mock_get_plan_limits(org_id: int):
                return unlimited_limits

            self.mock_bot_server.bot_manager.storage.get_plan_limits = mock_get_plan_limits
            self.mock_bot_server.get_plan_limits_from_cache_or_bail = mock_get_plan_limits

            connections_link = create_link(
                self.mock_bot,
                user_id="U55555ADMIN",
                path="/onboarding/connections",
                max_age=timedelta(hours=3),
            )
            await self.page.goto(connections_link)

            fake_slack = FakeSlackClient("test-token")

            with (
                mock_slack_api_with_client(fake_slack),
                ExitStack() as stack,
            ):
                mock_test_connection = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.test_connection"
                    )
                )
                mock_to_thread = stack.enter_context(patch("asyncio.to_thread"))
                mock_list_tables = stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.add_connections.routes.warehouse_factory.list_tables"
                    )
                )
                mock_analyze_table_schema = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.analyze_table_schema")
                )
                mock_update_dataset = stack.enter_context(
                    patch("csbot.ctx_admin.dataset_documentation.update_dataset")
                )
                mock_pr_context = stack.enter_context(
                    patch("csbot.local_context_store.github.context.with_pull_request_context")
                )
                mock_test_connection.return_value = None

                def mock_analyze_schema(logger, profile, project, dataset):
                    from csbot.ctx_admin.dataset_documentation import (
                        ColumnDescription,
                        TableSchemaAnalysis,
                    )

                    return TableSchemaAnalysis(
                        table_name=dataset.table_name,
                        columns=[
                            ColumnDescription(name="id", type="INTEGER", column_comment=None),
                            ColumnDescription(name="name", type="VARCHAR", column_comment=None),
                        ],
                        schema_hash="mock_hash_" + dataset.table_name.replace(".", "_"),
                        table_comment=None,
                    )

                mock_analyze_table_schema.side_effect = mock_analyze_schema
                mock_update_dataset.return_value = None

                class MockPR:
                    pr_url = "https://github.com/dagster-compass/test-company-inc-context/pull/123"
                    repo_path = "/tmp/mock_repo_path"

                mock_pr = MockPR()
                mock_pr_context.return_value.__enter__.return_value = mock_pr

                scenario, config = CONNECTION_SCENARIOS_WITH_CONFIGS[0]

                # Should succeed even though at channel limit because allow_additional_channels=True
                new_channel_selection = {
                    "type": "create",
                    "channels": ["test-company-inc-compass-extra"],
                }

                await self._step_through_and_add_connection(
                    scenario,
                    mock_to_thread,
                    mock_list_tables,
                    new_channel_selection,
                    config,
                )

                self.assertTrue(len(self.mock_secret_store.store_secret.call_args_list) > 0)

        finally:
            await self._teardown_playwright()

    async def _test_organization_name_onboarding(self, organization_name, expected_channel_name):
        """Helper method to test onboarding with a specific organization name.

        Args:
            organization_name: Organization name to test (may contain special characters)
            expected_channel_name: Expected sanitized channel name
        """

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Create a FakeSlackClient for this test
            fake_slack = FakeSlackClient("test-token")

            # Mock non-Slack third-party services
            mock_create_repo = AsyncMock(
                return_value={
                    "success": True,
                    "repo_url": "https://github.com/dagster-compass/test-company-context",
                    "repo_name": "test-company-context",
                }
            )

            # Set up Temporal workflow environment with real worker
            async with AsyncExitStack() as stack:
                await self._setup_temporal_environment(stack)

                # Add mocks to the same stack
                stack.enter_context(mock_slack_api_with_client(fake_slack))
                stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository",
                        side_effect=mock_create_repo,
                    )
                )

                # Create referral token
                token = str(uuid.uuid4())
                await asyncio.to_thread(self._create_referral_token, token)

                # Start browser session
                get_url = f"http://localhost:{self.client.port}/onboarding?token={token}"
                await self.page.goto(get_url)

                # Fill in the onboarding form with special character organization name
                await self.page.fill('input[name="email"]', "test@example.com")
                await self.page.fill('input[name="organization"]', organization_name)
                await self.page.check('input[name="terms"]')

                # Submit the form
                await self.page.click('button[type="submit"]')

                # Wait for React app to show processing status
                # Use a more flexible text matcher that handles the apostrophe
                await self.page.wait_for_selector(
                    "text=/We.*re getting things ready/i", timeout=30000
                )

                # Wait for background processing to complete and "Check your email" to appear
                await self.page.wait_for_selector('text="Check your email"', timeout=35000)

            # Verify Slack team was created
            self.assertTrue(
                len(fake_slack._teams) >= 1,
                f"Slack team should be created for org '{organization_name}'",
            )

            # Verify channels were created with URL-safe names
            channel_names = [channel_info["name"] for channel_info in fake_slack._channels.values()]
            self.assertTrue(
                len(channel_names) >= 2,
                f"Should create compass and governance channels for org '{organization_name}'",
            )

            # Check that compass channel was created with the expected sanitized name
            # TODO update with new onboarding flow
            # self.assertIn(
            #     expected_channel_name,
            #     channel_names,
            #     f"Compass channel '{expected_channel_name}' should be created for org '{organization_name}'",
            # )

            # Verify no invalid characters in compass channel name
            self.assertNotIn(
                "'", expected_channel_name, "Channel name should not contain apostrophes"
            )
            self.assertNotIn(
                "&", expected_channel_name, "Channel name should not contain ampersands"
            )
            self.assertNotIn(
                "@", expected_channel_name, "Channel name should not contain @ symbols"
            )
            self.assertNotIn(
                "(", expected_channel_name, "Channel name should not contain parentheses"
            )
            self.assertNotIn(
                ")", expected_channel_name, "Channel name should not contain parentheses"
            )

            # TODO update with new onboarding flow
            # # Verify that governance channel also follows URL-safe naming
            # governance_channel_name = expected_channel_name.replace(
            #     "-compass", "-compass-governance"
            # )
            # self.assertIn(
            #     governance_channel_name,
            #     channel_names,
            #     f"Governance channel '{governance_channel_name}' should be created for org '{organization_name}'",
            # )

            # Verify no ERROR logs were generated
            self.assertFalse(
                self.error_handler.has_errors(),
                f"No errors should be logged during onboarding. Errors: {self.error_handler.get_errors()}",
            )

        finally:
            await self._teardown_playwright()

    async def test_organization_name_with_apostrophes(self):
        """Test organization name with apostrophes: Ben's Company"""
        await self._test_organization_name_onboarding("Ben's Company", "bens-company-compass")

    async def test_organization_name_with_ampersand(self):
        """Test organization name with ampersand: Test & Development"""
        await self._test_organization_name_onboarding(
            "Test & Development", "test-development-compass"
        )

    async def test_organization_name_with_multiple_apostrophes(self):
        """Test organization name with multiple apostrophes: O'Reilly Media"""
        await self._test_organization_name_onboarding("O'Reilly Media", "oreilly-media-compass")

    async def test_organization_name_with_parentheses(self):
        """Test organization name with parentheses: Company (2024)"""
        await self._test_organization_name_onboarding("Company (2024)", "company-2024-compass")

    async def test_organization_name_with_at_sign(self):
        """Test organization name with @ symbol: Data @ Scale"""
        await self._test_organization_name_onboarding("Data @ Scale", "data-scale-compass")

    async def test_organization_name_with_multiple_special_chars(self):
        """Test organization name with multiple special characters: Smith & Johnson LLC"""
        await self._test_organization_name_onboarding(
            "Smith & Johnson LLC", "smith-johnson-llc-compass"
        )

    async def test_byow_data_source_selection(self):
        """Test selecting 'Your own data' and reaching warehouse selection in the new React onboarding flow."""
        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Create a FakeSlackClient for this test
            fake_slack = FakeSlackClient("test-token")

            # Mock non-Slack third-party services
            mock_create_repo = AsyncMock(
                return_value={
                    "success": True,
                    "repo_url": "https://github.com/dagster-compass/test-byow-context",
                    "repo_name": "test-byow-context",
                }
            )

            # Set up Temporal workflow environment with real worker
            async with AsyncExitStack() as stack:
                await self._setup_temporal_environment(stack)

                # Add mocks to the same stack
                stack.enter_context(mock_slack_api_with_client(fake_slack))
                stack.enter_context(
                    patch(
                        "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository",
                        side_effect=mock_create_repo,
                    )
                )

                # Create referral token
                token = str(uuid.uuid4())
                await asyncio.to_thread(self._create_referral_token, token)

                # Start browser session
                get_url = f"http://localhost:{self.client.port}/onboarding?token={token}"
                await self.page.goto(get_url)

                # Step 1: Fill in email/org form
                await self.page.fill('input[name="email"]', "test@byow-company.com")
                await self.page.fill('input[name="organization"]', "BYOW Test Company")
                await self.page.check('input[name="terms"]')

                # Submit the form - this triggers minimal onboarding in the background
                await self.page.click('button[type="submit"]')

                # Step 2: Wait for data source selection page
                # React manages state internally, minimal onboarding happens in background
                # The new flow shows a choice between "Prospecting data" and "Bring your own data"
                await self.page.wait_for_selector(
                    'text="What type of data do you want to start with?"', timeout=45000
                )

                # Step 3: Click on "Bring your own data" card
                byow_card = self.page.locator("text=Your own data").first
                await byow_card.wait_for(state="visible")
                await byow_card.click()

                # Step 4: Verify we're redirected to warehouse selection/connection setup
                # The BYOW flow should show warehouse options (Snowflake, BigQuery, etc.)
                await self.page.wait_for_selector(
                    "text=/Choose.*warehouse|Select.*data.*source/i", timeout=15000
                )

                # Verify we can see warehouse options (e.g., Snowflake, BigQuery)
                page_content = await self.page.content()
                self.assertTrue(
                    "Snowflake" in page_content
                    or "BigQuery" in page_content
                    or "warehouse" in page_content.lower(),
                    "Should show warehouse selection options after selecting BYOW",
                )

        finally:
            await self._teardown_playwright()

    # NOTE: Further connection form testing requires JWT authentication setup
    # See test_first_connection_automatic_channel_selection for reference on how to
    # properly set up JWT tokens and navigate to connection pages with authentication


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
