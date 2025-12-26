from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import BotKey
    from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig


class BotInstanceLoader(ABC):
    """Protocol for loading bot instance configurations from different sources."""

    @abstractmethod
    async def load_bot_instances(
        self, bot_keys: Sequence["BotKey"] | None = None
    ) -> dict[str, "CompassBotSingleChannelConfig"]:
        """Load bot instances from the configured source.

        Args:
            bot_keys: Optional list of bot keys to filter by. If None, load all instances.
        """
        pass
