"""Database-based bot instance loader with Jinja2 template processing."""

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import BotKey
    from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig

from csbot.slackbot.storage.interface import SlackbotStorage

from .bot_instance_loader_protocol import BotInstanceLoader


class DatabaseBotInstanceLoader(BotInstanceLoader):
    """Loads bot instances from database with Jinja2 template processing."""

    def __init__(
        self,
        storage: SlackbotStorage,
        template_context: dict[str, Any],
        get_template_context_for_org: Callable[[int], dict[str, Any]],
    ):
        """Initialize with storage and template context."""
        self._storage = storage
        self._template_context = template_context
        self._get_template_context_for_org = get_template_context_for_org

    async def load_bot_instances(
        self, bot_keys: Sequence["BotKey"] | None = None
    ) -> dict[str, "CompassBotSingleChannelConfig"]:
        """Load bot instances from database.

        Args:
            bot_keys: Optional list of bot keys to filter by. If None, load all instances.
        """
        return await self._storage.load_bot_instances(
            self._template_context, self._get_template_context_for_org, bot_keys
        )
