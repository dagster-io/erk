"""Session and StreamEvent data models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Session:
    """Represents a Claude CLI session.

    Attributes:
        session_id: Unique identifier for the session (Claude CLI session ID)
        external_id: Optional external identifier (e.g., Slack thread ID)
        working_directory: Path to the repository/directory for this session
        status: Current session status ("active", "processing", "error")
        created_at: When the session was created
        last_activity: When the session last had activity
        message_count: Number of messages exchanged in this session
    """

    session_id: str
    external_id: str | None
    working_directory: str
    status: str
    created_at: datetime
    last_activity: datetime
    message_count: int


@dataclass(frozen=True)
class StreamEvent:
    """Represents an SSE event from Claude CLI output.

    Attributes:
        event_type: Type of event ("text", "tool", "done", "error")
        data: Event payload with type-specific fields
    """

    event_type: str
    data: dict[str, str | int | bool]
