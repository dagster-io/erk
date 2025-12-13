"""Tests for SyncStripeSubscriptions background task."""

from unittest.mock import MagicMock, patch

import pytest

from csbot.slackbot.config import UnsupportedKekConfig
from csbot.slackbot.envelope_encryption import KekProvider
from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
from csbot.slackbot.storage.sqlite import SlackbotSqliteStorage, SqliteConnectionFactory
from csbot.slackbot.tasks.sync_stripe_subscriptions import SyncStripeSubscriptions
from csbot.slackbot.usage_tracking import UsageTracker


class TestSyncStripeSubscriptions:
    """Test suite for SyncStripeSubscriptions task."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_stripe_client = MagicMock()

        # Create a real SQLite connection factory for testing
        self.sql_conn_factory = SqliteConnectionFactory.temporary_for_testing()

        # Create mock KEK provider for testing
        self.kek_provider = KekProvider(UnsupportedKekConfig())

        # Create real storage with the connection factory
        self.storage = SlackbotSqliteStorage(self.sql_conn_factory, self.kek_provider)

        # Create real analytics store and usage tracker
        self.analytics_store = SlackbotAnalyticsStore(self.sql_conn_factory)
        self.usage_tracker = UsageTracker(self.sql_conn_factory)

        self.task = SyncStripeSubscriptions(
            stripe_client=self.mock_stripe_client,
            usage_tracker=UsageTracker(self.sql_conn_factory),
            plan_manager=MagicMock(),
            organizations_provider=self.storage.list_organizations,
            interval_hours=1,
        )  # 1 hour for testing

    async def create_test_organization(
        self,
        name: str = "Test Org",
        industry: str = "Software",
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
    ) -> int:
        """Helper method to create a test organization."""
        return await self.storage.create_organization(
            name=name,
            industry=industry,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            has_governance_channel=True,
            contextstore_github_repo="test/repo",
        )

    async def create_test_usage_data(
        self, bot_id: str, month: int, year: int, answer_count: int
    ) -> None:
        """Helper method to create test usage data."""
        await self.usage_tracker.insert_usage_data_for_testing(bot_id, month, year, answer_count)

    async def create_test_bot_instance(
        self,
        channel_name: str = "test",
        slack_team_id: str = "T123456",
        organization_id: int = 1,
    ) -> int:
        """Helper method to create a test bot instance."""
        return await self.storage.create_bot_instance(
            channel_name=channel_name,
            governance_alerts_channel="alerts",
            contextstore_github_repo="test/repo",
            slack_team_id=slack_team_id,
            bot_email="test@example.com",
            organization_id=organization_id,
        )

    def test_init_default_interval(self):
        """Test task initialization with default interval."""
        task = SyncStripeSubscriptions(
            stripe_client=self.mock_stripe_client,
            usage_tracker=self.usage_tracker,
            plan_manager=MagicMock(),
            organizations_provider=self.storage.list_organizations,
        )
        assert task.interval_seconds == 24 * 60 * 60  # 24 hours in seconds

    def test_init_custom_interval(self):
        """Test task initialization with custom interval."""
        task = SyncStripeSubscriptions(
            stripe_client=self.mock_stripe_client,
            usage_tracker=self.usage_tracker,
            plan_manager=MagicMock(),
            organizations_provider=self.storage.list_organizations,
            interval_hours=6,
        )
        assert task.interval_seconds == 6 * 3600  # 6 hours in seconds

    @pytest.mark.asyncio
    async def test_execute_no_organizations(self):
        """Test execute when no organizations exist."""

        # No need to mock - empty database will return empty list naturally

        await self.task.execute_tick()

        # Should not call stripe client when no organizations exist
        self.mock_stripe_client.get_subscription_details.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_organization_without_subscription(self):
        """Test execute with organization that has no Stripe subscription."""

        await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id=None,
        )

        await self.task.execute_tick()

        # Should skip organizations without subscriptions
        self.mock_stripe_client.get_subscription_details.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_inactive_subscription(self):
        """Test execute with organization that has inactive subscription."""

        await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Mock inactive subscription
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "canceled",
            "items": {"data": []},
        }

        await self.task.execute_tick()

        self.mock_stripe_client.get_subscription_details.assert_called_once_with("sub_test123")
        # Should skip inactive subscriptions - no plan limits update

    @pytest.mark.asyncio
    async def test_execute_subscription_without_product_id(self):
        """Test execute with subscription that has no product ID."""

        await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Mock active subscription without product ID
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {"data": []},  # No items
        }

        await self.task.execute_tick()

        self.mock_stripe_client.get_subscription_details.assert_called_once_with("sub_test123")
        # Should skip subscriptions without product ID

    @pytest.mark.asyncio
    @patch("csbot.slackbot.tasks.sync_stripe_subscriptions.update_plan_limits_from_product")
    async def test_execute_successful_sync(self, mock_update_plan_limits):
        """Test successful sync of plan limits for active subscription."""

        org_id = await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Mock active subscription with product ID
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {
                "data": [
                    {
                        "price": {
                            "product": "prod_test123",
                            "id": "price_test123",
                        }
                    }
                ]
            },
        }

        mock_update_plan_limits.return_value = None

        await self.task.execute_tick()

        self.mock_stripe_client.get_subscription_details.assert_called_once_with("sub_test123")

        # Should call update_plan_limits_from_product
        mock_update_plan_limits.assert_called_once_with(
            stripe_client=self.mock_stripe_client,
            plan_manager=self.task._plan_manager,
            product_id="prod_test123",
            organization_id=org_id,
        )

    @pytest.mark.asyncio
    @patch("csbot.slackbot.tasks.sync_stripe_subscriptions.update_plan_limits_from_product")
    async def test_execute_multiple_organizations(self, mock_update_plan_limits):
        """Test sync with multiple organizations."""

        org1_id = await self.create_test_organization(
            name="Test Org 1",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )
        org2_id = await self.create_test_organization(
            name="Test Org 2",
            industry="Finance",
            stripe_customer_id="cus_test456",
            stripe_subscription_id="sub_test456",
        )
        await self.create_test_organization(
            name="Test Org 3",
            industry="Healthcare",
            stripe_customer_id="cus_test789",
            stripe_subscription_id=None,  # No subscription
        )

        # Mock subscription responses
        def mock_get_subscription(sub_id):
            if sub_id == "sub_test123":
                return {
                    "id": "sub_test123",
                    "status": "active",
                    "items": {"data": [{"price": {"product": "prod_starter"}}]},
                }
            elif sub_id == "sub_test456":
                return {
                    "id": "sub_test456",
                    "status": "active",
                    "items": {"data": [{"price": {"product": "prod_team"}}]},
                }
            return None

        self.mock_stripe_client.get_subscription_details.side_effect = mock_get_subscription
        mock_update_plan_limits.return_value = None

        await self.task.execute_tick()

        # Should have called Stripe for the 2 organizations with subscriptions
        assert self.mock_stripe_client.get_subscription_details.call_count == 2

        # Should have called update_plan_limits_from_product for both active subscriptions
        assert mock_update_plan_limits.call_count == 2
        mock_update_plan_limits.assert_any_call(
            stripe_client=self.mock_stripe_client,
            plan_manager=self.task._plan_manager,
            product_id="prod_starter",
            organization_id=org1_id,
        )
        mock_update_plan_limits.assert_any_call(
            stripe_client=self.mock_stripe_client,
            plan_manager=self.task._plan_manager,
            product_id="prod_team",
            organization_id=org2_id,
        )

    @pytest.mark.asyncio
    @patch("csbot.slackbot.tasks.sync_stripe_subscriptions.update_plan_limits_from_product")
    async def test_execute_partial_failures(self, mock_update_plan_limits):
        """Test sync continues even when individual organizations fail."""

        org1_id = await self.create_test_organization(
            name="Test Org 1",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )
        await self.create_test_organization(
            name="Test Org 2",
            industry="Finance",
            stripe_customer_id="cus_test456",
            stripe_subscription_id="sub_test456",
        )

        # First organization will succeed
        # Second organization will fail during Stripe call
        def mock_get_subscription(sub_id):
            if sub_id == "sub_test123":
                return {
                    "id": "sub_test123",
                    "status": "active",
                    "items": {"data": [{"price": {"product": "prod_starter"}}]},
                }
            elif sub_id == "sub_test456":
                raise Exception("Stripe API error")

        self.mock_stripe_client.get_subscription_details.side_effect = mock_get_subscription
        mock_update_plan_limits.return_value = None

        await self.task.execute_tick()

        # Should have attempted both Stripe calls
        assert self.mock_stripe_client.get_subscription_details.call_count == 2

        # Should have only called update for the successful organization
        mock_update_plan_limits.assert_called_once_with(
            stripe_client=self.mock_stripe_client,
            plan_manager=self.task._plan_manager,
            product_id="prod_starter",
            organization_id=org1_id,
        )

    @pytest.mark.asyncio
    @patch("csbot.slackbot.tasks.sync_stripe_subscriptions.update_plan_limits_from_product")
    async def test_execute_plan_limits_update_fails(self, mock_update_plan_limits):
        """Test sync continues when plan limits update fails."""

        await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Mock active subscription
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {"data": [{"price": {"product": "prod_test123"}}]},
        }

        # Make plan limits update fail
        mock_update_plan_limits.side_effect = Exception("Plan limits update error")

        await self.task.execute_tick()

        self.mock_stripe_client.get_subscription_details.assert_called_once()
        mock_update_plan_limits.assert_called_once()
        # Task should complete without raising exception

    @pytest.mark.asyncio
    async def test_execute_empty_subscription_items(self):
        """Test execute with subscription that has empty items data."""

        await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Mock subscription with empty items
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {"data": []},
        }

        await self.task.execute_tick()

        self.mock_stripe_client.get_subscription_details.assert_called_once()
        # Should skip - no product ID found

    @pytest.mark.asyncio
    async def test_execute_subscription_item_no_price(self):
        """Test execute with subscription item that has no price."""

        await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Mock subscription with item but no price
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {"data": [{}]},  # Item without price
        }

        await self.task.execute_tick()

        self.mock_stripe_client.get_subscription_details.assert_called_once()
        # Should skip - no product ID found

    @pytest.mark.asyncio
    @patch("csbot.slackbot.tasks.sync_stripe_subscriptions.update_plan_limits_from_product")
    async def test_usage_submission_with_current_month(self, mock_update_plan_limits):
        """Test successful usage submission for current month."""

        # Create organization with Stripe information
        org_id = await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Create bot instance for the organization
        await self.create_test_bot_instance(
            channel_name="test",
            slack_team_id="T123456",
            organization_id=org_id,
        )

        # Mock active subscription with product ID
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {
                "data": [
                    {
                        "price": {
                            "product": "prod_test123",
                            "id": "price_test123",
                        }
                    }
                ]
            },
        }

        mock_update_plan_limits.return_value = None
        self.mock_stripe_client.submit_meter_usage.return_value = {"id": "bme_test123"}

        # Create test usage data directly in the database - this matches the bot_id format
        await self.create_test_usage_data("T123456-test", 12, 2024, 50)  # Current month usage

        # Mock date to be in December 2024
        with patch("csbot.slackbot.tasks.sync_stripe_subscriptions.datetime") as mock_datetime:
            mock_datetime.now.return_value.month = 12
            mock_datetime.now.return_value.year = 2024

            with patch.object(self.task, "_should_submit_previous_month", return_value=False):
                await self.task.execute_tick()

        self.mock_stripe_client.get_subscription_details.assert_called_once_with("sub_test123")

        # Should call update_plan_limits_from_product
        mock_update_plan_limits.assert_called_once_with(
            stripe_client=self.mock_stripe_client,
            plan_manager=self.task._plan_manager,
            product_id="prod_test123",
            organization_id=org_id,
        )

        # Should submit current month usage
        self.mock_stripe_client.submit_meter_usage.assert_called_once_with(
            meter_name="answers",
            customer_id="cus_test123",
            usage_value=50,
        )

    @pytest.mark.asyncio
    @patch("csbot.slackbot.tasks.sync_stripe_subscriptions.update_plan_limits_from_product")
    async def test_usage_submission_no_customer_id(self, mock_update_plan_limits):
        """Test that usage submission is skipped when organization has no Stripe customer ID."""

        await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id=None,  # No customer ID
            stripe_subscription_id="sub_test123",
        )

        # Mock active subscription
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {"data": [{"price": {"product": "prod_test123"}}]},
        }

        mock_update_plan_limits.return_value = None

        await self.task.execute_tick()

        # Should update plan limits but not submit usage
        mock_update_plan_limits.assert_called_once()
        self.mock_stripe_client.submit_meter_usage.assert_not_called()

    @pytest.mark.asyncio
    @patch("csbot.slackbot.tasks.sync_stripe_subscriptions.update_plan_limits_from_product")
    async def test_usage_submission_no_usage_data(self, mock_update_plan_limits):
        """Test usage submission when organization has no usage data."""

        await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Mock active subscription
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {"data": [{"price": {"product": "prod_test123"}}]},
        }

        mock_update_plan_limits.return_value = None

        # No usage data created, so should return 0 usage naturally
        await self.task.execute_tick()

        # Should update plan limits but not submit usage (0 usage)
        mock_update_plan_limits.assert_called_once()
        self.mock_stripe_client.submit_meter_usage.assert_not_called()

    @pytest.mark.asyncio
    @patch("csbot.slackbot.tasks.sync_stripe_subscriptions.update_plan_limits_from_product")
    async def test_usage_submission_month_border_both_months(self, mock_update_plan_limits):
        """Test that both current and previous month usage are submitted on the first day of the month."""

        # Create organization with Stripe information
        org_id = await self.create_test_organization(
            name="Test Org",
            industry="Software",
            stripe_customer_id="cus_test123",
            stripe_subscription_id="sub_test123",
        )

        # Create bot instance for the organization
        await self.create_test_bot_instance(
            channel_name="test",
            slack_team_id="T123456",
            organization_id=org_id,
        )

        # Mock active subscription with product ID
        self.mock_stripe_client.get_subscription_details.return_value = {
            "id": "sub_test123",
            "status": "active",
            "items": {
                "data": [
                    {
                        "price": {
                            "product": "prod_test123",
                            "id": "price_test123",
                        }
                    }
                ]
            },
        }

        mock_update_plan_limits.return_value = None
        self.mock_stripe_client.submit_meter_usage.return_value = {"id": "bme_test123"}

        # Create usage data for both current (February 2024) and previous (January 2024) months
        await self.create_test_usage_data("T123456-test", 2, 2024, 75)  # Current month usage
        await self.create_test_usage_data("T123456-test", 1, 2024, 50)  # Previous month usage

        # Mock date to be February 1st, 2024 (first day of month - month border)
        with patch("csbot.slackbot.tasks.sync_stripe_subscriptions.datetime") as mock_datetime:
            mock_datetime.now.return_value.month = 2
            mock_datetime.now.return_value.year = 2024
            mock_datetime.now.return_value.day = 1  # First day of month

            await self.task.execute_tick()

        self.mock_stripe_client.get_subscription_details.assert_called_once_with("sub_test123")

        # Should call update_plan_limits_from_product
        mock_update_plan_limits.assert_called_once_with(
            stripe_client=self.mock_stripe_client,
            plan_manager=self.task._plan_manager,
            product_id="prod_test123",
            organization_id=org_id,
        )

        # Should submit BOTH current month and previous month usage
        assert self.mock_stripe_client.submit_meter_usage.call_count == 2

        # Verify the calls - order might vary so check both possibilities
        calls = self.mock_stripe_client.submit_meter_usage.call_args_list
        call_args = [
            (call.kwargs["usage_value"] if "usage_value" in call.kwargs else call[1]["usage_value"])
            for call in calls
        ]

        # Should have called with both 75 (current) and 50 (previous) usage values
        assert 75 in call_args, f"Expected 75 (current month usage) in calls, got: {call_args}"
        assert 50 in call_args, f"Expected 50 (previous month usage) in calls, got: {call_args}"

        # Verify both calls used the correct customer ID and meter name
        for call in calls:
            if "meter_name" in call.kwargs:
                assert call.kwargs["meter_name"] == "answers"
                assert call.kwargs["customer_id"] == "cus_test123"
            else:
                assert call[1]["meter_name"] == "answers"
                assert call[1]["customer_id"] == "cus_test123"
