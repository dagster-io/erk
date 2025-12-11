"""
Base test class for billing webapp functionality.

This module provides common setup and utilities for billing tests including:
- JWT validation and cookie handling setup
- Mock bot server and Stripe client configuration
- Common test fixtures and helper methods
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import jwt
from aiohttp.test_utils import AioHTTPTestCase
from pydantic import SecretStr

from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
from csbot.slackbot.storage.interface import PlanLimits
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.billing.routes import add_billing_routes
from tests.utils.stripe_client import FakeStripeClient

# Import stripe for tests that need direct Stripe API access
try:
    import stripe
except ImportError:
    stripe = None

# Export for use by other test modules
__all__ = ["BaseBillingTest", "stripe"]


class BaseBillingTest(AioHTTPTestCase):
    """Base test class for billing webapp functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.team_id = "T123456"
        self.channel_name = "test-channel"
        self.bot_key = BotKey.from_channel_name(self.team_id, self.channel_name)
        self.jwt_secret = "test-secret-key-for-billing"
        self.stripe_customer_id = "cus_test123456789"

        # Set up test Stripe client
        self.test_stripe_client = FakeStripeClient("test_api_key")

        # Create a test customer in stripe client
        customer = self.test_stripe_client.create_customer(
            "Test Organization", "org123", "test@example.com"
        )
        self.stripe_customer_id = customer["id"]

        # Mock bot configuration
        self.mock_config = Mock(spec=CompassBotSingleChannelConfig)
        self.mock_config.stripe_customer_id = self.stripe_customer_id
        self.mock_config.stripe_subscription_id = None  # Default to no subscription
        self.mock_config.organization_name = "Test Organization"
        self.mock_config.organization_id = 123
        self.mock_config.team_id = self.team_id

        # Mock analytics store
        self.mock_analytics_store = Mock(spec=SlackbotAnalyticsStore)
        # Legacy bot-based methods (kept for backwards compatibility)
        self.mock_analytics_store.get_usage_tracking_data = AsyncMock(
            return_value=[
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "month": datetime.now().month,
                    "year": datetime.now().year,
                    "answer_count": 42,
                    "created_at": "2024-01-01 00:00:00",
                    "updated_at": "2024-01-15 10:30:00",
                }
            ]
        )
        self.mock_analytics_store.get_analytics_data = AsyncMock(
            return_value=[
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "user_id": "U123456",
                    "event_type": "new_conversation",
                    "created_at": datetime.now(),  # timezone-naive
                },
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "user_id": "U789012",
                    "event_type": "new_reply",
                    "created_at": datetime.now(),  # timezone-naive
                },
            ]
        )
        # New organization-based methods
        self.mock_analytics_store.get_organization_usage_tracking_data = AsyncMock(
            return_value=[
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "month": datetime.now().month,
                    "year": datetime.now().year,
                    "answer_count": 42,
                    "created_at": "2024-01-01 00:00:00",
                    "updated_at": "2024-01-15 10:30:00",
                }
            ]
        )
        self.mock_analytics_store.get_organization_analytics_data = AsyncMock(
            return_value=[
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "user_id": "U123456",
                    "event_type": "new_conversation",
                    "created_at": datetime.now(),  # timezone-naive
                },
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "user_id": "U789012",
                    "event_type": "new_reply",
                    "created_at": datetime.now(),  # timezone-naive
                },
            ]
        )
        # Organization bonus answer methods (used by billing)
        self.mock_analytics_store.get_organization_bonus_answer_grants = AsyncMock(return_value=0)
        self.mock_analytics_store.get_organization_bonus_answers_consumed = AsyncMock(
            return_value=0
        )

        # Mock bot instance
        self.mock_bot = Mock(spec=CompassChannelBaseBotInstance)
        self.mock_bot.key = self.bot_key
        self.mock_bot.analytics_store = self.mock_analytics_store
        self.mock_bot.bot_config = self.mock_config
        # Set bot type to governance for authentication validation
        from csbot.slackbot.channel_bot.bot import BotTypeGovernance

        self.mock_bot.bot_type = BotTypeGovernance(governed_bot_keys=set())

        # Mock bot manager with storage
        self.mock_bot_manager = Mock()
        self.mock_storage = Mock()
        self.mock_storage.set_plan_limits = AsyncMock()  # Mock plan limits storage
        self.mock_storage.get_plan_limits = AsyncMock(
            return_value=None
        )  # Default to no cached limits
        self.mock_bot_manager.storage = self.mock_storage

        # Mock bot server
        self.mock_bot_server = Mock(spec=CompassBotServer)
        self.mock_bot_server.config = Mock()
        self.mock_bot_server.config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_bot_server.config.public_url = "https://test.example.com"
        # Mock stripe config with product IDs
        self.mock_bot_server.config.stripe = Mock()
        self.mock_bot_server.config.stripe.publishable_key = "pk_test_mock_key"
        self.mock_bot_server.config.stripe.free_product_id = "prod_Swl8Ec25xkX2VE"
        self.mock_bot_server.config.stripe.starter_product_id = "prod_SwlG9kWDSHrfye"
        self.mock_bot_server.config.stripe.team_product_id = "prod_SwlG6vM56KdVWv"
        self.mock_bot_server.bots = {self.bot_key: self.mock_bot}
        self.mock_bot_server.stripe_client = self.test_stripe_client
        self.mock_bot_server.bot_manager = self.mock_bot_manager
        self.mock_bot_server.logger = Mock()  # Add missing logger attribute

        # Mock canonicalize_bot_key to return the same key (simple case)
        async def mock_canonicalize_bot_key(key: BotKey) -> BotKey:
            return key

        self.mock_bot_server.canonicalize_bot_key = mock_canonicalize_bot_key
        # Mock get_plan_limits_from_cache_or_fallback to return default plan limits
        self.mock_bot_server.get_plan_limits_from_cache_or_fallback = AsyncMock(
            return_value=PlanLimits(
                base_num_answers=100,
                allow_overage=True,
                num_channels=3,
                allow_additional_channels=False,
            )
        )

    async def get_application(self):
        """Create test application."""
        app = build_web_application(self.mock_bot_server)
        add_billing_routes(app, self.mock_bot_server)
        return app

    def create_valid_billing_jwt(
        self,
        manage_billing: bool = True,
        view_billing: bool = True,
        exp_hours: int = 3,
        user_id: str = "U123456",
    ):
        """Create a valid JWT token for billing access.

        Uses organization-based authentication (organization_id + team_id).
        """
        jwt_payload = {
            "organization_id": self.mock_config.organization_id,
            "team_id": self.team_id,
            "manage_billing": manage_billing,
            "view_billing": view_billing,
            "user_id": user_id,
            "exp": datetime.now(UTC) + timedelta(hours=exp_hours),
        }
        return jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    def get_billing_cookies(self, jwt_token: str) -> dict[str, str]:
        """Get cookies dict for billing requests.

        Uses compass_auth_token cookie name which is the standard for JWT auth.
        """
        return {"compass_auth_token": jwt_token}

    def create_expired_billing_jwt(self, user_id: str = "U123456"):
        """Create an expired JWT token.

        Uses organization-based authentication (organization_id + team_id).
        """
        jwt_payload = {
            "organization_id": self.mock_config.organization_id,
            "team_id": self.team_id,
            "manage_billing": True,
            "view_billing": True,
            "user_id": user_id,
            "exp": datetime.now(UTC) - timedelta(minutes=5),  # Expired 5 minutes ago
        }
        return jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    def create_active_subscription(self, plan_product_id: str):
        """Helper to create an active subscription for testing."""
        subscription = self.test_stripe_client.create_subscription(
            self.stripe_customer_id, plan_product_id
        )
        self.mock_config.stripe_subscription_id = subscription["id"]
        return subscription

    def add_test_payment_method(
        self, brand: str = "visa", last4: str = "4242", exp_month: int = 12, exp_year: int = 2025
    ):
        """Helper to add a test payment method."""
        return self.test_stripe_client.create_test_card_payment_method(
            self.stripe_customer_id,
            brand=brand,
            last4=last4,
            exp_month=exp_month,
            exp_year=exp_year,
        )

    def assert_payment_method_count(self, expected_count: int):
        """Helper to assert the number of payment methods."""
        actual_count = len(
            self.test_stripe_client.get_customer_payment_methods(self.stripe_customer_id)
        )
        self.assertEqual(actual_count, expected_count)
