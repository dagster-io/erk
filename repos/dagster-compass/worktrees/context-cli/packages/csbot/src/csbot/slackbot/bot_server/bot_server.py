"""
CompassBotServer class for handling multi-channel bot coordination.

This module contains the CompassBotServer class which manages multiple
CompassChannelBot instances and routes Slack events to the appropriate bot.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import structlog
from ddtrace.trace import tracer
from slack_sdk.web.async_client import AsyncWebClient
from temporalio.client import Client as TemporalClient
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.service import TLSConfig

from csbot.slackbot.exceptions import BotUserFacingError, UserFacingError
from csbot.slackbot.segment_analytics import init_segment_analytics
from csbot.slackbot.slack_types import SlackSlashCommandPayload
from csbot.slackbot.slackbot_core import TemporalCloudConfig
from csbot.slackbot.slackbot_secrets import LocalFileSecretStore, RenderSecretStore, SecretStore
from csbot.slackbot.storage.factory import create_connection_factory
from csbot.slackbot.storage.interface import PlanLimits, SlackbotStorage
from csbot.slackbot.tasks import BackgroundTaskManager
from csbot.slackbot.tasks.sync_stripe_subscriptions import SyncStripeSubscriptions
from csbot.slackbot.usage_tracking import UsageTracker
from csbot.slackbot.utils import send_ephemeral_message
from csbot.stripe.stripe_client import StripeClient
from csbot.utils.misc import normalize_channel_name
from csbot.utils.tracing import try_set_root_tags

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_reconciler import CompassBotReconciler
    from csbot.slackbot.channel_bot import CompassChannelBaseBotInstance
    from csbot.slackbot.slack_types import SlackInteractivePayload
    from csbot.slackbot.slackbot_core import CompassBotServerConfig


class BotKey(NamedTuple):
    """A key identifying a specific bot instance by team and channel."""

    team_id: str
    channel_name: str

    @classmethod
    def from_channel_name(cls, team_id: str, channel_name: str):
        return cls(team_id, normalize_channel_name(channel_name))

    def to_bot_id(self) -> str:
        return f"{self.team_id}-{self.channel_name}"

    @staticmethod
    def from_bot_id(bot_id: str) -> "BotKey":
        team_id, channel_name = bot_id.split("-", 1)
        return BotKey.from_channel_name(team_id, channel_name)


MAX_USER_MESSAGE_LENGTH = 2048


class CompassBotServer:
    """
    Base class for bot servers.

    This class is responsible for managing the bot instances and routing events to the appropriate bot.
    """

    def __init__(
        self,
        config: "CompassBotServerConfig",
        sql_conn_factory,
        bot_manager: "CompassBotReconciler",
        temporal_client: TemporalClient,
        stripe_client: StripeClient | None = None,
        skip_background_tasks: bool = False,
    ):
        self.config = config
        self.sql_conn_factory = sql_conn_factory
        self.temporal_client = temporal_client
        self.stripe_client = stripe_client
        self.channel_id_to_name: dict[str, str] = {}
        self.channel_id_to_team_id: dict[str, str] = {}
        self.logger = structlog.get_logger("CompassBotServer")
        self.bot_manager = bot_manager
        self.bot_manager.set_bot_server(self)

        self.github_auth_source = config.github.get_auth_source()

        # Initialize Segment analytics if configured
        if config.segment_write_key:
            segment_write_key = config.segment_write_key.get_secret_value()
            init_segment_analytics(
                write_key=segment_write_key, orgs_enabled=config.segment_orgs_enabled, debug=False
            )
            extra_message = (
                "for all orgs"
                if config.segment_orgs_enabled is None
                else f"for orgs: {', '.join(config.segment_orgs_enabled)}"
            )
            self.logger.info(f"Segment analytics initialized {extra_message}")
        else:
            init_segment_analytics(write_key=None)
            self.logger.debug("Segment analytics not configured")

        # Add default background tasks if not skipping
        if not skip_background_tasks and self.stripe_client:
            sync_task = SyncStripeSubscriptions(
                stripe_client=self.stripe_client,
                usage_tracker=UsageTracker(self.sql_conn_factory),
                plan_manager=self.bot_manager.storage,
                organizations_provider=self.bot_manager.storage.list_organizations,
                interval_hours=1,
            )
            self.background_task_manager = BackgroundTaskManager([sync_task], self.logger)
        else:
            self.background_task_manager = BackgroundTaskManager([], self.logger)

    async def start_background_tasks(self) -> None:
        """Start all background tasks."""
        await self.background_task_manager.start_all()

    async def stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        await self.background_task_manager.stop_all()

    @property
    def bots(self) -> dict[BotKey, "CompassChannelBaseBotInstance"]:
        return self.bot_manager.get_active_bots()

    def get_bots_for_channel(self, channel_id: str) -> list["CompassChannelBaseBotInstance"]:
        """
        Get all bot instances that have access to the specified channel.

        This method provides channel-centric bot lookup functionality to replace the
        problematic team_id-based bot matching that fails in Enterprise Grid shared
        channel scenarios.

        Args:
            channel_id: Slack channel ID to find bots for

        Returns:
            List of bot instances that can access the channel (empty if none found)
        """
        # Check if channel name is cached
        if channel_id not in self.channel_id_to_name:
            return []

        channel_name = self.channel_id_to_name[channel_id]
        return [bot for bot in self.bots.values() if bot.key.channel_name == channel_name]

    async def get_channel_name(self, team_id: str, channel_id: str) -> str:
        if channel_id in self.channel_id_to_name:
            return self.channel_id_to_name[channel_id]

        if self.config.is_local:
            client = self.get_local_client_for_team(team_id)
        else:
            client = self.get_global_slack_client()
        channel_info = await client.conversations_info(
            channel=channel_id,
        )
        channel_name = channel_info.get("channel", {}).get("name")
        if not channel_name:
            raise ValueError(f"Channel {channel_id} not found")
        self.channel_id_to_name[channel_id] = channel_name
        return channel_name

    async def get_bot_key(self, channel_id: str, team_id: str) -> BotKey:
        """Get the bot dictionary key (team_id, channel_name) for a channel."""
        channel_name = await self.get_channel_name(team_id, channel_id)
        return BotKey.from_channel_name(team_id, channel_name)

    async def update_channel_mapping(
        self, team_id: str, channel_id: str, channel_name: str | None
    ) -> None:
        """Update the channel mapping for a channel."""
        if channel_name is None:
            channel_name = await self.get_channel_name(team_id, channel_id)
        await self.bot_manager.storage.set_channel_mapping(
            team_id, normalize_channel_name(channel_name), channel_id
        )

    async def get_channel_id_from_name(self, team_id: str, channel_name: str) -> str | None:
        """Get the channel ID for a channel name."""
        return await self.bot_manager.storage.get_channel_id_by_name(
            team_id, normalize_channel_name(channel_name)
        )

    @tracer.wrap()
    async def handle_event(self, event: dict, event_type: str, team_id: str) -> None:
        """Handle a Slack event by routing it to the appropriate bot instance."""

        # Log incoming event
        channel = event.get("channel", "unknown")
        user = event.get("user", "unknown")
        thread_ts = event.get("thread_ts") or event.get("ts", "unknown")

        channel_id = event.get("channel")
        if isinstance(channel_id, dict):
            channel_id = channel_id.get("id")
        if not channel_id:
            self.logger.warning("No channel found in event")
            return

        try_set_root_tags(
            {
                "user": user,
                "thread_ts": thread_ts,
                "channel_id": channel_id,
                "team_id": team_id,
            }
        )

        self.logger.info(
            f"EVENT: {event_type} | team_id: {team_id} | channel:{channel} | user:{user} | thread:{thread_ts}",
            event_type=event_type,
            team_id=team_id,
            channel=channel,
            user=user,
            thread_ts=thread_ts,
        )

        await self.update_channel_mapping(team_id, channel_id, None)

        try:
            bot_key = await self.get_bot_key(channel_id, team_id)
            bot_key = await self.canonicalize_bot_key(bot_key)
            bot = self.bots.get(bot_key)
            if not bot:
                self.logger.warning(f"No bot found for key {bot_key.to_bot_id()}")
                return

            channel_name = bot_key.channel_name
            try_set_root_tags(
                {
                    "channel": channel_name,
                    "organization": bot.bot_config.organization_name,
                }
            )
            await bot.associate_channel_id(channel_id, channel_name)

            if event_type == "app_mention":
                await bot.handle_app_mention(self, event)
            elif event_type == "message":
                await bot.handle_message(self, event)
            elif event_type == "member_joined_channel":
                await bot.handle_member_joined_channel(self, event)
            elif event_type == "shared_channel_invite_accepted":
                await bot.handle_slack_connect_accepted(event)
        except (UserFacingError, BotUserFacingError):
            # Let IUserFacingError bubble up to web app for rich error display
            raise
        except Exception as e:
            self.logger.error(f"Error getting bot for channel {channel_id}: {e}", exc_info=True)
            return

    @tracer.wrap()
    async def handle_interactive(self, payload: "SlackInteractivePayload", team_id: str) -> None:
        """Handle an interactive Slack message by routing it to the appropriate bot instance."""
        channel_id = payload.get("channel", {}).get("id")
        origin_channel_id = payload.get("container", {}).get("channel_id")

        # Validate channel ID consistency
        if (
            channel_id is not None
            and origin_channel_id is not None
            and channel_id != origin_channel_id
        ):
            self.logger.warning(f"Channel ID mismatch: {channel_id} != {origin_channel_id}")
            return

        message_channel_id = channel_id or origin_channel_id

        try_set_root_tags(
            {
                "channel_id": channel_id,
                "team_id": team_id,
            }
        )

        if message_channel_id:
            await self.update_channel_mapping(team_id, message_channel_id, None)

        # Check if we have an encoded callback ID with channel name (for modal interactions)
        encoded_channel_name = None
        if not message_channel_id:
            raw_callback_id = payload.get("view", {}).get("callback_id")
            if raw_callback_id and "|" in raw_callback_id:
                encoded_channel_name = raw_callback_id.split("|", 1)[0]

        if not message_channel_id and not encoded_channel_name:
            self.logger.warning("No channel ID found in interactive payload")
            return

        try_set_root_tags({"channel": encoded_channel_name})

        try:
            if message_channel_id:
                bot_key = await self.get_bot_key(message_channel_id, team_id)
            elif encoded_channel_name:
                # Use encoded channel name to find the bot
                bot_key = BotKey.from_channel_name(team_id, encoded_channel_name)
            else:
                # This shouldn't happen due to the check above, but be safe
                self.logger.warning("No channel information available")
                return
            bot_key = await self.canonicalize_bot_key(bot_key)
            bot = self.bots.get(bot_key)
            if not bot:
                self.logger.warning(f"No bot found for key {bot_key.to_bot_id()}")
                return

            # Try admin intera
            # ctive handlers first, then GitHub monitor handlers
            if await bot.handle_interactive_message(self, payload):
                return

            await bot.github_monitor.handle_interactive_message(payload)
        except Exception as e:
            self.logger.error(
                f"Error getting bot for channel {message_channel_id}: {e}", exc_info=True
            )
            return

    def get_bot_for_team(self, team_id: str) -> "CompassChannelBaseBotInstance":
        if not self.bots:
            raise ValueError("No bots available to query channel information")

        # Find any bot from the same team to make the API call
        team_bots = [bot for bot in self.bots.values() if bot.key.team_id == team_id]
        if not team_bots:
            raise UserFacingError.bot_configuration_error(team_id=team_id)

        # Use the first available bot from the team
        any_bot = team_bots[0]
        return any_bot

    @cache
    def get_local_client_for_team(self, team_id: str) -> AsyncWebClient:
        any_bot = self.get_bot_for_team(team_id)
        return any_bot.client

    @cache
    def get_global_slack_client(self) -> AsyncWebClient:
        if self.config.slack_admin_token is None:
            raise ValueError("Need slack admin token to configure global slack client")
        return AsyncWebClient(token=self.config.slack_admin_token.get_secret_value())

    async def canonicalize_bot_key(self, bot_key: BotKey) -> BotKey:
        """
        This is a bit of a temporary hack. In the Slack Connect case, bots will belong to
        multiple teams. So we take a source bot_key, which will have the correct channel and
        some arbitrary team_id, and return a BotKey with the canonical team_id that the bot
        was registered to.

        In the future, we should rekey the database to work off of a single channel_id.
        """
        candidate_keys = set(self.bots.keys())
        for candidate_key in candidate_keys:
            if normalize_channel_name(candidate_key.channel_name) == normalize_channel_name(
                bot_key.channel_name
            ):
                if candidate_key.team_id == bot_key.team_id:
                    # identical keys. no need to check channel ids.
                    return candidate_key

                candidate_key_channel_id, bot_key_channel_id = await asyncio.gather(
                    self.get_channel_id_from_name(
                        candidate_key.team_id, candidate_key.channel_name
                    ),
                    self.get_channel_id_from_name(bot_key.team_id, bot_key.channel_name),
                )
                if (
                    candidate_key_channel_id
                    and bot_key_channel_id
                    and candidate_key_channel_id[1:] == bot_key_channel_id[1:]
                ):
                    return candidate_key
        return bot_key

    @tracer.wrap()
    async def handle_slash_command(self, payload: SlackSlashCommandPayload, team_id: str) -> None:
        """Handle a Slack slash command by routing it to the appropriate bot instance."""
        channel_id = payload.get("channel_id")
        if not channel_id:
            self.logger.warning("No channel ID found in slash command payload")
            return

        try_set_root_tags({"team_id": team_id, "channel_id": channel_id})

        try:
            bot_key = await self.get_bot_key(channel_id, team_id)
            bot = self.bots.get(bot_key)
            if not bot:
                self.logger.warning(f"No bot found for key {bot_key.to_bot_id()}")

                # Reply with ephemeral message to the user
                await send_ephemeral_message(
                    payload["response_url"],
                    "❌ This command can only be run from a Compass governance channel.",
                )

                return

            await bot.handle_slash_command(self, payload)
        except Exception as e:
            self.logger.error(f"Error getting bot for channel {channel_id}: {e}", exc_info=True)
            return

    async def get_product_id_for_organization(
        self, organization_id: int, stripe_subscription_id: str
    ) -> str:
        """Get the product ID for an organization based on its Stripe subscription ID."""
        if not stripe_subscription_id:
            raise ValueError("Organization has no Stripe subscription")

        if not self.stripe_client:
            raise ValueError("Stripe client not available")

        subscription = await asyncio.to_thread(
            self.stripe_client.get_subscription_details, stripe_subscription_id
        )

        if not subscription or subscription.get("status") != "active":
            raise ValueError(
                f"Organization '{organization_id}' (ID: {organization_id}) has inactive subscription {stripe_subscription_id}"
            )

        # Extract product ID from subscription
        product_id = None
        items_data = subscription.get("items", {}).get("data", [])
        if items_data:
            first_item = items_data[0]
            price_info = first_item.get("price", {})
            product_id = price_info.get("product")

        if not product_id:
            raise ValueError(
                f"No product ID found in subscription {stripe_subscription_id} for organization '{organization_id}' (ID: {organization_id})"
            )
        return product_id

    async def get_plan_limits_from_cache_or_fallback(
        self, organization_id: int, stripe_subscription_id: str
    ) -> PlanLimits:
        """Get the plan limits for an organization based on its organization ID and Stripe subscription ID.
        Attempts to get the plan limits from the cache first, and if not found, gets the product ID from the Stripe subscription and then gets the plan limits from the Stripe product."""
        cached_plan_limits = await self.bot_manager.storage.get_plan_limits(organization_id)
        if cached_plan_limits:
            return cached_plan_limits
        else:
            if not self.stripe_client:
                raise ValueError("Stripe client not available")
            product_id = await self.get_product_id_for_organization(
                organization_id, stripe_subscription_id
            )
            return await asyncio.to_thread(self.stripe_client.get_product_plan_limits, product_id)

    async def get_plan_limits_from_cache_or_bail(self, organization_id: int) -> PlanLimits | None:
        """Get the plan limits for an organization based on its organization ID and Stripe subscription ID.
        Attempts to get the plan limits from the cache first, if not found returns None."""
        return await self.bot_manager.storage.get_plan_limits(organization_id)


async def create_stripe_client(config: "CompassBotServerConfig") -> StripeClient | None:
    stripe_config = config.stripe
    if not stripe_config.token:
        return None
    stripe_client = StripeClient(stripe_config.token.get_secret_value())
    assert stripe_config.free_product_id is not None
    assert stripe_config.starter_product_id is not None
    assert stripe_config.team_product_id is not None
    await asyncio.to_thread(
        stripe_client.startup_assertions,
        prices_to_validate=[
            stripe_config.free_product_id,
            stripe_config.starter_product_id,
            stripe_config.team_product_id,
        ],
    )
    return stripe_client


async def create_temporal_client(config: "CompassBotServerConfig"):
    # Create Temporal client
    temporal_config = config.temporal
    connection_string = temporal_config.connection_string
    logger = structlog.get_logger("CompassBotServer")
    logger.info(f"Connecting to Temporal at {connection_string}")

    # Configure connection based on whether it's Cloud or OSS
    # Use pydantic_data_converter for Pydantic v2 support
    converter = pydantic_data_converter

    if isinstance(temporal_config, TemporalCloudConfig):
        logger.info(f"Using Temporal Cloud configuration (namespace: {temporal_config.namespace})")
        temporal_client = await TemporalClient.connect(
            connection_string,
            namespace=temporal_config.namespace,
            tls=TLSConfig(
                client_cert=None,
                client_private_key=None,
            ),
            api_key=temporal_config.api_key.get_secret_value(),
            data_converter=converter,
        )
    else:
        logger.info("Using Temporal OSS configuration")
        temporal_client = await TemporalClient.connect(
            connection_string,
            namespace=temporal_config.namespace,
            data_converter=converter,
        )

    return temporal_client


async def create_bot_reconciler(
    config: "CompassBotServerConfig",
    secret_store: SecretStore,
    config_root: Path,
    storage: SlackbotStorage,
    temporal_client: TemporalClient,
    skip_background_tasks: bool,
):
    """Creates and starts a bot reconciler, which will discover and start bot instances
    as they are added or removed."""
    from csbot.slackbot.bot_server.bot_reconciler import CompassBotReconciler, create_bot_loader

    bot_loader = create_bot_loader(storage, secret_store, config_root)
    return CompassBotReconciler(
        config,
        secret_store,
        storage,
        bot_loader,
        temporal_client,
        skip_background_tasks,
    )


def create_secret_store(server_config: "CompassBotServerConfig") -> SecretStore:
    return (
        RenderSecretStore(
            service_id=server_config.secret_store.render_service_id,
            api_key=server_config.secret_store.render_api_key.get_secret_value(),
        )
        if server_config.secret_store
        else LocalFileSecretStore()
    )


async def create_storage(server_config: "CompassBotServerConfig") -> SlackbotStorage:
    from csbot.slackbot.storage.factory import create_storage as create_storage_from_factory

    sql_conn_factory = await asyncio.to_thread(
        create_connection_factory,
        server_config.db_config,
    )
    return create_storage_from_factory(sql_conn_factory, server_config.db_config.kek_config)


@asynccontextmanager
async def create_reconciler_and_bot_server(
    config: "CompassBotServerConfig",
    secret_store: SecretStore,
    config_root: Path,
    storage: SlackbotStorage,
    sql_conn_factory,
    skip_background_tasks: bool,
) -> AsyncGenerator["CompassBotServer"]:
    """Creates and starts a bot reconciler, which will discover and start bot instances
    as they are added or removed."""
    temporal_client = await create_temporal_client(config)
    reconciler = await create_bot_reconciler(
        config,
        secret_store,
        config_root,
        storage,
        temporal_client,
        skip_background_tasks,
    )
    stripe_client = await create_stripe_client(config)

    _periodic_check_task = None
    server = None
    try:
        server = CompassBotServer(
            config=config,
            sql_conn_factory=sql_conn_factory,
            bot_manager=reconciler,
            temporal_client=temporal_client,
            stripe_client=stripe_client,
            skip_background_tasks=skip_background_tasks,
        )
        reconciler.set_bot_server(server)
        await reconciler.discover_and_update_bots()

        # Start periodic checking task
        _periodic_check_task = asyncio.create_task(reconciler._periodic_check())
        reconciler.logger.info(
            f"Started dynamic bot manager with {len(reconciler.active_bots)} bot instances"
        )

        # Start background tasks
        await server.start_background_tasks()

        yield server
    finally:
        # Stop background tasks
        if server:
            await server.stop_background_tasks()

        if _periodic_check_task:
            _periodic_check_task.cancel()
            try:
                await _periodic_check_task
            except asyncio.CancelledError:
                pass
        reconciler.logger.info("Stopped dynamic bot manager")
