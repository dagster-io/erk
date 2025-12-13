from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csbot.slackbot.slack_types import SlackInteractivePayload


def normalize_channel_name(channel_name: str) -> str:
    return channel_name.lower().strip().strip("#")


def detect_team_from_interactive_payload(payload: "SlackInteractivePayload") -> str | None:
    """Given an interactive payload, return the team_id.

    This is a best-effort attempt to detect the team_id from the payload - enterprise
    grid teams won't have a team.id field in the payload, but we can get it from the
    message.team field or the view.team_id field.
    """
    team_info = payload.get("team", {})
    team_id = team_info.get("id") if isinstance(team_info, dict) else None
    if team_id:
        return team_id
    message_team = payload.get("message", {}).get("team")
    if message_team:
        return message_team
    view_team = payload.get("view", {}).get("team_id")
    if view_team:
        return view_team
    user_team = payload.get("user", {}).get("team_id")
    if user_team:
        return user_team
    return None
