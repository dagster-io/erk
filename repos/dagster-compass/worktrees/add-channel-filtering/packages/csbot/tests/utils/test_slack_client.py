"""Tests for the FakeSlackClient implementation."""

import pytest

from tests.utils.slack_client import FakeSlackClient


class TestFakeSlackClient:
    """Test suite for the FakeSlackClient implementation."""

    @pytest.fixture
    def client(self) -> FakeSlackClient:
        """Create a fresh FakeSlackClient for each test."""
        return FakeSlackClient("xoxb-test-token")

    @pytest.mark.asyncio
    async def test_create_team(self, client: FakeSlackClient):
        """Test creating a Slack team."""
        result = await client.create_team(
            team_name="Test Team",
            team_domain="test-team-dgc",
            team_description="A test team",
        )

        assert result["ok"] is True
        assert result["team_name"] == "Test Team"
        assert result["team_domain"] == "test-team-dgc"
        assert result["team"].startswith("T")

    @pytest.mark.asyncio
    async def test_create_channel(self, client: FakeSlackClient):
        """Test creating a Slack channel."""
        result = await client.conversations_create(
            name="test-channel",
            is_private=False,
        )

        assert result["ok"] is True
        assert result["channel"]["name"] == "test-channel"
        assert result["channel"]["is_private"] is False
        assert result["channel"]["id"].startswith("C")

    @pytest.mark.asyncio
    async def test_list_channels(self, client: FakeSlackClient):
        """Test listing channels."""
        # Create a few channels
        await client.conversations_create(name="general")
        await client.conversations_create(name="random")
        await client.conversations_create(name="test-private", is_private=True)

        # List public channels
        result = await client.conversations_list(types="public_channel")

        assert result["ok"] is True
        assert len(result["channels"]) == 2
        channel_names = {ch["name"] for ch in result["channels"]}
        assert channel_names == {"general", "random"}

    @pytest.mark.asyncio
    async def test_post_message(self, client: FakeSlackClient):
        """Test posting a message to a channel."""
        # Create a channel first
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        # Post a message
        message_result = await client.chat_postMessage(
            channel=channel_id,
            text="Hello, world!",
        )

        assert message_result["ok"] is True
        assert message_result["channel"] == channel_id
        assert "ts" in message_result

        # Verify message was stored
        messages = client.get_channel_messages(channel_id)
        assert len(messages) == 1
        assert messages[0]["text"] == "Hello, world!"

    @pytest.mark.asyncio
    async def test_post_message_with_blocks(self, client: FakeSlackClient):
        """Test posting a message with BlockKit blocks."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Hello* from BlockKit!"},
            }
        ]

        message_result = await client.chat_postMessage(
            channel=channel_id,
            text="Fallback text",
            blocks=blocks,
        )

        assert message_result["ok"] is True

        # Verify blocks were stored
        messages = client.get_channel_messages(channel_id)
        assert len(messages) == 1
        assert messages[0]["blocks"] == blocks

    @pytest.mark.asyncio
    async def test_post_message_in_thread(self, client: FakeSlackClient):
        """Test posting a threaded message."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        # Post parent message
        parent_result = await client.chat_postMessage(
            channel=channel_id,
            text="Parent message",
        )
        parent_ts = parent_result["ts"]

        # Post reply in thread
        reply_result = await client.chat_postMessage(
            channel=channel_id,
            text="Reply message",
            thread_ts=parent_ts,
        )

        assert reply_result["ok"] is True
        assert reply_result["message"]["thread_ts"] == parent_ts

        # Verify both messages exist
        messages = client.get_channel_messages(channel_id)
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_update_message(self, client: FakeSlackClient):
        """Test updating an existing message."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        # Post original message
        post_result = await client.chat_postMessage(
            channel=channel_id,
            text="Original text",
        )
        ts = post_result["ts"]

        # Update the message
        update_result = await client.chat_update(
            channel=channel_id,
            ts=ts,
            text="Updated text",
        )

        assert update_result["ok"] is True
        assert update_result["text"] == "Updated text"

        # Verify message was updated
        messages = client.get_channel_messages(channel_id)
        assert len(messages) == 1
        assert messages[0]["text"] == "Updated text"

    @pytest.mark.asyncio
    async def test_ephemeral_message(self, client: FakeSlackClient):
        """Test posting ephemeral messages."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        user = client.create_test_user("testuser")
        user_id = user["id"]

        result = await client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="Only you can see this",
        )

        assert result["ok"] is True

        # Verify ephemeral message was stored
        ephemeral_messages = client.get_ephemeral_messages(user_id)
        assert len(ephemeral_messages) == 1
        assert ephemeral_messages[0]["text"] == "Only you can see this"

    @pytest.mark.asyncio
    async def test_invite_user_to_channel(self, client: FakeSlackClient):
        """Test inviting a user to a channel."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        user = client.create_test_user("testuser")
        user_id = user["id"]

        invite_result = await client.conversations_invite(
            channel=channel_id,
            users=user_id,
        )

        assert invite_result["ok"] is True

        # Verify user is in channel
        members_result = await client.conversations_members(channel=channel_id)
        assert user_id in members_result["members"]

    @pytest.mark.asyncio
    async def test_invite_user_already_in_channel(self, client: FakeSlackClient):
        """Test inviting a user who is already in the channel."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        user = client.create_test_user("testuser")
        user_id = user["id"]

        # First invite
        await client.conversations_invite(channel=channel_id, users=user_id)

        # Second invite should fail
        result = await client.conversations_invite(channel=channel_id, users=user_id)
        assert result["ok"] is False
        assert result["error"] == "already_in_channel"

    @pytest.mark.asyncio
    async def test_pin_message(self, client: FakeSlackClient):
        """Test pinning a message to a channel."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        # Post a message
        message_result = await client.chat_postMessage(
            channel=channel_id,
            text="Pin me!",
        )
        ts = message_result["ts"]

        # Pin the message
        pin_result = await client.pins_add(channel=channel_id, timestamp=ts)
        assert pin_result["ok"] is True

        # Verify message is pinned
        pins = client.get_channel_pins(channel_id)
        assert ts in pins

    @pytest.mark.asyncio
    async def test_list_pins(self, client: FakeSlackClient):
        """Test listing pinned messages."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        # Post and pin multiple messages
        ts_list = []
        for i in range(3):
            message_result = await client.chat_postMessage(
                channel=channel_id,
                text=f"Message {i}",
            )
            ts = message_result["ts"]
            ts_list.append(ts)
            await client.pins_add(channel=channel_id, timestamp=ts)

        # List pins
        pins_result = await client.pins_list(channel=channel_id)
        assert pins_result["ok"] is True
        assert len(pins_result["items"]) == 3

    @pytest.mark.asyncio
    async def test_slack_connect_invite_with_emails(self, client: FakeSlackClient):
        """Test creating Slack Connect invites with email addresses."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        result = await client.conversations_inviteShared(
            channel=channel_id,
            emails=["user1@example.com", "user2@example.com"],
        )

        assert result["ok"] is True
        assert "invite_id" in result

        # Verify invite was stored
        invites = client.get_slack_connect_invites(channel_id)
        assert len(invites) == 1
        assert invites[0]["emails"] == ["user1@example.com", "user2@example.com"]

    @pytest.mark.asyncio
    async def test_slack_connect_invite_with_user_ids(self, client: FakeSlackClient):
        """Test creating Slack Connect invites with user IDs."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        result = await client.conversations_inviteShared(
            channel=channel_id,
            user_ids="U123456,U789012",
        )

        assert result["ok"] is True

        # Verify invite was stored
        invites = client.get_slack_connect_invites(channel_id)
        assert len(invites) == 1
        assert invites[0]["user_ids"] == ["U123456", "U789012"]

    @pytest.mark.asyncio
    async def test_add_reaction(self, client: FakeSlackClient):
        """Test adding a reaction to a message."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        # Post a message
        message_result = await client.chat_postMessage(
            channel=channel_id,
            text="React to me!",
        )
        ts = message_result["ts"]

        # Add reaction
        reaction_result = await client.reactions_add(
            channel=channel_id,
            timestamp=ts,
            name="thumbsup",
        )

        assert reaction_result["ok"] is True

    @pytest.mark.asyncio
    async def test_auth_test(self, client: FakeSlackClient):
        """Test authentication and getting bot info."""
        result = await client.auth_test()

        assert result["ok"] is True
        assert "user_id" in result
        assert "bot_id" in result
        assert result["user_id"].startswith("U")
        assert result["bot_id"].startswith("B")

    @pytest.mark.asyncio
    async def test_get_permalink(self, client: FakeSlackClient):
        """Test getting a permalink to a message."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        message_result = await client.chat_postMessage(
            channel=channel_id,
            text="Permalink me!",
        )
        ts = message_result["ts"]

        permalink_result = await client.chat_getPermalink(
            channel=channel_id,
            message_ts=ts,
        )

        assert permalink_result["ok"] is True
        assert "permalink" in permalink_result
        assert channel_id in permalink_result["permalink"]

    @pytest.mark.asyncio
    async def test_conversations_history(self, client: FakeSlackClient):
        """Test retrieving message history."""
        channel_result = await client.conversations_create(name="test")
        channel_id = channel_result["channel"]["id"]

        # Post multiple messages
        for i in range(5):
            await client.chat_postMessage(
                channel=channel_id,
                text=f"Message {i}",
            )

        # Get history
        history_result = await client.conversations_history(
            channel=channel_id,
            limit=3,
        )

        assert history_result["ok"] is True
        assert len(history_result["messages"]) == 3

    def test_create_test_user(self, client: FakeSlackClient):
        """Test creating a test user."""
        user = client.create_test_user(
            name="Test User",
            email="test@example.com",
        )

        assert user["id"].startswith("U")
        assert user["name"] == "Test User"
        assert user["profile"]["email"] == "test@example.com"
        assert user["is_bot"] is False

    def test_create_test_channel(self, client: FakeSlackClient):
        """Test creating a test channel synchronously."""
        channel = client.create_test_channel(
            name="test-sync",
            is_private=True,
        )

        assert channel["id"].startswith("C")
        assert channel["name"] == "test-sync"
        assert channel["is_private"] is True

    def test_clear_all(self, client: FakeSlackClient):
        """Test clearing all data from storage."""
        # Create some data
        channel = client.create_test_channel(name="test")
        client.create_test_user(name="testuser")

        # Verify data exists
        assert len(client.get_channels()) > 0
        assert len(client.get_users()) > 0

        # Clear all
        client.clear_all()

        # Verify everything is cleared
        assert len(client.get_channels()) == 0
        assert len(client.get_users()) == 0
        assert len(client.get_channel_messages(channel["id"])) == 0
        assert len(client.get_teams()) == 0
