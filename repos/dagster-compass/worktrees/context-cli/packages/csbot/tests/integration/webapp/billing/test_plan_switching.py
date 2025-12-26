"""
Test cases for billing plan switching functionality.

This module tests:
- Plan switching API endpoints
- Plan switching frontend JavaScript
- Plan limits table updates
- Payment method requirements for plan switching
"""

from .base_billing_test import BaseBillingTest


class TestPlanSwitching(BaseBillingTest):
    """Test cases for plan switching functionality."""

    async def test_plan_switch_api_success(self):
        """Test successful plan switching via API endpoint."""
        jwt_token = self.create_valid_billing_jwt()

        # Add payment method so plan switching is allowed
        self.add_test_payment_method()

        # Create a subscription to the Starter plan
        self.create_active_subscription(self.mock_bot_server.config.stripe.starter_product_id)

        # Switch to Team plan
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Team"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        self.assertTrue(data["success"])
        # The test creates a new subscription instead of updating existing one
        # because FakeStripeClient doesn't have real Stripe integration
        self.assertIn("Team plan", data["message"])
        self.assertIn("subscription_id", data)

    async def test_plan_switch_api_invalid_plan(self):
        """Test plan switching API with invalid plan name."""
        jwt_token = self.create_valid_billing_jwt()

        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "NonexistentPlan"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 404)
        data = await resp.json()
        self.assertEqual(data["error"], "Plan not found")

    async def test_plan_switch_api_no_payment_method(self):
        """Test plan switching API when no payment method exists (except Free plan)."""
        jwt_token = self.create_valid_billing_jwt()

        # Ensure no payment methods exist
        self.assert_payment_method_count(0)

        # Try to switch to Starter plan (should fail)
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Starter"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertEqual(data["error"], "Please add a payment method before switching plans")

        # Switching to Free plan should work without payment method
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Free"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])

    async def test_plan_switch_api_no_stripe_client(self):
        """Test plan switching API when Stripe client is not available."""
        jwt_token = self.create_valid_billing_jwt()

        # Remove Stripe client
        self.mock_bot_server.stripe_client = None

        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Starter"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 503)
        data = await resp.json()
        self.assertEqual(data["error"], "Billing system not available")

    async def test_plan_switch_api_requires_valid_jwt(self):
        """Test plan switching API requires valid JWT token."""
        # Test without token
        resp = await self.client.request(
            "POST", "/api/billing/switch-plan", json={"plan_name": "Starter"}
        )
        self.assertEqual(resp.status, 401)

        # Test with expired token
        expired_jwt = self.create_expired_billing_jwt()
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Starter"},
            cookies={"compass_auth_token": expired_jwt},
        )
        self.assertEqual(resp.status, 401)

    async def test_plan_switch_api_invalid_request_body(self):
        """Test plan switching API with invalid request body."""
        jwt_token = self.create_valid_billing_jwt()

        # Test with missing plan_name
        resp = await self.client.request(
            "POST", "/api/billing/switch-plan", json={}, cookies={"compass_auth_token": jwt_token}
        )
        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertEqual(data["error"], "Invalid plan name")

        # Test with invalid plan_name type
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": 123},
            cookies={"compass_auth_token": jwt_token},
        )
        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertEqual(data["error"], "Invalid plan name")

    async def test_plan_switch_api_no_stripe_customer_id(self):
        """Test plan switching API when bot has no Stripe customer ID."""
        jwt_token = self.create_valid_billing_jwt()

        # Remove stripe_customer_id from config
        self.mock_config.stripe_customer_id = None

        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Starter"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertEqual(data["error"], "No Stripe customer associated with this organization")

    async def test_plan_switch_updates_plan_limits_table(self):
        """Test that successful plan switching updates the plan_limits table."""
        jwt_token = self.create_valid_billing_jwt()

        # Add payment method so plan switching is allowed
        self.add_test_payment_method()

        # Create a subscription to the Free plan
        self.create_active_subscription(self.mock_bot_server.config.stripe.free_product_id)

        # Switch to Starter plan
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Starter"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])

        # Verify that set_plan_limits was called with correct Starter plan metadata
        self.mock_storage.set_plan_limits.assert_called_once_with(
            organization_id=123,  # From mock_config.organization_id
            base_num_answers=100,  # From TestStripeClient Starter plan metadata
            allow_overage=True,  # From TestStripeClient Starter plan metadata
            num_channels=1,  # From TestStripeClient Starter plan metadata
            allow_additional_channels=False,  # From TestStripeClient Starter plan metadata
        )

    async def test_plan_switch_to_team_updates_plan_limits_correctly(self):
        """Test switching to Team plan updates plan limits with Team plan values."""
        jwt_token = self.create_valid_billing_jwt()

        # Add payment method so plan switching is allowed
        self.add_test_payment_method()

        # Create a subscription to the Starter plan
        self.create_active_subscription(self.mock_bot_server.config.stripe.starter_product_id)

        # Switch to Team plan
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Team"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])

        # Verify that set_plan_limits was called with Team plan metadata
        self.mock_storage.set_plan_limits.assert_called_once_with(
            organization_id=123,  # From mock_config.organization_id
            base_num_answers=1000,  # From TestStripeClient Team plan metadata
            allow_overage=True,  # From TestStripeClient Team plan metadata
            num_channels=3,  # From TestStripeClient Team plan metadata
            allow_additional_channels=False,  # From TestStripeClient Team plan metadata
        )

    async def test_plan_switch_to_free_updates_plan_limits_correctly(self):
        """Test switching to Free plan updates plan limits with Free plan values."""
        jwt_token = self.create_valid_billing_jwt()

        # Create a subscription to the Starter plan first
        self.create_active_subscription(self.mock_bot_server.config.stripe.starter_product_id)

        # Switch to Free plan (no payment method needed)
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Free"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])

        # Verify that set_plan_limits was called with Free plan metadata
        self.mock_storage.set_plan_limits.assert_called_once_with(
            organization_id=123,  # From mock_config.organization_id
            base_num_answers=10,  # From TestStripeClient Free plan metadata
            allow_overage=False,  # From TestStripeClient Free plan metadata
            num_channels=1,  # From TestStripeClient Free plan metadata
            allow_additional_channels=False,  # From TestStripeClient Free plan metadata
        )

    async def test_new_subscription_creation_updates_plan_limits(self):
        """Test that creating a new subscription (no existing subscription) updates plan limits."""
        jwt_token = self.create_valid_billing_jwt()

        # Add payment method so plan switching is allowed
        self.add_test_payment_method()

        # No existing subscription (mock_config.stripe_subscription_id is None by default)
        self.mock_config.stripe_subscription_id = None

        # Switch to Starter plan (this will create a new subscription)
        resp = await self.client.request(
            "POST",
            "/api/billing/switch-plan",
            json={"plan_name": "Starter"},
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])

        # Verify that set_plan_limits was called with Starter plan metadata
        self.mock_storage.set_plan_limits.assert_called_once_with(
            organization_id=123,  # From mock_config.organization_id
            base_num_answers=100,  # From TestStripeClient Starter plan metadata
            allow_overage=True,  # From TestStripeClient Starter plan metadata
            num_channels=1,  # From TestStripeClient Starter plan metadata
            allow_additional_channels=False,  # From TestStripeClient Starter plan metadata
        )
