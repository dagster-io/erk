"""Channel bot subpackage for CompassChannelBot."""

from csbot.slackbot.channel_bot.bot import (
    CompassChannelBaseBotInstance,
    SlackLoggingHandler,
    get_bot_intro_prompt,
)

__all__ = [
    "CompassChannelBaseBotInstance",
    "get_bot_intro_prompt",
    "SlackLoggingHandler",
]
