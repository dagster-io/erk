from datetime import timedelta
from typing import TYPE_CHECKING

from csbot.slackbot.webapp.security import create_link

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassChannelBaseBotInstance


def create_connection_management_url(
    bot: "CompassChannelBaseBotInstance", long_lived: bool, user_id: str
) -> str:
    """Create a JWT token for the connection management URL.

    This token grants access to all management pages including:
    - Billing information and plan management
    - Channel viewing, creation, updating, and deletion
    - Connection management

    Args:
        bot: The bot instance
        long_lived: If True, token expires in 72 hours. Otherwise 3 hours.
        user_id: Slack user ID for attribution and audit trail
    """
    return create_link(
        bot,
        user_id=user_id,
        path="/connections",
        max_age=timedelta(hours=3) if not long_lived else timedelta(hours=72),
    )


def create_industry_selection_url(bot: "CompassChannelBaseBotInstance", user_id: str) -> str:
    """Create a JWT token for the industry selection URL."""
    return create_link(
        bot,
        user_id=user_id,
        path="/onboarding-industry",
        max_age=timedelta(hours=3),
    )
