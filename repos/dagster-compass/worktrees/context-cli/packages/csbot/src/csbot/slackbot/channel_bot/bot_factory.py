import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import structlog
from slack_sdk.web.async_client import AsyncWebClient

from csbot.agents.factory import create_agent_from_config
from csbot.contextengine.context_engine import ContextEngine
from csbot.contextengine.contextstore_protocol import (
    ContextStoreProject,
)
from csbot.contextengine.loader import load_project_from_tree
from csbot.contextengine.read_only import ProspectorReadOnlyContextEngine
from csbot.csbot_client.csbot_client import CSBotClient
from csbot.csbot_client.csbot_profile import ProjectProfile
from csbot.local_context_store.github.config import GithubConfig
from csbot.local_context_store.local_context_store import LocalBackedGithubContextStoreManager
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.bot import (
    BotTypeCombined,
    BotTypeGovernance,
    BotTypeQA,
    CompassChannelCombinedCommunityProspectorBotInstance,
    CompassChannelCombinedNormalBotInstance,
    CompassChannelCombinedProspectorBotInstance,
    CompassChannelGovernanceBotInstance,
    CompassChannelQACommunityBotInstance,
    CompassChannelQANormalBotInstance,
)
from csbot.slackbot.flags import is_dagster_community_mode
from csbot.slackbot.issue_creator.github import GithubIssueCreator
from csbot.slackbot.slackbot_analytics import (
    SlackbotAnalyticsStore,
)
from csbot.slackbot.slackbot_core import AIConfig, CompassBotServerConfig
from csbot.slackbot.slackbot_github_monitor import GithubMonitor, SlackbotGithubMonitor
from csbot.slackbot.tasks.tasks.types import BotBackgroundTaskManager
from csbot.utils.misc import normalize_channel_name

if TYPE_CHECKING:
    from csbot.csbot_client.csbot_profile import ConnectionProfile
    from csbot.local_context_store.local_context_store import LocalContextStore
    from csbot.slackbot.channel_bot import CompassChannelBaseBotInstance
    from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
    from csbot.slackbot.storage.interface import SlackbotStorage


def load_project_from_config(local_context_store: "LocalContextStore") -> ContextStoreProject:
    """Load project configuration from GitHub repository."""
    with local_context_store.latest_file_tree() as tree:
        return load_project_from_tree(tree)


