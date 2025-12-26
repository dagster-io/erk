"""Temporal activity for sending daily exploration."""

from enum import Enum

from pydantic import BaseModel
from pygit2 import TYPE_CHECKING
from temporalio import activity, workflow

from csbot.temporal import constants

with workflow.unsafe.imports_passed_through():
    from csbot.slackbot.bot_server.bot_server import BotKey
    from csbot.slackbot.channel_bot.send_daily_exploration import send_daily_exploration

if TYPE_CHECKING:
    from csbot.temporal.utils import BotProvider


class DailyExplorationStatus(Enum):
    NO_CHANNEL_FOUND = "NO_CHANNEL_FOUND"


class DailyExplorationInput(BaseModel):
    bot_id: str
    channel_name: str


class DailyExplorationSuccess(BaseModel):
    status: DailyExplorationStatus | None = None


DailyExplorationResult = DailyExplorationSuccess


class DailyExplorationActivity:
    def __init__(self, bot_provider: "BotProvider"):
        self.bot_provider = bot_provider

    @activity.defn(name=constants.Activity.SEND_DAILY_EXPLORATION_ACTIVITY_NAME.value)
    async def send_daily_exploration_activity(
        self, args: DailyExplorationInput
    ) -> DailyExplorationResult:
        """Activity that sends daily exploration to a channel.

        Args:
            bot_id: Bot instance ID (team_id-channel_name format)
            channel_name: Channel name to send exploration to

        Returns:
            Status message
        """
        bot_id = args.bot_id
        channel_name = args.channel_name

        activity.logger.info(f"Executing daily exploration activity for bot {bot_id}")

        # Parse bot_id to get bot key
        bot_key = BotKey.from_bot_id(bot_id)
        bot = await self.bot_provider.fetch_bot(bot_key)

        channel_id = await bot.kv_store.get_channel_id(channel_name)
        if not channel_id:
            # indicates that the main channel hasn't been set up yet
            activity.logger.info(f"No channel {channel_name} found")
            return DailyExplorationSuccess(status=DailyExplorationStatus.NO_CHANNEL_FOUND)

        # Send daily exploration
        activity.logger.info(f"Sending daily exploration to channel {channel_name}")
        await send_daily_exploration(bot, channel_id)

        activity.logger.info(f"Daily exploration completed for {channel_name}")
        return DailyExplorationSuccess()
