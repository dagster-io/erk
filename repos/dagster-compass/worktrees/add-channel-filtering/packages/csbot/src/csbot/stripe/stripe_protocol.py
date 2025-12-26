"""Protocol defining the interface for Stripe client operations.

NOTE: When modifying this protocol, ensure the test implementation in
tests/stripe/test_stripe_client.py is kept in sync with any changes.
"""

from typing import Any, NamedTuple, Protocol, runtime_checkable

from csbot.slackbot.storage.interface import PlanLimits


class ProductWithPrice(NamedTuple):
    """Product details with pricing information."""

    product_id: str
    name: str
    description: str | None
    price_id: str
    unit_amount: int
    currency: str
    recurring_interval: str | None
    metadata: dict[str, str]


class MeterEvent(NamedTuple):
    """Stripe billing meter event data."""

    id: str
    object: str
    event_name: str
    identifier: str
    payload: dict[str, str]
    timestamp: int
    created: int
    livemode: bool


@runtime_checkable
class StripeClientProtocol(Protocol):
    """Protocol defining the interface for Stripe client operations."""

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
        ...

    def create_subscription(self, customer_id: str, product_id: str) -> dict[str, Any]:
        """Create a new Stripe subscription for a customer.

        Args:
            customer_id: The Stripe customer ID
            product_id: The Stripe product ID to subscribe to

        Returns:
            Dictionary containing the created subscription data
        """
        ...

    def get_customer_payment_methods(self, customer_id: str) -> list[dict[str, Any]]:
        """Get payment methods for a customer.

        Args:
            customer_id: The Stripe customer ID

        Returns:
            List of payment method dictionaries
        """
        ...

    def get_customer_details(self, customer_id: str) -> dict[str, Any]:
        """Get customer details including contact information.

        Args:
            customer_id: The Stripe customer ID

        Returns:
            Dictionary containing customer details
        """
        ...

    def get_subscription_details(self, subscription_id: str) -> dict[str, Any]:
        """Get subscription details.

        Args:
            subscription_id: The Stripe subscription ID

        Returns:
            Dictionary containing subscription details
        """
        ...

    def get_product_with_price(self, product_id: str) -> ProductWithPrice:
        """Get product details with pricing information.

        Args:
            product_id: The Stripe product ID

        Returns:
            ProductWithPrice containing structured product and pricing data
        """
        ...

    def create_setup_intent(self, customer_id: str) -> dict[str, Any]:
        """Create a setup intent for adding a payment method.

        Args:
            customer_id: The Stripe customer ID

        Returns:
            Dictionary containing setup intent data including client_secret
        """
        ...

    def detach_payment_method(self, payment_method_id: str) -> dict[str, Any]:
        """Detach a payment method from its customer.

        Args:
            payment_method_id: The Stripe payment method ID to detach

        Returns:
            Dictionary containing the detached payment method data
        """
        ...

    def update_customer(self, customer_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update customer details.

        Args:
            customer_id: The Stripe customer ID
            **kwargs: Fields to update (name, email, metadata, etc.)

        Returns:
            Dictionary containing the updated customer data
        """
        ...

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
        ...

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
        ...

    def submit_meter_usage(self, meter_name: str, customer_id: str, usage_value: int) -> MeterEvent:
        """Submit usage data to a Stripe billing meter.

        Args:
            meter_name: The name of the meter to record usage for
            customer_id: The Stripe customer ID
            usage_value: The usage value to record (must be a whole number)

        Returns:
            MeterEvent containing the created meter event data
        """
        ...
