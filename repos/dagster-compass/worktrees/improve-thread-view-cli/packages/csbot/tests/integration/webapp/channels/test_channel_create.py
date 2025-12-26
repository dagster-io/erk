"""Test cases for channel create API endpoint."""

from unittest.mock import patch

from csbot.slackbot.storage.interface import PlanLimits

from .base_channels_test import BaseChannelsTest


class TestChannelCreate(BaseChannelsTest):
    """Test cases for channel create API endpoint."""

    async def test_channel_create_success(self):
        """Test successful channel creation with connections."""
        jwt_token = self.create_valid_channels_jwt()

        with patch(
            "csbot.slackbot.webapp.channels.routes.create_channel_and_bot_instance"
        ) as mock_create:
            mock_create.return_value = {"success": True}

            resp = await self.client.request(
                "POST",
                "/api/channels/create",
                json={
                    "channel_name": "new-channel",
                    "connection_names": ["conn1", "conn2"],
                },
                cookies=self.get_channels_cookies(jwt_token),
            )

            self.assertEqual(resp.status, 200)
            data = await resp.json()
            self.assertTrue(data["success"])

            # Verify connections were reconciled and bot discovery triggered
            self.mock_storage.reconcile_bot_connection.assert_called_once()
            self.mock_bot_manager.discover_and_update_bots_for_keys.assert_called_once()

    async def test_channel_create_missing_required_field(self):
        """Test channel creation fails without channel_name."""
        jwt_token = self.create_valid_channels_jwt()

        resp = await self.client.request(
            "POST",
            "/api/channels/create",
            json={},
            cookies=self.get_channels_cookies(jwt_token),
        )

        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertIn("Channel name is required", data["error"])

    async def test_channel_create_enforces_plan_limits(self):
        """Test plan limits prevent channel creation when at limit."""
        jwt_token = self.create_valid_channels_jwt()

        # Set restrictive plan limits
        self.mock_bot_server.get_plan_limits_from_cache_or_bail.return_value = PlanLimits(
            base_num_answers=100,
            allow_overage=False,
            num_channels=2,  # Current count is 2
            allow_additional_channels=False,
        )

        resp = await self.client.request(
            "POST",
            "/api/channels/create",
            json={"channel_name": "new-channel"},
            cookies=self.get_channels_cookies(jwt_token),
        )

        self.assertEqual(resp.status, 403)
        data = await resp.json()
        self.assertIn("plan limit", data["error"].lower())

    async def test_channel_create_allows_additional_when_enabled(self):
        """Test allow_additional_channels bypasses plan limits."""
        jwt_token = self.create_valid_channels_jwt()

        self.mock_bot_server.get_plan_limits_from_cache_or_bail.return_value = PlanLimits(
            base_num_answers=100,
            allow_overage=False,
            num_channels=2,
            allow_additional_channels=True,  # Allow more
        )

        with patch(
            "csbot.slackbot.webapp.channels.routes.create_channel_and_bot_instance"
        ) as mock_create:
            mock_create.return_value = {"success": True}

            resp = await self.client.request(
                "POST",
                "/api/channels/create",
                json={"channel_name": "new-channel"},
                cookies=self.get_channels_cookies(jwt_token),
            )

            self.assertEqual(resp.status, 200)

    async def test_channel_create_slack_failure(self):
        """Test handling of Slack channel creation failure."""
        jwt_token = self.create_valid_channels_jwt()

        with patch(
            "csbot.slackbot.webapp.channels.routes.create_channel_and_bot_instance"
        ) as mock_create:
            mock_create.return_value = {
                "success": False,
                "error": "Slack channel creation failed",
            }

            resp = await self.client.request(
                "POST",
                "/api/channels/create",
                json={"channel_name": "new-channel"},
                cookies=self.get_channels_cookies(jwt_token),
            )

            self.assertEqual(resp.status, 400)
            data = await resp.json()
            self.assertEqual(data["error"], "Slack channel creation failed")
