from datetime import timedelta
from typing import TYPE_CHECKING

from csbot.slackbot.webapp.security import create_link

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


def create_channels_management_url(bot: "CompassChannelBaseBotInstance", user_id: str) -> str:
    """Create a JWT token for the channels management URL with 1-hour expiry.

    This token grants access to all billing and admin management pages including:
    - Billing information and plan management
    - Channel viewing, creation, updating, and deletion
    - Connection management

    Args:
        bot: The bot instance
        user_id: Slack user ID for attribution and audit trail
    """
    return create_link(
        bot,
        user_id=user_id,
        path="/channels",
        max_age=timedelta(hours=1),
    )
