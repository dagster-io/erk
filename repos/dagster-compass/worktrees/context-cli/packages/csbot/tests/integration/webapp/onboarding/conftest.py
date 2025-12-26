"""Shared fixtures for onboarding tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from csbot.slackbot.storage.interface import PlanLimits
from csbot.slackbot.storage.onboarding_state import OnboardingState


@pytest.fixture
def complete_mock_bot_server():
    """Create a fully mocked bot server for testing."""
    server = MagicMock()
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
    server.config.ai_config = MagicMock()
    server.config.ai_config.provider = "anthropic"

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

    # Mock storage and bot manager
    server.bot_manager = MagicMock()
    server.bot_manager.storage = MagicMock()
    server.bot_manager.discover_and_update_bots_for_keys = AsyncMock()
    server.bot_manager.storage.set_plan_limits = AsyncMock()

    # Mock storage methods that need to be async
    server.bot_manager.storage.is_referral_token_valid = AsyncMock()
    server.bot_manager.storage.create_organization = AsyncMock(return_value=123)
    server.bot_manager.storage.create_bot_instance = AsyncMock(return_value=456)
    server.bot_manager.storage.mark_referral_token_consumed = AsyncMock()
    server.bot_manager.storage.record_tos_acceptance = AsyncMock()
    server.bot_manager.storage.list_invite_tokens = AsyncMock(return_value=[])

    # Mock onboarding state management methods
    # IMPORTANT: Set return_value to None to ensure fresh state for each test
    server.bot_manager.storage.get_onboarding_state = AsyncMock()
    server.bot_manager.storage.get_onboarding_state.return_value = None

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

    # Mock Stripe client (use regular Mock, not AsyncMock, since it's called via asyncio.to_thread)
    server.stripe_client = MagicMock()
    server.stripe_client.create_customer = MagicMock(return_value={"id": "cus_test123"})
    server.stripe_client.create_subscription = MagicMock(
        return_value={"id": "sub_test123", "items": {"data": [{"id": "si_test123"}]}}
    )
    server.stripe_client.get_product_plan_limits = MagicMock(
        return_value=PlanLimits(
            base_num_answers=1000,
            allow_overage=True,
            num_channels=1,
            allow_additional_channels=False,
        )
    )

    # Reset mock state to ensure clean state for each test
    yield server

    # Cleanup: Reset all mocks after test and restore default return values
    server.bot_manager.storage.get_onboarding_state.reset_mock()
    server.bot_manager.storage.get_onboarding_state.return_value = None
    server.bot_manager.storage.create_onboarding_state.reset_mock()
    server.bot_manager.storage.update_onboarding_state.reset_mock()


@pytest.fixture
def valid_token_status():
    """Create a mock valid token status."""
    status = MagicMock()
    status.is_valid = True
    status.has_been_consumed = False
    return status
