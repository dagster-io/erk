"""Cron job scheduler task for background execution."""

import traceback
from typing import TYPE_CHECKING

from csbot.slackbot.channel_bot.tasks.bot_instance_task import BotInstanceBackgroundTask
from csbot.utils import tracing

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
    from csbot.slackbot.channel_bot.handlers.cron_job_handler import CronJobHandler


class CronJobSchedulerTask(BotInstanceBackgroundTask):
    """Handles the background scheduling and execution of cron jobs."""

    def __init__(self, bot: "CompassChannelBaseBotInstance", cron_job_handler: "CronJobHandler"):
        super().__init__(bot)
        self.cron_handler = cron_job_handler

    async def execute_tick(self) -> None:
        """Execute the next scheduled cron job."""
        # Get all cron jobs from the contextstore
        cron_jobs = await self.bot.csbot_client.get_cron_jobs()

        # Find next job to run
        result = self.cron_handler.find_next_due_job(cron_jobs)
        if not result:
            return

        job_name, cron_job, sleep_seconds = result

        tracing.try_set_tag("job_name", job_name)

        if sleep_seconds > 0:
            # jitter within 60 seconds to spread out the execution of cron jobs as many
            # may be scheduled exactly at 9a
            sleep_seconds = self._jitter_seconds(sleep_seconds, 60)
            self.bot.logger.info(f"Sleeping {sleep_seconds}s until cron job '{job_name}'")
            await self.async_sleep(sleep_seconds)

        # Double-check job still exists
        current_jobs = await self.bot.csbot_client.get_cron_jobs()
        if job_name not in current_jobs:
            self.bot.logger.info(f"Cron job '{job_name}' disappeared, skipping")
            return

        # Get channel and execute
        channel_id = await self.bot.kv_store.get_channel_id(self.bot.key.channel_name)
        if not channel_id:
            self.bot.logger.error(f"No channel found for cron job '{job_name}'")
            return

        try:
            await self.cron_handler.execute_cron_job(channel_id, job_name)
            self.bot.logger.info(f"Successfully executed cron job '{job_name}'")
        except Exception as e:
            tracing.try_set_exception()

            self.bot.logger.error(f"Error executing cron job '{job_name}': {e}", exc_info=True)
            await self.bot.send_simple_governance_message(
                f"⚠️ *Error executing scheduled analysis '{job_name}':* {e}"
            )

    def get_sleep_seconds(self) -> float:
        """Always check for new cron jobs every 60 seconds."""
        return self.cron_handler.get_default_sleep_seconds()

    async def on_error(self, error: Exception) -> None:
        """Handle errors with governance messages and 24-hour delay."""
        traceback.print_exc()
        await super().on_error(error)

        # Send governance message with 24-hour delay (commented out in original)
        # current_time = time.time()
        # delay_between_error_messages = 60 * 60 * 24  # 24 hours
        # if current_time - self.last_error_message_time > delay_between_error_messages:
        #     self.last_error_message_time = current_time
        #     await self.bot.send_simple_governance_message(
        #         f"⚠️ *Error loading scheduled analyses:* {error}"
        #     )
