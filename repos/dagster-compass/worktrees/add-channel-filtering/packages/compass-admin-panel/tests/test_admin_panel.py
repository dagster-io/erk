"""Tests for admin panel functionality."""

import uuid
from unittest.mock import Mock

from aiohttp.test_utils import AioHTTPTestCase
from csbot.slackbot.slackbot_core import CompassBotServerConfig
from csbot.slackbot.storage.interface import (
    OrganizationUsageData,
)
from pydantic import SecretStr

from compass_admin_panel.app import create_app


class FakeStripeClient:
    """Test implementation of Stripe client for admin panel tests."""

    def __init__(self, api_key: str, publishable_key: str):
        """Initialize the fake Stripe client."""
        self.api_key = api_key
        self.publishable_key = publishable_key
        self._customers: dict[str, dict] = {}
        self._subscriptions: dict[str, dict] = {}
        self._products: dict[str, dict] = {}
        self._prices: dict[str, dict] = {}

    def create_customer(self, name: str, org_id: str, email: str) -> dict:
        """Create a mock customer."""
        customer_id = f"cus_{uuid.uuid4().hex[:24]}"
        customer = {
            "id": customer_id,
            "object": "customer",
            "name": name,
            "email": email,
            "metadata": {"organization_id": org_id},
        }
        self._customers[customer_id] = customer
        return customer

    def create_subscription(self, customer_id: str, product_id: str) -> dict:
        """Create a mock subscription."""
        subscription_id = f"sub_{uuid.uuid4().hex[:24]}"
        price_id = f"price_{uuid.uuid4().hex[:24]}"

        # Create a mock price if it doesn't exist
        if price_id not in self._prices:
            self._prices[price_id] = {
                "id": price_id,
                "object": "price",
                "product": product_id,
                "active": True,
                "unit_amount": 10000,  # $100 in cents
                "currency": "usd",
                "recurring": {"interval": "month"},
            }

        subscription = {
            "id": subscription_id,
            "object": "subscription",
            "customer": customer_id,
            "status": "active",
            "items": {
                "object": "list",
                "data": [
                    {
                        "id": f"si_{uuid.uuid4().hex[:24]}",
                        "object": "subscription_item",
                        "price": self._prices[price_id],
                    }
                ],
            },
        }
        self._subscriptions[subscription_id] = subscription
        return subscription

    def get_customer_payment_methods(self, customer_id: str) -> list[dict]:
        """Get payment methods for a customer."""
        return [
            {
                "id": f"pm_{uuid.uuid4().hex[:24]}",
                "object": "payment_method",
                "type": "card",
                "card": {
                    "brand": "visa",
                    "last4": "4242",
                    "exp_month": 12,
                    "exp_year": 2025,
                },
            }
        ]


class MockStorage:
    """Mock storage implementation for admin panel tests."""

    def __init__(self):
        """Initialize mock storage with test data."""
        self.organizations: list[OrganizationUsageData] = []
        self.updated_orgs: dict[int, dict] = {}
        self.list_invite_tokens: Mock | None = None
        self.create_invite_token: Mock | None = None

    def add_test_organization(
        self,
        org_id: int,
        name: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        bot_count: int = 1,
        current_usage: int = 50,
        bonus_answers: int = 0,
    ):
        """Add a test organization to the mock storage."""
        org = OrganizationUsageData(
            organization_id=org_id,
            organization_name=name,
            organization_industry="Technology",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            bot_count=bot_count,
            current_usage=current_usage,
            bonus_answers=bonus_answers,
        )
        self.organizations.append(org)

    def list_organizations_with_usage_data(
        self, month: int, year: int, limit: int | None = None, offset: int | None = None
    ):
        """Return the test organizations with pagination support."""
        orgs = self.organizations
        if offset is not None:
            orgs = orgs[offset:]
        if limit is not None:
            orgs = orgs[:limit]
        return orgs

    def get_organization(self, org_id: int):
        """Get organization data."""
        for org in self.organizations:
            if org.organization_id == org_id:
                return org
        return None

    def update_organization(self, organization_id: int, **kwargs):
        """Update organization data."""
        self.updated_orgs[organization_id] = kwargs
        # Update the organization in our list
        for org in self.organizations:
            if org.organization_id == organization_id:
                for key, value in kwargs.items():
                    if hasattr(org, key):
                        setattr(org, key, value)


