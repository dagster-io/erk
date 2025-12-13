import logging
from typing import TYPE_CHECKING

from csbot.slackbot.tasks.background_task import BackgroundTask
from csbot.utils.time import AsyncSleep, system_async_sleep

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


class BotInstanceBackgroundTask(BackgroundTask):
    """Base class for background tasks with centralized loop management."""

    def __init__(
        self,
        bot: "CompassChannelBaseBotInstance",
        async_sleep: AsyncSleep = system_async_sleep,
    ):
        self.bot = bot
        super().__init__(async_sleep=async_sleep)

    @property
    def logger(self) -> logging.Logger:
        return self.bot.logger
