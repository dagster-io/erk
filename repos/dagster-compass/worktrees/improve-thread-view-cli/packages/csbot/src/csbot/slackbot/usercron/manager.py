"""User cron job management and execution for Slack bots."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from textwrap import dedent
from typing import TYPE_CHECKING, Any, cast

from csbot.local_context_store.github.utils import extract_pr_number_from_url
from csbot.slackbot.exceptions import BotUserFacingError
from csbot.slackbot.slackbot_models import PrInfo
from csbot.slackbot.webapp.security import create_governance_link

if TYPE_CHECKING:
    from slack_sdk.web.async_client import AsyncWebClient

    from csbot.agents.protocol import AsyncAgent
    from csbot.csbot_client.csbot_client import CSBotClient
    from csbot.slackbot.bot_server.bot_server import BotKey
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance
    from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
    from csbot.slackbot.slackbot_github_monitor import SlackbotGithubMonitor
    from csbot.slackbot.storage.interface import SlackbotInstanceStorage


class UserCronJobManager:
    """Manages user-defined cron job scheduling and execution for the Compass bot."""

    def __init__(
        self,
        bot: "CompassChannelBaseBotInstance",
        csbot_client: "CSBotClient",
        kv_store: "SlackbotInstanceStorage",
        slack_client: "AsyncWebClient",
        github_monitor: "SlackbotGithubMonitor",
        analytics_store: "SlackbotAnalyticsStore",
        bot_key: "BotKey",
        agent: "AsyncAgent",
        logger: logging.Logger,
        channel_name: str,
        governance_alerts_channel: str,
        create_attribution: Callable,
        handle_new_thread: Callable,
    ):
        self.bot = bot
        self.csbot_client = csbot_client
        self.kv_store = kv_store
        self.slack_client = slack_client
        self.github_monitor = github_monitor
        self.analytics_store = analytics_store
        self.bot_key = bot_key
        self.agent = agent
        self.logger = logger
        self.channel_name = channel_name
        self.governance_alerts_channel = governance_alerts_channel
        self.create_attribution = create_attribution
        self.handle_new_thread = handle_new_thread

        self.cron_executor = UserCronJobExecutor(bot)

    async def get_thread_cron_job_name(self, channel: str, thread_ts: str) -> str | None:
        """Get the cron job name that initiated this thread, if any."""
        result = await self.kv_store.get("cron_job_initiated_thread", f"{channel}:{thread_ts}")
        return result

    async def get_cron_tools(
        self,
        channel: str,
        message_ts: str | None,
        user: str | None,
    ) -> dict[str, Callable[..., Awaitable[Any]]]:
        """Get cron-related tools for the agent."""
        tools: dict[str, Callable[..., Awaitable[Any]]] = {}

        if message_ts is not None:

            async def list_cron_jobs():
                cron_jobs = await self.csbot_client.get_cron_jobs()
                return cron_jobs

            list_cron_jobs.__doc__ = self.csbot_client.get_cron_jobs.__doc__
            tools["list_cron_jobs"] = list_cron_jobs

            async def add_or_edit_cron_job(
                cron_job_name: str,
                cron_string: str,
                question: str,
                thread: str,
                did_you_call_list_cron_jobs: bool,
                is_edit: bool,
            ):
                if not did_you_call_list_cron_jobs:
                    return {
                        "error": "You must call list_cron_jobs before calling add_or_edit_cron_job."
                    }

                attribution = await self.create_attribution(
                    "Last updated", user, message_ts, channel
                )

                result = await self.csbot_client.add_cron_job(
                    cron_job_name, cron_string, question, thread, attribution
                )

                pr_number = extract_pr_number_from_url(result.cron_job_review_url)
                await self.bot.github_monitor.mark_pr(
                    self.bot.github_config.repo_name,
                    pr_number,
                    PrInfo(type="scheduled_analysis_created", bot_id=self.bot.key.to_bot_id()),
                )

                await asyncio.sleep(0.5)
                await self.github_monitor.tick()
                governance_url = create_governance_link(
                    self.bot,
                    pr_number,
                    user_id=cast("str", user),
                )
                await self.bot._post_governance_request_announcement(
                    channel=channel,
                    title=cron_job_name,
                    governance_url=governance_url,
                    fallback_url=result.cron_job_review_url,
                    action_id="github_monitor_view_cronjob",
                    action_value=str(pr_number),
                    emoji="🗓️",
                    request_type_label="scheduled analysis",
                )
                return result

            add_or_edit_cron_job.__doc__ = cast(
                "str", self.csbot_client.add_cron_job.__doc__
            ) + dedent("""
            Args:
                cron_job_name: The name of the cron job to add or edit
                cron_string: The cron string to use for the cron job
                question: The question to ask the cron job
                thread: The thread to use for the cron job
                did_you_call_list_cron_jobs: Whether you called list_cron_jobs first to get the existing cron jobs
                is_edit: True if editing an existing cron job, False if adding a new one
            Note: you must call list_cron_jobs first to get the existing cron jobs before calling this tool.
            """)

            tools["add_or_edit_cron_job"] = add_or_edit_cron_job

            async def delete_cron_job(cron_job_name: str):
                attribution = await self.create_attribution("Deleted", user, message_ts, channel)

                result = await self.csbot_client.delete_cron_job(cron_job_name, attribution)
                await asyncio.sleep(0.5)
                await self.github_monitor.tick()
                return result

            delete_cron_job.__doc__ = self.csbot_client.delete_cron_job.__doc__
            tools["delete_cron_job"] = delete_cron_job

        return tools

    async def handle_cron_command(self, channel: str, message_content: str):
        """Handle !cron commands."""
        cron_name = message_content.split("!cron ")[1].strip()
        await self.cron_executor.execute_cron_job(channel, cron_name)


class UserCronJobExecutor:
    """Handles the execution of individual user-defined cron jobs."""

    def __init__(self, bot: "CompassChannelBaseBotInstance"):
        self.bot = bot

    async def execute_cron_job(self, channel: str, cron_name: str):
        """Execute a specific cron job."""
        cron_jobs = await self.bot.csbot_client.get_cron_jobs()
        if cron_name not in cron_jobs:
            available_jobs = list(cron_jobs.keys())
            if not available_jobs:
                message = f"Unknown scheduled analysis: `{cron_name}`\n\nNo scheduled analyses are currently configured."
            else:
                jobs_list = "\n".join(f"• `{job}`" for job in available_jobs)
                message = f"Unknown scheduled analysis: `{cron_name}`\n\nAvailable scheduled analyses:\n{jobs_list}\n\nUsage: `!cron <analysis_name>`"

            raise BotUserFacingError(
                source_bot=self.bot,
                title="Unknown Scheduled Analysis",
                message=message,
                error_type="user_input",
            )
        cron_job = cron_jobs[cron_name]

        bot_user_id = await self.get_bot_user_id()
        if bot_user_id is None:
            raise ValueError("Bot user ID not found")

        response = await self.bot.client.chat_postMessage(
            channel=channel,
            text=cron_job.thread,
        )
        ts = response.get("ts")
        if not response.get("ok") or not ts:
            raise ValueError(f"Error sending daily insight: {response}")

        first_message_in_thread = f"""
You're running a regularly scheduled analysis called `{cron_name}`.
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

        await self.mark_thread_as_cron_job_initiated(channel, ts, cron_name)

        await self.bot._handle_new_thread(
            bot_user_id=bot_user_id,
            channel=channel,
            thread_ts=ts,
            user=bot_user_id,
            message_ts=ts,
            message_content=first_message_in_thread,
            collapse_thinking_steps=True,
            is_automated_message=True,
        )

    async def mark_thread_as_cron_job_initiated(
        self, channel: str, thread_ts: str, cron_job_name: str
    ):
        """Mark a thread as having been initiated by a cron job."""
        await self.bot.kv_store.set(
            "cron_job_initiated_thread",
            f"{channel}:{thread_ts}",
            cron_job_name,
            90 * 24 * 60 * 60,  # 90 days
        )
        self.bot.logger.info(
            f"Marked thread as cron-job-initiated: {channel}:{thread_ts} by {cron_job_name}"
        )

    async def get_bot_user_id(self) -> str | None:
        """Get the bot's own user ID to avoid self-replies."""
        try:
            response = await self.bot.client.auth_test()
            return response["user_id"]
        except Exception as e:
            self.bot.logger.warning(f"Could not get bot user ID: {e}")
            return None
