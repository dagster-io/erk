"""End-to-end test for adding prospector data to an existing organization."""

import logging
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp.test_utils import AioHTTPTestCase
from playwright.async_api import async_playwright
from testcontainers.postgres import PostgresContainer

from csbot.slackbot.bot_server.bot_server import CompassBotServer
from csbot.slackbot.config import DatabaseConfig
from csbot.slackbot.slackbot_slackstream import throttler
from csbot.slackbot.storage.onboarding_state import BotInstanceType
from csbot.slackbot.storage.postgresql import PostgresqlConnectionFactory, SlackbotPostgresqlStorage
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.routes import add_webapp_routes
from csbot.utils.time import SecondsNowFake
from tests.utils.slack_client import FakeSlackClient, mock_slack_api_with_client

# Skip all tests if psycopg is not available
psycopg = pytest.importorskip("psycopg")


class TestAddProspectorE2E(AioHTTPTestCase):
    """End-to-end test for adding prospector data to existing organization."""

    @classmethod
    def setUpClass(cls):
        """Set up test class with database container."""
        cls._setup_postgres()

    @classmethod
    def _setup_postgres(cls):
        """Set up PostgreSQL container for testing."""
        # Use environment variable if available (for CI/CD environments)
        if test_db_url := os.environ.get("TEST_DATABASE_URL"):
            if test_db_url.startswith("postgresql://"):
                cls.database_url = test_db_url
                return

        # Otherwise, spin up a test container
        cls.postgres_container = PostgresContainer(
            image="public.ecr.aws/docker/library/postgres:16-alpine3.21",
            username="test",
            password="test",
            dbname="test_db",
            driver="psycopg",
        )
        cls.postgres_container.start()
        cls.database_url = cls.postgres_container.get_connection_url()
        # Set environment variable for any code that might need it
        os.environ["TEST_DATABASE_URL"] = cls.database_url

        from csbot.utils.time import system_seconds_now

        cls.sql_conn_factory = PostgresqlConnectionFactory.from_db_config(
            DatabaseConfig.from_uri(cls.database_url), system_seconds_now
        )

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Initialize Playwright state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # Mock analytics logging - patch where it's defined, not where it's imported
        self.mock_analytics_logger = AsyncMock()
        self.analytics_patcher = patch(
            "csbot.slackbot.slackbot_analytics.log_analytics_event_unified",
            new=self.mock_analytics_logger,
        )
        self.analytics_patcher.start()

        # Mock Slack Connect API
        self.slack_connect_mock = AsyncMock(
            return_value=[{"success": True, "invite": {"id": "mock_invite_123"}}]
        )
        self.slack_connect_patcher = patch(
            "csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel",
            new=self.slack_connect_mock,
        )
        self.slack_connect_patcher.start()

        # Mock KEK provider for envelope encryption
        self.mock_kek_provider = Mock()
        # generate_data_key should return (plaintext_dek, encrypted_dek_blob)
        self.mock_kek_provider.generate_data_key = Mock(
            return_value=(b"test_plaintext_dek_32_bytes_long", b"test_encrypted_dek_blob")
        )
        self.mock_kek_provider.decrypt_data_key = Mock(
            return_value=b"test_plaintext_dek_32_bytes_long"
        )

        from csbot.utils.time import system_seconds_now

        self.storage = SlackbotPostgresqlStorage(
            self.sql_conn_factory, self.mock_kek_provider, system_seconds_now
        )

        # Create mock config
        self.mock_config = MagicMock()
        self.mock_config.compass_bot_token = MagicMock()
        self.mock_config.compass_bot_token.get_secret_value.return_value = "compass_token_12345"
        self.mock_config.slack_admin_token = MagicMock()
        self.mock_config.slack_admin_token.get_secret_value.return_value = "admin_token_12345"
        self.mock_config.compass_dev_tools_bot_token = MagicMock()
        self.mock_config.compass_dev_tools_bot_token.get_secret_value.return_value = (
            "dev_tools_token_12345"
        )
        self.mock_config.dagster_admins_to_invite = []
        self.mock_config.public_url = "http://localhost:8080"

        # Mock prospector data connection config
        import json

        self.mock_config.prospector_data_connection = MagicMock()
        self.mock_config.prospector_data_connection.type = "bigquery"
        self.mock_config.prospector_data_connection.config = {
            "location": "us",
            "service_account_json_string": json.dumps(
                {
                    "type": "service_account",
                    "project_id": "test-prospector-project",
                    "private_key_id": "test_key_id",
                    "private_key": "-----BEGIN PRIVATE KEY-----\ntest_key\n-----END PRIVATE KEY-----\n",
                    "client_email": "test@test-prospector-project.iam.gserviceaccount.com",
                    "client_id": "123456789",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            ),
        }

        self.mock_config.prospector_contextstore_repo = (
            "https://github.com/dagster-compass/prospector-template"
        )

        # Create mock bot server
        self.mock_bot_server = MagicMock(spec=CompassBotServer)
        self.mock_bot_server.config = self.mock_config
        self.mock_bot_server.sql_conn_factory = self.sql_conn_factory
        self.mock_bot_server.logger = logging.getLogger(__name__)
        self.mock_bot_server.bot_manager = MagicMock()
        self.mock_bot_server.bot_manager.storage = self.storage
        self.mock_bot_server.bot_manager.secret_store = MagicMock()
        self.mock_bot_server.bot_manager.secret_store.store_secret = AsyncMock(return_value=None)

        # Mock db_config with use_encrypted_connection_urls
        self.mock_config.db_config = MagicMock()
        self.mock_config.db_config.use_encrypted_connection_urls = True

        # Mock get_active_bots for Slack Connect invitation
        mock_bot = MagicMock()
        mock_bot.kv_store = MagicMock()
        mock_bot.kv_store.set = AsyncMock(return_value=None)
        mock_bot.kv_store.get = AsyncMock(return_value="U123456")  # Return pending user ID
        mock_bot.kv_store.delete = AsyncMock(return_value=None)
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")

        self.mock_bot_server.bot_manager.get_active_bots = MagicMock(
            return_value={MagicMock(): mock_bot}
        )

        # Mock bots dictionary for handle_fetch_channels
        self.mock_bot_server.bots = {}

        # Add Stripe client mock
        from tests.utils.stripe_client import FakeStripeClient

        self.mock_bot_server.stripe_client = FakeStripeClient("test_stripe_key")
        self.mock_bot_server.throttler = throttler
        self.mock_bot_server.seconds_now_source = SecondsNowFake()

        # Mock JWT secret
        self.mock_config.jwt_secret = MagicMock()
        self.mock_config.jwt_secret.get_secret_value.return_value = "test_jwt_secret_key_12345"

        # Mock plan limits
        self.mock_bot_server.get_plan_limits_from_cache_or_bail = AsyncMock(return_value=None)

    async def _setup_playwright(self):
        """Set up Playwright browser for testing."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

        # Capture console logs for debugging
        self.console_logs = []
        self.page.on("console", lambda msg: self.console_logs.append(f"[{msg.type}] {msg.text}"))

        # Capture page errors
        self.page_errors = []
        self.page.on("pageerror", lambda exc: self.page_errors.append(str(exc)))

        if os.environ.get("COMPASS_E2E_CI") == "1":
            self.page.set_default_navigation_timeout(30000)
            self.page.set_default_timeout(30000)
        else:
            self.page.set_default_navigation_timeout(5000)
            self.page.set_default_timeout(5000)

    async def _teardown_playwright(self):
        """Clean up Playwright browser."""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    @classmethod
    def tearDownClass(cls):
        """Clean up class-level resources."""
        if hasattr(cls, "postgres_container"):
            cls.postgres_container.stop()

    def tearDown(self):
        """Clean up test fixtures."""
        super().tearDown()

        if hasattr(self, "analytics_patcher"):
            self.analytics_patcher.stop()
        if hasattr(self, "slack_connect_patcher"):
            self.slack_connect_patcher.stop()

    async def get_application(self):
        """Create test application."""
        app = build_web_application(self.mock_bot_server)
        add_webapp_routes(app, self.mock_bot_server)
        return app

    async def test_add_prospector_to_existing_organization_new_channel(self):
        """Test adding prospector data to an existing organization with a NEW channel.

        Tests the backend logic flow:
        1. Create an existing organization with a warehouse connection
        2. Create a new channel and add prospector connection
        3. Verify prospector connection was added to organization
        4. Verify new bot instance has ONLY prospector connection
        5. Verify connection isolation between channels

        Validates:
        - Adding prospector to existing organizations (backend state)
        - New prospector channel creation
        - Prospector connection setup for existing org
        - Connection isolation: new channel has only prospector
        """
        await self._test_add_prospector_to_existing_organization(channel_type="new")

    async def test_add_prospector_to_existing_organization_existing_channel(self):
        """Test adding prospector data to an EXISTING data channel.

        Tests the backend logic flow:
        1. Create an existing organization with a warehouse connection
        2. Add prospector connection to existing data channel
        3. Verify prospector connection was added to organization
        4. Verify existing bot instance has BOTH connections
        5. Verify connection accumulation on existing channels

        Validates:
        - Adding prospector to existing organizations (backend state)
        - Reusing existing data channels
        - Prospector connection setup for existing org
        - Connection accumulation: existing channel gets prospector added
        """
        await self._test_add_prospector_to_existing_organization(channel_type="existing")

    async def test_add_prospector_to_existing_channel_idempotent(self):
        """Test adding prospector data to a channel that already has it (idempotent).

        Tests the backend logic flow:
        1. Create an existing organization with prospector already on a channel
        2. Add prospector connection again to the same channel
        3. Verify operation is idempotent (no errors, no duplicates)
        4. Verify bot instance still has correct connections

        Validates:
        - Idempotent behavior when adding prospector twice
        - No duplicate connections created
        - Graceful handling of already-connected channels
        """
        await self._test_add_prospector_to_existing_organization(channel_type="idempotent")

    async def _test_add_prospector_to_existing_organization(self, channel_type: str):
        """Helper method to test adding prospector data to an existing organization.

        Args:
            channel_type: Either "new" or "existing" to test different scenarios
        """
        # Mock Slack services
        fake_slack = FakeSlackClient("test-token")

        with mock_slack_api_with_client(fake_slack):
            # Step 1: Create an existing organization with a warehouse connection
            test_organization = "Test Warehouse Company"
            test_team_id = "T123456"

            organization_id = await self.storage.create_organization(
                name=test_organization,
                industry="Technology",
                has_governance_channel=True,
                contextstore_github_repo="test/repo",
            )

            # Create a governance channel and bot
            governance_channel = "test-governance"
            await self.storage.create_bot_instance(
                channel_name=governance_channel,
                governance_alerts_channel=governance_channel,
                contextstore_github_repo="test/repo",
                slack_team_id=test_team_id,
                bot_email="compassbot@dagster.io",
                organization_id=organization_id,
                instance_type=BotInstanceType.STANDARD,
                icp_text="",
            )

            # Add a warehouse connection to governance channel
            await self.storage.add_connection(
                organization_id=organization_id,
                connection_name="test_snowflake",
                url="snowflake://test",
                additional_sql_dialect=None,
                data_documentation_contextstore_github_repo=None,
            )

            # Link warehouse connection to governance bot
            governance_bot_key = f"{test_team_id}-{governance_channel}"
            await self.storage.add_bot_connection(
                organization_id=organization_id,
                bot_id=governance_bot_key,
                connection_name="test_snowflake",
            )

            # Step 2: Create prospector connection for the organization
            from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME
            from csbot.slackbot.webapp.onboarding.prospector_helpers import (
                create_prospector_connection_for_organization,
            )

            await create_prospector_connection_for_organization(
                self.mock_bot_server, organization_id
            )

            # Step 3: Determine target channel based on test parameter
            if channel_type == "new":
                # Create a new bot instance for prospector channel
                test_channel_name = "prospector-test"
                await self.storage.create_bot_instance(
                    channel_name=test_channel_name,
                    governance_alerts_channel=governance_channel,
                    contextstore_github_repo="test/repo",
                    slack_team_id=test_team_id,
                    bot_email="compassbot@dagster.io",
                    organization_id=organization_id,
                    instance_type=BotInstanceType.STANDARD,
                    icp_text="",
                )
            elif channel_type == "existing":
                # Use an existing data channel
                test_channel_name = "existing-data-channel"
                await self.storage.create_bot_instance(
                    channel_name=test_channel_name,
                    governance_alerts_channel=governance_channel,
                    contextstore_github_repo="test/repo",
                    slack_team_id=test_team_id,
                    bot_email="compassbot@dagster.io",
                    organization_id=organization_id,
                    instance_type=BotInstanceType.STANDARD,
                    icp_text="",
                )
                # Add warehouse connection to this existing channel
                existing_bot_key = f"{test_team_id}-{test_channel_name}"
                await self.storage.add_bot_connection(
                    organization_id=organization_id,
                    bot_id=existing_bot_key,
                    connection_name="test_snowflake",
                )
            else:  # idempotent case
                # Create channel with BOTH warehouse and prospector already connected
                test_channel_name = "idempotent-channel"
                await self.storage.create_bot_instance(
                    channel_name=test_channel_name,
                    governance_alerts_channel=governance_channel,
                    contextstore_github_repo="test/repo",
                    slack_team_id=test_team_id,
                    bot_email="compassbot@dagster.io",
                    organization_id=organization_id,
                    instance_type=BotInstanceType.STANDARD,
                    icp_text="",
                )
                # Add both connections to this channel
                idempotent_bot_key = f"{test_team_id}-{test_channel_name}"
                await self.storage.add_bot_connection(
                    organization_id=organization_id,
                    bot_id=idempotent_bot_key,
                    connection_name="test_snowflake",
                )
                # Add prospector connection FIRST time
                await self.storage.add_bot_connection(
                    organization_id=organization_id,
                    bot_id=idempotent_bot_key,
                    connection_name=PROSPECTOR_CONNECTION_NAME,
                )

            # Step 4: Add prospector connection to the target bot
            bot_key = f"{test_team_id}-{test_channel_name}"
            await self.storage.add_bot_connection(
                organization_id=organization_id,
                bot_id=bot_key,
                connection_name=PROSPECTOR_CONNECTION_NAME,
            )

            # Step 5: Verify prospector connection was created at organization level
            connections = await self.storage.get_connection_names_for_organization(organization_id)
            self.assertIn(
                PROSPECTOR_CONNECTION_NAME,
                connections,
                f"Prospector connection should be created. Found: {connections}",
            )
            # Should also have the warehouse connection
            self.assertIn("test_snowflake", connections)
            self.assertEqual(
                len(connections), 2, "Should have both warehouse and prospector connections"
            )

            # Step 6: Verify bot instance connections
            bot_instances = await self.storage.load_bot_instances(
                template_context={
                    "pull_from_secret_manager_to_string": lambda x: "",
                },
                get_template_context_for_org=lambda org_id: {
                    "pull_from_secret_manager_to_string": lambda x: "",
                },
            )

            # Find the prospector channel bot
            prospector_bot = None
            for bot_config in bot_instances.values():
                if bot_config.channel_name == test_channel_name:
                    prospector_bot = bot_config
                    break

            self.assertIsNotNone(
                prospector_bot,
                f"Prospector bot instance should be created for {channel_type} channel",
            )
            if prospector_bot:
                # Verify the bot has the prospector connection
                self.assertIn(
                    PROSPECTOR_CONNECTION_NAME,
                    prospector_bot.connections,
                    f"Bot should have prospector connection. Found: {prospector_bot.connections}",
                )
                # Verify the bot is associated with the correct organization
                self.assertEqual(prospector_bot.organization_id, organization_id)

                # Connection expectations differ based on channel type
                if channel_type == "new":
                    # New channel should ONLY have prospector connection
                    self.assertNotIn(
                        "test_snowflake",
                        prospector_bot.connections,
                        "New prospector channel should not have warehouse connection",
                    )
                    self.assertEqual(
                        len(prospector_bot.connections),
                        1,
                        "New prospector channel should have exactly 1 connection",
                    )
                elif channel_type == "existing":
                    # Existing channel should have BOTH connections
                    self.assertIn(
                        "test_snowflake",
                        prospector_bot.connections,
                        "Existing channel should retain warehouse connection",
                    )
                    self.assertEqual(
                        len(prospector_bot.connections),
                        2,
                        "Existing channel should have both connections",
                    )
                else:  # idempotent case
                    # Idempotent: should still have BOTH connections, no duplicates
                    self.assertIn(
                        "test_snowflake",
                        prospector_bot.connections,
                        "Idempotent case should retain warehouse connection",
                    )
                    self.assertEqual(
                        len(prospector_bot.connections),
                        2,
                        "Idempotent case should have exactly 2 connections (no duplicates)",
                    )
                    # Verify no duplicate prospector connections
                    connection_list = list(prospector_bot.connections)
                    self.assertEqual(
                        connection_list.count(PROSPECTOR_CONNECTION_NAME),
                        1,
                        "Should have exactly one prospector connection (idempotent)",
                    )

            # Step 7: Verify governance bot has correct connections
            governance_bot = None
            for bot_config in bot_instances.values():
                if bot_config.channel_name == governance_channel:
                    governance_bot = bot_config
                    break

            self.assertIsNotNone(governance_bot, "Governance bot should exist")
            if governance_bot:
                # Governance bot should have warehouse but NOT prospector (different channel)
                self.assertIn("test_snowflake", governance_bot.connections)
                self.assertNotIn(PROSPECTOR_CONNECTION_NAME, governance_bot.connections)

    @pytest.mark.skip(reason="Requires complex mock setup for existing bots - skipping for now")
    async def test_add_prospector_to_existing_channel(self):
        """Test adding prospector data to an existing channel.

        Tests the full flow:
        1. Create an existing organization with an existing channel
        2. Navigate to add connections page
        3. Select "Curated Data" tab
        4. Click "Prospecting Data" tile
        5. Select existing channel to add prospector data
        6. Verify prospector connection was added to existing bot
        7. Verify NO Slack Connect invitation (channel already exists)

        Validates:
        - Adding prospector to existing channels
        - No duplicate channel creation
        - Connection properly associated with existing bot
        - No invitation sent for existing channels
        """
        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Set the public URL to match the test server port
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"

            # Mock Slack services
            fake_slack = FakeSlackClient("test-token")

            with mock_slack_api_with_client(fake_slack):
                # Step 1: Create an existing organization with an existing channel
                test_organization = "Test Existing Channel Company"
                test_team_id = "T789012"
                existing_channel_name = "existing-data-channel"

                organization_id = await self.storage.create_organization(
                    name=test_organization,
                    industry="Technology",
                    has_governance_channel=True,
                    contextstore_github_repo="test/repo",
                )

                # Create an existing channel with a warehouse connection
                await self.storage.create_bot_instance(
                    channel_name=existing_channel_name,
                    governance_alerts_channel="test-governance",
                    contextstore_github_repo="test/repo",
                    slack_team_id=test_team_id,
                    bot_email="compassbot@dagster.io",
                    organization_id=organization_id,
                    instance_type=BotInstanceType.STANDARD,
                    icp_text="",
                )

                # Add a warehouse connection to the existing channel
                await self.storage.add_connection(
                    organization_id=organization_id,
                    connection_name="test_bigquery",
                    url="bigquery://test",
                    additional_sql_dialect=None,
                    data_documentation_contextstore_github_repo=None,
                )

                bot_key_str = f"{test_team_id}-{existing_channel_name}"
                await self.storage.add_bot_connection(
                    organization_id=organization_id,
                    bot_id=bot_key_str,
                    connection_name="test_bigquery",
                )

                # Add bot to bot_server.bots so it appears in fetch_channels
                from csbot.slackbot.bot_server.bot_server import BotKey
                from csbot.slackbot.channel_bot.bot import BotTypeQA

                bot_key_obj = BotKey.from_channel_name(test_team_id, existing_channel_name)
                mock_existing_bot = MagicMock()
                mock_existing_bot.bot_config = MagicMock()
                mock_existing_bot.bot_config.organization_id = organization_id
                mock_existing_bot.bot_type = BotTypeQA()  # Make it a QA bot, not governance-only
                mock_existing_bot.governance_alerts_channel = "test-governance"
                self.mock_bot_server.bots[bot_key_obj] = mock_existing_bot

                # Step 2: Generate JWT token and navigate to add connections page
                import jwt as jwt_lib

                token = jwt_lib.encode(
                    {"organization_id": organization_id, "team_id": test_team_id},
                    "test_jwt_secret_key_12345",
                    algorithm="HS256",
                )

                add_connection_url = (
                    f"http://localhost:{self.client.port}/connections/add-connection?token={token}"
                )
                await self.page.goto(add_connection_url)

                # Step 3: Wait for page to load and click "Curated Data" tab
                await self.page.wait_for_selector("text=Curated Data", timeout=5000)
                curated_data_tab = self.page.locator("text=Curated Data")
                await curated_data_tab.click()

                # Step 4: Click "Prospecting Data" tile
                await self.page.wait_for_selector("text=Prospecting Data", timeout=5000)
                prospecting_tile = self.page.locator("text=Prospecting Data").first
                await prospecting_tile.click()

                # Step 5: Wait for channel selection screen
                await self.page.wait_for_selector("text=Add Prospecting Data", timeout=5000)

                # Wait for channels to finish loading - the "Loading channels..." text should disappear
                # and radio buttons should appear
                import asyncio

                for _ in range(20):  # Try for up to 10 seconds
                    page_text = await self.page.text_content("body")
                    if page_text and "Loading channels..." not in page_text:
                        break
                    await asyncio.sleep(0.5)

                # Now wait for radio buttons to appear
                try:
                    await self.page.wait_for_selector('input[type="radio"]', timeout=10000)
                except Exception as e:
                    # Dump console logs and page state for debugging
                    page_text = await self.page.text_content("body")
                    console_output = (
                        "\n".join(self.console_logs[-30:])
                        if self.console_logs
                        else "No console logs"
                    )
                    page_errors_output = (
                        "\n".join(self.page_errors) if self.page_errors else "No page errors"
                    )
                    self.fail(
                        f"Radio buttons never appeared. Error: {e}\n"
                        f"Bot dict keys: {list(self.mock_bot_server.bots.keys())}\n"
                        f"Console logs:\n{console_output}\n"
                        f"Page errors:\n{page_errors_output}\n"
                        f"Page text:\n{page_text[:1000] if page_text else 'N/A'}"
                    )

                # Step 6: Select "Add to existing channel" option
                # The second radio button should be for existing channels
                existing_channel_radio = self.page.locator('input[type="radio"]').nth(1)
                await existing_channel_radio.click()

                # Step 7: Wait for channel checkboxes to appear and select our existing channel
                await self.page.wait_for_selector('input[type="checkbox"]', timeout=5000)

                # Find and click the checkbox for our existing channel
                # The checkbox should be labeled with the channel name
                channel_checkbox = self.page.locator(f"text=#{existing_channel_name}").locator(
                    ".."
                )  # Get parent to find associated checkbox
                channel_input = channel_checkbox.locator('input[type="checkbox"]')
                await channel_input.click()

                # Step 8: Submit the form
                submit_button = self.page.locator('button:has-text("Add Prospector Data")')
                await submit_button.click()

                # Step 9: Wait for redirect to connections page
                import asyncio

                await asyncio.sleep(2)  # Give API call time to complete

                # Verify we got redirected
                current_url = self.page.url
                if "prospector_added=true" not in current_url and "/connections" not in current_url:
                    console_output = (
                        "\n".join(self.console_logs[-20:])
                        if self.console_logs
                        else "No console logs"
                    )
                    self.fail(
                        f"Did not redirect to connections page. Current URL: {current_url}\n"
                        f"Console logs:\n{console_output}"
                    )

                # Step 10: Verify prospector connection was created
                from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME

                connections = await self.storage.get_connection_names_for_organization(
                    organization_id
                )
                self.assertIn(PROSPECTOR_CONNECTION_NAME, connections)

                # Step 11: Verify existing bot now has prospector connection
                bot_instances = await self.storage.load_bot_instances(
                    template_context={
                        "pull_from_secret_manager_to_string": lambda x: "",
                    },
                    get_template_context_for_org=lambda org_id: {
                        "pull_from_secret_manager_to_string": lambda x: "",
                    },
                )

                # Find the existing channel bot
                existing_bot = None
                for bot_config in bot_instances.values():
                    if bot_config.channel_name == existing_channel_name:
                        existing_bot = bot_config
                        break

                self.assertIsNotNone(
                    existing_bot, "Existing bot instance should still exist and be found"
                )
                if existing_bot:
                    # Verify the bot now has both the original connection and prospector connection
                    self.assertIn("test_bigquery", existing_bot.connections)
                    self.assertIn(PROSPECTOR_CONNECTION_NAME, existing_bot.connections)
                    self.assertEqual(
                        len(existing_bot.connections), 2, "Bot should have exactly 2 connections"
                    )

                # Step 12: Verify Slack Connect invitation was NOT called for existing channel
                # The mock was set up but should not have been called since the channel already exists
                # We can check this by verifying call count is 0
                self.assertEqual(
                    self.slack_connect_mock.call_count,
                    0,
                    "Slack Connect should not be called for existing channels",
                )

        finally:
            # Clean up Playwright
            await self._teardown_playwright()
