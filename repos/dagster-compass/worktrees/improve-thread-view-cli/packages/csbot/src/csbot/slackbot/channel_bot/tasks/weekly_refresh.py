"""Weekly dataset refresh background task for CompassChannelBotInstance."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from csbot.contextengine.loader import load_project_from_tree
from csbot.slackbot.channel_bot.tasks.bot_instance_task import BotInstanceBackgroundTask
from csbot.utils.sync_to_async import sync_to_async

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
    from csbot.slackbot.channel_bot.handlers.dataset_monitor import DatasetMonitor
    from csbot.slackbot.channel_bot.handlers.github_pr_handler import GitHubPRHandler


class WeeklyRefreshTask(BotInstanceBackgroundTask):
    """Manages the weekly dataset refresh background task."""

    def __init__(
        self,
        bot: "CompassChannelBaseBotInstance",
        dataset_monitor: "DatasetMonitor",
        github_pr_handler: "GitHubPRHandler",
    ):
        super().__init__(bot)
        self.monitor_handler = dataset_monitor
        self.github_pr_handler = github_pr_handler

    @sync_to_async
    def _load_project_config(self):
        """Load project configuration from the repository tree."""
        with self.bot.local_context_store.latest_file_tree() as tree:
            return load_project_from_tree(tree)

    async def execute_tick(self) -> None:
        """Execute weekly dataset refresh."""
        self.bot.logger.info("Starting weekly dataset refresh")

        context_store = await self.bot.load_context_store()
        datasets = context_store.datasets

        if not datasets:
            self.bot.logger.info("No datasets found for weekly refresh")
            return

        self.bot.logger.info(f"Starting weekly refresh of {len(datasets)} datasets")

        # Create weekly refresh PR with all datasets
        await self.github_pr_handler.create_weekly_refresh_pr(
            datasets=[dataset for dataset, _ in context_store.datasets],
            profile=self.bot.profile,
            agent=self.bot.agent,
            logger=self.bot.logger,
        )

        self.bot.logger.info("Weekly dataset refresh completed")

    def get_sleep_seconds(self) -> float:
        """Sleep until next Sunday at 11 PM +/- 1 hour."""
        now = datetime.now()

        # Calculate next Sunday at 11 PM
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 23:
            days_until_sunday = 7

        next_sunday = now + timedelta(days=days_until_sunday)
        next_sunday = next_sunday.replace(hour=23, minute=0, second=0, microsecond=0)

        sleep_for_seconds = (next_sunday - now).total_seconds()
        sleep_for_seconds = self._jitter_seconds(sleep_for_seconds, 3600)
        self.bot.logger.info(
            f"Sleeping for {sleep_for_seconds} seconds until next Sunday 11 PM +/- 1 hour for weekly "
            f"dataset refresh"
        )
        # Add small buffer to avoid immediate re-execution
        return max(sleep_for_seconds, 60)

    async def on_error(self, error: Exception) -> None:
        """Handle errors with governance messages."""
        await super().on_error(error)
        await self.bot.send_simple_governance_message(
            f"⚠️ *Error in weekly dataset refresh:* {error}"
        )
