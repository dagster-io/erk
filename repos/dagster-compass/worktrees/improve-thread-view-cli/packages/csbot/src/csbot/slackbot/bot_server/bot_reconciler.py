"""Dynamic bot instance management for periodic discovery and lifecycle management."""

import asyncio
import logging
import os
import sys
from collections.abc import Coroutine, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import structlog
from ddtrace.trace import tracer
from temporalio.client import Client as TemporalClient

from csbot.config.bot_instance_loader_protocol import BotInstanceLoader
from csbot.config.database_instance_loader import DatabaseBotInstanceLoader
from csbot.local_context_store.github.config import GithubAuthSource
from csbot.local_context_store.local_context_store import create_local_context_store
from csbot.slackbot.bot_server.bot_server import BotKey, CompassBotServer
from csbot.slackbot.channel_bot import CompassChannelBaseBotInstance
from csbot.slackbot.channel_bot.bot import BotTypeQA
from csbot.slackbot.channel_bot.bot_factory import CompassChannelBotInstanceFactory
from csbot.slackbot.slack_client import create_slack_client
from csbot.slackbot.slackbot_core import (
    get_jinja_template_context,
    get_jinja_template_context_with_secret_store,
)
from csbot.slackbot.slackbot_secrets import SecretStore
from csbot.slackbot.storage.interface import SlackbotStorage
from csbot.utils.misc import normalize_channel_name

if TYPE_CHECKING:
    from csbot.slackbot.slackbot_core import (
        CompassBotServerConfig,
        CompassBotSingleChannelConfig,
    )

logger = logging.getLogger(__name__)


def _get_bot_reconciler_interval() -> float:
    """Get bot reconciler interval in seconds from env var."""
    env_value = os.getenv("BOT_RECONCILER_INTERVAL_SECONDS", "30")
    try:
        interval = float(env_value)
        if interval <= 0:
            logger.warning(
                f"Invalid BOT_RECONCILER_INTERVAL_SECONDS value '{env_value}' (must be > 0), using default 30"
            )
            return 30.0
        return interval
    except ValueError:
        logger.warning(
            f"Invalid BOT_RECONCILER_INTERVAL_SECONDS value '{env_value}' (not a number), using default 30"
        )
        return 30.0


BOT_RECONCILER_INTERVAL = _get_bot_reconciler_interval()

BATCHED_GATHER_DEFAULT_BATCH_SIZE = 4

T = TypeVar("T")


async def gather_batched[T](
    *tasks: asyncio.Future[T] | Coroutine[Any, Any, T],
    batch_size: int = BATCHED_GATHER_DEFAULT_BATCH_SIZE,
) -> list[T]:
    """Gathers tasks in batches of the given size, to prevent overwhelming the event loop."""
    results = []
    for i in range(0, len(tasks), batch_size):
        batch_results = await asyncio.gather(*tasks[i : i + batch_size])
        results.extend(batch_results)
    return results


def create_bot_loader(
    storage: SlackbotStorage, secret_store: SecretStore, config_root: Path
) -> BotInstanceLoader:
    """Create a bot instance loader based on the current configuration."""

    # Create the same Jinja template context used for YAML config
    template_context = get_jinja_template_context(config_root)

    return DatabaseBotInstanceLoader(
        storage,
        template_context,
        lambda org_id: get_jinja_template_context_with_secret_store(
            config_root, secret_store, org_id
        ),
    )


