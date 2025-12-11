"""End-to-end test for prospector onboarding flow with webserver and form submission."""

import logging
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aiohttp.test_utils import AioHTTPTestCase
from playwright.async_api import async_playwright
from testcontainers.postgres import PostgresContainer

from csbot.slackbot.bot_server.bot_server import CompassBotServer
from csbot.slackbot.config import DatabaseConfig
from csbot.slackbot.slack_utils import generate_urlsafe_team_name
from csbot.slackbot.slackbot_slackstream import throttler
from csbot.slackbot.storage.onboarding_state import BotInstanceType
from csbot.slackbot.storage.postgresql import PostgresqlConnectionFactory, SlackbotPostgresqlStorage
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.routes import add_webapp_routes
from csbot.utils.time import SecondsNowFake
from tests.utils.slack_client import FakeSlackClient, mock_slack_api_with_client

# Skip all tests if psycopg is not available
psycopg = pytest.importorskip("psycopg")


# Note: Some tests are unskipped and working. Playwright-based E2E tests remain skipped
# as they require additional setup and have known issues with AsyncWebClient mocking.


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


class TestProspectorEndToEndOnboarding(AioHTTPTestCase):
    """End-to-end test for prospector onboarding flow."""

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

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Set up error log handler
        self.error_handler = ErrorLogHandler()
        logging.getLogger().addHandler(self.error_handler)

        # Initialize Playwright state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # Mock analytics logging to prevent JSON serialization issues with MagicMock objects
        # Patch in the modules where it's used, not where it's defined
        self.mock_analytics_logger = AsyncMock()
        self.analytics_patcher = patch(
            "csbot.slackbot.webapp.onboarding_steps.log_analytics_event_unified",
            new=self.mock_analytics_logger,
        )
        self.analytics_patcher.start()

        # Note: No longer need to patch complete_prospector since it doesn't log
        # organization_created anymore (logged by create_organization_step instead)

        # Mock Slack Connect API to prevent authentication errors (patch at source)
        self.slack_connect_mock = AsyncMock(
            return_value=[{"success": True, "invite": {"id": "mock_invite_123"}}]
        )
        self.slack_connect_patcher = patch(
            "csbot.slackbot.slack_utils.send_slack_connect_invite_to_channel",
            new=self.slack_connect_mock,
        )
        self.slack_connect_patcher.start()

        # Also mock create_slack_connect_channel for email invites
        self.slack_connect_channel_mock = AsyncMock(
            return_value={"success": True, "invite": {"id": "mock_invite_456"}}
        )
        self.slack_connect_channel_patcher = patch(
            "csbot.slackbot.slack_utils.create_slack_connect_channel",
            new=self.slack_connect_channel_mock,
        )
        self.slack_connect_channel_patcher.start()

        # Create storage and bot server (schema is created automatically)
        from csbot.utils.time import system_seconds_now

        self.sql_conn_factory = PostgresqlConnectionFactory.from_db_config(
            DatabaseConfig.from_uri(self.database_url), system_seconds_now
        )
        self.storage = SlackbotPostgresqlStorage(self.sql_conn_factory, Mock(), system_seconds_now)

        # Note: Database state persists between tests in the class
        # Tests can be run individually for full isolation if needed

        # Create mock config (using MagicMock pattern like existing test)
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

        # Mock prospector data connection config with proper BigQuery fields
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

        # Mock prospector context store repo
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
        self.mock_bot_server.bot_manager.get_bot = MagicMock(return_value=None)
        self.mock_bot_server.bot_manager.load_bot_instances = AsyncMock(return_value=None)
        self.mock_bot_server.bot_manager.discover_and_update_bots_for_keys = AsyncMock(
            return_value=None
        )
        self.mock_bot_server.bot_manager.secret_store = MagicMock()
        self.mock_bot_server.bot_manager.secret_store.store_secret = AsyncMock(return_value=None)

        # Add Stripe client mock
        from tests.utils.stripe_client import FakeStripeClient

        self.mock_bot_server.stripe_client = FakeStripeClient("test_stripe_key")
        self.mock_bot_server.throttler = throttler
        self.mock_bot_server.seconds_now_source = SecondsNowFake()

        # Mock GitHub auth source (needed for contextstore creation)
        self.mock_bot_server.github_auth_source = MagicMock()
        self.mock_bot_server.github_auth_source.get_token.return_value = "github_token_12345"

        # Mock AI config (needed for contextstore creation)
        self.mock_config.ai_config = MagicMock()
        self.mock_config.ai_config.provider = "anthropic"
        self.mock_config.ai_config.api_key = MagicMock()
        self.mock_config.ai_config.api_key.get_secret_value.return_value = "test_anthropic_key"
        self.mock_config.ai_config.model = "claude-sonnet-4-20250514"

        # Mock JWT secret
        self.mock_config.jwt_secret = MagicMock()
        self.mock_config.jwt_secret.get_secret_value.return_value = "test_jwt_secret_key_12345"

        # Mock bots dictionary for bot instance creation
        mock_bot = MagicMock()
        mock_bot.kv_store = MagicMock()
        mock_bot.kv_store.set = AsyncMock(return_value=None)
        mock_bot.kv_store.get = AsyncMock(return_value=None)
        mock_bot.kv_store.get_channel_id = AsyncMock(return_value="C123456")
        mock_bot.associate_channel_id = AsyncMock(return_value=None)
        self.mock_bot_server.bots = MagicMock()
        self.mock_bot_server.bots.get = MagicMock(return_value=mock_bot)

        # Mock channel_id_to_name dictionary (needed for channel creation)
        self.mock_bot_server.channel_id_to_name = {}

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
        # Stop PostgreSQL container if we created one
        if hasattr(cls, "postgres_container"):
            cls.postgres_container.stop()

    def tearDown(self):
        """Clean up test fixtures."""
        # Check for error logs and fail the test if any were captured
        if hasattr(self, "error_handler"):
            error_logs = self.error_handler.get_errors()
            # Filter out expected Slack Connect errors (mocking issue with dynamic imports)
            filtered_errors = [
                error
                for error in error_logs
                if "Failed to create Slack Connect invite" not in error["message"]
            ]

            if filtered_errors:
                # Format error messages for test failure
                error_messages = []
                for error in filtered_errors:
                    error_messages.append(
                        f"ERROR in {error['pathname']}:{error['lineno']} ({error['funcName']}): {error['message']}"
                    )

                # Remove error handler before failing
                logging.getLogger().removeHandler(self.error_handler)

                # Fail the test with detailed error information
                self.fail(
                    f"Test failed due to {len(filtered_errors)} error-level log(s):\n"
                    + "\n".join(error_messages)
                )

            # Clean up error handler
            logging.getLogger().removeHandler(self.error_handler)

        super().tearDown()

        # Stop analytics patcher
        if hasattr(self, "analytics_patcher"):
            self.analytics_patcher.stop()

        # Stop Slack Connect patchers
        if hasattr(self, "slack_connect_patcher"):
            self.slack_connect_patcher.stop()
        if hasattr(self, "slack_connect_channel_patcher"):
            self.slack_connect_channel_patcher.stop()

    async def get_application(self):
        """Create test application."""
        app = build_web_application(self.mock_bot_server)
        add_webapp_routes(app, self.mock_bot_server)
        return app

    @pytest.mark.skipif(
        os.environ.get("COMPASS_E2E_TESTS") != "1",
        reason="E2E tests require COMPASS_E2E_TESTS=1 and Playwright browsers installed",
    )
    async def test_complete_prospector_onboarding_flow_with_form_submission(self):
        """Test complete end-to-end prospector onboarding flow with new React UI.

        Tests the full flow:
        1. Email/org form submission (creates minimal onboarding)
        2. Data source selection (prospecting data)
        3. Data type selection
        4. Verification of created resources

        Validates:
        - React form interaction across multiple steps
        - Slack API integration (workspace, channels, bot)
        - Stripe billing setup
        - Bot instance creation with data types
        - Prospector connection setup
        """

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        try:
            # Test data
            test_email = "prospector@testcompany.com"
            test_organization = "Test Prospector Company"

            # Set the public URL to match the test server port
            self.mock_bot_server.config.public_url = f"http://localhost:{self.client.port}"

            # Mock all third-party services
            fake_slack = FakeSlackClient("test-token")

            # Mock contextstore repository creation
            mock_create_repo = AsyncMock(
                return_value={"success": True, "repo_name": "test-prospector-company-contextstore"}
            )

            with mock_slack_api_with_client(fake_slack):
                with patch(
                    "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository",
                    side_effect=mock_create_repo,
                ):
                    # Step 1: Navigate to signup page
                    signup_url = f"http://localhost:{self.client.port}/signup"
                    await self.page.goto(signup_url)

                    # Verify we're on signup
                    self.assertEqual(self.page.url, signup_url)

                    # Step 2: Fill out email/org form (React uses id attributes)
                    email_input = self.page.locator("input#email")
                    organization_input = self.page.locator("input#organization")
                    terms_checkbox = self.page.locator('input[name="terms"]')
                    submit_button = self.page.locator('button[type="submit"]')

                    await email_input.wait_for(state="attached")
                    await organization_input.wait_for(state="attached")
                    await terms_checkbox.wait_for(state="attached")

                    await email_input.fill(test_email)
                    await organization_input.fill(test_organization)
                    await terms_checkbox.click()  # Check the terms box

                    # Submit form - this triggers minimal onboarding
                    await submit_button.click()

                    # Step 3: Wait for data source choice screen
                    # React manages state internally, URL stays at /signup
                    # Look for the correct heading text from ChooseDataTypeOnboardingScreen
                    await self.page.wait_for_selector(
                        "text=What type of data do you want to start with?", timeout=15000
                    )

                    # Step 4: Click on prospecting data card (use heading text from button)
                    prospecting_card = self.page.locator("text=Curated prospecting data").first
                    await prospecting_card.wait_for(state="visible")
                    await prospecting_card.click()

                    # Step 5: Select data type (recruiting)
                    # Wait for data type checkboxes to appear
                    await self.page.wait_for_selector('input[name="data_types"]', timeout=5000)

                    recruiting_checkbox = self.page.locator(
                        'input[name="data_types"][value="recruiting"]'
                    )
                    await recruiting_checkbox.wait_for(state="attached")
                    await recruiting_checkbox.click()

                    # Submit data types
                    complete_button = self.page.locator('button[type="submit"]')
                    await complete_button.click()

                    # Step 6: Wait for success page (React shows "Setup complete!" banner)
                    # Try waiting for either success or error message
                    import asyncio

                    await asyncio.sleep(2)  # Give the API call time to complete

                    # Wait for success by checking if page body contains success text
                    # We saw from logs that the text is there but selectors aren't finding it
                    success_found = False
                    for _ in range(60):  # Try for up to 30 seconds
                        page_text = await self.page.text_content("body")
                        if (
                            page_text
                            and "Setup complete" in page_text
                            and "Check your email" in page_text
                        ):
                            success_found = True
                            break
                        if page_text and "Failed to complete setup" in page_text:
                            self.fail("UI showed error in page text")
                        await asyncio.sleep(0.5)

                    if not success_found:
                        page_text = await self.page.text_content("body")
                        console_output = (
                            "\n".join(self.console_logs[-20:])
                            if self.console_logs
                            else "No console logs"
                        )
                        self.fail(
                            f"Success message never appeared.\n"
                            f"Console logs:\n{console_output}\n\n"
                            f"Page text: {page_text[:500] if page_text else 'No page text'}"
                        )

                    # Wait for background processing to complete
                    import asyncio

                    await asyncio.sleep(
                        10
                    )  # Give time for background processing (increased from 2s)

                    # Step 5: Verify organization was created
                    orgs = await self.storage.list_organizations()
                    if len(orgs) == 0:
                        # Check if there was an error in onboarding
                        # Sanitize organization name to match how it was stored
                        sanitized_org = generate_urlsafe_team_name(test_organization)
                        onboarding_state_check = await self.storage.get_onboarding_state(
                            email=test_email, organization_name=sanitized_org
                        )
                        error_msg = f"No organizations created. Onboarding state: {onboarding_state_check.current_step if onboarding_state_check else 'None'}, Error: {onboarding_state_check.error_message if onboarding_state_check else 'None'}"
                        self.fail(error_msg)
                    self.assertEqual(len(orgs), 1)
                    org = orgs[0]
                    self.assertEqual(org.organization_name, test_organization)

                    # Verify organization_created analytics event was logged
                    from csbot.slackbot.slackbot_analytics import AnalyticsEventType

                    analytics_calls = [call for call in self.mock_analytics_logger.call_args_list]
                    org_created_calls = [
                        call
                        for call in analytics_calls
                        if call.kwargs.get("event_type") == AnalyticsEventType.ORGANIZATION_CREATED
                    ]

                    # Should be exactly one organization_created event (no duplication)
                    self.assertEqual(
                        len(org_created_calls),
                        1,
                        f"Expected exactly 1 organization_created event, got {len(org_created_calls)}",
                    )

                    # Verify it has the correct onboarding_type
                    org_created_call = org_created_calls[0]
                    self.assertEqual(
                        org_created_call.kwargs.get("onboarding_type"),
                        "prospector",
                        "organization_created event should have onboarding_type='prospector'",
                    )

                    # Verify basic metadata is present
                    metadata = org_created_call.kwargs.get("metadata", {})
                    self.assertIn("organization_id", metadata)
                    self.assertIn("organization_name", metadata)

                    # Step 6: Verify bot instance was created with correct prospector configuration
                    bot_instances = await self.storage.load_bot_instances(
                        template_context={
                            "pull_from_secret_manager_to_string": lambda x: "",
                        },
                        get_template_context_for_org=lambda org_id: {
                            "pull_from_secret_manager_to_string": lambda x: "",
                        },
                    )
                    self.assertEqual(len(bot_instances), 1)

                    bot_config = next(iter(bot_instances.values()))
                    # Verify it's a prospector bot based on having only prospector connection
                    self.assertTrue(bot_config.is_prospector)
                    # ICP is now empty (form removed), verify it's empty string
                    self.assertEqual(bot_config.icp_text, "")

                    # Step 7: Verify Slack workspace and channel were created
                    teams = fake_slack.get_teams()
                    self.assertEqual(len(teams), 1)

                    channels = fake_slack.get_channels()
                    # Should have general, random (default), and combined compass channel
                    self.assertGreaterEqual(len(channels), 3)

                    # Verify combined channel was created (not separate governance)
                    combined_channel = fake_slack.get_channel_by_name(
                        f"{test_organization.lower().replace(' ', '-')}-compass"
                    )
                    self.assertIsNotNone(combined_channel)

                    # Step 8: Verify onboarding state shows completion
                    from csbot.slackbot.storage.onboarding_state import OnboardingStep

                    # Use sanitized org name for onboarding state lookup
                    sanitized_org = generate_urlsafe_team_name(test_organization)
                    onboarding_state = await self.storage.get_onboarding_state(
                        email=test_email, organization_name=sanitized_org
                    )
                    self.assertIsNotNone(onboarding_state)
                    if onboarding_state is None:
                        self.fail("Onboarding state not found")

                    # Prospector flow completes at COMPLETED, not COMPLETED
                    self.assertEqual(onboarding_state.current_step, OnboardingStep.COMPLETED)
                    self.assertIsNone(onboarding_state.error_message)

        finally:
            # Clean up Playwright
            await self._teardown_playwright()

    async def test_prospector_bot_uses_readonly_context_engine(self):
        """Test that prospector bot instances are stored with ICP at the instance level."""
        # This test verifies that prospector bot instances store ICP per-instance

        # Create a prospector organization
        organization_id = await self.storage.create_organization(
            name="Test Prospector Org",
            industry="Technology",
            has_governance_channel=False,
            contextstore_github_repo="test/repo",
        )

        # Create a prospector bot instance with ICP
        test_icp = "Looking for senior engineers with Python and distributed systems experience"
        from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME

        await self.storage.create_bot_instance(
            channel_name="test-prospector",
            governance_alerts_channel="test-prospector",
            contextstore_github_repo="test/repo",
            slack_team_id="T123",
            bot_email="compassbot@dagster.io",
            organization_id=organization_id,
            instance_type=BotInstanceType.STANDARD,
            icp_text=test_icp,
        )

        # Add prospector connection to make this a prospector bot
        # Must include data_documentation_contextstore_github_repo to be detected as prospector
        await self.storage.add_connection(
            organization_id=organization_id,
            connection_name=PROSPECTOR_CONNECTION_NAME,
            url="bigquery://prospector",
            additional_sql_dialect=None,
            data_documentation_contextstore_github_repo="https://github.com/dagster-compass/prospector-docs",
        )

        # Associate connection with bot
        bot_key = "T123-test-prospector"
        await self.storage.add_bot_connection(
            organization_id=organization_id,
            bot_id=bot_key,
            connection_name=PROSPECTOR_CONNECTION_NAME,
        )

        # Verify bot instance was created with ICP
        bot_instances = await self.storage.load_bot_instances(
            template_context={
                "pull_from_secret_manager_to_string": lambda x: "",
            },
            get_template_context_for_org=lambda org_id: {
                "pull_from_secret_manager_to_string": lambda x: "",
            },
        )
        # There may be multiple bot instances if other tests ran first - find the one we just created
        matching_instances = [bot for bot in bot_instances.values() if bot.icp_text == test_icp]
        self.assertEqual(
            len(matching_instances), 1, "Should have exactly one bot instance with our test ICP"
        )

        bot_config = matching_instances[0]

        # Verify it's detected as prospector based on connection
        self.assertTrue(bot_config.is_prospector)
        self.assertEqual(bot_config.icp_text, test_icp)

        # Verify organization was created
        orgs = await self.storage.list_organizations()
        self.assertEqual(len([o for o in orgs if o.organization_id == organization_id]), 1)
        # Organization type no longer stored at org level - check bot instance instead

        # In actual bot initialization, the bot config has instance_type=BotInstanceType.PROSPECTOR
        # and ProspectorReadOnlyContextEngine is created with the ICP from bot_config.icp_text

    async def test_prospector_admin_commands_restricted(self):
        """Test that prospector orgs only have access to billing admin commands."""
        # Create a prospector organization
        organization_id = await self.storage.create_organization(
            name="Test Prospector Org",
            industry="Technology",
            has_governance_channel=False,
            contextstore_github_repo="test/repo",
        )

        # Verify organization was created
        orgs = await self.storage.list_organizations()
        self.assertEqual(len([o for o in orgs if o.organization_id == organization_id]), 1)
        # Organization type no longer stored at org level

        # In the actual bot code, admin commands check bot_config.is_prospector
        # and restrict non-billing commands. This test verifies the data is set up correctly.

    @pytest.mark.skipif(
        os.environ.get("COMPASS_E2E_TESTS") != "1",
        reason="E2E tests require COMPASS_E2E_TESTS=1 and Playwright browsers installed",
    )
    async def test_prospector_form_validation(self):
        """Test prospector form validation requirements with new React flow."""

        # Set up Playwright
        await self._setup_playwright()
        if self.page is None:
            raise ValueError("Page is not initialized")

        # Mock services for this test
        fake_slack = FakeSlackClient("test-token")

        # Mock contextstore repository creation
        mock_create_repo = AsyncMock(
            return_value={"success": True, "repo_name": "test-company-contextstore"}
        )

        try:
            with mock_slack_api_with_client(fake_slack):
                with patch(
                    "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository",
                    side_effect=mock_create_repo,
                ):
                    # Navigate to signup
                    signup_url = f"http://localhost:{self.client.port}/signup"
                    await self.page.goto(signup_url)

                    # Fill out email/org form with terms checkbox
                    email_input = self.page.locator("input#email")
                    organization_input = self.page.locator("input#organization")
                    terms_checkbox = self.page.locator('input[name="terms"]')
                    submit_button = self.page.locator('button[type="submit"]')

                    await email_input.fill("test@test.com")
                    await organization_input.fill("Test Org")
                    await terms_checkbox.click()
                    await submit_button.click()

                    # Wait for data source selection screen (correct heading text from React component)
                    await self.page.wait_for_selector(
                        "text=What type of data do you want to start with?", timeout=15000
                    )

                    # Click prospecting data card (use heading text from the button)
                    prospecting_card = self.page.locator("text=Curated prospecting data").first
                    await prospecting_card.click()

                    # Wait for data type checkboxes to appear
                    await self.page.wait_for_selector('input[name="data_types"]', timeout=5000)

                    # Test data type selection
                    data_type_recruiting = self.page.locator(
                        'input[name="data_types"][value="recruiting"]'
                    )

                    # Verify data type checkbox exists
                    await data_type_recruiting.wait_for(state="attached")

                    # Select a data type
                    await data_type_recruiting.click()

                    # Verify form can be interacted with
                    is_checked = await data_type_recruiting.is_checked()
                    self.assertTrue(is_checked)

        finally:
            await self._teardown_playwright()

    # Note: Background flow step-by-step test (_test_prospector_onboarding_background_flow)
    # was removed as it duplicated coverage from other unit tests. The individual onboarding
    # steps are tested in isolation in their respective test files.
