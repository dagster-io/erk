from typing import Literal

from pydantic import BaseModel
from temporalio import activity, workflow

from csbot.contextengine.contextstore_protocol import TableFrontmatter
from csbot.local_context_store.local_context_store import LocalBackedGithubContextStoreManager

with workflow.unsafe.imports_passed_through():
    from csbot.contextengine.contextstore_protocol import Dataset
    from csbot.slackbot.bot_server.bot_server import BotKey
    from csbot.slackbot.channel_bot.handlers.dataset_monitor import DatasetMonitor
    from csbot.slackbot.channel_bot.handlers.github_pr_handler import GitHubPRHandler
    from csbot.temporal import constants
    from csbot.temporal.utils import BotProvider


class DatasetMonitoringActivityInput(BaseModel):
    bot_id: str
    connection: str
    table_name: str
    frontmatter: TableFrontmatter | None


class DatasetMonitoringFailure(BaseModel):
    type: Literal["failure"] = "failure"
    error: str


class DatasetMonitoringSuccess(BaseModel):
    type: Literal["success"] = "success"

    # if the dataset content has changed, we will create a PR
    # and provide its url here
    pr_url: str | None


DatasetMonitoringResult = DatasetMonitoringSuccess | DatasetMonitoringFailure


class DatasetMonitoringActivity:
    """Manages the dataset monitoring background task."""

    def __init__(self, bot_provider: BotProvider):
        self._bot_provider = bot_provider

    @activity.defn(name=constants.Activity.DATASET_MONITORING_ACTIVITY_NAME.value)
    async def dataset_monitor_activity(
        self, args: DatasetMonitoringActivityInput
    ) -> DatasetMonitoringResult:
        activity.logger.info(f"Starting dataset monitoring for {args.connection}/{args.table_name}")
        frontmatter = args.frontmatter
        bot = await self._bot_provider.fetch_bot(BotKey.from_bot_id(args.bot_id))
        context_store_manager = LocalBackedGithubContextStoreManager(
            bot.local_context_store, bot.github_monitor
        )
        monitor = DatasetMonitor(
            activity.logger,
            bot.profile,
            bot.kv_store,
            GitHubPRHandler(context_store_manager),
            bot.agent,
        )
        try:
            project = (await bot.load_context_store()).project
            pr_url = await monitor.check_and_update_dataset_if_changed(
                Dataset(
                    connection=args.connection,
                    table_name=args.table_name,
                ),
                frontmatter,
                project,
            )
            return DatasetMonitoringSuccess(pr_url=pr_url)
        except Exception as e:
            activity.logger.exception("Failed checking dataset changes")
            return DatasetMonitoringFailure(error=str(e))
