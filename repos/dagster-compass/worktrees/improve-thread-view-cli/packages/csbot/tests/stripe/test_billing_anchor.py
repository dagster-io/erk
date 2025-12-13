"""Tests for billing anchor functionality in StripeClient."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

from csbot.stripe.stripe_client import StripeClient


class TestBillingAnchor:
    """Test suite for billing anchor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.stripe_client = StripeClient("test_api_key")

        # Mock the stripe library calls
        self.mock_price_list = Mock()
        self.mock_subscription_create = Mock()

        # Setup default mock responses
        mock_price = Mock()
        mock_price.id = "price_test123"
        self.mock_price_list.return_value.data = [mock_price]

        mock_subscription = {
            "id": "sub_test123",
            "object": "subscription",
            "customer": "cus_test123",
            "status": "active",
        }
        self.mock_subscription_create.return_value = mock_subscription

    @patch("stripe.Subscription.create")
    @patch("stripe.Price.list")
    def test_billing_anchor_mid_month_signup(self, mock_price_list, mock_subscription_create):
        """Test billing anchor when customer signs up mid-month."""
        # Setup mocks
        mock_price_list.side_effect = self.mock_price_list
        mock_subscription_create.side_effect = self.mock_subscription_create

        # Mock current time to January 15th, 2024 at 10:30 AM UTC
        mock_signup_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        with patch("csbot.stripe.stripe_client.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_signup_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Call create_subscription
            result = self.stripe_client.create_subscription("cus_test123", "prod_test123")

            # Verify the subscription was created
            assert result["id"] == "sub_test123"

            # Verify stripe.Subscription.create was called with correct billing anchor
            mock_subscription_create.assert_called_once()
            call_args = mock_subscription_create.call_args

            # Extract billing_cycle_anchor from the call
            billing_cycle_anchor = call_args.kwargs["billing_cycle_anchor"]

            # Expected billing anchor should be Feb 1st, 2024 at 00:00:00 UTC
            expected_anchor_dt = datetime(2024, 2, 1, 0, 0, 0, tzinfo=UTC)
            expected_anchor_timestamp = int(expected_anchor_dt.timestamp())

            assert billing_cycle_anchor == expected_anchor_timestamp

    @patch("stripe.Subscription.create")
    @patch("stripe.Price.list")
    def test_billing_anchor_december_signup(self, mock_price_list, mock_subscription_create):
        """Test billing anchor when customer signs up in December (year rollover)."""
        # Setup mocks
        mock_price_list.side_effect = self.mock_price_list
        mock_subscription_create.side_effect = self.mock_subscription_create

        # Mock current time to December 20th, 2024 at 2:15 PM UTC
        mock_signup_time = datetime(2024, 12, 20, 14, 15, 0, tzinfo=UTC)

        with patch("csbot.stripe.stripe_client.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_signup_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Call create_subscription
            result = self.stripe_client.create_subscription("cus_test123", "prod_test123")

            # Verify the subscription was created
            assert result["id"] == "sub_test123"

            # Verify stripe.Subscription.create was called with correct billing anchor
            mock_subscription_create.assert_called_once()
            call_args = mock_subscription_create.call_args

            # Extract billing_cycle_anchor from the call
            billing_cycle_anchor = call_args.kwargs["billing_cycle_anchor"]

            # Expected billing anchor should be Jan 1st, 2025 at 00:00:00 UTC (next year)
            expected_anchor_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
            expected_anchor_timestamp = int(expected_anchor_dt.timestamp())

            assert billing_cycle_anchor == expected_anchor_timestamp

    @patch("stripe.Subscription.create")
    @patch("stripe.Price.list")
    def test_billing_anchor_first_of_month_signup(self, mock_price_list, mock_subscription_create):
        """Test billing anchor when customer signs up on the first day of the month."""
        # Setup mocks
        mock_price_list.side_effect = self.mock_price_list
        mock_subscription_create.side_effect = self.mock_subscription_create

        # Mock current time to March 1st, 2024 at 9:00 AM UTC
        mock_signup_time = datetime(2024, 3, 1, 9, 0, 0, tzinfo=UTC)

        with patch("csbot.stripe.stripe_client.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_signup_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Call create_subscription
            result = self.stripe_client.create_subscription("cus_test123", "prod_test123")

            # Verify the subscription was created
            assert result["id"] == "sub_test123"

            # Verify stripe.Subscription.create was called with correct billing anchor
            mock_subscription_create.assert_called_once()
            call_args = mock_subscription_create.call_args

            # Extract billing_cycle_anchor from the call
            billing_cycle_anchor = call_args.kwargs["billing_cycle_anchor"]

            # Expected billing anchor should be April 1st, 2024 at 00:00:00 UTC
            expected_anchor_dt = datetime(2024, 4, 1, 0, 0, 0, tzinfo=UTC)
            expected_anchor_timestamp = int(expected_anchor_dt.timestamp())

            assert billing_cycle_anchor == expected_anchor_timestamp

    @patch("stripe.Subscription.create")
    @patch("stripe.Price.list")
    def test_billing_anchor_end_of_month_signup(self, mock_price_list, mock_subscription_create):
        """Test billing anchor when customer signs up at the end of the month."""
        # Setup mocks
        mock_price_list.side_effect = self.mock_price_list
        mock_subscription_create.side_effect = self.mock_subscription_create

        # Mock current time to January 31st, 2024 at 11:59 PM UTC
        mock_signup_time = datetime(2024, 1, 31, 23, 59, 0, tzinfo=UTC)

        with patch("csbot.stripe.stripe_client.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_signup_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Call create_subscription
            result = self.stripe_client.create_subscription("cus_test123", "prod_test123")

            # Verify the subscription was created
            assert result["id"] == "sub_test123"

            # Verify stripe.Subscription.create was called with correct billing anchor
            mock_subscription_create.assert_called_once()
            call_args = mock_subscription_create.call_args

            # Extract billing_cycle_anchor from the call
            billing_cycle_anchor = call_args.kwargs["billing_cycle_anchor"]

            # Expected billing anchor should be February 1st, 2024 at 00:00:00 UTC
            expected_anchor_dt = datetime(2024, 2, 1, 0, 0, 0, tzinfo=UTC)
            expected_anchor_timestamp = int(expected_anchor_dt.timestamp())

            assert billing_cycle_anchor == expected_anchor_timestamp

    @patch("stripe.Subscription.create")
    @patch("stripe.Price.list")
    def test_billing_anchor_leap_year_february(self, mock_price_list, mock_subscription_create):
        """Test billing anchor during leap year February."""
        # Setup mocks
        mock_price_list.side_effect = self.mock_price_list
        mock_subscription_create.side_effect = self.mock_subscription_create

        # Mock current time to February 29th, 2024 (leap year) at 3:30 PM UTC
        mock_signup_time = datetime(2024, 2, 29, 15, 30, 0, tzinfo=UTC)

        with patch("csbot.stripe.stripe_client.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_signup_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Call create_subscription
            result = self.stripe_client.create_subscription("cus_test123", "prod_test123")

            # Verify the subscription was created
            assert result["id"] == "sub_test123"

            # Verify stripe.Subscription.create was called with correct billing anchor
            mock_subscription_create.assert_called_once()
            call_args = mock_subscription_create.call_args

            # Extract billing_cycle_anchor from the call
            billing_cycle_anchor = call_args.kwargs["billing_cycle_anchor"]

            # Expected billing anchor should be March 1st, 2024 at 00:00:00 UTC
            expected_anchor_dt = datetime(2024, 3, 1, 0, 0, 0, tzinfo=UTC)
            expected_anchor_timestamp = int(expected_anchor_dt.timestamp())

            assert billing_cycle_anchor == expected_anchor_timestamp

    @patch("stripe.Subscription.create")
    @patch("stripe.Price.list")
    def test_billing_anchor_with_different_timezones(
        self, mock_price_list, mock_subscription_create
    ):
        """Test that billing anchor calculation uses UTC regardless of system timezone."""
        # Setup mocks
        mock_price_list.side_effect = self.mock_price_list
        mock_subscription_create.side_effect = self.mock_subscription_create

        # Mock current time to July 15th, 2024 at 4:00 PM UTC
        mock_signup_time = datetime(2024, 7, 15, 16, 0, 0, tzinfo=UTC)

        with patch("csbot.stripe.stripe_client.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_signup_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Call create_subscription
            result = self.stripe_client.create_subscription("cus_test123", "prod_test123")

            # Verify the subscription was created
            assert result["id"] == "sub_test123"

            # Verify stripe.Subscription.create was called with correct billing anchor
            mock_subscription_create.assert_called_once()
            call_args = mock_subscription_create.call_args

            # Extract billing_cycle_anchor from the call
            billing_cycle_anchor = call_args.kwargs["billing_cycle_anchor"]

            # Expected billing anchor should be August 1st, 2024 at 00:00:00 UTC
            expected_anchor_dt = datetime(2024, 8, 1, 0, 0, 0, tzinfo=UTC)
            expected_anchor_timestamp = int(expected_anchor_dt.timestamp())

            assert billing_cycle_anchor == expected_anchor_timestamp

            # Verify that datetime.now was called with UTC timezone
            mock_datetime.now.assert_called_with(UTC)

    @patch("stripe.Subscription.create")
    @patch("stripe.Price.list")
    def test_billing_anchor_subscription_metadata(self, mock_price_list, mock_subscription_create):
        """Test that subscription still includes proper metadata along with billing anchor."""
        # Setup mocks
        mock_price_list.side_effect = self.mock_price_list
        mock_subscription_create.side_effect = self.mock_subscription_create

        # Mock current time to May 10th, 2024
        mock_signup_time = datetime(2024, 5, 10, 12, 0, 0, tzinfo=UTC)

        with patch("csbot.stripe.stripe_client.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_signup_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # Call create_subscription
            result = self.stripe_client.create_subscription("cus_test123", "prod_test123")

            # Verify the subscription was created
            assert result["id"] == "sub_test123"

            # Verify stripe.Subscription.create was called with all expected parameters
            mock_subscription_create.assert_called_once()
            call_args = mock_subscription_create.call_args

            # Verify all expected parameters are present
            assert "customer" in call_args.kwargs
            assert "items" in call_args.kwargs
            assert "billing_cycle_anchor" in call_args.kwargs
            assert "metadata" in call_args.kwargs

            # Verify values
            assert call_args.kwargs["customer"] == "cus_test123"
            assert call_args.kwargs["metadata"] == {"product_id": "prod_test123"}

            # Verify items structure
            items = call_args.kwargs["items"]
            assert len(items) == 1
            assert items[0]["price"] == "price_test123"
