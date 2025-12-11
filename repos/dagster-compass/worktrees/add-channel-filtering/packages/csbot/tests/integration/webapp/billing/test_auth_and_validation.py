"""
Test cases for billing authentication and validation.

This module tests:
- JWT token validation for billing endpoints
- Permission requirements (manage_billing)
- Error handling for various edge cases
"""

from .base_billing_test import BaseBillingTest


class TestAuthAndValidation(BaseBillingTest):
    """Test cases for billing authentication and validation."""

    async def test_stripe_data_api_requires_valid_jwt(self):
        """Test the Stripe data API endpoint requires valid JWT token."""
        # Test without token
        resp = await self.client.request("GET", "/api/billing/stripe-data")
        self.assertEqual(resp.status, 401)

        # Test with expired token
        expired_jwt = self.create_expired_billing_jwt()
        resp = await self.client.request(
            "GET", "/api/billing/stripe-data", cookies={"compass_auth_token": expired_jwt}
        )
        self.assertEqual(resp.status, 401)

    async def test_create_setup_intent_requires_valid_jwt(self):
        """Test setup intent creation requires valid JWT token."""
        # Test without token
        resp = await self.client.request("POST", "/api/billing/create-setup-intent")
        self.assertEqual(resp.status, 401)

        # Test with expired token
        expired_jwt = self.create_expired_billing_jwt()
        resp = await self.client.request(
            "POST", "/api/billing/create-setup-intent", cookies={"compass_auth_token": expired_jwt}
        )
        self.assertEqual(resp.status, 401)

    async def test_delete_payment_method_requires_valid_jwt(self):
        """Test payment method deletion requires valid JWT token."""
        payment_method_id = "pm_test123456789"

        # Test without token
        resp = await self.client.request(
            "DELETE", f"/api/billing/payment-method/{payment_method_id}"
        )
        self.assertEqual(resp.status, 401)

        # Test with expired token
        expired_jwt = self.create_expired_billing_jwt()
        resp = await self.client.request(
            "DELETE",
            f"/api/billing/payment-method/{payment_method_id}",
            cookies={"compass_auth_token": expired_jwt},
        )
        self.assertEqual(resp.status, 401)

    async def test_update_customer_details_requires_valid_jwt(self):
        """Test customer details update requires valid JWT token."""
        update_data = {"email": "new@example.com"}

        # Test without token
        resp = await self.client.request("PUT", "/api/billing/customer-details", json=update_data)
        self.assertEqual(resp.status, 401)

        # Test with expired token
        expired_jwt = self.create_expired_billing_jwt()
        resp = await self.client.request(
            "PUT",
            "/api/billing/customer-details",
            json=update_data,
            cookies={"compass_auth_token": expired_jwt},
        )
        self.assertEqual(resp.status, 401)

    async def test_confirm_payment_method_requires_valid_jwt(self):
        """Test payment method confirmation requires valid JWT token."""
        setup_intent_id = "seti_test123456789"

        # Test without token
        resp = await self.client.request(
            "POST", "/api/billing/confirm-payment-method", json={"setup_intent_id": setup_intent_id}
        )
        self.assertEqual(resp.status, 401)

        # Test with expired token
        expired_jwt = self.create_expired_billing_jwt()
        resp = await self.client.request(
            "POST",
            "/api/billing/confirm-payment-method",
            json={"setup_intent_id": setup_intent_id},
            cookies={"compass_auth_token": expired_jwt},
        )
        self.assertEqual(resp.status, 401)