class CompassBotReconciler:
    """Manages dynamic discovery and lifecycle of CompassChannelBotInstances.

    Periodically queries the BotInstanceLoader, populated from config, and
    starts and stops bot instances as needed.
    """

    def __init__(
        self,
        config: "CompassBotServerConfig",
        secret_store: SecretStore,
        storage: SlackbotStorage,
        bot_loader: BotInstanceLoader,
        temporal_client: TemporalClient,
        skip_background_tasks: bool,
    ):
        self.config = config
        self.secret_store = secret_store
        self.storage = storage
        self.skip_background_tasks = skip_background_tasks

        self.active_bots: dict[BotKey, CompassChannelBaseBotInstance] = {}

        self.logger = structlog.get_logger("BotReconciler")
        self.check_interval = BOT_RECONCILER_INTERVAL  # Check for new bots periodically

        # Create bot loader once during initialization

        self.temporal_client = temporal_client
        self._periodic_check_task: asyncio.Task | None = None
        self.bot_loader = bot_loader
        self.initial_sync_complete = False

    async def _periodic_check(self) -> None:
        """Periodically check for new bot instances."""

        while True:
            try:
                await asyncio.sleep(self.check_interval)
                self.logger.debug("Checking for new bot instances")
                with tracer.trace("bot_reconciler.discover_and_update_bots"):
                    await self.discover_and_update_bots()
                self.logger.debug("Bot check complete")
            except asyncio.CancelledError:
                self.logger.info("Periodic bot check task cancelled")
                break

    async def discover_and_update_bots_for_keys(self, bot_keys: Sequence[BotKey]) -> None:
        """Discover/update bot instances only for the specified bot keys and their governance channels.

        This is a faster, targeted version of discover_and_update_bots that only fetches
        and processes data for the specified bot keys and their governance channels.
        """
        await self._discover_and_update_bots_for_keys(bot_keys)

    async def discover_and_update_bots(self) -> None:
        """Discover new bot instances and update the active bots."""
        await self._discover_and_update_bots_for_keys(None)
        self.initial_sync_complete = True

    async def _discover_and_update_bots_for_keys(self, bot_keys: Sequence[BotKey] | None) -> None:
        """Shared implementation for discovering and updating bots.

        Args:
            bot_keys: Optional list of bot keys to filter by. If None, discover all bots.
        """

        async def load_current_bot_configs():
            # When filtering by bot_keys, we need to load both the requested bots AND their governance bots
            if bot_keys:
                # First, load the requested bot instances
                initial_configs = await self.bot_loader.load_bot_instances(bot_keys)

                # Convert to bot_key -> bot_config mapping
                return {
                    BotKey.from_channel_name(
                        bot_config.team_id, bot_config.channel_name
                    ): bot_config
                    for _, bot_config in initial_configs.items()
                }
            else:
                # No filtering - load all instances
                return {
                    BotKey.from_channel_name(
                        bot_config.team_id, bot_config.channel_name
                    ): bot_config
                    for _, bot_config in (await self.bot_loader.load_bot_instances(None)).items()
                }

        initial_active_bot_keys = set(self.active_bots.keys())

        with tracer.trace("bot_reconciler.load_bot_configs") as span:
            current_bot_configs = await load_current_bot_configs()
            span.set_tag("bot_config_count", len(current_bot_configs))

        self.logger.debug(f"Current bot configs: {list(current_bot_configs.keys())}")
        self.logger.debug(f"Active bots: {list(self.active_bots.keys())}")

        with tracer.trace("bot_reconciler.compute_bot_keys"):
            next_keys = set(current_bot_configs.keys())
            # Add in governance bot keys too
            self_governed_keys = set(
                bot_key
                for bot_key, bot_config in current_bot_configs.items()
                if normalize_channel_name(bot_config.governance_alerts_channel)
                == normalize_channel_name(bot_key.channel_name)
            )
            next_governance_keys = (
                set(
                    BotKey.from_channel_name(
                        bot_config.team_id, bot_config.governance_alerts_channel
                    )
                    for _, bot_config in current_bot_configs.items()
                    if bot_config.governance_alerts_channel
                )
                - self_governed_keys
            )
            next_keys.update(next_governance_keys - self_governed_keys)

            # When filtering by bot_keys, only consider active bots in the filtered scope
            if bot_keys:
                # Build set of all bot keys that are in scope:
                # 1. Bots whose key is in the filter
                # 2. Bots that are in next_keys or next_governance_keys (newly discovered)
                filter_keys = set(bot_keys)
                scoped_active_bot_keys = set(
                    bot_key
                    for bot_key in initial_active_bot_keys
                    if bot_key in filter_keys
                    or bot_key in next_keys
                    or bot_key in next_governance_keys
                )
            else:
                # No filter - all active bots are in scope
                scoped_active_bot_keys = initial_active_bot_keys

            # Find new bots (present in config but not in active_bots)
            new_bot_keys = next_keys - scoped_active_bot_keys

            # Find removed bots (present in active_bots but not in config) - only within scope
            removed_bot_keys = scoped_active_bot_keys - next_keys

            same_bot_keys = scoped_active_bot_keys & next_keys

        restarted_bots = set[CompassChannelBaseBotInstance]()

        auth_source = self.config.github.get_auth_source()

        start_tasks = []
        if new_bot_keys:
            self.logger.info(
                "Discovered new bot instances:"
                f" {', '.join(key.to_bot_id() for key in new_bot_keys)}"
            )
            for key in new_bot_keys:
                if key in next_governance_keys:
                    continue
                start_tasks.append(
                    self._start_bot_instance(key, current_bot_configs[key], auth_source)
                )

        restart_tasks = []
        for key in same_bot_keys:
            if key in next_governance_keys:
                continue
            if self.active_bots[key].bot_config.should_restart(current_bot_configs[key]):
                self.logger.info(
                    f"Updating bot instance {key.to_bot_id()}, with changed connections"
                )
                restart_tasks.append(
                    self._restart_bot_instance(key, current_bot_configs[key], auth_source)
                )

        with tracer.trace("bot_reconciler.start_and_restart_bots") as span:
            span.set_tag("new_bot_count", len(start_tasks))
            span.set_tag("restart_bot_count", len(restart_tasks))
            restarted_bots.update(await gather_batched(*start_tasks, *restart_tasks))

        stop_tasks = []
        if removed_bot_keys:
            self.logger.info(
                f"Removing inactive bot instances:"
                f" {', '.join(key.to_bot_id() for key in removed_bot_keys)}"
            )
            for key in removed_bot_keys:
                stop_tasks.append(self._stop_bot_instance(key))

        with tracer.trace("bot_reconciler.stop_bots") as span:
            span.set_tag("stop_bot_count", len(stop_tasks))
            await gather_batched(*stop_tasks)

        # Reconciler will have removed any stale governance bots above, but we still need to
        # create or update the new ones.
        with tracer.trace("bot_reconciler.construct_governance_bots"):
            governance_bots = await asyncio.to_thread(
                CompassChannelBotInstanceFactory.construct_governance_bots,
                storage=self.storage,
                qa_bots=[
                    bot for bot in self.active_bots.values() if isinstance(bot.bot_type, BotTypeQA)
                ],
                selected_governance_channels=set(
                    bot.governance_alerts_channel
                    for bot in restarted_bots
                    if isinstance(bot.bot_type, BotTypeQA)
                ),
                server_config=self.config,
            )

        with tracer.trace("bot_reconciler.reconcile_governance_bots") as span:
            span.set_tag("governance_bot_count", len(governance_bots))
            await gather_batched(
                *[
                    self._stop_bot_instance(bot.key)
                    for bot in governance_bots
                    if bot.key in self.active_bots
                ]
            )
            await gather_batched(
                *[self._add_and_start_bot_instance(bot.key, bot) for bot in governance_bots]
            )

    async def _restart_bot_instance(
        self,
        key: BotKey,
        bot_config: "CompassBotSingleChannelConfig",
        auth_source: GithubAuthSource,
    ) -> "CompassChannelBaseBotInstance":
        await self._stop_bot_instance(key)
        return await self._start_bot_instance(key, bot_config, auth_source)

    async def _start_bot_instance(
        self,
        key: BotKey,
        bot_config: "CompassBotSingleChannelConfig",
        auth_source: GithubAuthSource,
    ) -> "CompassChannelBaseBotInstance":
        from csbot.local_context_store.github.config import GithubConfig
        from csbot.slackbot.tasks.tasks.temporal import TemporalBackgroundTaskManager

        """Start a new bot instance for the given channel."""
        if not bot_config.contextstore_github_repo:
            raise ValueError(
                f"Cannot start bot instance {key.to_bot_id()}: "
                "contextstore_github_repo is not configured for this organization"
            )
        github_config = GithubConfig(
            auth_source=auth_source,
            repo_name=bot_config.contextstore_github_repo,
        )
        local_context_store = create_local_context_store(github_config)
        # Use per-instance token if available, otherwise fall back to server-level token
        bot_token = self.config.compass_bot_token.get_secret_value()
        slack_client = create_slack_client(token=bot_token)

        # ICP is now loaded directly from bot_config for prospector instances
        prospector_icp = bot_config.icp_text if bot_config.is_prospector else None

        background_task_manager = TemporalBackgroundTaskManager(
            self.temporal_client,
            self.config.thread_health_inspector_config.start_delay_seconds
            if self.config.thread_health_inspector_config
            else sys.maxsize,
        )
        bot = await asyncio.to_thread(
            CompassChannelBotInstanceFactory.construct,
            key=key,
            logger=structlog.get_logger(f"bot:{key.team_id}:#{key.channel_name}"),
            github_config=github_config,
            local_context_store=local_context_store,
            bot_config=bot_config,
            client=slack_client,
            background_task_manager=background_task_manager,
            ai_config=self.config.ai_config,
            storage=self.storage,
            governance_alerts_channel=bot_config.governance_alerts_channel,
            server_config=self.config,
            prospector_icp=prospector_icp,
        )
        await self._add_and_start_bot_instance(key, bot)
        return bot

    async def _add_and_start_bot_instance(
        self, key: BotKey, bot: "CompassChannelBaseBotInstance"
    ) -> None:
        if not self.skip_background_tasks:
            await bot.start_background_tasks()
        self.active_bots[key] = bot

        self.logger.info(
            f"Started bot instance {key.to_bot_id()} with {len(bot.bot_config.connections)} connections"
        )

    async def _stop_bot_instance(self, key: BotKey) -> None:
        """Stop and clean up a bot instance."""
        bot = self.active_bots.pop(key, None)
        if bot:
            if not self.skip_background_tasks:
                await bot.stop_background_tasks()

        self.logger.info(f"Stopped bot instance {key.to_bot_id()}")

    def get_active_bots(self) -> dict[BotKey, "CompassChannelBaseBotInstance"]:
        """Get the current active bots dictionary."""
        return self.active_bots.copy()

    def set_bot_server(self, bot_server: CompassBotServer) -> None:
        """Set the bot server for the bot manager."""
        self.bot_server = bot_server
