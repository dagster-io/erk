"""Test cases for channel delete API endpoint."""

from unittest.mock import patch

from .base_channels_test import BaseChannelsTest


class TestChannelDelete(BaseChannelsTest):
    """Test cases for channel delete API endpoint."""

    async def test_channel_delete_success(self):
        """Test successful channel deletion."""
        jwt_token = self.create_valid_channels_jwt()

        with patch(
            "csbot.slackbot.webapp.channels.routes.delete_channel_and_bot_instance"
        ) as mock_delete:
            mock_delete.return_value = {"success": True}

            resp = await self.client.request(
                "DELETE",
                "/api/channels/delete",
                json={"bot_id": self.governed_bot_key_1.to_bot_id()},
                cookies=self.get_channels_cookies(jwt_token),
            )

            self.assertEqual(resp.status, 200)
            data = await resp.json()
            self.assertTrue(data["success"])

            # Verify delete was called with correct params
            call_kwargs = mock_delete.call_args[1]
            self.assertEqual(call_kwargs["channel_name"], "channel-1")
            self.assertEqual(call_kwargs["user_id"], "U123456")

    async def test_channel_delete_missing_required_field(self):
        """Test channel deletion fails without bot_id."""
        jwt_token = self.create_valid_channels_jwt()

        resp = await self.client.request(
            "DELETE",
            "/api/channels/delete",
            json={},
            cookies=self.get_channels_cookies(jwt_token),
        )

        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertIn("Bot ID is required", data["error"])

    async def test_channel_delete_slack_failure(self):
        """Test handling of Slack channel deletion failure."""
        jwt_token = self.create_valid_channels_jwt()

        with patch(
            "csbot.slackbot.webapp.channels.routes.delete_channel_and_bot_instance"
        ) as mock_delete:
            mock_delete.return_value = {
                "success": False,
                "error": "Failed to archive Slack channel",
            }

            resp = await self.client.request(
                "DELETE",
                "/api/channels/delete",
                json={"bot_id": self.governed_bot_key_1.to_bot_id()},
                cookies=self.get_channels_cookies(jwt_token),
            )

            self.assertEqual(resp.status, 400)
            data = await resp.json()
            self.assertEqual(data["error"], "Failed to archive Slack channel")
