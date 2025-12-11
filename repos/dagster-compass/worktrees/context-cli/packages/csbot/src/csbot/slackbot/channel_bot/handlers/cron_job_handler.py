"""Unified cron job handler that handles scheduling and execution."""

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from croniter import croniter
from slack_sdk.web.async_client import AsyncWebClient

from csbot.csbot_client.csbot_client import CSBotClient
from csbot.slackbot.storage.interface import SlackbotInstanceStorage

if TYPE_CHECKING:
    from csbot.slackbot.usercron.models import UserCronJob


class CronJobHandler:
    """Unified handler for cron job scheduling and execution."""

    def __init__(
        self,
        logger: logging.Logger,
        csbot_client: CSBotClient,
        slack_client: AsyncWebClient,
        kv_store: SlackbotInstanceStorage,
        handle_new_thread: Callable[..., Awaitable[None]],
    ):
        self.logger = logger
        self.csbot_client = csbot_client
        self.client = slack_client
        self.kv_store = kv_store
        self._handle_new_thread = handle_new_thread

    def find_next_due_job(
        self, cron_jobs: dict[str, "UserCronJob"]
    ) -> tuple[str, "UserCronJob", float] | None:
        """Find the next cron job that should run and return sleep seconds until then.

        Returns:
            (job_name, cron_job, sleep_seconds) or None if no jobs due soon
        """
        if not cron_jobs:
            return None

        now = datetime.now()
        next_runs = {}

        for job_name, cron_job in cron_jobs.items():
            try:
                cron = croniter(cron_job.cron, now)
                next_run = cron.get_next(datetime)
                # Only consider jobs due within 90 seconds
                if next_run - now <= timedelta(seconds=90):
                    next_runs[job_name] = (cron_job, next_run)
            except Exception as e:
                self.logger.error(f"Error parsing cron expression for job {job_name}: {e}")
                continue

        if not next_runs:
            return None

        # Find the job with the earliest next run time
        earliest_job_name = min(next_runs.keys(), key=lambda name: next_runs[name][1])
        cron_job, next_run = next_runs[earliest_job_name]

        sleep_seconds = (next_run - now).total_seconds()
        return (earliest_job_name, cron_job, max(sleep_seconds, 0))

    async def execute_cron_job(self, channel_id: str, job_name: str) -> None:
        """Execute a specific cron job by name.

        Args:
            channel_id: Slack channel ID to post the job results
            job_name: Name of the cron job to execute
        """
        # Get current cron jobs and validate the job exists
        cron_jobs = await self.csbot_client.get_cron_jobs()
        if job_name not in cron_jobs:
            available_jobs = list(cron_jobs.keys())
            if not available_jobs:
                message = f"Unknown scheduled analysis: `{job_name}`\n\nNo scheduled analyses are currently configured."
            else:
                jobs_list = "\n".join(f"• `{job}`" for job in available_jobs)
                message = f"Unknown scheduled analysis: `{job_name}`\n\nAvailable scheduled analyses:\n{jobs_list}\n\nUsage: `!cron <analysis_name>`"

            from csbot.slackbot.exceptions import UserFacingError

            raise UserFacingError(
                title="Unknown Scheduled Analysis",
                message=message,
                error_type="user_input",
            )

        cron_job = cron_jobs[job_name]

        # Get bot user ID
        bot_user_id = await self._get_bot_user_id()
        if bot_user_id is None:
            raise ValueError("Bot user ID not found")

        # Post initial message to create the thread
        response = await self.client.chat_postMessage(
            channel=channel_id,
            text=cron_job.thread,
        )
        ts = response.get("ts")
        if not response.get("ok") or not ts:
            raise ValueError(f"Error sending cron job message: {response}")

        # Create the analysis prompt for the bot
        first_message_in_thread = f"""
You're running a regularly scheduled analysis called `{job_name}`.
On a regular cadence (cron string: {cron_job.cron}) a thread will
be posted to slack with the title: "{cron_job.thread}", and the
analysis will be included as a reply to that thread.

That analysis is described below. As this is a regularly scheduled
analysis that is initiated by a schedule, not a user, do not respond
conversationally unless there are follow up questions; respond as if
this is a report.

Analysis description:
{cron_job.question}
        """.strip()

        # Mark thread as cron job initiated
        await self._mark_thread_as_cron_job_initiated(channel_id, ts, job_name)

        # Handle the new thread with the analysis prompt
        await self._handle_new_thread(
            bot_user_id,
            channel_id,
            ts,
            bot_user_id,
            ts,
            first_message_in_thread,
            collapse_thinking_steps=True,
            is_automated_message=True,
        )

    def validate_cron_expression(self, cron_expr: str) -> bool:
        """Validate if a cron expression is valid."""
        try:
            croniter(cron_expr, datetime.now())
            return True
        except Exception:
            return False

    def get_default_sleep_seconds(self) -> float:
        """Get default sleep time when no jobs are ready to execute."""
        return 60.0  # Check for new jobs every 60 seconds

    def calculate_sleep_until_execution(self, execution_time: datetime) -> float:
        """Calculate seconds to sleep until job execution.

        Args:
            execution_time: When the job should be executed

        Returns:
            Number of seconds to sleep (minimum 0)
        """
        sleep_seconds = (execution_time - datetime.now()).total_seconds()
        return max(sleep_seconds, 0)

    async def verify_job_still_exists(self, job_name: str) -> bool:
        """Verify job hasn't been deleted since we scheduled it.

        Args:
            job_name: Name of the cron job to verify

        Returns:
            True if job still exists, False otherwise
        """
        current_jobs = await self.csbot_client.get_cron_jobs()
        return job_name in current_jobs

    async def _get_bot_user_id(self) -> str | None:
        """Get the bot's own user ID to avoid self-replies."""
        try:
            response = await self.client.auth_test()
            return response["user_id"]
        except Exception as e:
            self.logger.warning(f"Could not get bot user ID: {e}")
            return "unknown"

    async def _mark_thread_as_cron_job_initiated(
        self, channel_id: str, thread_ts: str, cron_job_name: str
    ) -> None:
        """Mark a thread as having been initiated by a cron job."""
        await self.kv_store.set(
            "cron_job_initiated_thread",
            f"{channel_id}:{thread_ts}",
            cron_job_name,
            90 * 24 * 60 * 60,  # 90 days
        )
        self.logger.info(
            f"Marked thread as cron-job-initiated: {channel_id}:{thread_ts} by {cron_job_name}"
        )
