"""Stripe client implementation for customer management."""

from datetime import UTC, datetime
from typing import Any

import stripe

from csbot.stripe.stripe_protocol import MeterEvent, PlanLimits, ProductWithPrice
from csbot.utils.check_async_context import ensure_not_in_async_context


class StripeClient:
    """Implementation of StripeClientProtocol using the stripe library."""

    def __init__(self, api_key: str, test_clock_id: str | None = None):
        """Initialize the Stripe client with an API key.

        Args:
            api_key: Stripe API key for authentication
            test_clock_id: Optional test clock ID for time-controlled testing
        """
        self.api_key = api_key
        self.test_clock_id = test_clock_id
        stripe.api_key = api_key

    def startup_assertions(self, prices_to_validate: list[str]):
        """Asserts that all configured Stripe prices have valid plan limits."""
        ensure_not_in_async_context()
        for price_id in prices_to_validate:
            product = stripe.Product.retrieve(price_id)
            self.get_product_plan_limits(product_id=product.id)

    def create_customer(
        self, organization_name: str, organization_id: str, email: str
    ) -> dict[str, Any]:
        """Create a new Stripe customer.

        Args:
            organization_name: The organization name
            organization_id: The organization identifier
            email: Customer email address

        Returns:
            Dictionary containing the created customer data
        """
        ensure_not_in_async_context()

        customer_params = {
            "email": email,
            "name": organization_name,
            "metadata": {
                "organization_id": organization_id,
                "organization_name": organization_name,
            },
        }

        # If using test clock, associate customer with test clock
        if self.test_clock_id:
            customer_params["test_clock"] = self.test_clock_id  # type: ignore[assignment]

        customer = stripe.Customer.create(**customer_params)  # type: ignore[call-arg]

        return dict(customer)

    def create_subscription(self, customer_id: str, product_id: str) -> dict[str, Any]:
        """Create a new Stripe subscription for a customer.

        Args:
            customer_id: The Stripe customer ID
            product_id: The Stripe product ID to subscribe to

        Returns:
            Dictionary containing the created subscription data
        """
        ensure_not_in_async_context()

        # First, get the price for the product (assuming the product has a default price)
        prices = stripe.Price.list(product=product_id, active=True, limit=1)

        if not prices.data:
            raise ValueError(f"No active prices found for product {product_id}")

        price_id = prices.data[0].id

        # Prepare subscription creation parameters
        subscription_params = {
            "customer": customer_id,
            "items": [{"price": price_id}],
            "metadata": {"product_id": product_id},
        }

        # For test clocks, subscriptions inherit the test clock from the customer
        # For normal operation, set billing cycle anchor
        if not self.test_clock_id:
            # Calculate the first day of next month for billing anchor
            # This ensures all customers are billed on the 1st of each month
            now = datetime.now(UTC)

            if now.month == 12:
                next_month_first = now.replace(
                    year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                next_month_first = now.replace(
                    month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
                )

            billing_cycle_anchor = int(next_month_first.timestamp())
            subscription_params["billing_cycle_anchor"] = billing_cycle_anchor  # type: ignore[assignment]

        subscription = stripe.Subscription.create(**subscription_params)  # type: ignore[call-arg]

        return dict(subscription)

    def get_customer_payment_methods(self, customer_id: str) -> list[dict[str, Any]]:
        """Get payment methods for a customer.

        Args:
            customer_id: The Stripe customer ID

        Returns:
            List of payment method dictionaries
        """
        ensure_not_in_async_context()
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type="card",  # Focus on card payment methods
            limit=10,
        )

        return [dict(pm) for pm in payment_methods.data]

    def get_customer_details(self, customer_id: str) -> dict[str, Any]:
        """Get customer details including contact information.

        Args:
            customer_id: The Stripe customer ID

        Returns:
            Dictionary containing customer details
        """
        ensure_not_in_async_context()
        customer = stripe.Customer.retrieve(customer_id)
        return dict(customer)

    def get_subscription_details(self, subscription_id: str) -> dict[str, Any]:
        """Get subscription details.

        Args:
            subscription_id: The Stripe subscription ID

        Returns:
            Dictionary containing subscription details
        """
        ensure_not_in_async_context()
        subscription = stripe.Subscription.retrieve(subscription_id)
        return dict(subscription)

    def get_product_with_price(self, product_id: str) -> ProductWithPrice:
        """Get product details with pricing information.

        Args:
            product_id: The Stripe product ID

        Returns:
            ProductWithPrice containing structured product and pricing data
        """
        ensure_not_in_async_context()
        # Get product details
        product = stripe.Product.retrieve(product_id)

        # Get the default price for this product
        prices = stripe.Price.list(product=product_id, active=True, limit=1)
        if not prices.data:
            raise ValueError(f"No active prices found for product {product_id}")

        price = prices.data[0]
        recurring_interval = price.recurring.interval if price.recurring else None

        return ProductWithPrice(
            product_id=product.id,
            name=product.name,
            description=product.description,
            price_id=price.id,
            unit_amount=price.unit_amount or 0,
            currency=price.currency,
            recurring_interval=recurring_interval,
            metadata=product.metadata,
        )

    def create_setup_intent(self, customer_id: str) -> dict[str, Any]:
        """Create a setup intent for adding a payment method.

        Args:
            customer_id: The Stripe customer ID

        Returns:
            Dictionary containing setup intent data including client_secret
        """
        ensure_not_in_async_context()
        setup_intent = stripe.SetupIntent.create(
            customer=customer_id,
            payment_method_types=["card"],
            usage="off_session",
        )
        return dict(setup_intent)

    def detach_payment_method(self, payment_method_id: str) -> dict[str, Any]:
        """Detach a payment method from its customer.

        Args:
            payment_method_id: The Stripe payment method ID to detach

        Returns:
            Dictionary containing the detached payment method data
        """
        ensure_not_in_async_context()
        payment_method = stripe.PaymentMethod.detach(payment_method_id)
        return dict(payment_method)

    def update_customer(self, customer_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update customer details.

        Args:
            customer_id: The Stripe customer ID
            **kwargs: Fields to update (name, email, metadata, etc.)

        Returns:
            Dictionary containing the updated customer data
        """
        ensure_not_in_async_context()
        customer = stripe.Customer.modify(customer_id, **kwargs)
        return dict(customer)

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
        ensure_not_in_async_context()
        customer = stripe.Customer.modify(
            customer_id, invoice_settings={"default_payment_method": payment_method_id}
        )
        return dict(customer)

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
        ensure_not_in_async_context()
        product_data = self.get_product_with_price(product_id)

        # Extract base_num_answers and convert to int if present
        assert "base_num_answers" in product_data.metadata, (
            f"base_num_answers is required in Compass Stripe product metadata for product {product_id}"
        )
        assert "allow_overage" in product_data.metadata, (
            f"allow_overage is required in Compass Stripe product metadata for product {product_id}"
        )
        assert product_data.metadata["allow_overage"] in ("true", "false"), (
            f"allow_overage must be true or false for product {product_id}"
        )
        assert "num_channels" in product_data.metadata, (
            f"num_channels is required in Compass Stripe product metadata for product {product_id}"
        )
        assert "allow_additional_channels" in product_data.metadata, (
            f"allow_additional_channels is required in Compass Stripe product metadata for product {product_id}"
        )
        assert product_data.metadata["allow_additional_channels"] in ("true", "false"), (
            f"allow_additional_channels must be true or false for product {product_id}"
        )
        base_num_answers = int(product_data.metadata["base_num_answers"])
        allow_overage = product_data.metadata["allow_overage"] == "true"
        num_channels = int(product_data.metadata["num_channels"])
        allow_additional_channels = product_data.metadata["allow_additional_channels"] == "true"

        return PlanLimits(
            base_num_answers=base_num_answers,
            allow_overage=allow_overage,
            num_channels=num_channels,
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
        ensure_not_in_async_context()
        meter_event = stripe.billing.MeterEvent.create(
            event_name=meter_name,
            payload={
                "stripe_customer_id": customer_id,
                "value": str(usage_value),  # Stripe expects string representation
            },
        )
        return MeterEvent(
            id=meter_event.identifier,
            object=meter_event.object,
            event_name=meter_event.event_name,
            identifier=meter_event.identifier,
            payload=meter_event.payload,
            timestamp=meter_event.timestamp,
            created=meter_event.created,
            livemode=meter_event.livemode,
        )
