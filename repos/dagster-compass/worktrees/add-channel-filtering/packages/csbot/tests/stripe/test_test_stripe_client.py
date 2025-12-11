"""Tests for the FakeStripeClient implementation."""

import pytest

from tests.utils.stripe_client import FakeStripeClient


class TestFakeStripeClient:
    """Test suite for the FakeStripeClient implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = FakeStripeClient("test_api_key")

    def test_create_customer(self):
        """Test creating a customer."""
        organization_name = "Test Organization"
        organization_id = "org_123"
        email = "test@example.com"

        customer = self.client.create_customer(organization_name, organization_id, email)

        assert customer["object"] == "customer"
        assert customer["email"] == email
        assert customer["name"] == organization_name
        assert customer["metadata"]["organization_id"] == organization_id
        assert customer["metadata"]["organization_name"] == organization_name
        assert customer["id"].startswith("cus_")
        assert customer["livemode"] is False

    def test_create_multiple_customers(self):
        """Test creating multiple customers with different data."""
        customers_data = [
            ("Org One", "org_001", "one@example.com"),
            ("Org Two", "org_002", "two@example.com"),
            ("Org Three", "org_003", "three@example.com"),
        ]

        created_customers = []
        for org_name, org_id, email in customers_data:
            customer = self.client.create_customer(org_name, org_id, email)
            created_customers.append(customer)

        # Verify all customers were created with unique IDs
        customer_ids = {c["id"] for c in created_customers}
        assert len(customer_ids) == 3

        # Verify all customers are in storage
        stored_customers = self.client.list_customers()
        assert len(stored_customers) == 3

    def test_get_customer(self):
        """Test retrieving a customer by ID."""
        organization_name = "Test Organization"
        organization_id = "org_123"
        email = "test@example.com"

        created_customer = self.client.create_customer(organization_name, organization_id, email)
        customer_id = created_customer["id"]

        retrieved_customer = self.client.get_customer(customer_id)
        assert retrieved_customer == created_customer

    def test_get_nonexistent_customer(self):
        """Test retrieving a customer that doesn't exist."""
        result = self.client.get_customer("cus_nonexistent")
        assert result is None

    def test_list_customers_empty(self):
        """Test listing customers when storage is empty."""
        customers = self.client.list_customers()
        assert customers == []

    def test_list_customers_with_data(self):
        """Test listing customers after creating some."""
        self.client.create_customer("Org 1", "org_1", "one@example.com")
        self.client.create_customer("Org 2", "org_2", "two@example.com")

        customers = self.client.list_customers()
        assert len(customers) == 2
        emails = {c["email"] for c in customers}
        assert emails == {"one@example.com", "two@example.com"}

    def test_clear_customers(self):
        """Test clearing all customers from storage."""
        self.client.create_customer("Org 1", "org_1", "one@example.com")
        self.client.create_customer("Org 2", "org_2", "two@example.com")

        assert len(self.client.list_customers()) == 2

        self.client.clear_customers()
        assert len(self.client.list_customers()) == 0

    def test_customer_id_format(self):
        """Test that generated customer IDs follow expected format."""
        customer = self.client.create_customer("Test Org", "org_123", "test@example.com")
        customer_id = customer["id"]

        # Should start with 'cus_' followed by 24 hex characters
        assert customer_id.startswith("cus_")
        assert len(customer_id) == 28  # 'cus_' (4) + 24 hex chars

        # The part after 'cus_' should be valid hex
        hex_part = customer_id[4:]
        try:
            int(hex_part, 16)
        except ValueError:
            pytest.fail(f"Customer ID hex part '{hex_part}' is not valid hex")

    def test_create_subscription(self):
        """Test creating a subscription for a customer."""
        # First create a customer
        customer = self.client.create_customer("Test Org", "org_123", "test@example.com")
        customer_id = customer["id"]
        product_id = "prod_test123"

        # Create subscription
        subscription = self.client.create_subscription(customer_id, product_id)

        assert subscription["object"] == "subscription"
        assert subscription["customer"] == customer_id
        assert subscription["status"] == "active"
        assert subscription["metadata"]["product_id"] == product_id
        assert subscription["id"].startswith("sub_")
        assert subscription["livemode"] is False

        # Verify subscription items structure
        items = subscription["items"]["data"]
        assert len(items) == 1
        assert items[0]["price"]["product"] == product_id
        assert items[0]["price"]["type"] == "recurring"
        assert items[0]["price"]["recurring"]["interval"] == "month"

    def test_create_multiple_subscriptions(self):
        """Test creating multiple subscriptions for different customers."""
        # Create customers
        customer1 = self.client.create_customer("Org 1", "org_1", "one@example.com")
        customer2 = self.client.create_customer("Org 2", "org_2", "two@example.com")

        # Create subscriptions
        self.client.create_subscription(customer1["id"], "prod_basic")
        self.client.create_subscription(customer2["id"], "prod_premium")

        # Verify both subscriptions exist
        subscriptions = self.client.list_subscriptions()
        assert len(subscriptions) == 2

        customer_ids = {sub["customer"] for sub in subscriptions}
        assert customer_ids == {customer1["id"], customer2["id"]}

    def test_get_subscription(self):
        """Test retrieving a subscription by ID."""
        customer = self.client.create_customer("Test Org", "org_123", "test@example.com")
        created_subscription = self.client.create_subscription(customer["id"], "prod_test")

        retrieved_subscription = self.client.get_subscription(created_subscription["id"])
        assert retrieved_subscription == created_subscription

    def test_get_nonexistent_subscription(self):
        """Test retrieving a subscription that doesn't exist."""
        result = self.client.get_subscription("sub_nonexistent")
        assert result is None

    def test_list_subscriptions_empty(self):
        """Test listing subscriptions when storage is empty."""
        subscriptions = self.client.list_subscriptions()
        assert subscriptions == []

    def test_clear_subscriptions(self):
        """Test clearing all subscriptions from storage."""
        customer = self.client.create_customer("Test Org", "org_123", "test@example.com")
        self.client.create_subscription(customer["id"], "prod_1")
        self.client.create_subscription(customer["id"], "prod_2")

        assert len(self.client.list_subscriptions()) == 2

        self.client.clear_subscriptions()
        assert len(self.client.list_subscriptions()) == 0

    def test_clear_all(self):
        """Test clearing all data from storage."""
        customer = self.client.create_customer("Test Org", "org_123", "test@example.com")
        self.client.create_subscription(customer["id"], "prod_test")

        assert len(self.client.list_customers()) == 1
        assert len(self.client.list_subscriptions()) == 1

        self.client.clear_all()
        assert len(self.client.list_customers()) == 0
        assert len(self.client.list_subscriptions()) == 0

    def test_subscription_id_format(self):
        """Test that generated subscription IDs follow expected format."""
        customer = self.client.create_customer("Test Org", "org_123", "test@example.com")
        subscription = self.client.create_subscription(customer["id"], "prod_test")
        subscription_id = subscription["id"]

        # Should start with 'sub_' followed by 24 hex characters
        assert subscription_id.startswith("sub_")
        assert len(subscription_id) == 28  # 'sub_' (4) + 24 hex chars

        # The part after 'sub_' should be valid hex
        hex_part = subscription_id[4:]
        try:
            int(hex_part, 16)
        except ValueError:
            pytest.fail(f"Subscription ID hex part '{hex_part}' is not valid hex")

    def test_get_product_plan_limits(self):
        """Test getting product plan limits for different products."""
        # Test Free plan
        free_limits = self.client.get_product_plan_limits("prod_Swl8Ec25xkX2VE")
        assert free_limits.base_num_answers == 10
        assert free_limits.allow_overage is False
        assert free_limits.num_channels == 1
        assert free_limits.allow_additional_channels is False

        # Test Starter plan
        starter_limits = self.client.get_product_plan_limits("prod_SwlG9kWDSHrfye")
        assert starter_limits.base_num_answers == 100
        assert starter_limits.allow_overage is True
        assert starter_limits.num_channels == 1
        assert starter_limits.allow_additional_channels is False

        # Test Team plan
        team_limits = self.client.get_product_plan_limits("prod_SwlG6vM56KdVWv")
        assert team_limits.base_num_answers == 1000
        assert team_limits.allow_overage is True
        assert team_limits.num_channels == 3
        assert team_limits.allow_additional_channels is False

    def test_get_product_plan_limits_unknown_product(self):
        """Test getting product plan limits for unknown product (uses generic defaults)."""
        limits = self.client.get_product_plan_limits("prod_unknown123")
        assert limits.base_num_answers == 50
        assert limits.allow_overage is False

    def test_get_product_plan_limits_missing_metadata(self):
        """Test handling products without plan limit metadata."""
        # Test unknown product that gets default metadata values
        limits = self.client.get_product_plan_limits("prod_no_metadata")
        assert limits.base_num_answers == 50  # Default value for unknown products
        assert limits.allow_overage is False
