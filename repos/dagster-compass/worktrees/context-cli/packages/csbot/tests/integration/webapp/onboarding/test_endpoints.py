"""Tests for onboarding endpoints and request handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp.test_utils import make_mocked_request

from csbot.slackbot.bot_server.bot_server import CompassBotServer
from csbot.slackbot.storage.onboarding_state import OnboardingState
from csbot.slackbot.webapp.onboarding import create_onboarding_process_api_handler
from tests.utils.stripe_client import FakeStripeClient


class TestOnboardingRequestHandlers:
    """Test the main onboarding request handlers."""

    @pytest.fixture
    def mock_bot_server(self):
        """Create a mock bot server for testing."""
        server = MagicMock(spec=CompassBotServer)
        server.logger = MagicMock()
        server.bots = {}

        # Mock config
        server.config = MagicMock()
        server.config.compass_bot_token = MagicMock()
        server.config.compass_bot_token.get_secret_value.return_value = "compass_token"
        server.config.slack_admin_token = MagicMock()
        server.config.slack_admin_token.get_secret_value.return_value = "admin_token"
        server.config.compass_dev_tools_bot_token = MagicMock()
        server.config.compass_dev_tools_bot_token.get_secret_value.return_value = "dev_tools_token"
        server.config.github = MagicMock()
        server.config.github.get_auth_token = AsyncMock(return_value="github_token")
        server.config.dagster_admins_to_invite = ["admin@dagster.io"]

        # Mock GitHub auth source
        server.github_auth_source = MagicMock()
        server.github_auth_source.get_token.return_value = "github_token"

        # Mock storage
        server.bot_manager = MagicMock()
        server.bot_manager.storage = AsyncMock()
        server.bot_manager.discover_and_update_bots_for_keys = AsyncMock()

        return server

    @pytest.fixture
    def mock_valid_token_status(self):
        """Create a mock valid token status."""
        status = MagicMock()
        status.is_valid = True
        status.has_been_consumed = False
        status.is_single_use = True
        return status

    @pytest.fixture
    def mock_invalid_token_status(self):
        """Create a mock invalid token status."""
        status = MagicMock()
        status.is_valid = False
        status.has_been_consumed = False
        status.is_single_use = True
        return status

    @pytest.fixture
    def mock_consumed_token_status(self):
        """Create a mock consumed token status."""
        status = MagicMock()
        status.is_valid = True
        status.has_been_consumed = True
        status.is_single_use = True
        return status


class TestFormSubmission:
    """Test form submission handling."""

    @pytest.fixture
    def mock_bot_server(self):
        """Create a mock bot server for testing."""
        server = MagicMock(spec=CompassBotServer)
        server.logger = MagicMock()
        server.bots = {}

        # Mock config
        server.config = MagicMock()
        server.config.compass_bot_token = MagicMock()
        server.config.compass_bot_token.get_secret_value.return_value = "compass_token"
        server.config.slack_admin_token = MagicMock()
        server.config.slack_admin_token.get_secret_value.return_value = "admin_token"
        server.config.compass_dev_tools_bot_token = MagicMock()
        server.config.compass_dev_tools_bot_token.get_secret_value.return_value = "dev_tools_token"
        server.config.github = MagicMock()
        server.config.github.get_auth_token = AsyncMock(return_value="github_token")
        server.config.dagster_admins_to_invite = ["admin@dagster.io"]

        # Mock GitHub auth source
        server.github_auth_source = MagicMock()
        server.github_auth_source.get_token.return_value = "github_token"

        # Mock storage
        server.bot_manager = MagicMock()
        server.bot_manager.storage = AsyncMock()
        server.bot_manager.discover_and_update_bots_for_keys = AsyncMock()

        return server

    @pytest.mark.asyncio
    async def test_form_data_validation_missing_email(self, mock_bot_server):
        """Test form submission with missing email."""
        handler = create_onboarding_process_api_handler(mock_bot_server)

        request = make_mocked_request("POST", "/onboarding")
        request.json = AsyncMock(return_value={"token": "valid_token", "organization": "Test Org"})

        response = await handler(request)
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_form_data_validation_invalid_email(self, mock_bot_server):
        """Test form submission with invalid email format."""
        handler = create_onboarding_process_api_handler(mock_bot_server)

        request = make_mocked_request("POST", "/onboarding")
        request.json = AsyncMock(
            return_value={
                "token": "valid_token",
                "email": "invalid-email",
                "organization": "Test Org",
            }
        )

        response = await handler(request)
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_form_data_validation_missing_organization(self, mock_bot_server):
        """Test form submission with missing organization."""
        handler = create_onboarding_process_api_handler(mock_bot_server)

        request = make_mocked_request("POST", "/onboarding")
        request.json = AsyncMock(return_value={"token": "valid_token", "email": "test@example.com"})

        response = await handler(request)
        assert response.status == 400


class TestEndToEndIntegration:
    """Test complete onboarding flow integration scenarios."""

    @pytest.fixture
    def complete_mock_bot_server(self):
        """Create a fully mocked bot server for integration testing."""
        server = MagicMock(spec=CompassBotServer)
        server.logger = MagicMock()

        # Mock sql_conn_factory for analytics store creation
        server.sql_conn_factory = MagicMock()
        server.sql_conn_factory.supports_analytics.return_value = True

        # Mock the analytics store context manager and connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        server.sql_conn_factory.with_conn.return_value.__enter__.return_value = mock_conn
        server.sql_conn_factory.with_conn.return_value.__exit__.return_value = None

        # Mock config with all required tokens
        server.config = MagicMock()
        server.config.compass_bot_token = MagicMock()
        server.config.compass_bot_token.get_secret_value.return_value = "compass_token"
        server.config.slack_admin_token = MagicMock()
        server.config.slack_admin_token.get_secret_value.return_value = "admin_token"
        server.config.compass_dev_tools_bot_token = MagicMock()
        server.config.compass_dev_tools_bot_token.get_secret_value.return_value = "dev_tools_token"
        server.config.github = MagicMock()
        server.config.github.get_auth_token = AsyncMock(return_value="github_token")
        server.config.dagster_admins_to_invite = ["admin@dagster.io"]

        # Mock GitHub auth source
        server.github_auth_source = MagicMock()
        server.github_auth_source.get_token.return_value = "github_token"

        # Mock stripe config
        server.config.stripe = MagicMock()
        server.config.stripe.free_product_id = "prod_free_test"
        server.config.stripe.starter_product_id = "prod_starter_test"
        server.config.stripe.team_product_id = "prod_test123"
        server.config.stripe.default_product = "team"
        server.config.stripe.get_default_product_id.return_value = "prod_test123"

        # Mock JWT secret for token generation
        server.config.jwt_secret = MagicMock()
        server.config.jwt_secret.get_secret_value.return_value = "test_jwt_secret"

        # Mock storage and bot manager
        server.bot_manager = MagicMock()
        server.bot_manager.storage = MagicMock()
        server.bot_manager.discover_and_update_bots_for_keys = AsyncMock()
        server.bot_manager.storage.set_plan_limits = AsyncMock()  # Mock plan limits storage

        # Mock storage methods that need to be async
        server.bot_manager.storage.is_referral_token_valid = AsyncMock()
        server.bot_manager.storage.create_organization = AsyncMock()
        server.bot_manager.storage.create_bot_instance = AsyncMock()
        server.bot_manager.storage.mark_referral_token_consumed = AsyncMock()
        server.bot_manager.storage.record_tos_acceptance = AsyncMock()

        # Mock onboarding state management methods
        # IMPORTANT: Use fresh AsyncMock instances for each test to avoid state leakage
        server.bot_manager.storage.get_onboarding_state = AsyncMock(return_value=None)
        server.bot_manager.storage.create_onboarding_state = AsyncMock(
            side_effect=lambda state: OnboardingState(
                id=1,
                email=state.email,
                organization_name=state.organization_name,
                current_step=state.current_step,
                created_at=state.created_at,
                updated_at=state.updated_at,
            )
        )
        server.bot_manager.storage.update_onboarding_state = AsyncMock()

        # Mock for_instance to return an object with sql_conn_factory
        mock_kv_store = MagicMock()
        mock_kv_store.sql_conn_factory = MagicMock()
        server.bot_manager.storage.for_instance = MagicMock(return_value=mock_kv_store)

        # Mock bots dict
        server.bots = {}

        # Add test Stripe client
        server.stripe_client = FakeStripeClient("test_stripe_key")

        yield server

        # Cleanup after test to prevent state leakage
        server.bot_manager.storage.get_onboarding_state.reset_mock()
        server.bot_manager.storage.create_onboarding_state.reset_mock()
        server.bot_manager.storage.update_onboarding_state.reset_mock()

    @pytest.fixture
    def mock_valid_token_status(self):
        """Create a mock valid token status."""
        status = MagicMock()
        status.is_valid = True
        status.has_been_consumed = False
        status.is_single_use = True
        return status

    @pytest.mark.asyncio
    async def test_onboarding_failure_during_slack_team_creation(
        self, complete_mock_bot_server, mock_valid_token_status
    ):
        """Test onboarding failure when Slack team creation fails in background processing."""
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            mock_valid_token_status
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)
        request = make_mocked_request("POST", "/onboarding-background")
        request.json = AsyncMock(
            return_value={
                "token": "valid_token",
                "email": "test@example.com",
                "organization": "Test Organization",
            }
        )

        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
        ):
            # Simulate Slack team creation failure
            mock_create_team.return_value = {"success": False, "error": "domain_taken"}

            # Background handler returns error response instead of raising
            response = await handler(request)

            # Should return 400 with error message
            assert response.status == 400

            # Verify we attempted team creation
            mock_create_team.assert_called_once()

            # Verify token was not consumed on failure
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()

    @pytest.mark.asyncio
    async def test_onboarding_fails_without_stripe_client(
        self, complete_mock_bot_server, mock_valid_token_status
    ):
        """Test background onboarding flow fails when no Stripe client is available."""
        # Remove Stripe client to test the case where it's None
        complete_mock_bot_server.stripe_client = None

        # Setup storage responses
        complete_mock_bot_server.bot_manager.storage.is_referral_token_valid.return_value = (
            mock_valid_token_status
        )

        handler = create_onboarding_process_api_handler(complete_mock_bot_server)

        # Create a POST request with valid JSON data
        request = make_mocked_request("POST", "/onboarding-background")
        request.json = AsyncMock(
            return_value={
                "token": "valid_token",
                "email": "test@example.com",
                "organization": "Test Organization",
            }
        )

        # Mock all external API calls to succeed up to the Stripe failure
        with (
            patch("csbot.slackbot.webapp.onboarding_steps.create_slack_team") as mock_create_team,
            patch("csbot.slackbot.webapp.onboarding_steps.get_all_channels") as mock_get_channels,
            patch("csbot.slackbot.webapp.onboarding_steps.create_channel") as mock_create_channel,
            patch("csbot.slackbot.webapp.onboarding_steps.get_bot_user_id") as mock_get_bot_id,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_bot_to_channel"
            ) as mock_invite_bot,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.invite_user_to_slack_team"
            ) as mock_invite_user,
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_contextstore_repository"
            ) as mock_create_repo,
            patch("asyncio.sleep"),
            patch("csbot.slackbot.webapp.onboarding_steps.create_agent_from_config"),
        ):  # Mock sleep to speed up tests
            # Configure mock responses for successful flow up to Stripe
            mock_create_team.return_value = {"success": True, "team_id": "T12345"}
            mock_get_channels.return_value = {
                "success": True,
                "channel_ids": "C11111,C22222",
                "channel_names": ["general", "random"],
            }
            mock_create_channel.return_value = {"success": True, "channel_id": "C33333"}
            mock_get_bot_id.return_value = {
                "success": True,
                "user_id": "U12345",
                "bot_id": "B12345",
            }
            mock_invite_bot.return_value = {"success": True}
            mock_invite_user.return_value = {"success": True, "user_id": "U67890"}
            mock_create_repo.return_value = {
                "success": True,
                "repo_url": "https://github.com/org/test-context",
                "repo_name": "test-organization-context",
            }

            # Execute the handler
            response = await handler(request)

            # Assert failure due to missing Stripe client
            assert response.status == 500
            assert response.content_type == "application/json"

            # Verify token was not consumed on failure
            complete_mock_bot_server.bot_manager.storage.mark_referral_token_consumed.assert_not_called()
