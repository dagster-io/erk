"""GitHub monitor background task for CompassChannelBotInstance."""

import logging
import os
from typing import TYPE_CHECKING

from csbot.slackbot.channel_bot.tasks.bot_instance_task import BotInstanceBackgroundTask

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance

logger = logging.getLogger(__name__)


def _get_github_monitor_seconds() -> float:
    """Get GitHub monitor interval in seconds from env var."""
    env_value = os.getenv("GITHUB_MONITOR_SLEEP_SECONDS", "60")
    try:
        sleep_seconds = float(env_value)
        if sleep_seconds <= 0:
            logger.warning(
                f"Invalid GITHUB_MONITOR_SLEEP_SECONDS value '{env_value}' (must be > 0), using default 60"
            )
            return 60.0
        return sleep_seconds
    except ValueError:
        logger.warning(
            f"Invalid GITHUB_MONITOR_SLEEP_SECONDS value '{env_value}' (not a number), using default 60"
        )
        return 60.0


GITHUB_MONITOR_SLEEP_SECONDS = _get_github_monitor_seconds()


class GitHubMonitorTask(BotInstanceBackgroundTask):
    """Manages the GitHub monitor background task."""

    def __init__(self, bot: "CompassChannelBaseBotInstance"):
        super().__init__(bot)
        # Execute immediately on init, then sleep
        self._execute_on_init = True

    async def execute_tick(self) -> None:
        """Check GitHub PR status and send updates."""
        await self.bot.github_monitor.tick()

    def get_sleep_seconds(self) -> float:
        """Check every ~60 seconds (or use GITHUB_MONITOR_SLEEP_SECONDS env var to override)."""
        return self._jitter_seconds(GITHUB_MONITOR_SLEEP_SECONDS, 10)