class CompassChannelBotInstanceFactory:
    @staticmethod
    def construct(
        key: BotKey,
        logger: logging.Logger,
        github_config: GithubConfig,
        local_context_store: "LocalContextStore",
        bot_config: "CompassBotSingleChannelConfig",
        client: AsyncWebClient,
        background_task_manager: BotBackgroundTaskManager,
        ai_config: AIConfig,
        storage: "SlackbotStorage",
        governance_alerts_channel: str,
        server_config: CompassBotServerConfig,
        prospector_icp: str | None = None,
    ) -> "CompassChannelBaseBotInstance":
        """Builds a CompassChannelBotInstance from the given parameters."""

        # Share the kv_store amongst all bots in the same instance by
        # keying off the governance bot key
        governance_bot_key = BotKey.from_channel_name(key.team_id, governance_alerts_channel)
        kv_store = storage.for_instance(governance_bot_key.to_bot_id())
        analytics_store = SlackbotAnalyticsStore(kv_store.sql_conn_factory)

        # Create agent based on AI configuration
        agent = create_agent_from_config(ai_config)

        # Load project configuration to create the profile
        profile = ProjectProfile(connections=bot_config.connections)
        if not bot_config.contextstore_github_repo:
            raise ValueError(
                "Cannot create bot instance: contextstore_github_repo is not configured for this organization"
            )
        data_request_github_creds = GithubConfig(
            auth_source=github_config.auth_source,
            repo_name=bot_config.contextstore_github_repo,
        )

        slackbot_github_monitor = SlackbotGithubMonitor(
            channel_name=governance_alerts_channel,
            github_monitor=GithubMonitor(
                github_config=github_config,
                logger=logger,
            ),
            kv_store=kv_store,
            client=client,
            logger=logger,
            agent=agent,
        )

        mutable_manager = LocalBackedGithubContextStoreManager(
            local_context_store, slackbot_github_monitor
        )

        if bot_config.data_documentation_repos:
            from csbot.local_context_store.composite_context_store_provider import (
                CompositeContextStoreManager,
            )
            from csbot.local_context_store.local_context_store import create_local_context_store

            auth_source = github_config.auth_source
            shared_dataset_stores = [
                LocalBackedGithubContextStoreManager(
                    create_local_context_store(
                        GithubConfig(auth_source=auth_source, repo_name=doc_repo)
                    ),
                    slackbot_github_monitor,
                )
                for doc_repo in bot_config.data_documentation_repos
            ]

            context_store_manager = CompositeContextStoreManager(
                mutable_manager, shared_dataset_stores
            )
        else:
            context_store_manager = mutable_manager

        contextstore = ContextEngine(
            context_store_manager,
            agent,
            normalize_channel_name(bot_config.channel_name),
            available_connection_names=set(bot_config.connections.keys()),
            github_config=github_config,
        )

        bot_type = BotTypeQA()
        bot_class = CompassChannelQANormalBotInstance
        if is_dagster_community_mode(bot_config):
            bot_class = CompassChannelQACommunityBotInstance
        elif (
            normalize_channel_name(bot_config.channel_name)
            == normalize_channel_name(bot_config.governance_alerts_channel)
            or bot_config.is_prospector  # Bots in prospector mode must be of type combined.
        ):
            bot_type = BotTypeCombined(governed_bot_keys=set([key]))

            bot_class = CompassChannelCombinedNormalBotInstance
            if bot_config.is_prospector or bot_config.is_community_prospector:
                if bot_config.is_community_prospector:
                    bot_class = CompassChannelCombinedCommunityProspectorBotInstance
                else:
                    bot_class = CompassChannelCombinedProspectorBotInstance

                # Use ProspectorReadOnlyContextEngine for prospector organizations
                contextstore = ProspectorReadOnlyContextEngine(
                    context_store_manager,
                    agent,
                    normalize_channel_name(bot_config.channel_name),
                    available_connection_names=set(bot_config.connections.keys()),
                    icp=prospector_icp or "",
                )

        csbot_client = CSBotClient(
            contextstore,
            profile,
        )

        instance = bot_class(
            key=key,
            logger=logger,
            github_config=github_config,
            local_context_store=local_context_store,
            client=client,
            bot_background_task_manager=background_task_manager,
            ai_config=ai_config,
            kv_store=kv_store,
            governance_alerts_channel=governance_alerts_channel,
            analytics_store=analytics_store,
            profile=profile,
            csbot_client=csbot_client,
            data_request_github_creds=data_request_github_creds,
            slackbot_github_monitor=slackbot_github_monitor,
            scaffold_branch_enabled=bot_config.scaffold_branch_enabled,
            bot_config=bot_config,
            bot_type=bot_type,
            server_config=server_config,
            storage=storage,
            issue_creator=GithubIssueCreator(github_config),
        )
        slackbot_github_monitor.bot_instance = instance
        return instance

    @staticmethod
    def construct_governance_bots(
        storage: "SlackbotStorage",
        qa_bots: "list[CompassChannelBaseBotInstance]",
        selected_governance_channels: set[str] | None,
        server_config: CompassBotServerConfig,
    ) -> "list[CompassChannelBaseBotInstance]":
        """Builds a CompassChannelBotInstance from the given parameters."""
        if selected_governance_channels is not None:
            selected_governance_channels = set(
                normalize_channel_name(channel) for channel in selected_governance_channels
            )
        # First, let's group bots by their governance channel name
        bots: dict[str, set[CompassChannelBaseBotInstance]] = defaultdict(set)
        for bot in qa_bots:
            if not isinstance(bot.bot_type, BotTypeQA):
                raise ValueError(f"Bot {bot.key.to_bot_id()} is not a QA bot")
            if selected_governance_channels is not None:
                if (
                    normalize_channel_name(bot.bot_config.governance_alerts_channel)
                    not in selected_governance_channels
                ):
                    continue
            bots[bot.bot_config.governance_alerts_channel].add(bot)
        # Next, validate that every bot within the same governance channel
        # points to the same git repo
        for governance_channel, qa_bots_for_governance_channel in bots.items():
            qa_bots_for_governance_channel = list(qa_bots_for_governance_channel)
            first_bot = qa_bots_for_governance_channel[0]
            for bot in qa_bots_for_governance_channel:
                if (
                    bot.bot_config.contextstore_github_repo
                    != first_bot.bot_config.contextstore_github_repo
                ):
                    raise ValueError(
                        f"Bots {bot.key.to_bot_id()} and {first_bot.key.to_bot_id()} have different contextstore github repos but share a governance channel {governance_channel}"
                    )
                # check github config
                if bot.github_config != first_bot.github_config:
                    raise ValueError(
                        f"Bots {bot.key.to_bot_id()} and {first_bot.key.to_bot_id()} have different github configs but share a governance channel {governance_channel}"
                    )

        # OK, now let's create our governance bots
        rv: list[CompassChannelBaseBotInstance] = []
        for governance_channel, qa_bots_for_governance_channel in bots.items():
            qa_bots_for_governance_channel = list(qa_bots_for_governance_channel)
            first_bot = qa_bots_for_governance_channel[0]
            # Create it in any of the teams, it doesn't matter (see canonicalize_bot_key() for why)
            bot_key = BotKey.from_channel_name(first_bot.key.team_id, governance_channel)
            kv_store = storage.for_instance(bot_key.to_bot_id())
            analytics_store = SlackbotAnalyticsStore(kv_store.sql_conn_factory)

            # Create agent based on AI configuration
            agent = create_agent_from_config(first_bot.ai_config)

            local_context_store = first_bot.local_context_store

            # Aggregate all of the bot_config.connections across all of our qa bots
            connections: dict[str, ConnectionProfile] = {}
            for bot in qa_bots_for_governance_channel:
                for connection_name, connection in bot.bot_config.connections.items():
                    if connection_name in connections:
                        if connections[connection_name] != connection:
                            raise ValueError(
                                f"Two connections named {connection_name} with different profiles... this should never happen!"
                            )
                    connections[connection_name] = connection

            logger = structlog.get_logger(
                f"governance_bot:{bot_key.team_id}:#{bot_key.channel_name}"
            )

            slackbot_github_monitor = SlackbotGithubMonitor(
                channel_name=governance_channel,
                github_monitor=GithubMonitor(
                    github_config=first_bot.github_config,
                    logger=logger,
                ),
                kv_store=kv_store,
                client=first_bot.client,
                logger=logger,
                agent=agent,
            )

            context_store_manager = LocalBackedGithubContextStoreManager(
                local_context_store, slackbot_github_monitor
            )

            # Use ProspectorReadOnlyContextEngine for prospector organizations, ContextEngine otherwise
            # Governance bots use read-only if any of the QA bots are prospector
            if first_bot.bot_config.is_prospector:
                # ICP is now loaded directly from bot_config
                icp = first_bot.bot_config.icp_text or ""
                contextstore = ProspectorReadOnlyContextEngine(
                    context_store_manager,
                    agent,
                    None,
                    available_connection_names=set(connections.keys()),
                    icp=icp,
                )
            else:
                contextstore = ContextEngine(
                    context_store_manager,
                    agent,
                    None,
                    available_connection_names=set(connections.keys()),
                    github_config=first_bot.github_config,
                )

            profile = ProjectProfile(connections=connections)
            data_request_github_creds = first_bot.github_config

            csbot_client = CSBotClient(
                contextstore,
                profile,
            )

            instance = CompassChannelGovernanceBotInstance(
                key=bot_key,
                logger=logger,
                github_config=first_bot.github_config,
                local_context_store=local_context_store,
                client=first_bot.client,
                bot_background_task_manager=first_bot.bot_background_task_manager,
                ai_config=first_bot.ai_config,
                kv_store=kv_store,
                governance_alerts_channel=governance_channel,
                analytics_store=analytics_store,
                profile=profile,
                csbot_client=csbot_client,
                data_request_github_creds=data_request_github_creds,
                slackbot_github_monitor=slackbot_github_monitor,
                scaffold_branch_enabled=False,
                bot_config=first_bot.bot_config,  # TODO: this is a bit janky.
                bot_type=BotTypeGovernance(
                    governed_bot_keys=set(bot.key for bot in qa_bots_for_governance_channel)
                ),
                server_config=server_config,
                storage=storage,
                issue_creator=GithubIssueCreator(first_bot.github_config),
            )
            slackbot_github_monitor.bot_instance = instance
            rv.append(instance)
        return rv
