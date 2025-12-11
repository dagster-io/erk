"""Shared test Slack client implementation for use across test modules."""

import time
import uuid
from typing import Any
from unittest.mock import patch


class FakeSlackClient:
    """Test implementation of Slack AsyncWebClient using local in-memory storage.

    This mock provides a complete simulation of Slack workspace state including:
    - Teams and workspaces
    - Channels (public/private) with members
    - Users with profile information
    - Messages in channels/threads with timestamps
    - Reactions to messages
    - Pins in channels
    - Slack Connect invites
    - Ephemeral messages (visible only to specific users)

    All state is stored in-memory and can be inspected for testing.
    """

    def __init__(self, token: str):
        """Initialize the test Slack client with a token.

        Args:
            token: Slack API token for testing (not used but kept for compatibility)
        """
        self.token = token

        # Core state storage
        self._teams: dict[str, dict[str, Any]] = {}
        self._channels: dict[str, dict[str, Any]] = {}
        self._users: dict[str, dict[str, Any]] = {}
        self._messages: dict[str, list[dict[str, Any]]] = {}  # channel_id -> messages
        self._channel_members: dict[str, set[str]] = {}  # channel_id -> user_ids
        self._pins: dict[str, list[str]] = {}  # channel_id -> message timestamps
        self._reactions: dict[
            tuple[str, str], list[dict[str, Any]]
        ] = {}  # (channel_id, ts) -> reactions
        self._slack_connect_invites: list[dict[str, Any]] = []
        self._ephemeral_messages: list[dict[str, Any]] = []
        self._bot_tokens: dict[str, dict[str, str]] = {}  # token -> {user_id, bot_id}

        # Counters for generating IDs
        self._channel_counter = 1
        self._user_counter = 1
        self._team_counter = 1
        self._message_counter = 1

        # Track last timestamp to ensure uniqueness
        self._last_ts: float = 0.0

    def _generate_ts(self) -> str:
        """Generate a Slack-style timestamp.

        Ensures timestamps are unique and monotonically increasing by tracking
        the last generated timestamp and incrementing if necessary.
        """
        current_time = time.time()
        # Ensure timestamp is strictly greater than last one
        if current_time <= self._last_ts:
            # Increment by a small amount (1 microsecond)
            self._last_ts = self._last_ts + 0.000001
        else:
            self._last_ts = current_time
        return f"{self._last_ts:.6f}"

    def _generate_channel_id(self) -> str:
        """Generate a Slack-style channel ID."""
        channel_id = f"C{str(self._channel_counter).zfill(10)}"
        self._channel_counter += 1
        return channel_id

    def _generate_user_id(self) -> str:
        """Generate a Slack-style user ID."""
        user_id = f"U{str(self._user_counter).zfill(10)}"
        self._user_counter += 1
        return user_id

    def _generate_team_id(self) -> str:
        """Generate a Slack-style team ID."""
        team_id = f"T{str(self._team_counter).zfill(10)}"
        self._team_counter += 1
        return team_id

    def _generate_bot_user_id(self) -> str:
        """Generate a Slack-style bot user ID."""
        return f"U{uuid.uuid4().hex[:10].upper()}"

    def _generate_bot_id(self) -> str:
        """Generate a Slack-style bot ID."""
        return f"B{uuid.uuid4().hex[:10].upper()}"

    def _generate_invite_id(self) -> str:
        """Generate a Slack-style invite ID."""
        return f"I{uuid.uuid4().hex[:10].upper()}"

    # Team management

    async def create_team(
        self,
        team_name: str,
        team_domain: str,
        team_description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Slack team.

        Args:
            team_name: Name of the team
            team_domain: URL-safe domain for the team
            team_description: Optional description

        Returns:
            Dictionary containing team creation result
        """
        team_id = self._generate_team_id()

        team_data = {
            "id": team_id,
            "name": team_name,
            "domain": team_domain,
            "description": team_description or "",
            "created": int(time.time()),
        }

        self._teams[team_id] = team_data

        # Create default channels (like real Slack does)
        # Slack automatically creates #general and #random in new teams
        await self.conversations_create(name="general", is_private=False, team_id=team_id)
        await self.conversations_create(name="random", is_private=False, team_id=team_id)

        return {
            "ok": True,
            "team": team_id,
            "team_name": team_name,
            "team_domain": team_domain,
        }

    # Channel management

    async def conversations_create(
        self,
        name: str,
        is_private: bool = False,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new channel.

        Args:
            name: Channel name
            is_private: Whether the channel is private
            team_id: Optional team ID for Enterprise Grid

        Returns:
            Dictionary containing channel creation result
        """
        channel_id = self._generate_channel_id()

        channel_data = {
            "id": channel_id,
            "name": name,
            "is_private": is_private,
            "is_channel": True,
            "is_archived": False,
            "is_member": True,
            "team_id": team_id,
            "created": int(time.time()),
            "creator": "U0000000000",  # Mock creator
            "num_members": 0,
        }

        self._channels[channel_id] = channel_data
        self._messages[channel_id] = []
        self._channel_members[channel_id] = set()

        return {
            "ok": True,
            "channel": channel_data,
        }

    async def conversations_list(
        self,
        team_id: str | None = None,
        types: str = "public_channel",
        exclude_archived: bool = True,
        limit: int = 100,
    ) -> dict[str, Any]:
        """List channels in the workspace.

        Args:
            team_id: Optional team ID for Enterprise Grid
            types: Comma-separated list of channel types
            exclude_archived: Whether to exclude archived channels
            limit: Maximum number of channels to return

        Returns:
            Dictionary containing list of channels
        """
        channels = []
        for channel in self._channels.values():
            if exclude_archived and channel.get("is_archived"):
                continue
            if team_id and channel.get("team_id") != team_id:
                continue
            if "private" in types or channel.get("is_private") is False:
                channels.append(channel)

        return {
            "ok": True,
            "channels": channels[:limit],
        }

    async def conversations_info(self, channel: str) -> dict[str, Any]:
        """Get information about a channel.

        Args:
            channel: Channel ID

        Returns:
            Dictionary containing channel information
        """
        channel_data = self._channels.get(channel)
        if not channel_data:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        return {
            "ok": True,
            "channel": channel_data,
        }

    async def conversations_archive(self, channel: str) -> dict[str, Any]:
        """Archive a channel.

        Args:
            channel: Channel ID

        Returns:
            Dictionary containing result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        self._channels[channel]["is_archived"] = True

        return {"ok": True}

    async def conversations_invite(
        self,
        channel: str,
        users: str | list[str],
    ) -> dict[str, Any]:
        """Invite users to a channel.

        Args:
            channel: Channel ID
            users: User ID or comma-separated list of user IDs

        Returns:
            Dictionary containing result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        # Parse users parameter
        if isinstance(users, str):
            user_ids = [u.strip() for u in users.split(",")]
        else:
            user_ids = users

        # Check if any user is already in channel
        for user_id in user_ids:
            if user_id in self._channel_members.get(channel, set()):
                return {
                    "ok": False,
                    "error": "already_in_channel",
                }

        # Add users to channel
        if channel not in self._channel_members:
            self._channel_members[channel] = set()

        for user_id in user_ids:
            self._channel_members[channel].add(user_id)

        # Update num_members
        self._channels[channel]["num_members"] = len(self._channel_members[channel])

        return {
            "ok": True,
            "channel": self._channels[channel],
        }

    async def conversations_members(
        self,
        channel: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get members of a channel.

        Args:
            channel: Channel ID
            limit: Maximum number of members to return

        Returns:
            Dictionary containing list of member IDs
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        members = list(self._channel_members.get(channel, set()))

        return {
            "ok": True,
            "members": members[:limit],
        }

    async def conversations_history(
        self,
        channel: str,
        limit: int = 100,
        oldest: str | None = None,
        latest: str | None = None,
    ) -> dict[str, Any]:
        """Get message history from a channel.

        Args:
            channel: Channel ID
            limit: Maximum number of messages to return
            oldest: Only messages after this timestamp
            latest: Only messages before this timestamp

        Returns:
            Dictionary containing list of messages
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        messages = self._messages.get(channel, [])

        # Filter by timestamp if provided
        if oldest:
            messages = [m for m in messages if float(m["ts"]) >= float(oldest)]
        if latest:
            messages = [m for m in messages if float(m["ts"]) <= float(latest)]

        # Sort by timestamp descending (most recent first)
        messages = sorted(messages, key=lambda m: float(m["ts"]), reverse=True)

        return {
            "ok": True,
            "messages": messages[:limit],
            "has_more": len(messages) > limit,
        }

    async def conversations_replies(
        self,
        channel: str,
        ts: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get replies in a thread.

        Args:
            channel: Channel ID
            ts: Thread timestamp (parent message timestamp)
            limit: Maximum number of messages to return

        Returns:
            Dictionary containing list of messages in the thread
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        messages = self._messages.get(channel, [])

        # Filter to only the parent message and its replies
        thread_messages = [msg for msg in messages if msg["ts"] == ts or msg.get("thread_ts") == ts]

        # Sort by timestamp ascending (oldest first, parent at top)
        thread_messages = sorted(thread_messages, key=lambda m: float(m["ts"]))

        return {
            "ok": True,
            "messages": thread_messages[:limit],
            "has_more": len(thread_messages) > limit,
        }

    async def conversations_inviteShared(
        self,
        channel: str,
        emails: str | list[str] | None = None,
        user_ids: str | None = None,
    ) -> dict[str, Any]:
        """Create a Slack Connect invite for a channel.

        Args:
            channel: Channel ID
            emails: Email addresses to invite (comma-separated or list)
            user_ids: User IDs to invite (comma-separated)

        Returns:
            Dictionary containing invite result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        invite_id = self._generate_invite_id()

        # Parse emails
        email_list = []
        if emails:
            if isinstance(emails, str):
                email_list = [e.strip() for e in emails.split(",")]
            else:
                email_list = emails

        # Parse user_ids
        user_id_list = []
        if user_ids:
            user_id_list = [u.strip() for u in user_ids.split(",")]

        invite_data = {
            "invite_id": invite_id,
            "channel": channel,
            "emails": email_list,
            "user_ids": user_id_list,
            "created": int(time.time()),
        }

        self._slack_connect_invites.append(invite_data)

        return {
            "ok": True,
            "invite_id": invite_id,
        }

    # User management

    async def users_info(self, user: str, include_locale: bool = False) -> dict[str, Any]:
        """Get information about a user.

        Args:
            user: User ID
            include_locale: Whether to include locale information (optional, ignored in fake)

        Returns:
            Dictionary containing user information
        """
        user_data = self._users.get(user)
        if not user_data:
            return {
                "ok": False,
                "error": "user_not_found",
            }

        return {
            "ok": True,
            "user": user_data,
        }

    # Message management

    async def chat_postMessage(
        self,
        channel: str,
        text: str | None = None,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str | None = None,
        unfurl_links: bool = True,
        unfurl_media: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Post a message to a channel.

        Args:
            channel: Channel ID
            text: Message text
            blocks: BlockKit blocks
            thread_ts: Optional thread timestamp to reply to
            unfurl_links: Whether to unfurl links
            unfurl_media: Whether to unfurl media
            **kwargs: Additional message parameters

        Returns:
            Dictionary containing message result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        ts = self._generate_ts()

        message_data = {
            "type": "message",
            "user": "U0000000000",  # Mock user
            "text": text or "",
            "blocks": blocks or [],
            "ts": ts,
            "channel": channel,
            "thread_ts": thread_ts,
            **kwargs,
        }

        if channel not in self._messages:
            self._messages[channel] = []

        self._messages[channel].append(message_data)

        return {
            "ok": True,
            "ts": ts,
            "channel": channel,
            "message": message_data,
        }

    async def chat_postEphemeral(
        self,
        channel: str,
        user: str,
        text: str | None = None,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Post an ephemeral message (visible only to one user).

        Args:
            channel: Channel ID
            user: User ID who can see the message
            text: Message text
            blocks: BlockKit blocks
            thread_ts: Optional thread timestamp
            **kwargs: Additional message parameters

        Returns:
            Dictionary containing message result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        ts = self._generate_ts()

        ephemeral_data = {
            "type": "ephemeral",
            "user": user,
            "text": text or "",
            "blocks": blocks or [],
            "ts": ts,
            "channel": channel,
            "thread_ts": thread_ts,
            **kwargs,
        }

        self._ephemeral_messages.append(ephemeral_data)

        return {
            "ok": True,
            "message_ts": ts,
        }

    async def chat_update(
        self,
        channel: str,
        ts: str,
        text: str | None = None,
        blocks: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update an existing message.

        Args:
            channel: Channel ID
            ts: Message timestamp
            text: New message text
            blocks: New BlockKit blocks
            **kwargs: Additional message parameters

        Returns:
            Dictionary containing update result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        messages = self._messages.get(channel, [])
        for message in messages:
            if message["ts"] == ts:
                if text is not None:
                    message["text"] = text
                if blocks is not None:
                    message["blocks"] = blocks
                message.update(kwargs)

                return {
                    "ok": True,
                    "channel": channel,
                    "ts": ts,
                    "text": message["text"],
                }

        return {
            "ok": False,
            "error": "message_not_found",
        }

    async def chat_getPermalink(
        self,
        channel: str,
        message_ts: str,
    ) -> dict[str, Any]:
        """Get a permalink to a message.

        Args:
            channel: Channel ID
            message_ts: Message timestamp

        Returns:
            Dictionary containing permalink
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        # Generate a mock permalink
        permalink = f"https://example.slack.com/archives/{channel}/p{message_ts.replace('.', '')}"

        return {
            "ok": True,
            "permalink": permalink,
        }

    # Pin management

    async def pins_add(
        self,
        channel: str,
        timestamp: str,
    ) -> dict[str, Any]:
        """Pin a message to a channel.

        Args:
            channel: Channel ID
            timestamp: Message timestamp to pin

        Returns:
            Dictionary containing result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        if channel not in self._pins:
            self._pins[channel] = []

        if timestamp not in self._pins[channel]:
            self._pins[channel].append(timestamp)

        return {"ok": True}

    async def pins_remove(
        self,
        channel: str,
        timestamp: str,
    ) -> dict[str, Any]:
        """Unpin a message from a channel.

        Args:
            channel: Channel ID
            timestamp: Message timestamp to unpin

        Returns:
            Dictionary containing result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        if channel in self._pins and timestamp in self._pins[channel]:
            self._pins[channel].remove(timestamp)

        return {"ok": True}

    async def pins_list(self, channel: str) -> dict[str, Any]:
        """List pinned messages in a channel.

        Args:
            channel: Channel ID

        Returns:
            Dictionary containing list of pinned items
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        pinned_timestamps = self._pins.get(channel, [])
        messages = self._messages.get(channel, [])

        pinned_items = []
        for ts in pinned_timestamps:
            for message in messages:
                if message["ts"] == ts:
                    pinned_items.append(
                        {
                            "type": "message",
                            "message": message,
                            "created": int(time.time()),
                            "created_by": "U0000000000",
                        }
                    )
                    break

        return {
            "ok": True,
            "items": pinned_items,
        }

    # Reaction management

    async def reactions_add(
        self,
        channel: str,
        timestamp: str,
        name: str,
    ) -> dict[str, Any]:
        """Add a reaction to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            name: Reaction emoji name (without colons)

        Returns:
            Dictionary containing result
        """
        if channel not in self._channels:
            return {
                "ok": False,
                "error": "channel_not_found",
            }

        key = (channel, timestamp)
        if key not in self._reactions:
            self._reactions[key] = []

        # Check if reaction already exists
        for reaction in self._reactions[key]:
            if reaction["name"] == name:
                return {"ok": True}  # Already reacted

        self._reactions[key].append(
            {
                "name": name,
                "count": 1,
                "users": ["U0000000000"],
            }
        )

        return {"ok": True}

    # Auth and bot info

    async def auth_test(self, token: str | None = None) -> dict[str, Any]:
        """Test authentication and get bot/user info.

        Args:
            token: Bot token (used to cache bot identity)

        Returns:
            Dictionary containing bot authentication info
        """
        # Use token to cache bot identity - same token returns same bot
        if token and token in self._bot_tokens:
            cached = self._bot_tokens[token]
            user_id = cached["user_id"]
            bot_id = cached["bot_id"]
        else:
            user_id = self._generate_bot_user_id()
            bot_id = self._generate_bot_id()

            # Create bot user in _users dict
            bot_user = self.create_test_user(
                name=f"bot_{bot_id}",
                email=f"bot_{bot_id}@example.com",
                is_bot=True,
            )
            # Override the generated user ID with our bot user ID
            del self._users[bot_user["id"]]
            bot_user["id"] = user_id
            self._users[user_id] = bot_user

            if token:
                self._bot_tokens[token] = {"user_id": user_id, "bot_id": bot_id}

        return {
            "ok": True,
            "url": "https://example.slack.com/",
            "team": "Test Team",
            "user": "testbot",
            "team_id": "T0000000000",
            "user_id": user_id,
            "bot_id": bot_id,
        }

    # Test helper methods

    def create_test_user(
        self,
        name: str,
        email: str | None = None,
        is_bot: bool = False,
    ) -> dict[str, Any]:
        """Create a test user (helper for tests).

        Args:
            name: User display name
            email: User email
            is_bot: Whether this is a bot user

        Returns:
            The created user data
        """
        user_id = self._generate_user_id()

        user_data = {
            "id": user_id,
            "team_id": "T0000000000",
            "name": name,
            "deleted": False,
            "profile": {
                "real_name": name,
                "display_name": name,
                "email": email or f"{name.lower()}@example.com",
            },
            "is_bot": is_bot,
            "is_admin": False,
            "is_owner": False,
        }

        self._users[user_id] = user_data
        return user_data

    def create_test_channel(
        self,
        name: str,
        is_private: bool = False,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a test channel synchronously (helper for tests).

        Args:
            name: Channel name
            is_private: Whether the channel is private
            team_id: Optional team ID

        Returns:
            The created channel data
        """
        channel_id = self._generate_channel_id()

        channel_data = {
            "id": channel_id,
            "name": name,
            "is_private": is_private,
            "is_channel": True,
            "is_archived": False,
            "team_id": team_id,
            "created": int(time.time()),
            "num_members": 0,
        }

        self._channels[channel_id] = channel_data
        self._messages[channel_id] = []
        self._channel_members[channel_id] = set()

        return channel_data

    def get_channel_messages(self, channel_id: str) -> list[dict[str, Any]]:
        """Get all messages in a channel (helper for tests).

        Args:
            channel_id: Channel ID

        Returns:
            List of messages in chronological order
        """
        messages = self._messages.get(channel_id, [])
        return sorted(messages, key=lambda m: float(m["ts"]))

    def get_ephemeral_messages(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """Get ephemeral messages (helper for tests).

        Args:
            user_id: Optional user ID to filter by

        Returns:
            List of ephemeral messages
        """
        if user_id:
            return [m for m in self._ephemeral_messages if m["user"] == user_id]
        return self._ephemeral_messages.copy()

    def get_slack_connect_invites(self, channel_id: str | None = None) -> list[dict[str, Any]]:
        """Get Slack Connect invites (helper for tests).

        Args:
            channel_id: Optional channel ID to filter by

        Returns:
            List of Slack Connect invites
        """
        if channel_id:
            return [i for i in self._slack_connect_invites if i["channel"] == channel_id]
        return self._slack_connect_invites.copy()

    def get_channel_pins(self, channel_id: str) -> list[str]:
        """Get pinned message timestamps in a channel (helper for tests).

        Args:
            channel_id: Channel ID

        Returns:
            List of pinned message timestamps
        """
        return self._pins.get(channel_id, []).copy()

    async def render_thread_to_html(
        self, channel_id: str, thread_ts: str, *, use_relative_timestamps: bool = False
    ) -> str:
        """Render a Slack thread as complete HTML page for testing and debugging.

        This uses the same template rendering as the production webapp (thread.html with layout.html).

        Args:
            channel_id: Channel ID containing the thread
            thread_ts: Thread timestamp (parent message timestamp)
            use_relative_timestamps: If True, show timestamps as relative to parent (e.g., "+5s", "+10s")
                                    instead of absolute times. Useful for snapshot tests.

        Returns:
            Complete HTML page with stylesheets and thread content
        """
        import pathlib

        from jinja2 import Environment, FileSystemLoader

        from csbot.slackbot.webapp.thread_html_renderer import render_slack_messages_to_html

        # Get the thread content HTML
        thread_content = await render_slack_messages_to_html(
            self,
            channel_id,
            thread_ts,
            bot_user_id=None,
        )

        # Set up Jinja2 environment with template directory
        template_dir = (
            pathlib.Path(__file__).parent.parent.parent
            / "src"
            / "csbot"
            / "slackbot"
            / "webapp"
            / "templates"
        )
        env = Environment(loader=FileSystemLoader(str(template_dir)))

        # Render the test template (simpler than production thread.html)
        template = env.get_template("thread_test.html")
        return template.render(thread_content=thread_content)

    async def render_all_threads_to_html(self, channel_id: str) -> str:
        """Render all thread conversations in a channel as HTML for testing and debugging.

        This creates a page showing all parent messages and their replies in the channel.

        In Slack's data model:
        - Top-level messages (thread parents) have no thread_ts field
        - Replies have a thread_ts field pointing to the parent message's ts
        - We render each top-level message as a separate thread

        Args:
            channel_id: Channel ID to render threads from

        Returns:
            Complete HTML page with all threads
        """
        import pathlib

        from jinja2 import Environment, FileSystemLoader

        from csbot.slackbot.webapp.thread_html_renderer import render_slack_messages_to_html

        # Get all messages in the channel
        messages = self.get_channel_messages(channel_id)

        # Collect all top-level messages (those without thread_ts)
        # These are thread parents or standalone messages
        top_level_messages = [msg for msg in messages if not msg.get("thread_ts")]

        # Sort by timestamp to maintain chronological order
        top_level_messages.sort(key=lambda m: float(m["ts"]))

        # Render each thread (parent + replies)
        thread_htmls = []
        for parent_msg in top_level_messages:
            thread_html = await render_slack_messages_to_html(
                self,
                channel_id,
                parent_msg["ts"],
                bot_user_id=None,
            )
            thread_htmls.append(thread_html)

        # Combine all threads with dividers
        all_threads_html = '<hr class="my-8 border-gray-300">'.join(thread_htmls)

        # Set up Jinja2 environment with template directory
        template_dir = (
            pathlib.Path(__file__).parent.parent.parent
            / "src"
            / "csbot"
            / "slackbot"
            / "webapp"
            / "templates"
        )
        env = Environment(loader=FileSystemLoader(str(template_dir)))

        # Render with the test template
        template = env.get_template("thread_test.html")
        return template.render(thread_content=all_threads_html)

    async def snapshot_channel_threads(
        self,
        channel_id: str,
        snapshot_name: str,
        *,
        snapshot_dir: str | None = None,
        user_id: str | None = None,
        update: bool | None = None,
        view: bool | None = None,
    ) -> None:
        """Render all channel threads and ephemeral messages to HTML and compare against snapshot.

        This method automates the snapshot testing workflow:
        1. Renders all threads in the channel to HTML
        2. Renders all ephemeral messages (if any)
        3. If snapshot exists and update=False, compares and raises AssertionError if different
        4. If snapshot doesn't exist or update=True, creates/updates it
        5. If view=True, opens the snapshot in the browser

        Args:
            channel_id: Channel ID to render threads from
            snapshot_name: Name for the snapshot file (e.g., "test_my_scenario")
            snapshot_dir: Optional custom snapshot directory. Defaults to
                         tests/utils/__snapshots__/ relative to this file.
            user_id: Optional user ID to filter ephemeral messages
            update: If True, update snapshot instead of comparing. If None (default), reads from
                   PYTEST_SNAPSHOT_UPDATE env var (set by --snapshot-update flag)
            view: If True, open snapshot in browser. If None (default), reads from
                 PYTEST_SNAPSHOT_VIEW env var (set by --view flag)

        Raises:
            AssertionError: If the generated HTML differs from existing snapshot (when update=False)

        Example:
            ```python
            async def test_my_scenario(client: FakeSlackClient):
                # Create some threaded conversations
                await client.chat_postMessage(channel=channel_id, text="Hello")
                # ...

                # Automatically snapshot and compare (includes ephemeral messages)
                # Flags automatically read from environment (set by pytest --snapshot-update --view)
                await client.snapshot_channel_threads(
                    channel_id,
                    "test_my_scenario",
                    user_id="U123456789",  # Optional: filter ephemeral by user
                )
            ```
        """
        import inspect
        import os
        import pathlib

        # Read flags from environment if not explicitly provided
        # Environment variables are set by pytest_configure in conftest.py
        if update is None:
            update = os.environ.get("PYTEST_SNAPSHOT_UPDATE") == "1"
        if view is None:
            view = os.environ.get("PYTEST_SNAPSHOT_VIEW") == "1"

        # Render all threads to HTML
        threads_html = await self.render_all_threads_to_html(channel_id)

        # Also render ephemeral messages for this channel
        ephemeral_html = await self.render_ephemeral_messages_to_html(channel_id, user_id=user_id)

        # Extract just the content from ephemeral HTML (remove the full page wrapper)
        # We'll combine both into one page
        import re

        ephemeral_content_match = re.search(
            r'<div class="prose max-w-none">\s*(.*?)\s*</div>\s*</div>\s*</div>\s*</body>',
            ephemeral_html,
            re.DOTALL,
        )
        ephemeral_content = ephemeral_content_match.group(1) if ephemeral_content_match else ""

        # Similarly extract threads content
        threads_content_match = re.search(
            r'<div class="prose max-w-none">\s*(.*?)\s*</div>\s*</div>\s*</div>\s*</body>',
            threads_html,
            re.DOTALL,
        )
        threads_content = threads_content_match.group(1) if threads_content_match else ""

        # Combine both with a separator if both exist
        combined_content = ""
        if threads_content and ephemeral_content:
            combined_content = f'{threads_content}\n\n<hr class="my-8 border-gray-400 border-2">\n<h2 class="text-xl font-bold text-gray-700 mb-4">Ephemeral Messages</h2>\n\n{ephemeral_content}'
        elif threads_content:
            combined_content = threads_content
        elif ephemeral_content:
            combined_content = f'<h2 class="text-xl font-bold text-gray-700 mb-4">Ephemeral Messages</h2>\n\n{ephemeral_content}'
        else:
            combined_content = '<div class="text-gray-500 p-4 text-center italic">No messages or ephemeral messages</div>'

        # Re-wrap in the template
        from jinja2 import Environment, FileSystemLoader

        template_dir = (
            pathlib.Path(__file__).parent.parent.parent
            / "src"
            / "csbot"
            / "slackbot"
            / "webapp"
            / "templates"
        )
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("thread_test.html")
        html = template.render(thread_content=combined_content)

        # Determine snapshot directory
        if snapshot_dir is None:
            # Get the calling test file's location
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_file = frame.f_back.f_code.co_filename
                snapshot_path = (
                    pathlib.Path(caller_file).parent / "__snapshots__" / f"{snapshot_name}.html"
                )
            else:
                # Fallback if inspect fails
                snapshot_path = (
                    pathlib.Path(__file__).parent / "__snapshots__" / f"{snapshot_name}.html"
                )
        else:
            snapshot_path = pathlib.Path(snapshot_dir) / f"{snapshot_name}.html"

        # Create directory if needed
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        # Compare or create snapshot
        if update or not snapshot_path.exists():
            # Update mode or creating new snapshot
            snapshot_path.write_text(html)
            action = "updated" if snapshot_path.exists() and update else "created"
            print(f"\n✓ Snapshot {action}: {snapshot_path.name}")
            if not view:
                print("  To view snapshot in browser, run: pytest --view")
        else:
            # Compare mode
            expected_html = snapshot_path.read_text()
            if html != expected_html:
                # Calculate diff for better error message
                import difflib

                diff = difflib.unified_diff(
                    expected_html.splitlines(keepends=True),
                    html.splitlines(keepends=True),
                    fromfile="expected",
                    tofile="actual",
                    lineterm="",
                )
                diff_text = "".join(list(diff)[:50])  # Limit diff output

                raise AssertionError(
                    f"HTML output differs from snapshot {snapshot_path}.\n\n"
                    f"First 50 lines of diff:\n{diff_text}\n\n"
                    f"To update snapshot:  pytest --snapshot-update\n"
                    f"To view snapshot:    pytest --view\n"
                    f"To view and update:  pytest --snapshot-update --view"
                )
            else:
                # Snapshot matches - inform user about view option
                if not view:
                    print(f"✓ Snapshot matches: {snapshot_path.name} (use --view to inspect)")

        # Open in browser if view flag is set
        if view:
            import webbrowser

            print(f"Opening snapshot in browser: {snapshot_path.name}")
            webbrowser.open(f"file://{snapshot_path.absolute()}")

    async def render_ephemeral_messages_to_html(
        self, channel_id: str, user_id: str | None = None
    ) -> str:
        """Render ephemeral messages as HTML for testing and debugging.

        Args:
            channel_id: Channel ID to render ephemeral messages from
            user_id: Optional user ID to filter ephemeral messages

        Returns:
            Complete HTML page with ephemeral messages
        """
        import pathlib

        from jinja2 import Environment, FileSystemLoader

        # Get ephemeral messages
        ephemeral_messages = self.get_ephemeral_messages(user_id=user_id)

        # Filter by channel if needed
        if channel_id:
            ephemeral_messages = [
                msg for msg in ephemeral_messages if msg.get("channel") == channel_id
            ]

        # Render each message as HTML
        message_htmls = []
        for msg in ephemeral_messages:
            import html

            text_content = msg.get("text", "")
            blocks = msg.get("blocks", [])
            user = msg.get("user", "Unknown")

            # Render blocks if present
            blocks_html = ""
            if blocks:
                blocks_html = '<div class="mt-2 space-y-1">'
                for block in blocks:
                    if block.get("type") == "markdown":
                        block_text = block.get("text", "")
                        blocks_html += f'<div class="text-sm bg-gray-50 p-2 rounded border border-gray-200">{html.escape(block_text)}</div>'
                    elif block.get("type") == "actions":
                        blocks_html += (
                            '<div class="text-sm text-gray-600 italic">[ Action buttons ]</div>'
                        )
                blocks_html += "</div>"

            # Build message HTML
            escaped_text = html.escape(text_content)
            message_content_html = f"{escaped_text}{blocks_html}"

            # User icon
            user_icon_html = f"""
                <div class="w-8 h-8 rounded bg-purple-500 flex items-center justify-center text-white text-xs font-semibold">
                    {html.escape((user or "U")[:2].upper())}
                </div>
            """

            message_html = f"""
<div class="bg-purple-50 rounded-lg border-2 border-purple-200 shadow-sm mb-4">
    <div class="bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-700 rounded-t-lg">
        Ephemeral (only visible to @{html.escape(user)})
    </div>
    <div class="flex gap-3 p-4">
        {user_icon_html}
        <div class="flex-1 min-w-0">
            <div class="flex items-baseline gap-2">
                <span class="font-semibold text-gray-900 text-md">{html.escape(user)}</span>
            </div>
            <div class="text-gray-900 text-md leading-relaxed -mt-1">{message_content_html}</div>
        </div>
    </div>
</div>
"""
            message_htmls.append(message_html)

        # Combine all messages
        all_messages_html = (
            "\n".join(message_htmls)
            if message_htmls
            else '<div class="text-gray-500 p-4 text-center italic">No ephemeral messages</div>'
        )

        # Set up Jinja2 environment with template directory
        template_dir = (
            pathlib.Path(__file__).parent.parent.parent
            / "src"
            / "csbot"
            / "slackbot"
            / "webapp"
            / "templates"
        )
        env = Environment(loader=FileSystemLoader(str(template_dir)))

        # Render with the test template
        template = env.get_template("thread_test.html")
        return template.render(thread_content=all_messages_html)

    async def snapshot_ephemeral_messages(
        self,
        channel_id: str,
        snapshot_name: str,
        *,
        user_id: str | None = None,
        snapshot_dir: str | None = None,
        update: bool | None = None,
        view: bool | None = None,
    ) -> None:
        """Render ephemeral messages to HTML and compare against snapshot.

        This is similar to snapshot_channel_threads but for ephemeral messages.

        Args:
            channel_id: Channel ID to render ephemeral messages from
            snapshot_name: Name for the snapshot file
            user_id: Optional user ID to filter ephemeral messages
            snapshot_dir: Optional custom snapshot directory
            update: If True, update snapshot instead of comparing. If None (default), reads from
                   PYTEST_SNAPSHOT_UPDATE env var (set by --snapshot-update flag)
            view: If True, open snapshot in browser. If None (default), reads from
                 PYTEST_SNAPSHOT_VIEW env var (set by --view flag)

        Raises:
            AssertionError: If the generated HTML differs from existing snapshot (when update=False)
        """
        import inspect
        import os
        import pathlib

        # Read flags from environment if not explicitly provided
        if update is None:
            update = os.environ.get("PYTEST_SNAPSHOT_UPDATE") == "1"
        if view is None:
            view = os.environ.get("PYTEST_SNAPSHOT_VIEW") == "1"

        # Render ephemeral messages to HTML
        html = await self.render_ephemeral_messages_to_html(channel_id, user_id=user_id)

        # Determine snapshot directory
        if snapshot_dir is None:
            # Get the calling test file's location
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_file = frame.f_back.f_code.co_filename
                snapshot_path = (
                    pathlib.Path(caller_file).parent / "__snapshots__" / f"{snapshot_name}.html"
                )
            else:
                # Fallback if inspect fails
                snapshot_path = (
                    pathlib.Path(__file__).parent / "__snapshots__" / f"{snapshot_name}.html"
                )
        else:
            snapshot_path = pathlib.Path(snapshot_dir) / f"{snapshot_name}.html"

        # Create directory if needed
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        # Compare or create snapshot
        if update or not snapshot_path.exists():
            # Update mode or creating new snapshot
            snapshot_path.write_text(html)
            action = "updated" if snapshot_path.exists() and update else "created"
            print(f"\n✓ Ephemeral snapshot {action}: {snapshot_path.name}")
            if not view:
                print("  To view snapshot in browser, run: pytest --view")
        else:
            # Compare mode
            expected_html = snapshot_path.read_text()
            if html != expected_html:
                # Calculate diff for better error message
                import difflib

                diff = difflib.unified_diff(
                    expected_html.splitlines(keepends=True),
                    html.splitlines(keepends=True),
                    fromfile="expected",
                    tofile="actual",
                    lineterm="",
                )
                diff_text = "".join(list(diff)[:50])  # Limit diff output

                raise AssertionError(
                    f"HTML output differs from snapshot {snapshot_path}.\n\n"
                    f"First 50 lines of diff:\n{diff_text}\n\n"
                    f"To update snapshot:  pytest --snapshot-update\n"
                    f"To view snapshot:    pytest --view\n"
                    f"To view and update:  pytest --snapshot-update --view"
                )
            else:
                # Snapshot matches - inform user about view option
                if not view:
                    print(
                        f"✓ Ephemeral snapshot matches: {snapshot_path.name} (use --view to inspect)"
                    )

        # Open in browser if view flag is set
        if view:
            import webbrowser

            print(f"Opening ephemeral snapshot in browser: {snapshot_path.name}")
            webbrowser.open(f"file://{snapshot_path.absolute()}")

    # Public getters for test assertions (avoid accessing private fields)

    def get_teams(self) -> dict[str, dict[str, Any]]:
        """Get all teams.

        Returns:
            Dictionary mapping team_id -> team data
        """
        return self._teams.copy()

    def get_team_ids(self) -> list[str]:
        """Get all team IDs.

        Returns:
            List of team IDs
        """
        return list(self._teams.keys())

    def get_channels(self) -> dict[str, dict[str, Any]]:
        """Get all channels.

        Returns:
            Dictionary mapping channel_id -> channel data
        """
        return self._channels.copy()

    def get_channel_ids(self) -> list[str]:
        """Get all channel IDs.

        Returns:
            List of channel IDs
        """
        return list(self._channels.keys())

    def get_channel_by_name(self, name: str) -> dict[str, Any] | None:
        """Get a channel by name.

        Args:
            name: Channel name

        Returns:
            Channel data or None if not found
        """
        for channel in self._channels.values():
            if channel["name"] == name:
                return channel.copy()
        return None

    def get_users(self) -> dict[str, dict[str, Any]]:
        """Get all users.

        Returns:
            Dictionary mapping user_id -> user data
        """
        return self._users.copy()

    def get_user_ids(self) -> list[str]:
        """Get all user IDs.

        Returns:
            List of user IDs
        """
        return list(self._users.keys())

    def get_channel_members(self, channel_id: str) -> set[str]:
        """Get members of a channel.

        Args:
            channel_id: Channel ID

        Returns:
            Set of user IDs in the channel
        """
        return self._channel_members.get(channel_id, set()).copy()

    def clear_all(self) -> None:
        """Clear all data from storage (helper for tests)."""
        self._teams.clear()
        self._channels.clear()
        self._users.clear()
        self._messages.clear()
        self._channel_members.clear()
        self._pins.clear()
        self._reactions.clear()
        self._slack_connect_invites.clear()
        self._ephemeral_messages.clear()
        self._bot_tokens.clear()

    # Compatibility methods matching slack_utils.py wrapper format
    # These methods return {"success": bool, ...} instead of {"ok": bool, ...}

    async def create_slack_team_compat(
        self,
        admin_token: str,
        team_name: str,
        team_domain: str,
        team_description: str | None = None,
    ) -> dict[str, Any]:
        """Create a Slack team - compatible with slack_utils.create_slack_team format.

        Args:
            admin_token: Slack API token (ignored in mock)
            team_name: Name of the team to create
            team_domain: Team domain (max 21 chars)
            team_description: Optional team description

        Returns:
            Dictionary with 'success' boolean and either 'team_id' or 'error' message
        """
        if len(team_domain) > 21:
            return {"success": False, "error": "team domain must be 21 characters or fewer"}

        result = await self.create_team(team_name, team_domain, team_description)

        if result.get("ok"):
            return {
                "success": True,
                "team_id": result["team"],
                "team_name": team_name,
                "team_domain": team_domain,
                "team_description": team_description or "",
            }
        else:
            return {"success": False, "error": result.get("error", "unknown")}

    async def create_channel_compat(
        self,
        admin_token: str,
        team_id: str,
        channel_name: str,
        is_private: bool = False,
    ) -> dict[str, Any]:
        """Create a channel - compatible with slack_utils.create_channel format.

        Args:
            admin_token: Slack API token (ignored in mock)
            team_id: ID of the team to create the channel in
            channel_name: Name of the channel to create
            is_private: Whether the channel should be private

        Returns:
            Dictionary with 'success' boolean and either 'channel_id' or 'error' message
        """
        result = await self.conversations_create(
            name=channel_name,
            is_private=is_private,
            team_id=team_id,
        )

        if result.get("ok"):
            channel = result["channel"]
            return {
                "success": True,
                "channel_id": channel["id"],
                "channel_name": channel_name,
                "is_private": is_private,
            }
        else:
            return {"success": False, "error": result.get("error", "unknown")}

    async def get_all_channels_compat(
        self,
        org_bot_token: str,
        team_id: str,
    ) -> dict[str, Any]:
        """Get all channels - compatible with slack_utils.get_all_channels format.

        Args:
            org_bot_token: Slack API token (ignored in mock)
            team_id: ID of the Slack team to get channels from

        Returns:
            Dictionary with 'success' boolean and either 'channel_ids' or 'error' message
        """
        result = await self.conversations_list(
            team_id=team_id,
            types="public_channel",
            exclude_archived=True,
            limit=100,
        )

        if result.get("ok"):
            channels = result["channels"]
            all_channel_ids = [channel["id"] for channel in channels]
            all_channel_names = [channel["name"] for channel in channels]
            channel_name_to_id = {channel["name"]: channel["id"] for channel in channels}

            return {
                "success": True,
                "channel_ids": ",".join(all_channel_ids),
                "channel_names": all_channel_names,
                "channel_name_to_id": channel_name_to_id,
            }
        else:
            return {"success": False, "error": result.get("error", "unknown")}

    async def get_bot_user_id_compat(self, bot_token: str) -> dict[str, Any]:
        """Get bot user ID - compatible with slack_utils.get_bot_user_id format.

        Args:
            bot_token: Slack bot token (ignored in mock)

        Returns:
            Dictionary with 'success' boolean and either 'user_id' or 'error' message
        """
        result = await self.auth_test()

        if result.get("ok"):
            return {
                "success": True,
                "user_id": result["user_id"],
                "bot_id": result["bot_id"],
            }
        else:
            return {"success": False, "error": result.get("error", "unknown")}

    async def invite_bot_to_channel_compat(
        self,
        admin_token: str,
        channel: str,
        bot_user_id: str,
    ) -> dict[str, Any]:
        """Invite bot to channel - compatible with slack_utils.invite_bot_to_channel format.

        Args:
            admin_token: Slack admin token (ignored in mock)
            channel: Channel ID to invite the bot to
            bot_user_id: Bot's user ID to invite

        Returns:
            Dictionary with 'success' boolean and either success data or 'error' message
        """
        result = await self.conversations_invite(channel=channel, users=bot_user_id)

        if result.get("ok"):
            return {
                "success": True,
                "channel": channel,
                "user_id": bot_user_id,
            }
        else:
            # Handle the case where the bot is already in the channel
            if result.get("error") == "already_in_channel":
                return {
                    "success": True,
                    "channel": channel,
                    "user_id": bot_user_id,
                    "was_already_in_channel": True,
                }
            else:
                return {"success": False, "error": result.get("error", "unknown")}

    async def invite_user_to_slack_team_compat(
        self,
        admin_token: str,
        team_id: str,
        email: str,
        channel_ids: str,
    ) -> dict[str, Any]:
        """Invite user to Slack team - compatible with slack_utils.invite_user_to_slack_team format.

        Args:
            admin_token: Slack API token (ignored in mock)
            team_id: ID of the Slack team to invite the user to
            email: Email address of the user to invite
            channel_ids: Comma-separated list of channel IDs to join

        Returns:
            Dictionary with 'success' boolean and either 'user_id' or 'error' message
        """
        # In the real API, this creates a user if they don't exist
        # For the mock, we'll create a user with this email
        user = self.create_test_user(name=email.split("@")[0], email=email)
        user_id = user["id"]

        # Add user to specified channels
        if channel_ids:
            for channel_id in channel_ids.split(","):
                channel_id = channel_id.strip()
                if channel_id and channel_id in self._channels:
                    if channel_id not in self._channel_members:
                        self._channel_members[channel_id] = set()
                    self._channel_members[channel_id].add(user_id)

        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "team_id": team_id,
        }

    async def create_slack_connect_channel_compat(
        self,
        bot_token: str,
        channel: str,
        emails: list[str],
    ) -> dict[str, Any]:
        """Create Slack Connect channel - compatible with slack_utils.create_slack_connect_channel format.

        Args:
            bot_token: Slack bot token (ignored in mock)
            channel: Channel ID to share externally
            emails: List of email addresses to invite to the shared channel

        Returns:
            Dictionary with 'success' boolean and either success data or 'error' message
        """
        result = await self.conversations_inviteShared(channel=channel, emails=emails)

        if result.get("ok"):
            return {
                "success": True,
                "channel": channel,
                "emails": emails,
                "invite_id": result["invite_id"],
            }
        else:
            return {"success": False, "error": result.get("error", "unknown")}

    # HTTP-level API endpoint router
    # Routes Slack API endpoints to appropriate methods

    async def handle_api_endpoint(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Route Slack API endpoint calls to appropriate mock methods.

        This method enables HTTP-level mocking by routing endpoint strings
        (e.g., "admin.teams.create") to the corresponding mock implementation.

        Args:
            endpoint: Slack API endpoint (e.g., "admin.teams.create")
            payload: Request payload as a dictionary

        Returns:
            Dictionary with Slack API response format ({"ok": bool, ...})
        """
        # Route to appropriate handler based on endpoint
        if endpoint == "admin.teams.create":
            return await self.create_team(
                team_name=payload["team_name"],
                team_domain=payload["team_domain"],
                team_description=payload.get("team_description"),
            )

        elif endpoint == "conversations.create":
            return await self.conversations_create(
                name=payload["name"],
                is_private=payload.get("is_private", "false") == "true",
                team_id=payload.get("team_id"),
            )

        elif endpoint == "conversations.list":
            return await self.conversations_list(
                team_id=payload.get("team_id"),
                types=payload.get("types", "public_channel"),
                exclude_archived=payload.get("exclude_archived", "true") == "true",
                limit=int(payload.get("limit", "100")),
            )

        elif endpoint == "conversations.info":
            return await self.conversations_info(channel=payload["channel"])

        elif endpoint == "conversations.archive":
            return await self.conversations_archive(channel=payload["channel"])

        elif endpoint == "conversations.invite":
            return await self.conversations_invite(
                channel=payload["channel"],
                users=payload["users"],
            )

        elif endpoint == "conversations.members":
            return await self.conversations_members(
                channel=payload["channel"],
                limit=int(payload.get("limit", "100")),
            )

        elif endpoint == "conversations.history":
            return await self.conversations_history(
                channel=payload["channel"],
                limit=int(payload.get("limit", "100")),
                oldest=payload.get("oldest"),
                latest=payload.get("latest"),
            )

        elif endpoint == "conversations.inviteShared":
            emails = payload.get("emails")
            if emails and isinstance(emails, str):
                emails = [e.strip() for e in emails.split(",")]
            return await self.conversations_inviteShared(
                channel=payload["channel"],
                emails=emails,
                user_ids=payload.get("user_ids"),
            )

        elif endpoint == "admin.users.invite":
            # Create a user with the provided email
            email = payload.get("email", "unknown@example.com")
            user = self.create_test_user(name=email.split("@")[0], email=email)
            # Also add user to specified channels
            channel_ids_str = payload.get("channel_ids", "")
            if channel_ids_str:
                for channel_id in channel_ids_str.split(","):
                    channel_id = channel_id.strip()
                    if channel_id and channel_id in self._channels:
                        if channel_id not in self._channel_members:
                            self._channel_members[channel_id] = set()
                        self._channel_members[channel_id].add(user["id"])
            return {
                "ok": True,
                "user": {"id": user["id"]},
            }

        elif endpoint == "admin.apps.approve":
            return {"ok": True}

        elif endpoint == "auth.test":
            # Extract token from context if available (will be passed by mock_post_slack_api)
            return await self.auth_test(token=payload.get("_token"))

        elif endpoint == "chat.postMessage":
            return await self.chat_postMessage(
                channel=payload["channel"],
                text=payload.get("text"),
                blocks=payload.get("blocks"),
                thread_ts=payload.get("thread_ts"),
            )

        elif endpoint == "chat.postEphemeral":
            return await self.chat_postEphemeral(
                channel=payload["channel"],
                user=payload["user"],
                text=payload.get("text"),
                blocks=payload.get("blocks"),
                thread_ts=payload.get("thread_ts"),
            )

        elif endpoint == "chat.update":
            return await self.chat_update(
                channel=payload["channel"],
                ts=payload["ts"],
                text=payload.get("text"),
                blocks=payload.get("blocks"),
            )

        elif endpoint == "chat.getPermalink":
            return await self.chat_getPermalink(
                channel=payload["channel"],
                message_ts=payload["message_ts"],
            )

        elif endpoint == "pins.add":
            return await self.pins_add(
                channel=payload["channel"],
                timestamp=payload["timestamp"],
            )

        elif endpoint == "pins.remove":
            return await self.pins_remove(
                channel=payload["channel"],
                timestamp=payload["timestamp"],
            )

        elif endpoint == "pins.list":
            return await self.pins_list(channel=payload["channel"])

        elif endpoint == "reactions.add":
            return await self.reactions_add(
                channel=payload["channel"],
                timestamp=payload["timestamp"],
                name=payload["name"],
            )

        elif endpoint == "users.info":
            return await self.users_info(user=payload["user"])

        else:
            # Unknown endpoint - return error
            return {
                "ok": False,
                "error": f"unknown_method: {endpoint}",
            }


def mock_slack_api_with_client(fake_client: FakeSlackClient):
    """Create a mock patch for post_slack_api that routes to FakeSlackClient.

    This function returns a context manager that patches post_slack_api to route
    all Slack API calls through the provided FakeSlackClient instance.

    Args:
        fake_client: FakeSlackClient instance to route API calls to

    Returns:
        Context manager that patches post_slack_api

    Example:
        ```python
        fake_slack = FakeSlackClient("token")
        with mock_slack_api_with_client(fake_slack):
            # All slack_utils functions will now use fake_slack
            result = await create_slack_team("token", "My Team", "my-team-dgc")
            # Verify state
            assert len(fake_slack._teams) == 1
        ```
    """

    async def mock_post_slack_api(endpoint: str, token: str, payload: dict | None = None):
        """Mock implementation of post_slack_api that routes to FakeSlackClient."""
        # Parse payload if it's URL-encoded string
        if payload is None:
            payload = {}

        # Add token to payload for endpoints that need it (like auth.test)
        payload_with_token = {**payload, "_token": token}

        # Route to the fake client's API handler
        result = await fake_client.handle_api_endpoint(endpoint, payload_with_token)

        # Convert from Slack API format ({"ok": bool}) to slack_utils format ({"success": bool})
        if result.get("ok"):
            return {"success": True, **result}
        else:
            error = result.get("error", "Unknown error")
            detail = result.get("detail", "")
            error_msg = f"{error}: {detail}" if detail else error
            return {"success": False, "error": error_msg}

    return patch("csbot.slackbot.slack_utils.post_slack_api", side_effect=mock_post_slack_api)
