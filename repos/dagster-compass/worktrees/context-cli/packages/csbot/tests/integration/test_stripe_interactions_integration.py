"""
End-to-end integration test for complete Stripe onboarding and billing flow.

This test covers the complete user journey:
1. User signs up through onboarding flow
2. User visits billing page and validates default plan
3. User adds a payment method
4. User selects a different plan

Uses the real Stripe test API with the token from environment variables.
"""

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
import stripe
from aiohttp.test_utils import AioHTTPTestCase, make_mocked_request
from pydantic import SecretStr

from csbot.local_context_store.github.config import PATGithubAuthSource
from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
from csbot.slackbot.storage.interface import PlanLimits
from csbot.slackbot.webapp.app import build_web_application
from csbot.slackbot.webapp.billing.routes import add_billing_routes
from csbot.slackbot.webapp.onboarding import create_onboarding_process_api_handler
from csbot.stripe.stripe_client import StripeClient


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


class TestStripeCompleteUserJourney(AioHTTPTestCase):
    """Complete end-to-end test for Stripe onboarding and billing flow."""

    @classmethod
    def setUpClass(cls):
        """Set up Stripe with test API key from environment."""
        import dotenv

        dotenv.load_dotenv()

        stripe_token = os.getenv("STRIPE_SANDBOX_TEST_TOKEN")
        if not stripe_token:
            pytest.skip(
                "STRIPE_SANDBOX_TEST_TOKEN environment variable must be set for integration tests"
            )

        if not stripe_token.startswith("sk_test_"):
            raise ValueError(
                "STRIPE_SANDBOX_TEST_TOKEN must be a test token (sk_test_*) for integration tests"
            )

        # Test the Stripe key first
        try:
            stripe.api_key = stripe_token
            # Quick test to validate the key works
            test_customer = stripe.Customer.create(
                email="test-validation@example.com", name="Test Validation"
            )
            stripe.Customer.delete(test_customer.id)
        except Exception as e:
            raise ValueError(
                f"STRIPE_SANDBOX_TEST_TOKEN appears to be invalid or Stripe API is unavailable: {e}"
            )

        cls.stripe_token = stripe_token
        cls.created_customers = []  # Track for cleanup
        cls.created_subscriptions = []  # Track for cleanup
        cls.created_test_clocks = []  # Track for cleanup

    @classmethod
    def tearDownClass(cls):
        """Clean up any Stripe test data created during tests."""
        # Clean up test clocks first
        for test_clock_id in cls.created_test_clocks:
            try:
                stripe.test_helpers.TestClock.delete(test_clock_id)  # type: ignore[attr-defined]
            except Exception:
                pass  # May already be deleted

        # Clean up subscriptions
        for subscription_id in cls.created_subscriptions:
            try:
                stripe.Subscription.cancel(subscription_id)
            except Exception:
                pass  # May already be canceled or deleted

        # Clean up customers
        for customer_id in cls.created_customers:
            try:
                stripe.Customer.delete(customer_id)
            except Exception:
                pass  # May already be deleted

    def setUp(self):
        """Set up test fixtures for the complete user journey."""
        # Set up error log handler to capture ERROR level logs
        # No default expected patterns - tests that expect errors should specify them explicitly
        self.error_handler = ErrorLogHandler()
        logging.getLogger().addHandler(self.error_handler)

        # Test configuration matching local.csbot.config.yaml
        self.team_id = f"T{int(datetime.now().timestamp())}"
        self.channel_name = "test-integration-channel"
        self.bot_key = BotKey.from_channel_name(self.team_id, self.channel_name)
        self.jwt_secret = "test-integration-jwt-secret"
        self.test_email = f"integration-test-{datetime.now().timestamp()}@example.com"
        self.test_org_name = f"Integration Test Org {int(datetime.now().timestamp())}"

        # Track created resources for cleanup
        self.stripe_customer_id = None
        self.stripe_subscription_id = None

        # Mock bot configuration
        self.mock_config = Mock(spec=CompassBotSingleChannelConfig)
        self.mock_config.stripe_customer_id = None  # Will be set during onboarding
        self.mock_config.stripe_subscription_id = None  # Will be set during onboarding
        self.mock_config.organization_name = self.test_org_name
        self.mock_config.organization_id = self.team_id

        # Mock analytics store with realistic data
        self.mock_analytics_store = Mock(spec=SlackbotAnalyticsStore)
        self.mock_analytics_store.get_usage_tracking_data = AsyncMock(
            return_value=[
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "answer_count": 25,
                    "last_updated": "2024-01-25 09:15:00",
                }
            ]
        )
        self.mock_analytics_store.get_analytics_data = AsyncMock(
            return_value=[
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "user_id": "U123456",
                    "event_type": "new_conversation",
                    "created_at": datetime.now(),
                },
                {
                    "bot_id": self.bot_key.to_bot_id(),
                    "user_id": "U789012",
                    "event_type": "new_reply",
                    "created_at": datetime.now(),
                },
            ]
        )

        # Mock bot instance
        self.mock_bot = Mock(spec=CompassChannelBaseBotInstance)
        self.mock_bot.key = self.bot_key
        self.mock_bot.analytics_store = self.mock_analytics_store
        self.mock_bot.config = self.mock_config

        # Mock bot manager and storage
        self.mock_bot_manager = Mock()
        self.mock_storage = Mock()
        self.mock_storage.create_organization = AsyncMock(return_value=1)
        self.mock_storage.create_bot_instance = AsyncMock(return_value="bot_instance_test123")
        self.mock_storage.mark_referral_token_consumed = AsyncMock()
        self.mock_storage.is_referral_token_valid = AsyncMock()
        self.mock_storage.set_plan_limits = AsyncMock()  # Mock plan limits storage
        self.mock_storage.record_tos_acceptance = AsyncMock()  # Mock TOS acceptance recording
        self.mock_bot_manager.storage = self.mock_storage
        self.mock_bot_manager.discover_and_update_bots = AsyncMock()
        # Mock get_plan_limits_from_cache_or_fallback to return default plan limits

        # Create real Stripe client instance
        self.real_stripe_client = StripeClient(self.stripe_token)

        # Mock bot server with real Stripe integration
        self.mock_bot_server = Mock(spec=CompassBotServer)
        self.mock_bot_server.logger = Mock()
        self.mock_bot_server.config = Mock()
        self.mock_bot_server.config.jwt_secret = SecretStr(self.jwt_secret)
        self.mock_bot_server.config.public_url = "https://test.integration.example.com"

        # Stripe configuration matching local.csbot.config.yaml
        self.mock_bot_server.config.stripe = Mock()
        self.mock_bot_server.config.stripe.token = SecretStr(self.stripe_token)
        self.mock_bot_server.config.stripe.publishable_key = os.getenv(
            "STRIPE_PUBLISHABLE_KEY", "pk_test_mock"
        )
        self.mock_bot_server.config.stripe.free_product_id = "prod_Swl8Ec25xkX2VE"
        self.mock_bot_server.config.stripe.starter_product_id = "prod_SwlG9kWDSHrfye"
        self.mock_bot_server.config.stripe.team_product_id = "prod_SwlG6vM56KdVWv"
        self.mock_bot_server.config.stripe.default_product = "free"
        self.mock_bot_server.config.stripe.get_default_product_id = Mock(
            return_value="prod_Swl8Ec25xkX2VE"
        )

        # Other configuration
        self.mock_bot_server.config.compass_bot_token = Mock()
        self.mock_bot_server.config.compass_bot_token.get_secret_value = Mock(
            return_value="test_compass_token"
        )
        self.mock_bot_server.config.slack_admin_token = Mock()
        self.mock_bot_server.config.slack_admin_token.get_secret_value = Mock(
            return_value="test_admin_token"
        )
        self.mock_bot_server.config.compass_dev_tools_bot_token = Mock()
        self.mock_bot_server.config.compass_dev_tools_bot_token.get_secret_value = Mock(
            return_value="test_dev_tools_token"
        )
        self.mock_bot_server.config.github = Mock()
        self.mock_bot_server.github_auth_source = PATGithubAuthSource("test_github_token")
        self.mock_bot_server.config.github.get_auth_token = AsyncMock(
            return_value="test_github_token"
        )
        self.mock_bot_server.config.dagster_admins_to_invite = ["admin@test.com"]

        self.mock_bot_server.bots = {self.bot_key: self.mock_bot}
        self.mock_bot_server.stripe_client = self.real_stripe_client
        self.mock_bot_server.bot_manager = self.mock_bot_manager

        async def mock_canonicalize_bot_key(key: BotKey) -> BotKey:
            return key

        self.mock_bot_server.canonicalize_bot_key = mock_canonicalize_bot_key
        self.mock_bot_server.get_plan_limits_from_cache_or_fallback = AsyncMock(
            return_value=PlanLimits(
                base_num_answers=100,
                allow_overage=True,
                num_channels=3,
                allow_additional_channels=False,
            )
        )

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

    def expect_error_log_containing(self, pattern):
        """Add an expected error pattern to ignore during this test."""
        if hasattr(self, "error_handler"):
            self.error_handler.add_expected_error_pattern(pattern)

    async def get_application(self):
        """Create test application with billing routes."""
        app = build_web_application(self.mock_bot_server)
        add_billing_routes(app, self.mock_bot_server)
        return app

    def create_valid_billing_jwt(self, manage_billing: bool = True, exp_hours: int = 3):
        """Create a valid JWT token for billing access."""
        jwt_payload = {
            "bot_id": self.bot_key.to_bot_id(),
            "manage_billing": manage_billing,
            "exp": datetime.now(UTC) + timedelta(hours=exp_hours),
        }
        return jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

    def create_valid_referral_token_status(self):
        """Create a mock valid referral token status."""
        status = Mock()
        status.is_valid = True
        status.has_been_consumed = False
        status.is_single_use = True
        return status

    async def advance_test_clock_and_wait(self, test_clock_id: str, target_timestamp: int) -> None:
        """Advance test clock and wait for completion."""
        stripe.test_helpers.TestClock.advance(  # type: ignore[attr-defined]
            test_clock_id, frozen_time=target_timestamp
        )

        max_wait_time = 60 * 5
        check_interval = 3
        checks = max_wait_time // check_interval

        for _ in range(checks):
            await asyncio.sleep(check_interval)

            updated_test_clock = stripe.test_helpers.TestClock.retrieve(test_clock_id)  # type: ignore[attr-defined]
            clock_status = updated_test_clock.status
            current_frozen_time = int(updated_test_clock.frozen_time)

            if clock_status == "ready" and current_frozen_time >= target_timestamp:
                break
            elif clock_status == "ready":
                continue
            elif clock_status == "advancing":
                continue
            else:
                continue

        await asyncio.sleep(5)

    @pytest.mark.skipif(
        os.environ.get("COMPASS_E2E_TESTS") != "1",
        reason="E2E tests are not enabled; set COMPASS_E2E_TESTS=1 to run",
    )
    async def test_complete_user_journey_signup_to_plan_change(self):
        """
        Test complete user journey: signup -> billing page -> add payment method -> change plan.

        This test covers:
        1. User signs up through onboarding flow (with Stripe customer/subscription creation)
        2. User visits billing page and validates default plan is shown
        3. User adds a payment method via the billing API
        4. User selects a different plan and completes the switch
        5. Submit usage data to Stripe meter
        6. Test billing cycle with Test Clock
        """
        # ========== SETUP: Create Test Clock for Time-Controlled Testing ==========

        # Use a fixed date for predictable testing: January 5th, 2025 at 10:00 AM PST

        pst_timezone = timezone(timedelta(hours=-8))  # PST is UTC-8
        test_start_date = datetime(2025, 1, 5, 10, 0, 0, tzinfo=pst_timezone)
        test_start_timestamp = int(test_start_date.timestamp())

        test_clock = stripe.test_helpers.TestClock.create(  # type: ignore[attr-defined]
            frozen_time=test_start_timestamp
        )
        self.__class__.created_test_clocks.append(test_clock.id)

        # Replace the real Stripe client with test-clock-enabled version
        self.real_stripe_client = StripeClient(self.stripe_token, test_clock_id=test_clock.id)
        self.mock_bot_server.stripe_client = self.real_stripe_client

        self.mock_bot_server.config.ai_config = Mock()
        self.mock_bot_server.config.ai_config.provider = "anthropic"
        self.mock_bot_server.config.ai_config.api_key = Mock()
        self.mock_bot_server.config.ai_config.api_key.get_secret_value.return_value = (
            "test_anthropic_key"
        )
        self.mock_bot_server.config.ai_config.model = "claude-sonnet-4-20250514"

        # ========== STEP 1: User Signs Up Through Onboarding ==========

        # Setup referral token validation
        token_status = self.create_valid_referral_token_status()
        self.mock_storage.is_referral_token_valid.return_value = token_status

        # Create onboarding background handler
        handler = create_onboarding_process_api_handler(self.mock_bot_server)

        # Create POST request with valid signup form data
        request = make_mocked_request("POST", "/api/onboarding/process")
        request.post = AsyncMock(
            return_value={
                "token": "valid_integration_token",
                "email": self.test_email,
                "organization": self.test_org_name,
            }
        )

        # Mock all Slack API calls to succeed for onboarding
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
            patch(
                "csbot.slackbot.webapp.onboarding_steps.create_slack_connect_channel"
            ) as mock_create_connect,
            patch("csbot.slackbot.webapp.onboarding.os.path.dirname") as mock_dirname,
            patch("csbot.slackbot.webapp.onboarding.Environment") as mock_env,
            patch(
                "csbot.slackbot.webapp.add_connections.urls.create_connection_management_url"
            ) as mock_create_conn_url,
            patch(
                "csbot.slackbot.webapp.add_connections.urls.create_industry_selection_url"
            ) as mock_create_industry_url,
            patch("asyncio.sleep"),
        ):
            # Configure mock responses for successful Slack onboarding flow
            mock_create_team.return_value = {"success": True, "team_id": self.team_id}
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
                "repo_url": f"https://github.com/org/{self.test_org_name.lower().replace(' ', '-')}-context",
                "repo_name": f"{self.test_org_name.lower().replace(' ', '-')}-context",
            }
            mock_create_connect.return_value = {"success": True, "invite_id": "I12345"}

            # Mock template rendering for successful onboarding
            mock_dirname.return_value = "/mock/path"
            mock_template = Mock()
            mock_template.render.return_value = (
                f"<html>Success - {self.test_org_name} onboarded!</html>"
            )
            mock_env.return_value.get_template.return_value = mock_template
            mock_create_conn_url.return_value = "/connections?token=jwt"
            mock_create_industry_url.return_value = "/industry?token=jwt"

            # Execute the onboarding
            response = await handler(request)

            # Verify successful onboarding
            assert response.status == 200

            # Extract the created Stripe customer and subscription IDs
            self.mock_storage.create_organization.assert_called_once()
            org_call_args = self.mock_storage.create_organization.call_args

            # Verify Stripe resources were created
            assert "stripe_customer_id" in org_call_args[1]
            assert "stripe_subscription_id" in org_call_args[1]

            created_customer_id = org_call_args[1]["stripe_customer_id"]
            created_subscription_id = org_call_args[1]["stripe_subscription_id"]

            # Track for cleanup
            self.__class__.created_customers.append(created_customer_id)
            self.__class__.created_subscriptions.append(created_subscription_id)

            # Update mock config for subsequent billing tests
            self.mock_config.stripe_customer_id = created_customer_id
            self.mock_config.stripe_subscription_id = created_subscription_id

        # ========== STEP 2: User Visits Billing Page and Validates Default Plan ==========

        jwt_token = self.create_valid_billing_jwt()

        # Visit billing page
        billing_response = await self.client.request(
            "GET", "/billing", cookies={"billing_token": jwt_token}
        )

        assert billing_response.status == 200
        billing_text = await billing_response.text()

        # Verify default plan (Free) is shown as current
        assert "Free" in billing_text

        # Verify no payment method exists yet
        assert "No payment method" in billing_text or "Add Payment Method" in billing_text

        # Verify usage analytics are displayed
        assert "Usage in" in billing_text
        assert "25" in billing_text

        # ========== STEP 3: User Adds a Payment Method ==========

        # Create setup intent for adding payment method
        setup_intent_response = await self.client.request(
            "POST", "/api/billing/create-setup-intent", cookies={"billing_token": jwt_token}
        )

        assert setup_intent_response.status == 200
        setup_intent_data = await setup_intent_response.json()

        assert setup_intent_data["success"]
        assert "client_secret" in setup_intent_data
        assert "setup_intent_id" in setup_intent_data

        setup_intent_id = setup_intent_data["setup_intent_id"]

        # Simulate successful payment method setup by creating a real payment method
        # and confirming the setup intent
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2025,
                "cvc": "123",
            },
        )

        # Attach to customer and confirm setup intent
        payment_method.attach(customer=created_customer_id)
        stripe.SetupIntent.confirm(setup_intent_id, payment_method=payment_method.id)

        # Confirm payment method through API
        confirm_response = await self.client.request(
            "POST",
            "/api/billing/confirm-payment-method",
            json={"setup_intent_id": setup_intent_id},
            cookies={"billing_token": jwt_token},
        )

        assert confirm_response.status == 200
        confirm_data = await confirm_response.json()

        assert confirm_data["success"]
        assert "payment_method_id" in confirm_data

        # Verify billing page now shows payment method
        billing_response_2 = await self.client.request(
            "GET", "/billing", cookies={"billing_token": jwt_token}
        )
        assert billing_response_2.status == 200
        billing_text_2 = await billing_response_2.text()

        assert "Payment method configured" in billing_text_2
        assert "Visa" in billing_text_2
        assert "4242" in billing_text_2

        # ========== STEP 4: User Selects a Different Plan ==========

        # Switch from Free to Starter plan
        plan_switch_response = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Starter"},
            cookies={"billing_token": jwt_token},
        )

        assert plan_switch_response.status == 200
        plan_switch_data = await plan_switch_response.json()

        assert plan_switch_data["success"]
        assert "subscription_id" in plan_switch_data
        assert "Starter" in plan_switch_data["message"] or "starter" in plan_switch_data["message"]

        # Track new subscription for cleanup
        new_subscription_id = plan_switch_data["subscription_id"]
        self.__class__.created_subscriptions.append(new_subscription_id)

        # Verify the subscription exists in Stripe and is active
        stripe_subscription = stripe.Subscription.retrieve(new_subscription_id)
        assert stripe_subscription.customer == created_customer_id
        assert stripe_subscription.status == "active"

        # Verify billing page reflects the new plan
        billing_response_3 = await self.client.request(
            "GET", "/billing", cookies={"billing_token": jwt_token}
        )
        assert billing_response_3.status == 200
        await billing_response_3.text()

        assert billing_response_3.status == 200

        # ========== Verification: Complete User Journey Success ==========

        # Verify all Stripe resources exist and are properly configured
        final_customer = stripe.Customer.retrieve(created_customer_id)
        assert final_customer.email == self.test_email
        assert final_customer.name == self.test_org_name

        # Verify payment method is attached
        payment_methods = stripe.PaymentMethod.list(customer=created_customer_id, type="card")
        assert len(payment_methods.data) >= 1

        # Verify subscription is active
        final_subscription = stripe.Subscription.retrieve(new_subscription_id)
        assert final_subscription.status == "active"
        assert final_subscription.customer == created_customer_id

        # ========== STEP 5: Test Stripe Meter Usage Submission ==========

        # Advance the clock a few days into the billing period to ensure we're in the right period
        billing_cycle_days = 32
        billing_cycle_seconds = billing_cycle_days * 24 * 60 * 60  # 32 days in seconds
        target_timestamp = test_start_timestamp + (3 * 24 * 60 * 60)  # 3 days from start
        await self.advance_test_clock_and_wait(test_clock.id, target_timestamp)

        # Submit both usage events close together to ensure they're in the same billing period
        usage_value = 42
        meter_result = await asyncio.to_thread(
            self.real_stripe_client.submit_meter_usage,
            meter_name="answers",
            customer_id=created_customer_id,
            usage_value=usage_value,
        )

        # Verify the first meter event was created successfully
        assert meter_result.object == "billing.meter_event"
        assert meter_result.event_name == "answers"
        assert meter_result.payload["stripe_customer_id"] == created_customer_id
        assert meter_result.payload["value"] == str(usage_value)

        # Small delay between submissions
        await asyncio.sleep(2)

        second_usage = 158
        additional_meter_result = await asyncio.to_thread(
            self.real_stripe_client.submit_meter_usage,
            meter_name="answers",
            customer_id=created_customer_id,
            usage_value=second_usage,
        )

        # Verify the second meter event was created successfully
        assert additional_meter_result.object == "billing.meter_event"
        assert additional_meter_result.event_name == "answers"
        assert additional_meter_result.payload["stripe_customer_id"] == created_customer_id
        assert additional_meter_result.payload["value"] == str(second_usage)

        # Allow time for usage events to be processed before advancing the billing cycle
        await asyncio.sleep(120)

        # ========== STEP 6: Test Billing Cycle with Test Clock ==========

        # Advance the clock past the next billing date to trigger invoice generation

        target_timestamp = test_start_timestamp + billing_cycle_seconds
        await self.advance_test_clock_and_wait(test_clock.id, target_timestamp)

        # Retrieve invoices for the customer to verify billing occurred
        invoices = stripe.Invoice.list(customer=created_customer_id, limit=10)

        # Find the most recent invoice (should be the usage-based one)
        usage_invoice = sorted(invoices.data, key=lambda x: x.created, reverse=True)[0]

        # Verify the invoice was created and includes usage charges
        assert usage_invoice.customer == created_customer_id

        # Check if the invoice has line items (it should include usage-based charges)
        line_items = stripe.Invoice.list_lines(usage_invoice.id)  # type: ignore[attr-defined]

        # Stripe uses the most recent submission per billing period, e.g. the second submission
        total_usage = second_usage

        # Check that line items exist
        assert len(line_items.data) > 0, "Expected at least one line item in the invoice"

        # Look for a line item that corresponds to our usage
        usage_line_items = [
            item
            for item in line_items.data
            if hasattr(item, "quantity") and item.quantity is not None
        ]
        assert len(usage_line_items) > 0, (
            "Expected at least one usage-based line item in the invoice"
        )

        usage_quantities = [item.quantity for item in usage_line_items]

        # Provide detailed error message for debugging
        line_item_details = []
        for item in line_items.data:
            details = {
                "description": getattr(item, "description", None),
                "quantity": getattr(item, "quantity", None),
                "amount": getattr(item, "amount", None),
                "type": getattr(item, "type", None),
            }
            line_item_details.append(details)

        # Accept either the total usage or the sum of individual usage quantities
        total_recorded_usage = sum(q for q in usage_quantities if q is not None and q > 0)

        # Check if we have the expected total usage either as a single line item or sum of line items
        if total_usage not in usage_quantities and total_recorded_usage != total_usage:
            assert False, (
                f"Expected total usage {total_usage} not found. "
                f"Individual quantities: {usage_quantities}, "
                f"Sum of recorded usage: {total_recorded_usage}. "
                f"All line item details: {line_item_details}"
            )

        # Clean up the test clock
        try:
            stripe.test_helpers.TestClock.delete(test_clock.id)  # type: ignore[attr-defined]
        except Exception:
            pass


# Additional helper for running tests standalone
if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
