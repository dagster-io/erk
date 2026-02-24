from typing import Any

from slack_sdk.errors import SlackApiError


async def add_eyes_emoji(client: Any, *, channel: str, timestamp: str) -> None:
    try:
        await client.reactions_add(channel=channel, timestamp=timestamp, name="eyes")
    except SlackApiError as exc:
        ignored_errors = {"already_reacted", "missing_scope", "not_reactable"}
        if exc.response.get("error") not in ignored_errors:
            raise


async def remove_eyes_emoji(client: Any, *, channel: str, timestamp: str) -> None:
    try:
        await client.reactions_remove(channel=channel, timestamp=timestamp, name="eyes")
    except SlackApiError as exc:
        ignored_errors = {"no_reaction", "missing_scope", "not_reactable"}
        if exc.response.get("error") not in ignored_errors:
            raise


async def add_result_emoji(client: Any, *, channel: str, timestamp: str, success: bool) -> None:
    name = "white_check_mark" if success else "x"
    try:
        await client.reactions_add(channel=channel, timestamp=timestamp, name=name)
    except SlackApiError as exc:
        ignored_errors = {"already_reacted", "missing_scope", "not_reactable"}
        if exc.response.get("error") not in ignored_errors:
            raise
