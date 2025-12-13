"""
TypedDict definitions for Slack Events API payloads.

Based on https://api.slack.com/apis/events-api#events-JSON
"""

from typing import Any, NotRequired, TypedDict


class SlackAuthorization(TypedDict):
    """Authorization details for the app installation."""

    enterprise_id: NotRequired[str | None]
    team_id: str
    user_id: str
    is_bot: bool
    is_enterprise_install: NotRequired[bool]


class SlackEventBase(TypedDict):
    """Base structure for all Slack events."""

    type: str
    event_ts: NotRequired[str]


class SlackMessageEvent(TypedDict):
    """Slack message event structure."""

    type: str  # "message"
    user: NotRequired[str]
    text: NotRequired[str]
    ts: str
    channel: str
    event_ts: str
    channel_type: NotRequired[str]
    thread_ts: NotRequired[str]
    parent_user_id: NotRequired[str]
    bot_id: NotRequired[str]
    subtype: NotRequired[str]


class SlackAppMentionEvent(TypedDict):
    """Slack app mention event structure."""

    type: str  # "app_mention"
    user: str
    text: str
    ts: str
    channel: str
    event_ts: str
    thread_ts: NotRequired[str]


class SlackReactionEvent(TypedDict):
    """Slack reaction added/removed event structure."""

    type: str  # "reaction_added" or "reaction_removed"
    user: str
    reaction: str
    item_user: NotRequired[str]
    item: dict[str, Any]
    event_ts: str


class SlackSlashCommandEvent(TypedDict):
    """Slack slash command event structure."""

    type: str  # "slash_command"
    user: str
    command: str
    text: str
    ts: str
    channel: str
    event_ts: str
    thread_ts: NotRequired[str]


class SlackEventPayload(TypedDict):
    """Complete Slack Events API payload structure."""

    token: NotRequired[str]
    team_id: str
    api_app_id: str
    event: (
        SlackEventBase
        | SlackMessageEvent
        | SlackAppMentionEvent
        | SlackReactionEvent
        | SlackSlashCommandEvent
    )
    type: str  # Usually "event_callback"
    event_id: str
    event_time: int
    event_context: NotRequired[str]
    authorizations: NotRequired[list[SlackAuthorization]]


class SlackUrlVerificationPayload(TypedDict):
    """Slack URL verification challenge payload."""

    token: str
    challenge: str
    type: str  # "url_verification"


class SlackInteractivePayload(TypedDict):
    """Slack interactive component payload structure."""

    type: str  # "block_actions", "interactive_message", etc.
    team: dict[str, str]
    user: dict[str, str]
    api_app_id: str
    token: NotRequired[str]
    container: NotRequired[dict[str, Any]]
    trigger_id: str | None
    channel: NotRequired[dict[str, str]]
    message: NotRequired[dict[str, Any]]
    response_url: NotRequired[str]
    actions: NotRequired[list[dict[str, Any]]]
    view: NotRequired[dict[str, Any]]


class SlackSlashCommandPayload(TypedDict):
    """Slack slash command payload structure."""

    token: str
    command: str
    text: str
    response_url: str
    trigger_id: str
    user_id: str
    user_name: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    api_app_id: str


# Union type for all possible event structures
SlackEvent = (
    SlackEventBase
    | SlackMessageEvent
    | SlackAppMentionEvent
    | SlackReactionEvent
    | SlackSlashCommandEvent
)

# Union type for all possible payload structures
SlackPayload = (
    SlackEventPayload
    | SlackUrlVerificationPayload
    | SlackInteractivePayload
    | SlackSlashCommandPayload
)
