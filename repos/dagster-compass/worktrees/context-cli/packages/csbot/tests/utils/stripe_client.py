"""Shared test Stripe client implementation for use across test modules."""

import uuid
from typing import Any

from csbot.stripe.stripe_protocol import (
    MeterEvent,
    PlanLimits,
    ProductWithPrice,
    StripeClientProtocol,
)


class FakeStripeClient:
    """Test implementation of StripeClientProtocol using local in-memory storage."""

    def __init__(self, api_key: str):
        """Initialize the test Stripe client with an API key.

        Args:
            api_key: API key for testing (not used but kept for compatibility)
        """
        self.api_key = api_key
        self._customers: dict[str, dict[str, Any]] = {}
        self._subscriptions: dict[str, dict[str, Any]] = {}
        self._payment_methods: dict[str, list[dict[str, Any]]] = {}

    def create_customer(
        self, organization_name: str, organization_id: str, email: str
    ) -> dict[str, Any]:
        """Create a new customer and store it in local memory.

        Args:
            organization_name: The organization name
            organization_id: The organization identifier
            email: Customer email address

        Returns:
            Dictionary containing the created customer data
        """
        customer_id = f"cus_{uuid.uuid4().hex[:24]}"

        customer_data = {
            "id": customer_id,
            "object": "customer",
            "email": email,
            "name": organization_name,
            "created": 1640995200,  # Mock timestamp
            "metadata": {
                "organization_id": organization_id,
                "organization_name": organization_name,
            },
            "livemode": False,
        }

        self._customers[customer_id] = customer_data
        return customer_data

    def create_subscription(self, customer_id: str, product_id: str) -> dict[str, Any]:
        """Create a new subscription and store it in local memory.

        Args:
            customer_id: The Stripe customer ID
            product_id: The Stripe product ID to subscribe to

        Returns:
            Dictionary containing the created subscription data
        """
        subscription_id = f"sub_{uuid.uuid4().hex[:24]}"
        price_id = f"price_{uuid.uuid4().hex[:24]}"  # Mock price ID

        subscription_data = {
            "id": subscription_id,
            "object": "subscription",
            "customer": customer_id,
            "status": "active",
            "created": 1640995200,  # Mock timestamp
            "current_period_start": 1640995200,
            "current_period_end": 1643673600,  # Mock end date (30 days later)
            "items": {
                "object": "list",
                "data": [
                    {
                        "id": f"si_{uuid.uuid4().hex[:24]}",
                        "object": "subscription_item",
                        "subscription": subscription_id,
                        "price": {
                            "id": price_id,
                            "object": "price",
                            "product": product_id,
                            "active": True,
                            "currency": "usd",
                            "type": "recurring",
                            "recurring": {
                                "interval": "month",
                                "interval_count": 1,
                            },
                        },
                    }
                ],
            },
            "metadata": {
                "product_id": product_id,
            },
            "livemode": False,
        }

        self._subscriptions[subscription_id] = subscription_data
        return subscription_data

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Get a customer by ID (helper method for testing).

        Args:
            customer_id: The customer ID to retrieve

        Returns:
            Customer data dictionary or None if not found
        """
        return self._customers.get(customer_id)

    def list_customers(self) -> list[dict[str, Any]]:
        """List all customers (helper method for testing).

        Returns:
            List of all customer data dictionaries
        """
        return list(self._customers.values())

    def get_subscription(self, subscription_id: str) -> dict[str, Any] | None:
        """Get a subscription by ID (helper method for testing).

        Args:
            subscription_id: The subscription ID to retrieve

        Returns:
            Subscription data dictionary or None if not found
        """
        return self._subscriptions.get(subscription_id)

    def list_subscriptions(self) -> list[dict[str, Any]]:
        """List all subscriptions (helper method for testing).

        Returns:
            List of all subscription data dictionaries
        """
        return list(self._subscriptions.values())

    def clear_customers(self) -> None:
        """Clear all customers from storage (helper method for testing)."""
        self._customers.clear()

    def clear_subscriptions(self) -> None:
        """Clear all subscriptions from storage (helper method for testing)."""
        self._subscriptions.clear()

    def get_customer_payment_methods(self, customer_id: str) -> list[dict[str, Any]]:
        """Get payment methods for a customer.

        Args:
            customer_id: The customer ID to retrieve payment methods for

        Returns:
            List of payment method dictionaries
        """
        return self._payment_methods.get(customer_id, [])

    def get_customer_details(self, customer_id: str) -> dict[str, Any]:
        """Get customer details including contact information.

        Args:
            customer_id: The customer ID to retrieve

        Returns:
            Dictionary containing customer details or empty dict if not found
        """
        customer = self._customers.get(customer_id)
        if customer is None:
            return {}
        return customer.copy()

    def add_payment_method(self, customer_id: str, payment_method: dict[str, Any]) -> None:
        """Add a payment method for a customer (test helper).

        Args:
            customer_id: The customer ID
            payment_method: Payment method data
        """
        if customer_id not in self._payment_methods:
            self._payment_methods[customer_id] = []
        self._payment_methods[customer_id].append(payment_method)

    def create_test_card_payment_method(
        self,
        customer_id: str,
        brand: str = "visa",
        last4: str = "4242",
        exp_month: int = 12,
        exp_year: int = 2025,
    ) -> dict[str, Any]:
        """Create a test card payment method (test helper).

        Args:
            customer_id: The customer ID
            brand: Card brand (visa, mastercard, etc.)
            last4: Last 4 digits of the card
            exp_month: Expiration month
            exp_year: Expiration year

        Returns:
            The created payment method data
        """
        payment_method_id = f"pm_{uuid.uuid4().hex[:24]}"
        payment_method = {
            "id": payment_method_id,
            "object": "payment_method",
            "type": "card",
            "card": {
                "brand": brand,
                "last4": last4,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "funding": "credit",
                "country": "US",
            },
            "customer": customer_id,
            "created": 1640995200,
            "livemode": False,
        }
        self.add_payment_method(customer_id, payment_method)
        return payment_method

    def get_subscription_details(self, subscription_id: str) -> dict[str, Any]:
        """Get subscription details.

        Args:
            subscription_id: The Stripe subscription ID

        Returns:
            Dictionary containing subscription details
        """
        subscription = self._subscriptions.get(subscription_id, {})
        return subscription.copy()

    def get_product_with_price(self, product_id: str) -> ProductWithPrice:
        """Get product details with pricing information.

        Args:
            product_id: The Stripe product ID

        Returns:
            ProductWithPrice containing structured product and pricing data
        """
        # Mock pricing data for specific test products used in billing tests
        mock_products = {
            "prod_Swl8Ec25xkX2VE": ProductWithPrice(  # Free plan
                product_id="prod_Swl8Ec25xkX2VE",
                name="Free",
                description=None,
                price_id="price_free",
                unit_amount=0,
                currency="usd",
                recurring_interval="month",
                metadata={},
            ),
            "prod_SwlG9kWDSHrfye": ProductWithPrice(  # Starter plan
                product_id="prod_SwlG9kWDSHrfye",
                name="Starter",
                description=None,
                price_id="price_starter",
                unit_amount=9900,  # $99.00 in cents
                currency="usd",
                recurring_interval="month",
                metadata={},
            ),
            "prod_SwlG6vM56KdVWv": ProductWithPrice(  # Team plan
                product_id="prod_SwlG6vM56KdVWv",
                name="Team",
                description=None,
                price_id="price_team",
                unit_amount=49900,  # $499.00 in cents
                currency="usd",
                recurring_interval="month",
                metadata={},
            ),
            "prod_test123": ProductWithPrice(  # Test Team plan for onboarding tests
                product_id="prod_test123",
                name="Team",
                description=None,
                price_id="price_test123",
                unit_amount=49900,  # $499.00 in cents
                currency="usd",
                recurring_interval="month",
                metadata={},
            ),
        }

        # Return specific mock data if available, otherwise generic mock data
        if product_id in mock_products:
            return mock_products[product_id]

        # Generic mock product with pricing data for unknown product IDs
        return ProductWithPrice(
            product_id=product_id,
            name=f"Test Product {product_id}",
            description=f"Mock product for testing: {product_id}",
            price_id=f"price_{uuid.uuid4().hex[:24]}",
            unit_amount=2000,  # $20.00 in cents
            currency="usd",
            recurring_interval="month",
            metadata={},
        )

    def get_product_plan_limits(self, product_id: str) -> PlanLimits:
        """Get plan limit metadata from a Stripe product.

        Args:
            product_id: The Stripe product ID

        Returns:
            PlanLimits containing plan limit information:
            - base_num_answers: int | None
            - allow_overage: bool (defaults to False)
            - num_channels: int
            - allow_additional_channels: bool (defaults to False)
        """
        # Mock metadata for test products
        metadata_by_product = {
            "prod_Swl8Ec25xkX2VE": {  # Free plan
                "base_num_answers": "10",
                "allow_overage": "false",
                "num_channels": "1",
                "allow_additional_channels": "false",
            },
            "prod_SwlG9kWDSHrfye": {  # Starter plan
                "base_num_answers": "100",
                "allow_overage": "true",
                "num_channels": "1",
                "allow_additional_channels": "false",
            },
            "prod_SwlG6vM56KdVWv": {  # Team plan
                "base_num_answers": "1000",
                "allow_overage": "true",
                "num_channels": "3",
                "allow_additional_channels": "false",
            },
            "prod_test123": {  # Test Team plan for onboarding tests
                "base_num_answers": "1000",
                "allow_overage": "true",
                "num_channels": "3",
                "allow_additional_channels": "false",
            },
        }

        metadata = metadata_by_product.get(
            product_id,
            {
                "base_num_answers": "50",
                "allow_overage": "false",
                "num_channels": "5",
                "allow_additional_channels": "false",
            },
        )

        # Extract base_num_answers and convert to int if present
        base_num_answers = metadata.get("base_num_answers")
        if base_num_answers is not None:
            base_num_answers = int(base_num_answers)

        # Extract allow_overage and convert to bool
        allow_overage_str = metadata.get("allow_overage", "false").lower()
        allow_overage = allow_overage_str in ("true", "1", "yes")

        # Extract num_channels and convert to int if present
        num_channels = metadata.get("num_channels")
        if num_channels is not None:
            num_channels = int(num_channels)

        # Extract allow_additional_channels and convert to bool
        allow_additional_channels_str = metadata.get("allow_additional_channels", "false").lower()
        allow_additional_channels = allow_additional_channels_str in ("true", "1", "yes")

        return PlanLimits(
            base_num_answers=base_num_answers or 0,
            allow_overage=allow_overage,
            num_channels=num_channels or 1,
            allow_additional_channels=allow_additional_channels,
        )

    def submit_meter_usage(self, meter_name: str, customer_id: str, usage_value: int) -> MeterEvent:
        """Submit usage data to a Stripe billing meter.

        Args:
            meter_name: The name of the meter to record usage for
            customer_id: The Stripe customer ID
            usage_value: The usage value to record (must be a whole number)

        Returns:
            MeterEvent containing the created meter event data
        """
        meter_event_id = f"bme_{uuid.uuid4().hex[:24]}"

        return MeterEvent(
            id=meter_event_id,
            object="billing.meter_event",
            event_name=meter_name,
            identifier=meter_event_id,
            payload={
                "stripe_customer_id": customer_id,
                "value": str(usage_value),
            },
            timestamp=1640995200,  # Mock timestamp
            created=1640995200,
            livemode=False,
        )

    def create_setup_intent(self, customer_id: str) -> dict[str, Any]:
        """Create a setup intent for adding a payment method.

        Args:
            customer_id: The Stripe customer ID

        Returns:
            Dictionary containing setup intent data including client_secret
        """
        setup_intent_id = f"seti_{uuid.uuid4().hex[:24]}"
        client_secret = f"{setup_intent_id}_secret_{uuid.uuid4().hex[:16]}"

        return {
            "id": setup_intent_id,
            "object": "setup_intent",
            "customer": customer_id,
            "status": "requires_payment_method",
            "usage": "off_session",
            "client_secret": client_secret,
            "created": 1640995200,
            "livemode": False,
        }

    def detach_payment_method(self, payment_method_id: str) -> dict[str, Any]:
        """Detach a payment method from its customer.

        Args:
            payment_method_id: The Stripe payment method ID to detach

        Returns:
            Dictionary containing the detached payment method data
        """
        # Find and remove the payment method from all customers
        detached_method = None
        for methods in self._payment_methods.values():
            for i, method in enumerate(methods):
                if method["id"] == payment_method_id:
                    detached_method = methods.pop(i).copy()
                    detached_method["customer"] = None
                    break
            if detached_method:
                break

        if not detached_method:
            # Return a mock detached payment method if not found
            detached_method = {
                "id": payment_method_id,
                "object": "payment_method",
                "type": "card",
                "customer": None,
                "livemode": False,
            }

        return detached_method

    def update_customer(self, customer_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update customer details.

        Args:
            customer_id: The Stripe customer ID
            **kwargs: Fields to update (name, email, metadata, etc.)

        Returns:
            Dictionary containing the updated customer data
        """
        customer = self._customers.get(customer_id)
        if not customer:
            # Return empty dict if customer not found
            return {}

        # Update the customer data with provided fields
        for key, value in kwargs.items():
            if key == "metadata" and isinstance(value, dict) and "metadata" in customer:
                # Merge metadata
                customer["metadata"].update(value)
            else:
                customer[key] = value

        return customer.copy()

    def set_default_payment_method(
        self, customer_id: str, payment_method_id: str
    ) -> dict[str, Any]:
        """Set a payment method as the default for a customer.

        Args:
            customer_id: The Stripe customer ID
            payment_method_id: The payment method ID to set as default

        Returns:
            Dictionary containing the updated customer data
        """
        customer = self._customers.get(customer_id)
        if not customer:
            return {}

        # Set the default payment method on the customer
        customer["invoice_settings"] = {
            "default_payment_method": payment_method_id,
        }

        return customer.copy()

    def clear_all(self) -> None:
        """Clear all data from storage (helper method for testing)."""
        self._customers.clear()
        self._subscriptions.clear()
        self._payment_methods.clear()


# Ensure the test client follows the protocol
assert isinstance(FakeStripeClient("test_key"), StripeClientProtocol)
