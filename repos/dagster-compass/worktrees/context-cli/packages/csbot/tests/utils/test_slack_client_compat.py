"""Tests for FakeSlackClient compatibility methods matching slack_utils.py format."""

import pytest

from tests.utils.slack_client import FakeSlackClient


class TestFakeSlackClientCompat:
    """Test suite for FakeSlackClient compatibility methods."""

    @pytest.fixture
    def client(self) -> FakeSlackClient:
        """Create a fresh FakeSlackClient for each test."""
        return FakeSlackClient("xoxb-test-token")

    @pytest.mark.asyncio
    async def test_create_slack_team_compat(self, client: FakeSlackClient):
        """Test create_slack_team compatibility method."""
        result = await client.create_slack_team_compat(
            admin_token="admin_token_12345",
            team_name="Test Organization",
            team_domain="test-org-dgc",
            team_description="A test organization",
        )

        assert result["success"] is True
        assert result["team_name"] == "Test Organization"
        assert result["team_domain"] == "test-org-dgc"
        assert result["team_id"].startswith("T")

    @pytest.mark.asyncio
    async def test_create_slack_team_compat_domain_too_long(self, client: FakeSlackClient):
        """Test create_slack_team with domain that's too long."""
        result = await client.create_slack_team_compat(
            admin_token="admin_token_12345",
            team_name="Test Organization",
            team_domain="this-is-a-very-long-domain-name-that-exceeds-limit",
        )

        assert result["success"] is False
        assert "team domain must be 21 characters or fewer" in result["error"]

    @pytest.mark.asyncio
    async def test_create_channel_compat(self, client: FakeSlackClient):
        """Test create_channel compatibility method."""
        # Create team first
        team_result = await client.create_slack_team_compat(
            "admin_token", "Test Org", "test-org-dgc"
        )
        team_id = team_result["team_id"]

        # Create channel
        result = await client.create_channel_compat(
            admin_token="admin_token_12345",
            team_id=team_id,
            channel_name="test-compass",
            is_private=False,
        )

        assert result["success"] is True
        assert result["channel_name"] == "test-compass"
        assert result["is_private"] is False
        assert result["channel_id"].startswith("C")

    @pytest.mark.asyncio
    async def test_get_all_channels_compat(self, client: FakeSlackClient):
        """Test get_all_channels compatibility method."""
        # Create team and channels
        team_result = await client.create_slack_team_compat(
            "admin_token", "Test Org", "test-org-dgc"
        )
        team_id = team_result["team_id"]

        await client.create_channel_compat("admin_token", team_id, "general", False)
        await client.create_channel_compat("admin_token", team_id, "random", False)

        # Get all channels
        result = await client.get_all_channels_compat(
            org_bot_token="org_bot_token_12345",
            team_id=team_id,
        )

        assert result["success"] is True
        # Team automatically creates general + random, plus we created 2 more = 4 total
        assert len(result["channel_names"]) == 4
        assert "general" in result["channel_names"]
        assert "random" in result["channel_names"]
        assert "general" in result["channel_name_to_id"]
        assert len(result["channel_ids"].split(",")) == 4

    @pytest.mark.asyncio
    async def test_get_bot_user_id_compat(self, client: FakeSlackClient):
        """Test get_bot_user_id compatibility method."""
        result = await client.get_bot_user_id_compat(bot_token="bot_token_12345")

        assert result["success"] is True
        assert "user_id" in result
        assert "bot_id" in result
        assert result["user_id"].startswith("U")
        assert result["bot_id"].startswith("B")

    @pytest.mark.asyncio
    async def test_invite_bot_to_channel_compat(self, client: FakeSlackClient):
        """Test invite_bot_to_channel compatibility method."""
        # Create team and channel
        team_result = await client.create_slack_team_compat(
            "admin_token", "Test Org", "test-org-dgc"
        )
        team_id = team_result["team_id"]

        channel_result = await client.create_channel_compat(
            "admin_token", team_id, "test-channel", False
        )
        channel_id = channel_result["channel_id"]

        # Get bot user ID
        bot_result = await client.get_bot_user_id_compat("bot_token")
        bot_user_id = bot_result["user_id"]

        # Invite bot to channel
        result = await client.invite_bot_to_channel_compat(
            admin_token="admin_token_12345",
            channel=channel_id,
            bot_user_id=bot_user_id,
        )

        assert result["success"] is True
        assert result["channel"] == channel_id
        assert result["user_id"] == bot_user_id

    @pytest.mark.asyncio
    async def test_invite_bot_to_channel_already_in_channel(self, client: FakeSlackClient):
        """Test invite_bot_to_channel when bot is already in channel."""
        # Create team and channel
        team_result = await client.create_slack_team_compat(
            "admin_token", "Test Org", "test-org-dgc"
        )
        team_id = team_result["team_id"]

        channel_result = await client.create_channel_compat(
            "admin_token", team_id, "test-channel", False
        )
        channel_id = channel_result["channel_id"]

        # Get bot user ID
        bot_result = await client.get_bot_user_id_compat("bot_token")
        bot_user_id = bot_result["user_id"]

        # Invite bot once
        await client.invite_bot_to_channel_compat("admin_token", channel_id, bot_user_id)

        # Invite again - should succeed with flag
        result = await client.invite_bot_to_channel_compat("admin_token", channel_id, bot_user_id)

        assert result["success"] is True
        assert result.get("was_already_in_channel") is True

    @pytest.mark.asyncio
    async def test_invite_user_to_slack_team_compat(self, client: FakeSlackClient):
        """Test invite_user_to_slack_team compatibility method."""
        # Create team and channel
        team_result = await client.create_slack_team_compat(
            "admin_token", "Test Org", "test-org-dgc"
        )
        team_id = team_result["team_id"]

        channel_result = await client.create_channel_compat(
            "admin_token", team_id, "general", False
        )
        channel_id = channel_result["channel_id"]

        # Invite user
        result = await client.invite_user_to_slack_team_compat(
            admin_token="admin_token_12345",
            team_id=team_id,
            email="user@example.com",
            channel_ids=channel_id,
        )

        assert result["success"] is True
        assert result["email"] == "user@example.com"
        assert result["team_id"] == team_id
        assert "user_id" in result

        # Verify user was added to channel
        members_result = await client.conversations_members(channel=channel_id)
        assert result["user_id"] in members_result["members"]

    @pytest.mark.asyncio
    async def test_create_slack_connect_channel_compat(self, client: FakeSlackClient):
        """Test create_slack_connect_channel compatibility method."""
        # Create team and channel
        team_result = await client.create_slack_team_compat(
            "admin_token", "Test Org", "test-org-dgc"
        )
        team_id = team_result["team_id"]

        channel_result = await client.create_channel_compat(
            "admin_token", team_id, "test-channel", False
        )
        channel_id = channel_result["channel_id"]

        # Create Slack Connect invite
        result = await client.create_slack_connect_channel_compat(
            bot_token="bot_token_12345",
            channel=channel_id,
            emails=["user1@example.com", "user2@example.com"],
        )

        assert result["success"] is True
        assert result["channel"] == channel_id
        assert result["emails"] == ["user1@example.com", "user2@example.com"]
        assert "invite_id" in result

        # Verify invite was stored
        invites = client.get_slack_connect_invites(channel_id)
        assert len(invites) == 1
        assert invites[0]["emails"] == ["user1@example.com", "user2@example.com"]

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow_simulation(self, client: FakeSlackClient):
        """Test simulating a complete onboarding flow using compatibility methods."""
        # Step 1: Create Slack team
        team_result = await client.create_slack_team_compat(
            admin_token="admin_token",
            team_name="Test Company",
            team_domain="test-company-dgc",
        )
        assert team_result["success"] is True
        team_id = team_result["team_id"]

        # Step 2: List channels (should have default channels)
        # In real Slack, new teams come with #general and #random
        # We'll simulate this by creating them
        await client.create_channel_compat("admin_token", team_id, "general", False)
        await client.create_channel_compat("admin_token", team_id, "random", False)

        channels_result = await client.get_all_channels_compat("org_bot_token", team_id)
        assert channels_result["success"] is True
        assert "general" in channels_result["channel_names"]

        # Step 3: Create compass channel
        compass_result = await client.create_channel_compat(
            "admin_token", team_id, "test-company-compass", False
        )
        assert compass_result["success"] is True
        compass_channel_id = compass_result["channel_id"]

        # Step 4: Create governance channel
        governance_result = await client.create_channel_compat(
            "admin_token", team_id, "test-company-governance", True
        )
        assert governance_result["success"] is True
        governance_channel_id = governance_result["channel_id"]

        # Step 5: Get bot user IDs
        dev_tools_bot_result = await client.get_bot_user_id_compat("dev_tools_token")
        assert dev_tools_bot_result["success"] is True
        dev_tools_bot_id = dev_tools_bot_result["user_id"]

        compass_bot_result = await client.get_bot_user_id_compat("compass_token")
        assert compass_bot_result["success"] is True
        compass_bot_id = compass_bot_result["user_id"]

        # Step 6: Invite bots to channels
        for bot_id in [dev_tools_bot_id, compass_bot_id]:
            result = await client.invite_bot_to_channel_compat(
                "admin_token", compass_channel_id, bot_id
            )
            assert result["success"] is True

            result = await client.invite_bot_to_channel_compat(
                "admin_token", governance_channel_id, bot_id
            )
            assert result["success"] is True

        # Step 7: Invite user to team
        general_channel_id = channels_result["channel_name_to_id"]["general"]
        user_result = await client.invite_user_to_slack_team_compat(
            "admin_token", team_id, "admin@example.com", general_channel_id
        )
        assert user_result["success"] is True

        # Step 8: Create Slack Connect for governance channel
        connect_result = await client.create_slack_connect_channel_compat(
            "org_bot_token", governance_channel_id, ["admin@example.com"]
        )
        assert connect_result["success"] is True

        # Verify final state
        assert len(client.get_channel_messages(compass_channel_id)) == 0  # No messages yet
        assert len(client.get_slack_connect_invites(governance_channel_id)) == 1