class AdminPanelTestCase(AioHTTPTestCase):
    """Base test case for admin panel functionality."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Create mock config
        self.mock_config = Mock(spec=CompassBotServerConfig)
        self.mock_config.database_uri = "sqlite:///:memory:"

        # Set up Stripe config with design partner product
        self.mock_config.stripe = Mock()
        self.mock_config.stripe.token = SecretStr("sk_test_mock_key")
        self.mock_config.stripe.publishable_key = "pk_test_mock_key"
        self.mock_config.stripe.free_product_id = "prod_Free123"
        self.mock_config.stripe.starter_product_id = "prod_Starter123"
        self.mock_config.stripe.team_product_id = "prod_Team123"
        self.mock_config.stripe.design_partner_product_id = "prod_DesignPartner123"

        # Create mock storage with test data
        self.mock_storage = MockStorage()

        # Add test organizations
        self.mock_storage.add_test_organization(
            org_id=1,
            name="Acme Corp",
            stripe_customer_id="cus_acme123",
            stripe_subscription_id="sub_acme123",
            bot_count=2,
            current_usage=75,
            bonus_answers=10,
        )

        self.mock_storage.add_test_organization(
            org_id=2,
            name="Tech Startup",
            stripe_customer_id="cus_tech123",
            stripe_subscription_id=None,  # Free plan
            bot_count=1,
            current_usage=15,
            bonus_answers=0,
        )

        self.mock_storage.add_test_organization(
            org_id=3,
            name="Enterprise Ltd",
            stripe_customer_id="cus_enterprise123",
            stripe_subscription_id="sub_enterprise123",
            bot_count=5,
            current_usage=450,
            bonus_answers=25,
        )

    async def get_application(self):
        """Create test application."""
        from dataclasses import dataclass
        from unittest.mock import Mock

        from compass_admin_panel.app import AdminPanelContext

        app = create_app()

        # Create a proper mock Stripe client that implements the expected interface
        mock_stripe_client = Mock()

        # Mock subscription details response
        def mock_get_subscription_details(subscription_id):
            return {
                "id": subscription_id,
                "items": {
                    "data": [
                        {
                            "price": {
                                "product": "prod_Starter123"  # Default to starter plan
                            }
                        }
                    ]
                },
            }

        # Mock plan limits response
        @dataclass
        class MockPlanLimits:
            base_num_answers: int = 100

        def mock_get_product_plan_limits(product_id):
            return MockPlanLimits(base_num_answers=100)

        mock_stripe_client.get_subscription_details = mock_get_subscription_details
        mock_stripe_client.get_product_plan_limits = mock_get_product_plan_limits

        # Create proper AdminPanelContext for tests
        # Type ignore needed because MockStorage doesn't fully implement SlackbotStorage interface
        context = AdminPanelContext(
            config=self.mock_config,
            storage=self.mock_storage,
            stripe_client=mock_stripe_client,  # type: ignore[arg-type]
        )
        app["context"] = context

        return app


class TestOrganizationLoading(AdminPanelTestCase):
    """Test organization loading functionality."""

    async def test_plan_types_api_endpoint(self):
        """Test the new plan-types API endpoint works correctly."""
        # Test with specific organization IDs
        resp = await self.client.request("GET", "/api/plan-types?org_ids=1,2,3")
        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertIn("plan_types", data)

        plan_types = data["plan_types"]
        # Should have plan info for all requested organizations
        self.assertIn("1", plan_types)  # Acme Corp
        self.assertIn("2", plan_types)  # Tech Startup (free plan)
        self.assertIn("3", plan_types)  # Enterprise Ltd

        # Check plan info structure
        acme_plan = plan_types["1"]
        self.assertIn("plan_type", acme_plan)
        self.assertIn("plan_limit", acme_plan)
        self.assertIn("usage_over_limit", acme_plan)

        # Check free plan for Tech Startup
        tech_plan = plan_types["2"]
        self.assertEqual(tech_plan["plan_type"], "free")
        self.assertEqual(tech_plan["plan_limit"], 50)

    async def test_plan_types_api_endpoint_missing_org_ids(self):
        """Test the plan-types API endpoint fails without org_ids parameter."""
        resp = await self.client.request("GET", "/api/plan-types")
        self.assertEqual(resp.status, 400)

        data = await resp.json()
        self.assertIn("error", data)
        self.assertIn("No organization IDs provided", data["error"])

    async def test_plan_types_api_endpoint_invalid_org_ids(self):
        """Test the plan-types API endpoint fails with invalid org_ids."""
        resp = await self.client.request("GET", "/api/plan-types?org_ids=invalid,format")
        self.assertEqual(resp.status, 400)

        data = await resp.json()
        self.assertIn("error", data)
        self.assertIn("Invalid organization ID format", data["error"])

    async def test_plan_types_api_endpoint_empty_result(self):
        """Test the plan-types API endpoint with non-existent org IDs."""
        resp = await self.client.request("GET", "/api/plan-types?org_ids=999,1000")
        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertIn("plan_types", data)
        self.assertEqual(len(data["plan_types"]), 0)  # No matching organizations

    async def test_index_page_loads_successfully(self):
        """Test that the admin panel index page loads without errors."""
        resp = await self.client.request("GET", "/")
        self.assertEqual(resp.status, 200)

        # Check that the response is HTML
        self.assertEqual(resp.content_type, "text/html")

        # Check that the page contains expected elements
        text = await resp.text()
        self.assertIn("Compass Admin Panel", text)
        self.assertIn("Organizations", text)
        # Actions header should appear since we have organizations with subscriptions
        self.assertIn("Actions", text)

    async def test_organizations_display_correctly(self):
        """Test that organizations are displayed with correct information."""
        resp = await self.client.request("GET", "/")
        self.assertEqual(resp.status, 200)

        text = await resp.text()

        # Check that organizations WITH subscriptions are displayed
        self.assertIn("Acme Corp", text)
        self.assertIn("Enterprise Ltd", text)

        # Check that Stripe customer IDs are displayed for subscribed organizations
        self.assertIn("cus_acme123", text)
        self.assertIn("cus_enterprise123", text)

        # Check that usage information is displayed for all organizations with loading indicators
        # With deferred loading, we show current usage with "Loading..." for limits
        self.assertIn("75 (+10 bonus) / ", text)  # Acme Corp usage with bonus
        self.assertIn("450 (+25 bonus) / ", text)  # Enterprise Ltd usage with bonus
        self.assertIn("15 / ", text)  # Tech Startup usage (no bonus)
        self.assertIn("Loading...", text)  # Should show loading indicators for limits

        # Check that all organizations are shown with loading indicators
        self.assertIn("Tech Startup", text)

    async def test_plan_types_display_correctly(self):
        """Test that plan types are determined and displayed correctly."""
        resp = await self.client.request("GET", "/")
        self.assertEqual(resp.status, 200)

        text = await resp.text()

        # Organizations with subscriptions should have plan types displayed
        # Our mock returns Starter plan for all subscriptions
        self.assertIn('class="plan-type plan-', text)
        self.assertIn("plan-starter", text)  # Should show starter plan from our mock

    async def test_actions_dropdown_present(self):
        """Test that action dropdowns are present for organizations with subscriptions."""
        resp = await self.client.request("GET", "/")
        self.assertEqual(resp.status, 200)

        text = await resp.text()

        # Check for actions dropdown elements (should appear for subscribed organizations)
        self.assertIn("actions-dropdown", text)
        self.assertIn("Actions ▼", text)
        self.assertIn("Convert to Design Partner", text)

        # Check JavaScript functions are present
        self.assertIn("toggleDropdown", text)
        self.assertIn("convertToDesignPartner", text)
        self.assertIn("convertToStarterPlan", text)

    async def test_empty_organizations_display(self):
        """Test behavior when no organizations exist."""
        # Clear organizations
        self.mock_storage.organizations = []

        resp = await self.client.request("GET", "/")
        self.assertEqual(resp.status, 200)

        text = await resp.text()
        self.assertIn("No organizations found", text)

    async def test_pagination_default_page(self):
        """Test pagination with default page parameters."""
        resp = await self.client.request("GET", "/")
        self.assertEqual(resp.status, 200)

        text = await resp.text()
        # Should show all organizations since we have less than 25 (default page size)
        self.assertIn("Acme Corp", text)
        self.assertIn("Tech Startup", text)
        self.assertIn("Enterprise Ltd", text)

        # Should show pagination info (for single page shows "Showing all X organizations")
        self.assertIn("Showing all 3 organizations", text)

    async def test_pagination_with_page_size(self):
        """Test pagination with custom page size."""
        resp = await self.client.request("GET", "/?page=1&page_size=2")
        self.assertEqual(resp.status, 200)

        text = await resp.text()
        # Should show pagination controls
        self.assertIn("pagination", text)
        self.assertIn("Showing 1-2 of 3 organizations", text)

        # Should show Next button since there are more pages
        self.assertIn("Next", text)

    async def test_pagination_second_page(self):
        """Test pagination on second page."""
        resp = await self.client.request("GET", "/?page=2&page_size=2")
        self.assertEqual(resp.status, 200)

        text = await resp.text()
        # Should show the remaining organization(s)
        self.assertIn("Showing 3-3 of 3 organizations", text)

        # Should show Previous button
        self.assertIn("Previous", text)

    async def test_pagination_invalid_page(self):
        """Test pagination with invalid page number."""
        # Page 0 should be treated as page 1
        resp = await self.client.request("GET", "/?page=0&page_size=25")
        self.assertEqual(resp.status, 200)

        text = await resp.text()
        # Should show all organizations
        self.assertIn("Acme Corp", text)
        self.assertIn("Tech Startup", text)
        self.assertIn("Enterprise Ltd", text)

    async def test_pagination_large_page_size_limit(self):
        """Test that page size is limited to maximum."""
        # Try to set page_size > 200 (our limit)
        resp = await self.client.request("GET", "/?page=1&page_size=500")
        self.assertEqual(resp.status, 200)

        # Page should still load successfully with limited page size
        text = await resp.text()
        self.assertIn("Compass Admin Panel", text)

    async def test_health_check_endpoint(self):
        """Test the health check endpoint."""
        resp = await self.client.request("GET", "/health")
        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "compass-admin-panel")


class TestDesignPartnerPlanDisplay(AdminPanelTestCase):
    """Test Design Partner plan display functionality."""

    def setUp(self):
        """Set up test with design partner organization."""
        super().setUp()

        # Add an organization with design partner subscription
        self.mock_storage.add_test_organization(
            org_id=99,
            name="Design Partner Co",
            stripe_customer_id="cus_design123",
            stripe_subscription_id="sub_design123",
            bot_count=3,
            current_usage=200,
            bonus_answers=50,
        )

    async def get_application(self):
        """Create test application with Design Partner mock."""
        from dataclasses import dataclass
        from unittest.mock import Mock

        from compass_admin_panel.app import AdminPanelContext

        app = create_app()

        # Create a mock Stripe client that returns Design Partner for sub_design123
        mock_stripe_client = Mock()

        def mock_get_subscription_details(subscription_id):
            if subscription_id == "sub_design123":
                return {
                    "id": subscription_id,
                    "items": {"data": [{"price": {"product": "prod_DesignPartner123"}}]},
                }
            # Default for other subscriptions
            return {
                "id": subscription_id,
                "items": {"data": [{"price": {"product": "prod_Starter123"}}]},
            }

        @dataclass
        class MockPlanLimits:
            base_num_answers: int = 100

        def mock_get_product_plan_limits(product_id):
            return MockPlanLimits(base_num_answers=100)

        mock_stripe_client.get_subscription_details = mock_get_subscription_details
        mock_stripe_client.get_product_plan_limits = mock_get_product_plan_limits

        # Create proper AdminPanelContext for tests
        # Type ignore needed because MockStorage doesn't fully implement SlackbotStorage interface
        context = AdminPanelContext(
            config=self.mock_config,
            storage=self.mock_storage,
            stripe_client=mock_stripe_client,  # type: ignore[arg-type]
        )
        app["context"] = context

        return app


class TestPlanConversionToDesignPartner(AdminPanelTestCase):
    """Test plan conversion to design partner functionality."""

    def setUp(self):
        """Set up test with mocking for shared billing routes function."""
        super().setUp()

        # Mock the shared function from billing routes
        from unittest.mock import AsyncMock, patch

        self.mock_switch_subscription = AsyncMock()
        self.mock_switch_subscription.return_value = {
            "success": True,
            "subscription_id": "sub_new_design123",
            "message": "Successfully switched to Design Partner plan",
        }

        # Patch the import in the organizations module (where it's now imported)
        self.switch_subscription_patcher = patch(
            "compass_admin_panel.organizations.switch_subscription_to_product",
            self.mock_switch_subscription,
        )
        self.switch_subscription_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.switch_subscription_patcher.stop()
        super().tearDown()

    async def test_convert_to_design_partner_success(self):
        """Test successful conversion to Design Partner plan."""
        payload = {
            "organization_id": 1,
            "stripe_customer_id": "cus_acme123",
            "stripe_subscription_id": "sub_acme123",  # Include existing subscription ID like frontend would
        }

        resp = await self.client.request(
            "POST",
            "/api/convert-to-design-partner",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertTrue(data["success"])
        self.assertIn("Successfully converted", data["message"])
        self.assertIn("subscription_id", data)

        # Verify the shared function was called with correct parameters
        self.mock_switch_subscription.assert_called_once()
        call_args = self.mock_switch_subscription.call_args

        # Check the function was called with expected arguments
        self.assertEqual(call_args.kwargs["stripe_customer_id"], "cus_acme123")
        self.assertEqual(call_args.kwargs["target_product_id"], "prod_DesignPartner123")
        self.assertEqual(call_args.kwargs["organization_id"], 1)

        # Verify the existing subscription ID was passed (from test org 1)
        self.assertEqual(call_args.kwargs["existing_subscription_id"], "sub_acme123")

    async def test_convert_missing_customer_id(self):
        """Test conversion fails with missing Stripe customer ID."""
        payload = {
            "organization_id": 2,
            "stripe_customer_id": None,  # Missing customer ID
        }

        resp = await self.client.request(
            "POST",
            "/api/convert-to-design-partner",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 400)

        data = await resp.json()
        self.assertIn("Missing", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()

    async def test_convert_stripe_function_error(self):
        """Test conversion when the shared billing function fails."""
        # Make the shared function raise an exception
        self.mock_switch_subscription.side_effect = Exception("Stripe API error")

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-design-partner",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("error", data)

        # Verify the shared function was called
        self.mock_switch_subscription.assert_called_once()

    async def test_convert_without_design_partner_config(self):
        """Test conversion fails when design partner product is not configured."""
        # Remove design partner product ID
        delattr(self.mock_config.stripe, "design_partner_product_id")

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-design-partner",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("Design Partner product not configured", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()

    async def test_convert_malformed_request(self):
        """Test conversion with malformed request body."""
        resp = await self.client.request(
            "POST",
            "/api/convert-to-design-partner",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Should get a JSON parsing error
        self.assertEqual(resp.status, 400)

    async def test_convert_missing_config(self):
        """Test conversion fails when admin panel is not properly configured."""
        # Remove context from app to simulate missing configuration
        del self.app["context"]

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-design-partner",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("not properly configured", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()


class TestPlanConversionToFreePlan(AdminPanelTestCase):
    """Test plan conversion to Free plan functionality."""

    def setUp(self):
        """Set up test with mocking for shared billing routes function."""
        super().setUp()

        # Mock the shared function from billing routes
        from unittest.mock import AsyncMock, patch

        self.mock_switch_subscription = AsyncMock()
        self.mock_switch_subscription.return_value = {
            "success": True,
            "subscription_id": "sub_new_free123",
            "message": "Successfully switched to Free plan",
        }

        # Patch the import in the organizations module (where it's now imported)
        self.switch_subscription_patcher = patch(
            "compass_admin_panel.organizations.switch_subscription_to_product",
            self.mock_switch_subscription,
        )
        self.switch_subscription_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.switch_subscription_patcher.stop()
        super().tearDown()

    async def test_convert_to_free_plan_success(self):
        """Test successful conversion to Free plan."""
        payload = {
            "organization_id": 1,
            "stripe_customer_id": "cus_acme123",
            "stripe_subscription_id": "sub_acme123",  # Include existing subscription ID like frontend would
        }

        resp = await self.client.request(
            "POST",
            "/api/convert-to-free-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertTrue(data["success"])
        self.assertIn("Successfully converted", data["message"])
        self.assertIn("subscription_id", data)

        # Verify the shared function was called with correct parameters
        self.mock_switch_subscription.assert_called_once()
        call_args = self.mock_switch_subscription.call_args

        # Check the function was called with expected arguments
        self.assertEqual(call_args.kwargs["stripe_customer_id"], "cus_acme123")
        self.assertEqual(call_args.kwargs["target_product_id"], "prod_Free123")
        self.assertEqual(call_args.kwargs["organization_id"], 1)

        # Verify the existing subscription ID was passed (from test org 1)
        self.assertEqual(call_args.kwargs["existing_subscription_id"], "sub_acme123")

    async def test_convert_missing_customer_id(self):
        """Test conversion fails with missing Stripe customer ID."""
        payload = {
            "organization_id": 2,
            "stripe_customer_id": None,  # Missing customer ID
        }

        resp = await self.client.request(
            "POST",
            "/api/convert-to-free-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 400)

        data = await resp.json()
        self.assertIn("Missing", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()

    async def test_convert_stripe_function_error(self):
        """Test conversion when the shared billing function fails."""
        # Make the shared function raise an exception
        self.mock_switch_subscription.side_effect = Exception("Stripe API error")

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-free-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("error", data)

        # Verify the shared function was called
        self.mock_switch_subscription.assert_called_once()

    async def test_convert_without_free_plan_config(self):
        """Test conversion fails when free product is not configured."""
        # Remove free product ID
        delattr(self.mock_config.stripe, "free_product_id")

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-free-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("Free product not configured", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()

    async def test_convert_malformed_request(self):
        """Test conversion with malformed request body."""
        resp = await self.client.request(
            "POST",
            "/api/convert-to-free-plan",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Should get a JSON parsing error
        self.assertEqual(resp.status, 400)

    async def test_convert_missing_config(self):
        """Test conversion fails when admin panel is not properly configured."""
        # Remove context from app to simulate missing configuration
        del self.app["context"]

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-free-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("not properly configured", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()


class TestPlanConversionToStarterPlan(AdminPanelTestCase):
    """Test plan conversion to Starter plan functionality."""

    def setUp(self):
        """Set up test with mocking for shared billing routes function."""
        super().setUp()

        # Mock the shared function from billing routes
        from unittest.mock import AsyncMock, patch

        self.mock_switch_subscription = AsyncMock()
        self.mock_switch_subscription.return_value = {
            "success": True,
            "subscription_id": "sub_new_starter123",
            "message": "Successfully switched to Starter plan",
        }

        # Patch the import in the organizations module (where it's now imported)
        self.switch_subscription_patcher = patch(
            "compass_admin_panel.organizations.switch_subscription_to_product",
            self.mock_switch_subscription,
        )
        self.switch_subscription_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.switch_subscription_patcher.stop()
        super().tearDown()

    async def test_convert_to_starter_plan_success(self):
        """Test successful conversion to Starter plan."""
        payload = {
            "organization_id": 1,
            "stripe_customer_id": "cus_acme123",
            "stripe_subscription_id": "sub_acme123",  # Include existing subscription ID like frontend would
        }

        resp = await self.client.request(
            "POST",
            "/api/convert-to-starter-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertTrue(data["success"])
        self.assertIn("Successfully converted", data["message"])
        self.assertIn("subscription_id", data)

        # Verify the shared function was called with correct parameters
        self.mock_switch_subscription.assert_called_once()
        call_args = self.mock_switch_subscription.call_args

        # Check the function was called with expected arguments
        self.assertEqual(call_args.kwargs["stripe_customer_id"], "cus_acme123")
        self.assertEqual(call_args.kwargs["target_product_id"], "prod_Starter123")
        self.assertEqual(call_args.kwargs["organization_id"], 1)

        # Verify the existing subscription ID was passed (from test org 1)
        self.assertEqual(call_args.kwargs["existing_subscription_id"], "sub_acme123")

    async def test_convert_missing_customer_id(self):
        """Test conversion fails with missing Stripe customer ID."""
        payload = {
            "organization_id": 2,
            "stripe_customer_id": None,  # Missing customer ID
        }

        resp = await self.client.request(
            "POST",
            "/api/convert-to-starter-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 400)

        data = await resp.json()
        self.assertIn("Missing", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()

    async def test_convert_stripe_function_error(self):
        """Test conversion when the shared billing function fails."""
        # Make the shared function raise an exception
        self.mock_switch_subscription.side_effect = Exception("Stripe API error")

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-starter-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("error", data)

        # Verify the shared function was called
        self.mock_switch_subscription.assert_called_once()

    async def test_convert_without_starter_plan_config(self):
        """Test conversion fails when starter product is not configured."""
        # Remove starter product ID
        delattr(self.mock_config.stripe, "starter_product_id")

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-starter-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("Starter product not configured", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()

    async def test_convert_malformed_request(self):
        """Test conversion with malformed request body."""
        resp = await self.client.request(
            "POST",
            "/api/convert-to-starter-plan",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Should get a JSON parsing error
        self.assertEqual(resp.status, 400)

    async def test_convert_missing_config(self):
        """Test conversion fails when admin panel is not properly configured."""
        # Remove context from app to simulate missing configuration
        del self.app["context"]

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-starter-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("not properly configured", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()


class TestPlanConversionToTeamPlan(AdminPanelTestCase):
    """Test plan conversion to Team plan functionality."""

    def setUp(self):
        """Set up test with mocking for shared billing routes function."""
        super().setUp()

        # Mock the shared function from billing routes
        from unittest.mock import AsyncMock, patch

        self.mock_switch_subscription = AsyncMock()
        self.mock_switch_subscription.return_value = {
            "success": True,
            "subscription_id": "sub_new_team123",
            "message": "Successfully switched to Team plan",
        }

        # Patch the import in the organizations module (where it's now imported)
        self.switch_subscription_patcher = patch(
            "compass_admin_panel.organizations.switch_subscription_to_product",
            self.mock_switch_subscription,
        )
        self.switch_subscription_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.switch_subscription_patcher.stop()
        super().tearDown()

    async def test_convert_to_team_plan_success(self):
        """Test successful conversion to Team plan."""
        payload = {
            "organization_id": 1,
            "stripe_customer_id": "cus_acme123",
            "stripe_subscription_id": "sub_acme123",  # Include existing subscription ID like frontend would
        }

        resp = await self.client.request(
            "POST",
            "/api/convert-to-team-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 200)

        data = await resp.json()
        self.assertTrue(data["success"])
        self.assertIn("Successfully converted", data["message"])
        self.assertIn("subscription_id", data)

        # Verify the shared function was called with correct parameters
        self.mock_switch_subscription.assert_called_once()
        call_args = self.mock_switch_subscription.call_args

        # Check the function was called with expected arguments
        self.assertEqual(call_args.kwargs["stripe_customer_id"], "cus_acme123")
        self.assertEqual(call_args.kwargs["target_product_id"], "prod_Team123")
        self.assertEqual(call_args.kwargs["organization_id"], 1)

        # Verify the existing subscription ID was passed (from test org 1)
        self.assertEqual(call_args.kwargs["existing_subscription_id"], "sub_acme123")

    async def test_convert_missing_customer_id(self):
        """Test conversion fails with missing Stripe customer ID."""
        payload = {
            "organization_id": 2,
            "stripe_customer_id": None,  # Missing customer ID
        }

        resp = await self.client.request(
            "POST",
            "/api/convert-to-team-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 400)

        data = await resp.json()
        self.assertIn("Missing", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()

    async def test_convert_stripe_function_error(self):
        """Test conversion when the shared billing function fails."""
        # Make the shared function raise an exception
        self.mock_switch_subscription.side_effect = Exception("Stripe API error")

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-team-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("error", data)

        # Verify the shared function was called
        self.mock_switch_subscription.assert_called_once()

    async def test_convert_without_team_plan_config(self):
        """Test conversion fails when team product is not configured."""
        # Remove team product ID
        delattr(self.mock_config.stripe, "team_product_id")

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-team-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("Team product not configured", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()

    async def test_convert_malformed_request(self):
        """Test conversion with malformed request body."""
        resp = await self.client.request(
            "POST",
            "/api/convert-to-team-plan",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Should get a JSON parsing error
        self.assertEqual(resp.status, 400)

    async def test_convert_missing_config(self):
        """Test conversion fails when admin panel is not properly configured."""
        # Remove context from app to simulate missing configuration
        del self.app["context"]

        payload = {"organization_id": 1, "stripe_customer_id": "cus_acme123"}

        resp = await self.client.request(
            "POST",
            "/api/convert-to-team-plan",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(resp.status, 500)

        data = await resp.json()
        self.assertIn("not properly configured", data["error"])

        # Verify the shared function was not called
        self.mock_switch_subscription.assert_not_called()


class TestTokensPage(AdminPanelTestCase):
    """Test invite tokens page functionality."""

    def setUp(self):
        """Set up test with mock tokens."""
        super().setUp()

        # Add mock token methods to storage
        self.mock_storage.list_invite_tokens = Mock(return_value=[])
        self.mock_storage.create_invite_token = Mock()

    async def test_tokens_page_loads(self):
        """Test that the tokens page loads successfully."""
        resp = await self.client.request("GET", "/tokens")
        self.assertEqual(resp.status, 200)

        text = await resp.text()
        self.assertIn("Invite Tokens", text)
        self.assertIn("Create New Token", text)

    async def test_create_token_endpoint(self):
        """Test token creation endpoint."""
        resp = await self.client.request("POST", "/tokens/create", allow_redirects=False)

        # Should redirect back to tokens page
        self.assertEqual(resp.status, 302)
        self.assertEqual(resp.headers["Location"], "/tokens")

        # Verify that create_invite_token was called
        self.mock_storage.create_invite_token.assert_called_once()


if __name__ == "__main__":
    import unittest

    unittest.main()
