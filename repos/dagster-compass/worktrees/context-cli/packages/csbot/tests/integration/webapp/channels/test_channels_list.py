"""Test cases for channels list API endpoint."""

from .base_channels_test import BaseChannelsTest


class TestChannelsList(BaseChannelsTest):
    """Test cases for channels list API endpoint."""

    async def test_channels_list_success(self):
        """Test successful channels list retrieval with all data."""
        jwt_token = self.create_valid_channels_jwt()

        resp = await self.client.request(
            "GET",
            "/api/channels/list",
            cookies=self.get_channels_cookies(jwt_token),
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        # Verify channels
        self.assertEqual(len(data["channels"]), 2)
        self.assertEqual(data["channels"][0]["bot_id"], self.governed_bot_key_1.to_bot_id())
        self.assertEqual(data["channels"][0]["channel_name"], "channel-1")
        self.assertEqual(data["channels"][0]["connection_names"], ["conn1", "conn2"])

        # Verify plan limits
        self.assertEqual(data["plan_limits"]["num_channels"], 3)
        self.assertEqual(data["plan_limits"]["allow_additional_channels"], False)

        # Verify available connections
        self.assertEqual(data["available_connections"], ["conn1", "conn2", "conn3"])

    async def test_channels_list_multiple_combined_bots(self):
        """Test that both QA and Combined bot types (data channels) appear, but Governance bots don't."""
        from unittest.mock import Mock

        from csbot.slackbot.bot_server.bot_server import BotKey
        from csbot.slackbot.channel_bot.bot import (
            BotTypeCombined,
            BotTypeGovernance,
            BotTypeQA,
            CompassChannelBaseBotInstance,
        )
        from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig

        jwt_token = self.create_valid_channels_jwt()

        # Add a third combined bot to verify multiple self-governing channels
        governed_bot_key_3 = BotKey(team_id=self.team_id, channel_name="channel-3")
        mock_governed_bot_3 = Mock(spec=CompassChannelBaseBotInstance)
        mock_governed_bot_3.key = governed_bot_key_3
        mock_governed_bot_3.bot_type = BotTypeCombined(governed_bot_keys=set([governed_bot_key_3]))
        mock_governed_bot_3.bot_config = Mock(spec=CompassBotSingleChannelConfig)
        mock_governed_bot_3.bot_config.organization_id = self.organization_id
        mock_governed_bot_3.bot_config.team_id = self.team_id

        # Add a QA bot (SHOULD appear - it's a data channel)
        qa_bot_key = BotKey(team_id=self.team_id, channel_name="qa-channel")
        mock_qa_bot = Mock(spec=CompassChannelBaseBotInstance)
        mock_qa_bot.key = qa_bot_key
        mock_qa_bot.bot_type = BotTypeQA()
        mock_qa_bot.bot_config = Mock(spec=CompassBotSingleChannelConfig)
        mock_qa_bot.bot_config.organization_id = self.organization_id
        mock_qa_bot.bot_config.team_id = self.team_id

        # Add a Governance-only bot (should NOT appear - admin channel, not data channel)
        governance_bot_key = BotKey(team_id=self.team_id, channel_name="governance-channel")
        mock_governance_bot = Mock(spec=CompassChannelBaseBotInstance)
        mock_governance_bot.key = governance_bot_key
        mock_governance_bot.bot_type = BotTypeGovernance(governed_bot_keys=set())
        mock_governance_bot.bot_config = Mock(spec=CompassBotSingleChannelConfig)
        mock_governance_bot.bot_config.organization_id = self.organization_id
        mock_governance_bot.bot_config.team_id = self.team_id

        # Add a bot from different organization (should NOT appear)
        other_org_bot_key = BotKey(team_id=self.team_id, channel_name="other-org-channel")
        mock_other_org_bot = Mock(spec=CompassChannelBaseBotInstance)
        mock_other_org_bot.key = other_org_bot_key
        mock_other_org_bot.bot_type = BotTypeCombined(governed_bot_keys=set([other_org_bot_key]))
        mock_other_org_bot.bot_config = Mock(spec=CompassBotSingleChannelConfig)
        mock_other_org_bot.bot_config.organization_id = 999  # Different org
        mock_other_org_bot.bot_config.team_id = self.team_id

        # Update bot server with all bots
        self.mock_bot_server.bots = {
            self.governed_bot_key_1: self.mock_governed_bot_1,
            self.governed_bot_key_2: self.mock_governed_bot_2,
            governed_bot_key_3: mock_governed_bot_3,
            qa_bot_key: mock_qa_bot,
            governance_bot_key: mock_governance_bot,
            other_org_bot_key: mock_other_org_bot,
        }

        resp = await self.client.request(
            "GET",
            "/api/channels/list",
            cookies=self.get_channels_cookies(jwt_token),
        )

        self.assertEqual(resp.status, 200)
        data = await resp.json()

        # Should return 4 channels: 3 combined + 1 QA (all data channels from our org)
        # Excludes: governance-only bot and other org bot
        self.assertEqual(len(data["channels"]), 4)

        # Verify all data channels are present
        channel_names = {ch["channel_name"] for ch in data["channels"]}
        self.assertEqual(channel_names, {"channel-1", "channel-2", "channel-3", "qa-channel"})

        # Verify they're sorted by channel name
        self.assertEqual(data["channels"][0]["channel_name"], "channel-1")
        self.assertEqual(data["channels"][1]["channel_name"], "channel-2")
        self.assertEqual(data["channels"][2]["channel_name"], "channel-3")
        self.assertEqual(data["channels"][3]["channel_name"], "qa-channel")

        # Verify governance-only bot and other org bot are NOT included
        for channel in data["channels"]:
            self.assertNotEqual(channel["channel_name"], "governance-channel")
            self.assertNotEqual(channel["channel_name"], "other-org-channel")

    async def test_channels_list_no_bots(self):
        """Test channels list when no bots exist for organization."""
        jwt_token = self.create_valid_channels_jwt()

        # Remove all bots to simulate no bots available
        self.mock_bot_server.bots = {}

        resp = await self.client.request(
            "GET",
            "/api/channels/list",
            cookies=self.get_channels_cookies(jwt_token),
        )

        # Bot validation happens in check_compass_cookie
        # When no bot is found for the organization, authentication fails with 401
        self.assertEqual(resp.status, 401)
        data = await resp.json()
        self.assertEqual(data["error"], "Unauthorized")
