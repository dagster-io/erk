from pydantic import BaseModel
from temporalio import activity

from csbot.contextengine.contextstore_protocol import ContextStore
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.temporal import constants
from csbot.temporal.utils import BotProvider


class ContextStoreLoaderInput(BaseModel):
    bot_id: str


class ContextStoreLoadResult(BaseModel):
    context_store: ContextStore


class ContextStoreLoaderActivity:
    def __init__(self, bot_provider: BotProvider):
        self._bot_provider = bot_provider

    @activity.defn(name=constants.Activity.CONTEXT_STORE_LOADER_ACTIVITY_NAME.value)
    async def load_context_store(self, args: ContextStoreLoaderInput) -> ContextStoreLoadResult:
        """
        returns a context store where all datasets have been validated against
        the bots available connections
        """
        bot = await self._bot_provider.fetch_bot(BotKey.from_bot_id(args.bot_id))
        context_store = await bot.load_context_store()

        available_connections = bot.profile.connections

        datasets = []
        logged = set()
        for dataset, documentation in context_store.datasets:
            if dataset.connection not in available_connections:
                if dataset.connection not in logged:
                    activity.logger.error(f"Connection {dataset.connection} does not exist")
                    logged.add(dataset.connection)
            else:
                datasets.append((dataset, documentation))

        return ContextStoreLoadResult(
            context_store=ContextStore(
                project=context_store.project,
                datasets=datasets,
                general_context=context_store.general_context,
                general_cronjobs=context_store.general_cronjobs,
                channels=context_store.channels,
            )
        )
