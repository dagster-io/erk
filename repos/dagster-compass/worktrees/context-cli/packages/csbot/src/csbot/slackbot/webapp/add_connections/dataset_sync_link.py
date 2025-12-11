"""Generate authenticated links to the dataset sync progress page."""

from datetime import timedelta
from typing import TYPE_CHECKING

from csbot.slackbot.webapp.security import create_link

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


def create_dataset_sync_progress_link(
    bot: "CompassChannelBaseBotInstance",
    user_id: str,
    connection_name: str,
    max_age: timedelta | None = None,
) -> str:
    """Create a JWT-authenticated link to the dataset sync progress page.

    Args:
        bot: The bot instance
        user_id: Slack user ID for attribution and audit trail
        connection_name: Name of the connection to view progress for
        max_age: How long the JWT token should be valid (default: 6 hours)

    Returns:
        A URL with JWT token that allows viewing the dataset sync progress
    """
    if max_age is None:
        # max_age=None defaults to 6 hours for dataset sync progress links
        max_age = timedelta(hours=6)

    # Create authenticated link
    path = "/dataset-sync"

    # Use create_link which adds the JWT token
    link = create_link(bot, user_id=user_id, path=path, max_age=max_age)

    # Append the connection query parameter after the JWT token
    return f"{link}&connection={connection_name}"
