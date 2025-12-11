from typing import TYPE_CHECKING, Protocol

from csbot.slackbot.bot_server.bot_reconciler import CompassBotReconciler
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance

if TYPE_CHECKING:
    from csbot.slackbot.slackbot_core import CompassBotServerConfig


class BotProvider(Protocol):
    async def fetch_bot(self, bot_key: BotKey) -> CompassChannelBaseBotInstance: ...

    def get_config(self) -> "CompassBotServerConfig": ...


class BotReconcilerBotProvider(BotProvider):
    def __init__(self, reconciler: CompassBotReconciler):
        self._reconciler = reconciler

    async def fetch_bot(self, bot_key: BotKey) -> CompassChannelBaseBotInstance:
        await self._reconciler.discover_and_update_bots_for_keys([bot_key])
        bot = self._reconciler.get_active_bots().get(bot_key)
        if bot:
            return bot

        await self._reconciler.discover_and_update_bots_for_keys([bot_key])

        bot = self._reconciler.get_active_bots().get(bot_key)
        if not bot:
            raise Exception(f"Bot instance not found for {bot_key}")

        return bot

    def get_config(self) -> "CompassBotServerConfig":
        return self._reconciler.config
