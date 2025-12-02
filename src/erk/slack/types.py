"""Type definitions for Slack bot.

This module contains immutable dataclasses for Slack data types used
throughout the Slack bot module.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SlackMessage:
    """Immutable representation of a Slack message.

    Attributes:
        channel: The Slack channel ID (e.g., "C01234ABCDE")
        ts: Slack's unique message timestamp ID (e.g., "1234567890.123456")
        thread_ts: Thread timestamp if this message is in a thread, None otherwise
        user: The user ID who sent the message (e.g., "U01234ABCDE")
        text: The text content of the message
    """

    channel: str
    ts: str
    thread_ts: str | None
    user: str
    text: str


@dataclass(frozen=True)
class SlackEvent:
    """Event from Socket Mode listener.

    Attributes:
        event_type: Type of event (e.g., "app_mention", "message")
        message: The SlackMessage associated with this event
    """

    event_type: str
    message: SlackMessage


@dataclass(frozen=True)
class ThreadRecord:
    """Persistent thread state in SQLite.

    Tracks ongoing conversations in Slack threads to maintain
    context across bot restarts.

    Attributes:
        channel: The Slack channel ID
        thread_ts: Thread timestamp (primary identifier with channel)
        session_id: Claude session ID for conversation resume, None if new
        last_message_ts: Timestamp of most recent message processed
        created_at: When this thread record was created
        updated_at: When this thread record was last updated
    """

    channel: str
    thread_ts: str
    session_id: str | None
    last_message_ts: str
    created_at: datetime
    updated_at: datetime
