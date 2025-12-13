"""
Test cases for payment method management functionality.

This module tests:
- Payment method setup intents creation
- Payment method confirmation and setting as default
- Payment method deletion
- Customer details updates
"""

from .base_billing_test import BaseBillingTest, stripe


class TestPaymentMethods(BaseBillingTest):
    """Test cases for payment method management functionality."""

    async def test_create_setup_intent_success(self):
        """Test successful setup intent creation for adding payment methods."""
        jwt_token = self.create_valid_billing_jwt()

        resp = await self.client.request(
            "POST", "/api/billing/create-setup-intent", cookies={"compass_auth_token": jwt_token}
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        self.assertTrue(data["success"])
        self.assertIn("client_secret", data)
        self.assertIn("setup_intent_id", data)
        self.assertTrue(data["client_secret"].startswith("seti_"))

    async def test_create_setup_intent_no_stripe_client(self):
        """Test setup intent creation when Stripe client is not available."""
        jwt_token = self.create_valid_billing_jwt()

        # Remove Stripe client
        self.mock_bot_server.stripe_client = None

        resp = await self.client.request(
            "POST", "/api/billing/create-setup-intent", cookies={"compass_auth_token": jwt_token}
        )

        self.assertEqual(resp.status, 503)
        data = await resp.json()
        self.assertEqual(data["error"], "Billing system not available")

    async def test_delete_payment_method_success(self):
        """Test successful payment method deletion."""
        jwt_token = self.create_valid_billing_jwt()

        # Add a payment method first
        payment_method = self.add_test_payment_method()
        payment_method_id = payment_method["id"]

        resp = await self.client.request(
            "DELETE",
            f"/api/billing/payment-method/{payment_method_id}",
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Payment method removed successfully")
        self.assertEqual(data["payment_method_id"], payment_method_id)

        # Verify payment method was removed
        self.assert_payment_method_count(0)

    async def test_delete_payment_method_not_found(self):
        """Test payment method deletion when payment method doesn't exist."""
        jwt_token = self.create_valid_billing_jwt()

        fake_payment_method_id = "pm_nonexistent123456789"

        resp = await self.client.request(
            "DELETE",
            f"/api/billing/payment-method/{fake_payment_method_id}",
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 404)
        data = await resp.json()
        self.assertEqual(
            data["error"], "Payment method not found or not associated with this account"
        )

    async def test_update_customer_details_success(self):
        """Test successful customer details update."""
        jwt_token = self.create_valid_billing_jwt()

        update_data = {"email": "updated@example.com"}

        resp = await self.client.request(
            "PUT",
            "/api/billing/customer-details",
            json=update_data,
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Customer details updated successfully")
        self.assertEqual(data["customer"]["email"], "updated@example.com")
        # Name field should not be in the response
        self.assertNotIn("name", data["customer"])

        # Verify the update in the test client
        updated_customer = self.test_stripe_client.get_customer_details(self.stripe_customer_id)
        self.assertEqual(updated_customer["email"], "updated@example.com")

    async def test_update_customer_details_partial_update(self):
        """Test customer details update with only email field."""
        jwt_token = self.create_valid_billing_jwt()

        # Update only email (which is the only allowed field now)
        update_data = {"email": "newemail@example.com"}

        resp = await self.client.request(
            "PUT",
            "/api/billing/customer-details",
            json=update_data,
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["customer"]["email"], "newemail@example.com")
        # Name field should not be in the response since it's no longer editable
        self.assertNotIn("name", data["customer"])

    async def test_update_customer_details_no_valid_fields(self):
        """Test customer details update with no valid fields."""
        jwt_token = self.create_valid_billing_jwt()

        # Send empty data
        update_data = {}

        resp = await self.client.request(
            "PUT",
            "/api/billing/customer-details",
            json=update_data,
            cookies={"compass_auth_token": jwt_token},
        )

        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertEqual(data["error"], "No valid fields to update")

    async def test_confirm_payment_method_success(self):
        """Test successful payment method confirmation and default setting."""
        jwt_token = self.create_valid_billing_jwt()

        # Mock a successful setup intent
        setup_intent_id = "seti_test123456789"
        payment_method_id = "pm_test123456789"

        # Mock the stripe API call in the handler by importing it directly
        if stripe:
            # Mock the Stripe SetupIntent.retrieve call
            original_retrieve = stripe.SetupIntent.retrieve

            def mock_retrieve(id, **params):
                class MockSetupIntent:
                    status = "succeeded"
                    payment_method = payment_method_id

                return MockSetupIntent()

            stripe.SetupIntent.retrieve = mock_retrieve  # type: ignore

            try:
                resp = await self.client.request(
                    "POST",
                    "/api/billing/confirm-payment-method",
                    json={"setup_intent_id": setup_intent_id},
                    cookies={"compass_auth_token": jwt_token},
                )

                self.assertEqual(resp.status, 200)
                data = await resp.json()

                self.assertTrue(data["success"])
                self.assertEqual(data["message"], "Payment method confirmed and set as default")
                self.assertEqual(data["payment_method_id"], payment_method_id)
                self.assertIn("customer_id", data)

            finally:
                # Restore original method
                stripe.SetupIntent.retrieve = original_retrieve

    async def test_confirm_payment_method_failed_setup_intent(self):
        """Test payment method confirmation with failed setup intent."""
        jwt_token = self.create_valid_billing_jwt()

        setup_intent_id = "seti_test123456789"

        if stripe:
            original_retrieve = stripe.SetupIntent.retrieve

            def mock_retrieve(id, **params):
                class MockSetupIntent:
                    status = "requires_payment_method"  # Not succeeded
                    payment_method = None

                return MockSetupIntent()

            stripe.SetupIntent.retrieve = mock_retrieve  # type: ignore

            try:
                resp = await self.client.request(
                    "POST",
                    "/api/billing/confirm-payment-method",
                    json={"setup_intent_id": setup_intent_id},
                    cookies={"compass_auth_token": jwt_token},
                )

                self.assertEqual(resp.status, 400)
                data = await resp.json()
                self.assertEqual(data["error"], "Setup intent has not succeeded")

            finally:
                stripe.SetupIntent.retrieve = original_retrieve

    async def test_confirm_payment_method_with_old_payment_method_removal(self):
        """Test payment method confirmation with old payment method removal."""
        jwt_token = self.create_valid_billing_jwt()

        # Add an existing payment method to remove
        old_payment_method = self.add_test_payment_method(brand="mastercard", last4="8888")
        old_payment_method_id = old_payment_method["id"]

        setup_intent_id = "seti_test123456789"
        new_payment_method_id = "pm_new123456789"

        if stripe:
            original_retrieve = stripe.SetupIntent.retrieve

            def mock_retrieve(id, **params):
                class MockSetupIntent:
                    status = "succeeded"
                    payment_method = new_payment_method_id

                return MockSetupIntent()

            stripe.SetupIntent.retrieve = mock_retrieve  # type: ignore

            try:
                resp = await self.client.request(
                    "POST",
                    "/api/billing/confirm-payment-method",
                    json={
                        "setup_intent_id": setup_intent_id,
                        "old_payment_method_id": old_payment_method_id,
                    },
                    cookies={"compass_auth_token": jwt_token},
                )

                self.assertEqual(resp.status, 200)
                data = await resp.json()

                self.assertTrue(data["success"])
                self.assertEqual(data["payment_method_id"], new_payment_method_id)
                self.assertTrue(data["old_payment_method_removed"])

                # Verify old payment method was removed
                self.assert_payment_method_count(0)

            finally:
                stripe.SetupIntent.retrieve = original_retrieve

    async def test_stripe_data_api_endpoint_success(self):
        """Test the Stripe data API endpoint returns correct data."""
        jwt_token = self.create_valid_billing_jwt()

        # Add payment method and subscription
        self.add_test_payment_method()
        self.create_active_subscription(self.mock_bot_server.config.stripe.starter_product_id)

        resp = await self.client.request(
            "GET", "/api/billing/stripe-data", cookies={"compass_auth_token": jwt_token}
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        self.assertTrue(data["stripe_available"])
        self.assertIsNotNone(data["payment_method_info"])
        self.assertTrue(data["payment_method_info"]["has_payment_method"])
        self.assertIsNotNone(data["billing_details"])
        self.assertEqual(data["billing_details"]["email"], "test@example.com")
        self.assertIsNotNone(data["plan_pricing_data"])
        self.assertEqual(data["current_plan"], "starter")

    async def test_stripe_data_api_no_stripe_client(self):
        """Test the Stripe data API endpoint when no Stripe client exists."""
        jwt_token = self.create_valid_billing_jwt()

        # Remove Stripe client
        self.mock_bot_server.stripe_client = None

        resp = await self.client.request(
            "GET", "/api/billing/stripe-data", cookies={"compass_auth_token": jwt_token}
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        self.assertFalse(data["stripe_available"])
        self.assertIsNone(data["payment_method_info"])
        self.assertIsNone(data["billing_details"])
        self.assertIsNotNone(data["plan_pricing_data"])  # Should still have placeholder pricing
        self.assertIsNone(data["current_plan"])
