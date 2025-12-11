"""Tests for mock_slack_api_with_client that routes slack_utils.py through FakeSlackClient."""

import pytest

from csbot.slackbot.slack_utils import (
    create_channel,
    create_slack_connect_channel,
    create_slack_team,
    get_all_channels,
    get_bot_user_id,
    invite_bot_to_channel,
    invite_user_to_slack_team,
)
from tests.utils.slack_client import FakeSlackClient, mock_slack_api_with_client


class TestSlackApiMock:
    """Test suite for HTTP-level Slack API mocking."""

    @pytest.fixture
    def fake_client(self) -> FakeSlackClient:
        """Create a fresh FakeSlackClient for each test."""
        return FakeSlackClient("xoxb-test-token")

    @pytest.mark.asyncio
    async def test_create_slack_team_via_mock(self, fake_client: FakeSlackClient):
        """Test that create_slack_team from slack_utils.py routes to FakeSlackClient."""
        with mock_slack_api_with_client(fake_client):
            result = await create_slack_team(
                admin_token="admin_token_12345",
                team_name="Test Organization",
                team_domain="test-org-dgc",
            )

            assert result["success"] is True
            assert result["team_name"] == "Test Organization"
            assert result["team_domain"] == "test-org-dgc"
            assert result["team_id"].startswith("T")

            # Verify state in fake client
            teams = fake_client.get_teams()
            assert len(teams) == 1
            team = list(teams.values())[0]
            assert team["name"] == "Test Organization"

    @pytest.mark.asyncio
    async def test_create_channel_via_mock(self, fake_client: FakeSlackClient):
        """Test that create_channel from slack_utils.py routes to FakeSlackClient."""
        with mock_slack_api_with_client(fake_client):
            # Create team first
            team_result = await create_slack_team("admin_token", "Test Org", "test-org-dgc")
            team_id = team_result["team_id"]

            # Create channel
            result = await create_channel(
                admin_token="admin_token_12345",
                team_id=team_id,
                channel_name="test-compass",
                is_private=False,
            )

            assert result["success"] is True
            assert result["channel_name"] == "test-compass"
            assert result["is_private"] is False

            # Verify state (team creates general + random, plus test-compass = 3)
            channels = fake_client.get_channels()
            assert len(channels) >= 3

    @pytest.mark.asyncio
    async def test_get_all_channels_via_mock(self, fake_client: FakeSlackClient):
        """Test that get_all_channels from slack_utils.py routes to FakeSlackClient."""
        with mock_slack_api_with_client(fake_client):
            # Create team and channels
            team_result = await create_slack_team("admin_token", "Test Org", "test-org-dgc")
            team_id = team_result["team_id"]

            await create_channel("admin_token", team_id, "general", False)
            await create_channel("admin_token", team_id, "random", False)

            # Get all channels
            result = await get_all_channels(
                org_bot_token="org_bot_token",
                team_id=team_id,
            )

            assert result["success"] is True
            # Should have general, random (created by team), plus the 2 we created = 4
            assert len(result["channel_names"]) == 4
            assert "general" in result["channel_names"]
            assert "random" in result["channel_names"]

    @pytest.mark.asyncio
    async def test_get_bot_user_id_via_mock(self, fake_client: FakeSlackClient):
        """Test that get_bot_user_id from slack_utils.py routes to FakeSlackClient."""
        with mock_slack_api_with_client(fake_client):
            result = await get_bot_user_id(bot_token="bot_token")

            assert result["success"] is True
            assert "user_id" in result
            assert "bot_id" in result
            assert result["user_id"].startswith("U")
            assert result["bot_id"].startswith("B")

    @pytest.mark.asyncio
    async def test_invite_bot_to_channel_via_mock(self, fake_client: FakeSlackClient):
        """Test that invite_bot_to_channel from slack_utils.py routes to FakeSlackClient."""
        with mock_slack_api_with_client(fake_client):
            # Setup: create team, channel, and get bot user ID
            team_result = await create_slack_team("admin_token", "Test Org", "test-org-dgc")
            team_id = team_result["team_id"]

            channel_result = await create_channel("admin_token", team_id, "test-channel", False)
            channel_id = channel_result["channel_id"]

            bot_result = await get_bot_user_id("bot_token")
            bot_user_id = bot_result["user_id"]

            # Invite bot to channel
            result = await invite_bot_to_channel(
                admin_token="admin_token",
                channel=channel_id,
                bot_user_id=bot_user_id,
            )

            assert result["success"] is True
            assert result["channel"] == channel_id
            assert result["user_id"] == bot_user_id

            # Verify state: bot is in channel members
            members = fake_client.get_channel_members(channel_id)
            assert bot_user_id in members

    @pytest.mark.asyncio
    async def test_invite_user_to_slack_team_via_mock(self, fake_client: FakeSlackClient):
        """Test that invite_user_to_slack_team from slack_utils.py routes to FakeSlackClient."""
        with mock_slack_api_with_client(fake_client):
            # Setup: create team and channel
            team_result = await create_slack_team("admin_token", "Test Org", "test-org-dgc")
            team_id = team_result["team_id"]

            channel_result = await create_channel("admin_token", team_id, "general", False)
            channel_id = channel_result["channel_id"]

            # Invite user
            result = await invite_user_to_slack_team(
                admin_token="admin_token",
                team_id=team_id,
                email="user@example.com",
                channel_ids=channel_id,
            )

            assert result["success"] is True
            assert "user_id" in result

            # Verify state: user exists
            user_id = result["user_id"]
            user_ids = fake_client.get_user_ids()
            assert user_id in user_ids

    @pytest.mark.asyncio
    async def test_create_slack_connect_channel_via_mock(self, fake_client: FakeSlackClient):
        """Test that create_slack_connect_channel from slack_utils.py routes to FakeSlackClient."""
        with mock_slack_api_with_client(fake_client):
            # Setup: create team and channel
            team_result = await create_slack_team("admin_token", "Test Org", "test-org-dgc")
            team_id = team_result["team_id"]

            channel_result = await create_channel("admin_token", team_id, "test-channel", False)
            channel_id = channel_result["channel_id"]

            # Create Slack Connect invite
            result = await create_slack_connect_channel(
                bot_token="bot_token",
                channel=channel_id,
                emails=["user@example.com"],
            )

            assert result["success"] is True
            assert result["channel"] == channel_id
            assert result["emails"] == ["user@example.com"]
            assert "invite_id" in result

            # Verify state: invite was stored
            invites = fake_client.get_slack_connect_invites(channel_id)
            assert len(invites) == 1

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow_via_slack_utils(self, fake_client: FakeSlackClient):
        """Test complete onboarding flow using real slack_utils.py functions with mock."""
        with mock_slack_api_with_client(fake_client):
            # Step 1: Create Slack team
            team_result = await create_slack_team(
                "admin_token",
                "Test Company",
                "test-company-dgc",
            )
            assert team_result["success"] is True
            team_id = team_result["team_id"]

            # Step 2: Create default channels
            await create_channel("admin_token", team_id, "general", False)
            await create_channel("admin_token", team_id, "random", False)

            # Step 3: List channels
            channels_result = await get_all_channels("org_bot_token", team_id)
            assert channels_result["success"] is True
            general_channel_id = channels_result["channel_name_to_id"]["general"]

            # Step 4: Create compass channel
            compass_result = await create_channel("admin_token", team_id, "test-compass", False)
            assert compass_result["success"] is True
            compass_channel_id = compass_result["channel_id"]

            # Step 5: Create governance channel (private)
            governance_result = await create_channel(
                "admin_token", team_id, "test-governance", True
            )
            assert governance_result["success"] is True
            governance_channel_id = governance_result["channel_id"]

            # Step 6: Get bot user IDs
            dev_tools_bot = await get_bot_user_id("dev_tools_token")
            compass_bot = await get_bot_user_id("compass_token")
            assert dev_tools_bot["success"] is True
            assert compass_bot["success"] is True

            # Step 7: Invite both bots to both channels
            for bot_id in [dev_tools_bot["user_id"], compass_bot["user_id"]]:
                for channel_id in [compass_channel_id, governance_channel_id]:
                    result = await invite_bot_to_channel("admin_token", channel_id, bot_id)
                    assert result["success"] is True

            # Step 8: Invite user to team
            user_result = await invite_user_to_slack_team(
                "admin_token",
                team_id,
                "admin@example.com",
                general_channel_id,
            )
            assert user_result["success"] is True

            # Step 9: Create Slack Connect for governance
            connect_result = await create_slack_connect_channel(
                "org_bot_token",
                governance_channel_id,
                ["admin@example.com"],
            )
            assert connect_result["success"] is True

            # Verify final state
            assert len(fake_client.get_teams()) == 1
            # Team creates general + random (2), we created 2 more = 4, plus compass + governance = 6
            assert len(fake_client.get_channels()) == 6
            assert len(fake_client.get_users()) == 3  # 2 bots + 1 user

            # Verify channel members
            assert len(fake_client.get_channel_members(compass_channel_id)) == 2  # 2 bots
            assert len(fake_client.get_channel_members(governance_channel_id)) == 2  # 2 bots
            assert len(fake_client.get_channel_members(general_channel_id)) == 1  # 1 user

            # Verify Slack Connect invite
            invites = fake_client.get_slack_connect_invites(governance_channel_id)
            assert len(invites) == 1
            assert invites[0]["emails"] == ["admin@example.com"]

    @pytest.mark.asyncio
    async def test_error_handling_via_mock(self, fake_client: FakeSlackClient):
        """Test that errors are properly propagated through the mock."""
        with mock_slack_api_with_client(fake_client):
            # Try to create team with domain that's too long
            result = await create_slack_team(
                "admin_token",
                "Test Company",
                "this-is-a-very-long-domain-that-exceeds-the-limit",
            )

            assert result["success"] is False
            assert "team domain must be 21 characters or fewer" in result["error"]

    @pytest.mark.asyncio
    async def test_already_in_channel_error_via_mock(self, fake_client: FakeSlackClient):
        """Test that already_in_channel is handled correctly through the mock."""
        with mock_slack_api_with_client(fake_client):
            # Setup
            team_result = await create_slack_team("admin_token", "Test Org", "test-org-dgc")
            team_id = team_result["team_id"]

            channel_result = await create_channel("admin_token", team_id, "test", False)
            channel_id = channel_result["channel_id"]

            bot_result = await get_bot_user_id("bot_token")
            bot_user_id = bot_result["user_id"]

            # Invite bot once
            result1 = await invite_bot_to_channel("admin_token", channel_id, bot_user_id)
            assert result1["success"] is True

            # Invite again - should succeed with flag
            result2 = await invite_bot_to_channel("admin_token", channel_id, bot_user_id)
            assert result2["success"] is True
            assert result2.get("was_already_in_channel") is True
