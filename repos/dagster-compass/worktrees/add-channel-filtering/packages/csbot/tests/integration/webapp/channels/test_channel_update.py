"""Test cases for channel update API endpoint."""

from .base_channels_test import BaseChannelsTest


class TestChannelUpdate(BaseChannelsTest):
    """Test cases for channel update API endpoint."""

    async def test_channel_update_success(self):
        """Test successful channel connection update."""
        jwt_token = self.create_valid_channels_jwt()

        resp = await self.client.request(
            "POST",
            "/api/channels/update",
            json={
                "bot_id": self.governed_bot_key_1.to_bot_id(),
                "connection_names": ["conn1", "conn3"],
            },
            cookies=self.get_channels_cookies(jwt_token),
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data["success"])

        # Verify connections were reconciled
        self.mock_storage.reconcile_bot_connection.assert_called_once_with(
            self.organization_id,
            self.governed_bot_key_1.to_bot_id(),
            ["conn1", "conn3"],
        )

        # Verify bot discovery was triggered
        self.mock_bot_manager.discover_and_update_bots_for_keys.assert_called_once()

    async def test_channel_update_missing_required_field(self):
        """Test channel update fails without bot_id."""
        jwt_token = self.create_valid_channels_jwt()

        resp = await self.client.request(
            "POST",
            "/api/channels/update",
            json={"connection_names": ["conn1"]},
            cookies=self.get_channels_cookies(jwt_token),
        )

        self.assertEqual(resp.status, 400)
        data = await resp.json()
        self.assertIn("Bot ID is required", data["error"])

    async def test_channel_update_empty_connections(self):
        """Test updating channel with empty connections removes all."""
        jwt_token = self.create_valid_channels_jwt()

        resp = await self.client.request(
            "POST",
            "/api/channels/update",
            json={
                "bot_id": self.governed_bot_key_1.to_bot_id(),
                "connection_names": [],
            },
            cookies=self.get_channels_cookies(jwt_token),
        )

        self.assertEqual(resp.status, 200)

        # Verify connections were cleared
        self.mock_storage.reconcile_bot_connection.assert_called_once_with(
            self.organization_id,
            self.governed_bot_key_1.to_bot_id(),
            [],
        )
