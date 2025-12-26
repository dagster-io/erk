"""Onboarding step handlers for the Compass Bot onboarding flow.

This module contains all the individual step handlers that execute specific parts
of the onboarding process, along with their result dataclasses.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddtrace.trace import tracer
from slack_sdk.errors import SlackApiError

from csbot.agents.factory import create_agent_from_config
from csbot.local_context_store.github.api import (
    create_repository,
    initialize_contextstore_repository,
)
from csbot.local_context_store.github.config import GithubAuthSource
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.channel_bot.personalization import get_company_info_from_domain
from csbot.slackbot.logs.step_logging import StepContext, StepEventType
from csbot.slackbot.slack_client import create_slack_client
from csbot.slackbot.slack_utils import (
    create_channel,
    create_slack_connect_channel,
    create_slack_team,
    generate_team_domain,
    generate_urlsafe_team_name,
    get_all_channels,
    get_bot_user_id,
    grant_bonus_answers,
    invite_bot_to_channel,
    invite_user_to_slack_team,
)
from csbot.slackbot.slackbot_analytics import (
    AnalyticsEventType,
    SlackbotAnalyticsStore,
    log_analytics_event_unified,
)
from csbot.slackbot.storage.onboarding_context import OnboardingContext
from csbot.slackbot.storage.onboarding_exceptions import (
    BillingSetupError,
    BotInstanceCreationError,
    BotSetupError,
    ChannelSetupError,
    ContextstoreCreationError,
    OrganizationCreationError,
    SlackConnectError,
    SlackTeamCreationError,
)
from csbot.slackbot.storage.onboarding_state import (
    OnboardingState,
    OnboardingStep,
)
from csbot.slackbot.welcome import send_compass_pinned_welcome_message
from csbot.stripe.stripe_utils import update_plan_limits_from_product
from csbot.utils.sync_to_async import sync_to_async

if TYPE_CHECKING:
    from csbot.agents.protocol import AsyncAgent
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


# Dataclasses for onboarding step results
@dataclass
class SlackTeamResult:
    team_id: str
    team_domain: str
    team_name: str


@dataclass
class ChannelSetupResult:
    general_channel_id: str


@dataclass
class CompassChannelsResult:
    compass_channel_id: str
    compass_channel_name: str
    governance_channel_id: str
    governance_channel_name: str


@dataclass
class ContextstoreResult:
    contextstore_repo_name: str
    repo_result: dict


@dataclass
class BillingResult:
    stripe_customer_id: str
    stripe_subscription_id: str
    product_id: str


@dataclass
class OrganizationResult:
    organization_id: int
    analytics_store: "SlackbotAnalyticsStore"


async def create_slack_team_step(
    ctx: OnboardingContext,
    admin_token: str,
    organization: str,
    email: str,
    bot_server: "CompassBotServer",
) -> SlackTeamResult:
    """Create Slack team and return SlackTeamResult."""
    team_domain = generate_team_domain(organization)
    team_name = generate_urlsafe_team_name(organization)

    bot_server.logger.info(
        f"Starting onboarding for organization: {organization} (domain: {team_domain})"
    )

    try:
        with tracer.trace("onboarding.create_slack_team"):
            slack_team_result = await create_slack_team(admin_token, organization, team_domain)

        if not slack_team_result["success"]:
            error = slack_team_result.get("error", "unknown")

            # Log onboarding abandonment analytics event
            try:
                analytics_store = SlackbotAnalyticsStore(bot_server.sql_conn_factory)
                await log_analytics_event_unified(
                    analytics_store=analytics_store,
                    event_type=AnalyticsEventType.ONBOARDING_ABANDONED,
                    bot_id=f"onboarding-{organization}",
                    channel_id=None,
                    user_id=None,
                    thread_ts=None,
                    message_ts=None,
                    metadata={
                        "organization_name": organization,
                        "abandonment_stage": "slack_team_creation",
                        "error_reason": error,
                        "team_domain": team_domain,
                        "user_email": email,
                    },
                    user_email=email,
                    organization_name=organization,
                )
            except Exception as analytics_error:
                bot_server.logger.error(f"Failed to log onboarding abandonment: {analytics_error}")

            if error == "domain_taken":
                bot_server.logger.error(
                    f"API Error: Slack domain already taken\n"
                    f"  Organization: {organization}\n"
                    f"  Team Domain: {team_domain}\n"
                    f"  API Error: {error}\n"
                    f"  Full Response: {slack_team_result}"
                )
                raise SlackTeamCreationError(
                    message=f"Slack domain '{team_domain}' is already taken for organization '{organization}'. Full API response: {slack_team_result}",
                    user_facing_message=f"Slack domain already taken: {team_domain}",
                )
            else:
                bot_server.logger.error(
                    f"API Error: Failed to create Slack team\n"
                    f"  Organization: {organization}\n"
                    f"  Team Domain: {team_domain}\n"
                    f"  API Error: {error}\n"
                    f"  Full Response: {slack_team_result}"
                )
                raise SlackTeamCreationError(
                    message=f"Failed to create Slack team: {error}. Full API response: {slack_team_result}",
                    user_facing_message=f"Failed to create Slack team: {error}",
                )

        team_id = slack_team_result["team_id"]
        bot_server.logger.info(f"Successfully created Slack team: {organization} (ID: {team_id})")

        await ctx.mark_step_completed(
            OnboardingStep.SLACK_TEAM_CREATED,
            slack_team_id=team_id,
            team_domain=team_domain,
            team_name=team_name,
        )

        return SlackTeamResult(team_id=team_id, team_domain=team_domain, team_name=team_name)

    except SlackTeamCreationError:
        raise
    except Exception as e:
        raise SlackTeamCreationError(
            message=f"Unexpected error creating Slack team: {e}",
            user_facing_message="Account creation failed. Please contact support.",
        ) from e


async def list_channels_step(
    ctx: OnboardingContext,
    org_bot_token: str,
    team_id: str,
    organization: str,
    bot_server: "CompassBotServer",
) -> ChannelSetupResult:
    """List channels and find general channel. Returns ChannelSetupResult."""
    try:
        # List all channels from the newly created team
        bot_server.logger.info("Listing channels in newly created team")
        channels_result = await get_all_channels(org_bot_token, team_id)

        if not channels_result["success"]:
            error = channels_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to list channels\n"
                f"  Team ID: {team_id}\n"
                f"  Organization: {organization}\n"
                f"  API Error: {error}\n"
                f"  Full Response: {channels_result}"
            )
            raise ChannelSetupError(
                message=f"Failed to list channels: {error}. Full API response: {channels_result}",
                user_facing_message=f"Failed to list channels: {error}",
            )

        # Find the general channel
        general_channel_id = None
        channel_names = channels_result["channel_names"]
        all_channel_ids = channels_result["channel_ids"].split(",")

        bot_server.logger.info(f"Found {len(channel_names)} channels: {', '.join(channel_names)}")

        for i, channel_name in enumerate(channel_names):
            if channel_name == "general":
                general_channel_id = all_channel_ids[i]
                break

        if not general_channel_id:
            bot_server.logger.error(f"No general channel found for {organization} team {team_id}")
            raise ChannelSetupError(
                message=f"No general channel found for team {team_id}",
                user_facing_message="No general channel found",
            )

        await ctx.mark_step_completed(
            OnboardingStep.CHANNELS_LISTED, general_channel_id=general_channel_id
        )

        return ChannelSetupResult(general_channel_id=general_channel_id)

    except ChannelSetupError:
        raise
    except Exception as e:
        raise ChannelSetupError(
            message=f"Unexpected error listing channels: {e}",
            user_facing_message="Failed to list channels. Please contact support.",
        ) from e


async def invite_admins_step(
    ctx: OnboardingContext,
    admin_token: str,
    team_id: str,
    general_channel_id: str,
    dagster_admins_to_invite: list[str],
    bot_server: "CompassBotServer",
) -> None:
    """Invite admins to general channel."""
    try:
        for admin_email in dagster_admins_to_invite:
            bot_server.logger.info(
                f"Inviting Dagster admins to #general channel: {dagster_admins_to_invite}"
            )
            with tracer.trace("onboarding.invite_user_to_slack_team"):
                invite_result = await invite_user_to_slack_team(
                    admin_token, team_id, admin_email, general_channel_id
                )

            if not invite_result["success"]:
                error = invite_result.get("error", "unknown")
                bot_server.logger.error(
                    f"API Error: Failed to invite admin to general channel\n"
                    f"  Team ID: {team_id}\n"
                    f"  Channel ID: {general_channel_id}\n"
                    f"  Admin Email: {admin_email}\n"
                    f"  API Error: {error}\n"
                    f"  Full Response: {invite_result}"
                )
                raise ChannelSetupError(
                    message=f"Failed to invite {admin_email} to general channel: {error}. Full API response: {invite_result}",
                    user_facing_message=f"Failed to invite {admin_email} to general channel: {error}",
                )

            bot_server.logger.info(f"Successfully invited {admin_email} to #general")

        await ctx.mark_step_completed(OnboardingStep.ADMINS_INVITED)

    except ChannelSetupError:
        raise
    except Exception as e:
        raise ChannelSetupError(
            message=f"Unexpected error inviting admins: {e}",
            user_facing_message="Failed to invite admins. Please contact support.",
        ) from e


async def create_compass_channel_step(
    ctx: OnboardingContext,
    admin_token: str,
    slack_team_result: SlackTeamResult,
    bot_server: "CompassBotServer",
) -> None:
    """Create public compass channel."""
    try:
        # Create the public compass channel
        compass_channel_name = f"{slack_team_result.team_name}-compass"
        bot_server.logger.info(f"Creating public compass channel: #{compass_channel_name}")

        with tracer.trace("onboarding.create_channel") as span:
            span.set_tag("channel_name", compass_channel_name)
            compass_result = await create_channel(
                admin_token, slack_team_result.team_id, compass_channel_name, is_private=False
            )

        if not compass_result["success"]:
            error = compass_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to create compass channel\n"
                f"  Channel Name: {compass_channel_name}\n"
                f"  Team ID: {slack_team_result.team_id}\n"
                f"  Is Private: False\n"
                f"  API Error: {error}\n"
                f"  Full Response: {compass_result}"
            )
            raise ChannelSetupError(
                message=f"Failed to create compass channel: {error}. Full API response: {compass_result}",
                user_facing_message=f"Failed to create compass channel: {error}",
            )

        compass_channel_id = compass_result["channel_id"]
        bot_server.logger.info(f"Successfully created compass channel (ID: {compass_channel_id})")

        await ctx.mark_step_completed(
            OnboardingStep.COMPASS_CHANNEL_CREATED,
            compass_channel_id=compass_channel_id,
            compass_channel_name=compass_channel_name,
        )

    except ChannelSetupError:
        raise
    except Exception as e:
        raise ChannelSetupError(
            message=f"Unexpected error creating compass channel: {e}",
            user_facing_message="Failed to create compass channel. Please contact support.",
        ) from e


async def create_governance_channel_step(
    ctx: OnboardingContext,
    admin_token: str,
    slack_team_result: SlackTeamResult,
    bot_server: "CompassBotServer",
) -> CompassChannelsResult:
    """Create private governance channel. Returns CompassChannelsResult."""
    try:
        # Create the governance channel
        governance_channel_name = f"{slack_team_result.team_name}-compass-governance"
        bot_server.logger.info(f"Creating private governance channel: #{governance_channel_name}")

        with tracer.trace("onboarding.create_channel") as span:
            span.set_tag("channel_name", governance_channel_name)
            governance_result = await create_channel(
                admin_token, slack_team_result.team_id, governance_channel_name, is_private=True
            )

        if not governance_result["success"]:
            error = governance_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to create governance channel\n"
                f"  Channel Name: {governance_channel_name}\n"
                f"  Team ID: {slack_team_result.team_id}\n"
                f"  Is Private: True\n"
                f"  API Error: {error}\n"
                f"  Full Response: {governance_result}"
            )
            raise ChannelSetupError(
                message=f"Failed to create governance channel: {error}. Full API response: {governance_result}",
                user_facing_message=f"Failed to create governance channel: {error}",
            )

        governance_channel_id = governance_result["channel_id"]
        bot_server.logger.info(
            f"Successfully created governance channel (ID: {governance_channel_id})"
        )

        await ctx.mark_step_completed(
            OnboardingStep.GOVERNANCE_CHANNEL_CREATED,
            governance_channel_id=governance_channel_id,
            governance_channel_name=governance_channel_name,
        )

        # Get compass channel info from state (already created in previous step)
        assert ctx.state.compass_channel_id is not None
        assert ctx.state.compass_channel_name is not None

        return CompassChannelsResult(
            compass_channel_id=ctx.state.compass_channel_id,
            compass_channel_name=ctx.state.compass_channel_name,
            governance_channel_id=governance_channel_id,
            governance_channel_name=governance_channel_name,
        )

    except ChannelSetupError:
        raise
    except Exception as e:
        raise ChannelSetupError(
            message=f"Unexpected error creating governance channel: {e}",
            user_facing_message="Failed to create governance channel. Please contact support.",
        ) from e


async def retrieve_bot_ids_step(
    ctx: OnboardingContext,
    org_bot_token: str,
    compass_bot_token: str,
    bot_server: "CompassBotServer",
) -> None:
    """Retrieve bot user IDs."""
    try:
        # Get both bots' user IDs
        bot_server.logger.info("Retrieving bot user IDs for channel invitations")
        dev_tools_bot_auth_result = await get_bot_user_id(org_bot_token)
        if not dev_tools_bot_auth_result["success"]:
            error = dev_tools_bot_auth_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to get dev tools bot user ID\n"
                f"  Bot Type: dev_tools\n"
                f"  API Error: {error}\n"
                f"  Full Response: {dev_tools_bot_auth_result}"
            )
            raise BotSetupError(
                message=f"Failed to get dev tools bot user ID: {error}. Full API response: {dev_tools_bot_auth_result}",
                user_facing_message=f"Failed to get dev tools bot user ID: {error}",
            )

        compass_bot_auth_result = await get_bot_user_id(compass_bot_token)
        if not compass_bot_auth_result["success"]:
            error = compass_bot_auth_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to get compass bot user ID\n"
                f"  Bot Type: compass\n"
                f"  API Error: {error}\n"
                f"  Full Response: {compass_bot_auth_result}"
            )
            raise BotSetupError(
                message=f"Failed to get compass bot user ID: {error}. Full API response: {compass_bot_auth_result}",
                user_facing_message=f"Failed to get compass bot user ID: {error}",
            )

        dev_tools_bot_user_id = dev_tools_bot_auth_result["user_id"]
        compass_bot_user_id = compass_bot_auth_result["user_id"]
        bot_server.logger.info(
            f"Retrieved bot user IDs - Dev tools: {dev_tools_bot_user_id}, "
            f"Compass: {compass_bot_user_id}"
        )

        await ctx.mark_step_completed(
            OnboardingStep.BOT_IDS_RETRIEVED,
            dev_tools_bot_user_id=dev_tools_bot_user_id,
            compass_bot_user_id=compass_bot_user_id,
        )

    except BotSetupError:
        raise
    except Exception as e:
        raise BotSetupError(
            message=f"Unexpected error retrieving bot IDs: {e}",
            user_facing_message="Failed to retrieve bot IDs. Please contact support.",
        ) from e


async def invite_bots_to_compass_step(
    ctx: OnboardingContext,
    admin_token: str,
    compass_bot_token: str,
    compass_channels_result: CompassChannelsResult,
    bot_server: "CompassBotServer",
) -> None:
    """Invite both bots to compass channel and send welcome message."""
    try:
        # Get bot user IDs from state
        assert ctx.state.dev_tools_bot_user_id is not None
        assert ctx.state.compass_bot_user_id is not None
        dev_tools_bot_user_id = ctx.state.dev_tools_bot_user_id
        compass_bot_user_id = ctx.state.compass_bot_user_id

        bot_server.logger.info("Inviting bots to compass channel")

        # Invite dev tools bot to compass channel
        with tracer.trace("onboarding.invite_bot_to_channel") as span:
            span.set_tag("channel_id", compass_channels_result.compass_channel_id)
            span.set_tag("bot_user_id", dev_tools_bot_user_id)
            dev_tools_compass_invite_result = await invite_bot_to_channel(
                admin_token, compass_channels_result.compass_channel_id, dev_tools_bot_user_id
            )
        if not dev_tools_compass_invite_result["success"]:
            error = dev_tools_compass_invite_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to invite dev tools bot to compass channel\n"
                f"  Bot Type: dev_tools\n"
                f"  Channel ID: {compass_channels_result.compass_channel_id}\n"
                f"  Bot User ID: {dev_tools_bot_user_id}\n"
                f"  API Error: {error}\n"
                f"  Full Response: {dev_tools_compass_invite_result}"
            )
            raise BotSetupError(
                message=f"Failed to invite dev tools bot to compass channel: {error}. Full API response: {dev_tools_compass_invite_result}",
                user_facing_message=f"Failed to invite dev tools bot to compass channel: {error}",
            )

        # Invite compass bot to compass channel
        with tracer.trace("onboarding.invite_bot_to_channel") as span:
            span.set_tag("channel_id", compass_channels_result.compass_channel_id)
            span.set_tag("bot_user_id", compass_bot_user_id)
            compass_compass_invite_result = await invite_bot_to_channel(
                admin_token, compass_channels_result.compass_channel_id, compass_bot_user_id
            )
        if not compass_compass_invite_result["success"]:
            error = compass_compass_invite_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to invite compass bot to compass channel\n"
                f"  Bot Type: compass\n"
                f"  Channel ID: {compass_channels_result.compass_channel_id}\n"
                f"  Bot User ID: {compass_bot_user_id}\n"
                f"  API Error: {error}\n"
                f"  Full Response: {compass_compass_invite_result}"
            )
            raise BotSetupError(
                message=f"Failed to invite compass bot to compass channel: {error}. Full API response: {compass_compass_invite_result}",
                user_facing_message=f"Failed to invite compass bot to compass channel: {error}",
            )

        await ctx.mark_step_completed(OnboardingStep.BOTS_INVITED_TO_COMPASS)

        # Send welcome message to compass channel (non-blocking - log warning if it fails)
        try:
            async with StepContext(
                step=StepEventType.COMPASS_CHANNEL_WELCOME, bot=ctx.create_bot_adapter()
            ) as step_context:
                step_context.add_slack_event_metadata(
                    channel_id=compass_channels_result.compass_channel_id
                )
                client = create_slack_client(token=compass_bot_token)
                with tracer.trace("onboarding.send_compass_welcome_message"):
                    await send_compass_pinned_welcome_message(
                        client, compass_channels_result.compass_channel_id, bot_server.logger
                    )
        except SlackApiError:
            # don't fail onboarding if we can't send a slack message
            pass

    except BotSetupError:
        raise
    except Exception as e:
        raise BotSetupError(
            message=f"Unexpected error inviting bots to compass channel: {e}",
            user_facing_message="Failed to invite bots to compass channel. Please contact support.",
        ) from e


async def invite_bots_to_governance_step(
    ctx: OnboardingContext,
    admin_token: str,
    compass_channels_result: CompassChannelsResult,
    bot_server: "CompassBotServer",
) -> None:
    """Invite both bots to governance channel."""
    try:
        # Get bot user IDs from state
        assert ctx.state.dev_tools_bot_user_id is not None
        assert ctx.state.compass_bot_user_id is not None
        dev_tools_bot_user_id = ctx.state.dev_tools_bot_user_id
        compass_bot_user_id = ctx.state.compass_bot_user_id

        bot_server.logger.info("Inviting bots to governance channel")

        # Invite dev tools bot to governance channel
        with tracer.trace("onboarding.invite_bot_to_channel") as span:
            span.set_tag("channel_id", compass_channels_result.governance_channel_id)
            span.set_tag("bot_user_id", dev_tools_bot_user_id)
            dev_tools_governance_invite_result = await invite_bot_to_channel(
                admin_token, compass_channels_result.governance_channel_id, dev_tools_bot_user_id
            )
        if not dev_tools_governance_invite_result["success"]:
            error = dev_tools_governance_invite_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to invite dev tools bot to governance channel\n"
                f"  Bot Type: dev_tools\n"
                f"  Channel ID: {compass_channels_result.governance_channel_id}\n"
                f"  Bot User ID: {dev_tools_bot_user_id}\n"
                f"  API Error: {error}\n"
                f"  Full Response: {dev_tools_governance_invite_result}"
            )
            raise BotSetupError(
                message=f"Failed to invite dev tools bot to governance channel: {error}. Full API response: {dev_tools_governance_invite_result}",
                user_facing_message=f"Failed to invite dev tools bot to governance channel: {error}",
            )

        # Invite compass bot to governance channel
        with tracer.trace("onboarding.invite_bot_to_channel") as span:
            span.set_tag("channel_id", compass_channels_result.governance_channel_id)
            span.set_tag("bot_user_id", compass_bot_user_id)
            compass_governance_invite_result = await invite_bot_to_channel(
                admin_token, compass_channels_result.governance_channel_id, compass_bot_user_id
            )
        if not compass_governance_invite_result["success"]:
            error = compass_governance_invite_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to invite compass bot to governance channel\n"
                f"  Bot Type: compass\n"
                f"  Channel ID: {compass_channels_result.governance_channel_id}\n"
                f"  Bot User ID: {compass_bot_user_id}\n"
                f"  API Error: {error}\n"
                f"  Full Response: {compass_governance_invite_result}"
            )
            raise BotSetupError(
                message=f"Failed to invite compass bot to governance channel: {error}. Full API response: {compass_governance_invite_result}",
                user_facing_message=f"Failed to invite compass bot to governance channel: {error}",
            )

        await ctx.mark_step_completed(OnboardingStep.BOTS_INVITED_TO_GOVERNANCE)

    except BotSetupError:
        raise
    except Exception as e:
        raise BotSetupError(
            message=f"Unexpected error inviting bots to governance channel: {e}",
            user_facing_message="Failed to invite bots to governance channel. Please contact support.",
        ) from e


async def create_contextstore_repo(
    ctx: OnboardingContext,
    slack_team_result: SlackTeamResult,
    email: str,
    bot_server: "CompassBotServer",
) -> ContextstoreResult:
    """Create contextstore GitHub repository. Returns ContextstoreResult."""
    try:
        bot_server.logger.info(
            f"Creating contextstore repository for team: {slack_team_result.team_domain}"
        )

        with tracer.trace("onboarding.create_contextstore_repository"):
            repo_result = await create_contextstore_repository(
                bot_server.logger,
                create_agent_from_config(bot_server.config.ai_config),
                bot_server.github_auth_source,
                slack_team_result.team_name,
                user_email=email,
            )

        if not repo_result["success"]:
            error = repo_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to create contextstore repository\n"
                f"  Team Name: {slack_team_result.team_name}\n"
                f"  User Email: {email}\n"
                f"  API Error: {error}\n"
                f"  Full Response: {repo_result}"
            )
            raise ContextstoreCreationError(
                message=f"Failed to create contextstore repository: {error}. Full API response: {repo_result}",
                user_facing_message=f"Failed to create contextstore repository: {error}",
            )

        contextstore_repo_name = repo_result["repo_name"]
        bot_server.logger.info(
            f"Successfully created contextstore repository: {contextstore_repo_name}"
        )

        await ctx.mark_step_completed(
            OnboardingStep.CONTEXTSTORE_REPO_CREATED,
            contextstore_repo_name=contextstore_repo_name,
        )

        return ContextstoreResult(
            contextstore_repo_name=contextstore_repo_name, repo_result=repo_result
        )

    except ContextstoreCreationError:
        raise
    except Exception as e:
        raise ContextstoreCreationError(
            message=f"Unexpected error creating contextstore repository: {e}",
            user_facing_message="Failed to create contextstore repository. Please contact support.",
        ) from e


async def create_stripe_customer_step(
    ctx: OnboardingContext,
    slack_team_result: SlackTeamResult,
    organization: str,
    email: str,
    bot_server: "CompassBotServer",
    organization_raw: str | None = None,
) -> None:
    """Create Stripe customer.

    Args:
        ctx: Onboarding context
        slack_team_result: Slack team result
        organization: Sanitized organization name (lowercase, URL-safe)
        email: User email
        bot_server: Bot server instance
        organization_raw: Original organization name for Stripe display (defaults to organization if not provided)
    """
    try:
        if not bot_server.stripe_client:
            raise BillingSetupError(
                message="No Stripe client available - billing setup is required for onboarding",
                user_facing_message="No Stripe client available - billing setup is required for onboarding",
            )

        # Use raw organization name for Stripe if provided, otherwise use sanitized
        org_name_for_stripe = organization_raw if organization_raw else organization

        # Create Stripe customer
        bot_server.logger.info(f"Creating Stripe customer for organization: {org_name_for_stripe}")
        try:
            with tracer.trace("onboarding.create_stripe_customer"):
                customer = await asyncio.to_thread(
                    bot_server.stripe_client.create_customer,
                    organization_name=org_name_for_stripe,
                    organization_id=slack_team_result.team_id,
                    email=email,
                )
            bot_server.logger.info(
                f"Successfully created Stripe customer: {customer['id']} for {organization}"
            )

            await ctx.mark_step_completed(
                OnboardingStep.STRIPE_CUSTOMER_CREATED,
                stripe_customer_id=customer["id"],
            )
        except Exception as e:
            raise BillingSetupError(
                message=f"Failed to create Stripe customer: {e}",
                user_facing_message=f"Failed to create Stripe customer: {e}",
            ) from e

    except BillingSetupError:
        raise
    except Exception as e:
        raise BillingSetupError(
            message=f"Unexpected error creating Stripe customer: {e}",
            user_facing_message="Failed to create Stripe customer. Please contact support.",
        ) from e


async def create_stripe_subscription_step(
    ctx: OnboardingContext,
    bot_server: "CompassBotServer",
) -> BillingResult:
    """Create Stripe subscription. Returns BillingResult."""
    try:
        if not bot_server.stripe_client:
            raise BillingSetupError(
                message="No Stripe client available - billing setup is required for onboarding",
                user_facing_message="No Stripe client available - billing setup is required for onboarding",
            )

        # Get customer ID from state
        assert ctx.state.stripe_customer_id is not None
        customer_id = ctx.state.stripe_customer_id

        # Create Stripe subscription
        product_id = bot_server.config.stripe.get_default_product_id()
        if not product_id:
            raise BillingSetupError(
                message="No default product configured - subscription creation is required for onboarding",
                user_facing_message="No default product configured - subscription creation is required for onboarding",
            )

        bot_server.logger.info(
            f"Creating Stripe subscription for customer: {customer_id} with product: {bot_server.config.stripe.default_product}"
        )
        try:
            with tracer.trace("onboarding.create_stripe_subscription"):
                subscription = await asyncio.to_thread(
                    bot_server.stripe_client.create_subscription,
                    customer_id=customer_id,
                    product_id=product_id,
                )
            bot_server.logger.info(
                f"Successfully created Stripe subscription: {subscription['id']} for customer: {customer_id}"
            )

            await ctx.mark_step_completed(
                OnboardingStep.STRIPE_SUBSCRIPTION_CREATED,
                stripe_subscription_id=subscription["id"],
            )
        except Exception as e:
            raise BillingSetupError(
                message=f"Failed to create Stripe subscription: {e}",
                user_facing_message=f"Failed to create Stripe subscription: {e}",
            ) from e

        return BillingResult(
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription["id"],
            product_id=product_id,
        )

    except BillingSetupError:
        raise
    except Exception as e:
        raise BillingSetupError(
            message=f"Unexpected error creating Stripe subscription: {e}",
            user_facing_message="Failed to create Stripe subscription. Please contact support.",
        ) from e


async def create_organization_step(
    ctx: OnboardingContext,
    billing_result: BillingResult,
    organization: str,
    email: str,
    token: str | None,
    bot_server: "CompassBotServer",
    organization_raw: str,
    contextstore_repo_name: str,
    onboarding_type: str = "standard",
) -> None:
    """Create organization in database and log analytics.

    Args:
        ctx: Onboarding context
        billing_result: Billing result from Stripe
        organization: Sanitized organization name (lowercase, URL-safe) for bot_id
        email: User email
        token: Referral token (optional)
        bot_server: Bot server instance
        organization_raw: Original organization name for database/display (defaults to organization if not provided)
        contextstore_repo_name: GitHub repository for context store in 'owner/repo' format (optional)
        onboarding_type: Type of onboarding flow ("standard" or "prospector")
    """
    try:
        # Use raw organization name for database if provided, otherwise use sanitized
        org_name_for_db = organization_raw if organization_raw else organization

        # Create organization in database first
        # Set has_governance_channel=False for onboarding (combined bot model)
        bot_server.logger.info("Creating organization in database")
        with tracer.trace("onboarding.create_organization"):
            organization_id = await bot_server.bot_manager.storage.create_organization(
                name=org_name_for_db,
                industry=None,
                stripe_customer_id=billing_result.stripe_customer_id,
                stripe_subscription_id=billing_result.stripe_subscription_id,
                has_governance_channel=False,
                contextstore_github_repo=contextstore_repo_name,
            )
        bot_server.logger.info(f"Created organization with ID: {organization_id}")

        await ctx.mark_step_completed(
            OnboardingStep.ORGANIZATION_CREATED,
            organization_id=organization_id,
        )

        # Log organization creation analytics event
        analytics_store = SlackbotAnalyticsStore(bot_server.sql_conn_factory)
        await log_analytics_event_unified(
            analytics_store=analytics_store,
            event_type=AnalyticsEventType.ORGANIZATION_CREATED,
            bot_id=f"onboarding-{organization}",
            channel_id=None,
            user_id=None,
            thread_ts=None,
            message_ts=None,
            metadata={
                "organization_id": organization_id,
                "organization_name": org_name_for_db,
                "referral_token": token,
                "stripe_customer_id": billing_result.stripe_customer_id,
                "stripe_subscription_id": billing_result.stripe_subscription_id,
                "user_email": email,
            },
            user_email=email,
            organization_name=org_name_for_db,
            organization_id=organization_id,
            onboarding_type=onboarding_type,
        )

    except OrganizationCreationError:
        raise
    except Exception as e:
        raise OrganizationCreationError(
            message=f"Unexpected error creating organization: {e}",
            user_facing_message="Failed to create organization. Please contact support.",
        ) from e


async def record_tos_step(
    ctx: OnboardingContext,
    billing_result: BillingResult,
    channel_setup_result: ChannelSetupResult | None,
    slack_team_result: SlackTeamResult,
    organization_raw: str,
    email: str,
    bot_server: "CompassBotServer",
) -> OrganizationResult:
    """Record TOS acceptance, log team member analytics, set plan limits. Returns OrganizationResult.

    Args:
        channel_setup_result: Optional channel setup result (None for minimal onboarding without channels)
    """
    try:
        # Get organization ID from state
        assert ctx.state.organization_id is not None
        organization_id = ctx.state.organization_id

        # Record terms of service acceptance
        bot_server.logger.info("Recording terms of service acceptance")
        with tracer.trace("onboarding.record_tos_acceptance"):
            await bot_server.bot_manager.storage.record_tos_acceptance(
                email=email,
                organization_id=organization_id,
                organization_name=organization_raw,
            )
        bot_server.logger.info("Terms of service acceptance recorded")

        await ctx.mark_step_completed(OnboardingStep.TOS_RECORDED)

        # Log team member invited analytics events for Dagster admins (fire-and-forget)
        # Skip analytics if no general channel (minimal onboarding)
        analytics_store = SlackbotAnalyticsStore(bot_server.sql_conn_factory)
        if channel_setup_result:
            for admin_email in bot_server.config.dagster_admins_to_invite:
                asyncio.create_task(
                    log_analytics_event_unified(
                        analytics_store=analytics_store,
                        event_type=AnalyticsEventType.TEAM_MEMBER_INVITED,
                        bot_id=f"onboarding-{organization_id}",
                        channel_id=channel_setup_result.general_channel_id,
                        user_id=None,
                        metadata={
                            "invite_type": "slack_team_invite",
                            "organization_id": organization_id,
                            "invited_email": admin_email,
                            "invite_method": "email",
                            "is_onboarding": True,
                            "team_id": slack_team_result.team_id,
                            "channel_ids": channel_setup_result.general_channel_id,
                        },
                        user_email=admin_email,
                        organization_id=organization_id,
                        organization_name=organization_raw,
                        team_id=slack_team_result.team_id,
                    )
                )

        # Set plan limits for the organization
        if billing_result.product_id:
            bot_server.logger.info("Setting plan limits from Stripe product metadata")
            if not bot_server.stripe_client:
                raise OrganizationCreationError(
                    message="Stripe client not available",
                    user_facing_message="Failed to set plan limits: Stripe client not available",
                )
            try:
                with tracer.trace("onboarding.update_plan_limits_from_product"):
                    await update_plan_limits_from_product(
                        stripe_client=bot_server.stripe_client,
                        plan_manager=bot_server.bot_manager.storage,
                        product_id=billing_result.product_id,
                        organization_id=organization_id,
                        provided_logger=bot_server.logger,
                    )
            except Exception as e:
                raise OrganizationCreationError(
                    message=f"Failed to set plan limits: {e}",
                    user_facing_message=f"Failed to set plan limits: {e}",
                ) from e

        return OrganizationResult(organization_id=organization_id, analytics_store=analytics_store)

    except OrganizationCreationError:
        raise
    except Exception as e:
        raise OrganizationCreationError(
            message=f"Unexpected error recording TOS: {e}",
            user_facing_message="Failed to record TOS. Please contact support.",
        ) from e


async def create_bot_instance_step(
    ctx: OnboardingContext,
    compass_channels_result: CompassChannelsResult,
    contextstore_result: ContextstoreResult,
    slack_team_result: SlackTeamResult,
    organization_result: OrganizationResult,
    email: str,
    token: str | None,
    has_valid_token: bool,
    bot_server: "CompassBotServer",
) -> None:
    """Create bot instance, mark token consumed, grant bonus answers."""
    try:
        # Create bot instances for both channels
        bot_server.logger.info("Creating bot instances in database")

        with tracer.trace("onboarding.create_bot_instance"):
            compass_instance_id = await bot_server.bot_manager.storage.create_bot_instance(
                channel_name=compass_channels_result.compass_channel_name,
                governance_alerts_channel=compass_channels_result.governance_channel_name,
                contextstore_github_repo=contextstore_result.contextstore_repo_name,
                slack_team_id=slack_team_result.team_id,
                bot_email="compassbot@dagster.io",
                organization_id=organization_result.organization_id,
            )

        bot_server.logger.info(f"Created compass bot instance with ID: {compass_instance_id}")

        await ctx.mark_step_completed(
            OnboardingStep.BOT_INSTANCE_CREATED,
            compass_bot_instance_id=compass_instance_id,
        )

        # Mark token as consumed (if token was provided)
        if token:
            await bot_server.bot_manager.storage.mark_referral_token_consumed(
                token, compass_instance_id
            )

        # Grant bonus answers if a valid token was used
        if has_valid_token and token:
            await grant_bonus_answers(
                organization_id=organization_result.organization_id,
                token=token,
                bot_server=bot_server,
            )

        # Store the original signup email for later use in join notifications
        bot_key = BotKey.from_channel_name(
            slack_team_result.team_id, compass_channels_result.compass_channel_name
        )
        bot = bot_server.bots.get(bot_key)
        if bot:
            await bot.kv_store.set("onboarding", "original_signup_email", email.lower())

    except BotInstanceCreationError:
        raise
    except Exception as e:
        raise BotInstanceCreationError(
            message=f"Unexpected error creating bot instance: {e}",
            user_facing_message="Failed to create bot instance. Please contact support.",
        ) from e


async def associate_channels_step(
    ctx: OnboardingContext,
    compass_channels_result: CompassChannelsResult,
    slack_team_result: SlackTeamResult,
    bot_server: "CompassBotServer",
) -> None:
    """Trigger bot discovery and associate channel IDs."""
    try:
        # Trigger targeted bot discovery to handle incoming Slack events (faster than full discovery)
        bot_server.logger.info("Triggering targeted bot discovery after instance creation")
        bot_key = BotKey.from_channel_name(
            slack_team_result.team_id, compass_channels_result.compass_channel_name
        )
        with tracer.trace("onboarding.discover_and_update_bots_for_keys"):
            await bot_server.bot_manager.discover_and_update_bots_for_keys([bot_key])

        # Associate channel IDs with newly created channels
        bot_server.logger.info("Associating channel IDs for newly created channels")
        bot = bot_server.bots.get(bot_key)
        if bot:
            # Associate compass channel ID with channel name
            await bot.associate_channel_id(
                compass_channels_result.compass_channel_id,
                compass_channels_result.compass_channel_name,
            )
            await bot_server.update_channel_mapping(
                slack_team_result.team_id,
                compass_channels_result.compass_channel_id,
                compass_channels_result.compass_channel_name,
            )
            # Associate governance channel ID with channel name
            await bot.associate_channel_id(
                compass_channels_result.governance_channel_id,
                compass_channels_result.governance_channel_name,
            )
            await bot_server.update_channel_mapping(
                slack_team_result.team_id,
                compass_channels_result.governance_channel_id,
                compass_channels_result.governance_channel_name,
            )
            bot_server.logger.info("Successfully associated channel IDs for newly created channels")

            await ctx.mark_step_completed(OnboardingStep.CHANNELS_ASSOCIATED)
        else:
            bot_server.logger.warning(f"Bot instance not found for key: {bot_key}")

    except BotInstanceCreationError:
        raise
    except Exception as e:
        raise BotInstanceCreationError(
            message=f"Unexpected error associating channels: {e}",
            user_facing_message="Failed to associate channels. Please contact support.",
        ) from e


async def send_slack_connect_invitation(
    ctx: OnboardingContext,
    org_bot_token: str,
    compass_channels_result: CompassChannelsResult,
    organization_result: OrganizationResult,
    email: str,
    organization: str,
    bot_server: "CompassBotServer",
) -> None:
    """Send Slack Connect invitation to governance channel for signup user."""
    try:
        bot_server.logger.info(f"Creating governance channel Slack Connect invitation for {email}")

        with tracer.trace("onboarding.create_slack_connect_channel"):
            governance_connect_result = await create_slack_connect_channel(
                org_bot_token, compass_channels_result.governance_channel_id, [email]
            )

        if not governance_connect_result["success"]:
            error = governance_connect_result.get("error", "unknown")
            bot_server.logger.error(
                f"API Error: Failed to create Slack Connect invitation\n"
                f"  Channel ID: {compass_channels_result.governance_channel_id}\n"
                f"  Email: {email}\n"
                f"  Organization: {organization}\n"
                f"  API Error: {error}\n"
                f"  Full Response: {governance_connect_result}"
            )
            raise SlackConnectError(
                message=f"Slack Connect invitation failed: {error}. Full API response: {governance_connect_result}",
                user_facing_message=f"Failed to create Slack Connect for governance channel: {error}",
            )

        bot_server.logger.info("Successfully created Slack Connect for governance channel")

        # Log coworker invited analytics event for governance channel
        await log_analytics_event_unified(
            analytics_store=organization_result.analytics_store,
            event_type=AnalyticsEventType.COWORKER_INVITED,
            bot_id=f"onboarding-{organization_result.organization_id}",
            channel_id=compass_channels_result.governance_channel_id,
            metadata={
                "invite_type": "slack_connect_governance_channel",
                "organization_id": organization_result.organization_id,
                "invited_email": email,
                "invite_method": "email",
                "is_onboarding": True,
            },
            user_email=email,
            organization_name=organization,
            organization_id=organization_result.organization_id,
        )

        # Note: External invite permissions are now set automatically when the
        # shared_channel_invite_accepted event is received via the bot's event handler

        await ctx.mark_step_completed(OnboardingStep.SLACK_CONNECT_SENT)

    except SlackConnectError:
        raise
    except Exception as e:
        raise SlackConnectError(
            message=f"Unexpected error sending Slack Connect invitation: {e}",
            user_facing_message="Failed to send workspace invitation. Please contact support.",
        ) from e


def reconstruct_results_from_state(
    state: OnboardingState,
    analytics_store: "SlackbotAnalyticsStore | None" = None,
) -> tuple[
    SlackTeamResult | None,
    ChannelSetupResult | None,
    CompassChannelsResult | None,
    ContextstoreResult | None,
    BillingResult | None,
    OrganizationResult | None,
]:
    """Reconstruct result objects from onboarding state for idempotent resumption.

    Args:
        state: OnboardingState with stored values
        analytics_store: Optional analytics store for OrganizationResult

    Returns:
        Tuple of result objects (each may be None if step not completed)
    """
    slack_team_result = None
    if state.is_step_completed(OnboardingStep.SLACK_TEAM_CREATED):
        assert state.slack_team_id is not None
        assert state.team_domain is not None
        assert state.team_name is not None
        slack_team_result = SlackTeamResult(
            team_id=state.slack_team_id,
            team_domain=state.team_domain,
            team_name=state.team_name,
        )

    channel_setup_result = None
    if state.is_step_completed(OnboardingStep.CHANNELS_LISTED):
        assert state.general_channel_id is not None
        channel_setup_result = ChannelSetupResult(general_channel_id=state.general_channel_id)

    compass_channels_result = None
    if state.is_step_completed(OnboardingStep.GOVERNANCE_CHANNEL_CREATED):
        assert state.compass_channel_id is not None
        assert state.compass_channel_name is not None
        assert state.governance_channel_id is not None
        assert state.governance_channel_name is not None
        compass_channels_result = CompassChannelsResult(
            compass_channel_id=state.compass_channel_id,
            compass_channel_name=state.compass_channel_name,
            governance_channel_id=state.governance_channel_id,
            governance_channel_name=state.governance_channel_name,
        )

    contextstore_result = None
    if state.is_step_completed(OnboardingStep.CONTEXTSTORE_REPO_CREATED):
        assert state.contextstore_repo_name is not None
        contextstore_result = ContextstoreResult(
            contextstore_repo_name=state.contextstore_repo_name,
            repo_result={"success": True, "repo_name": state.contextstore_repo_name},
        )

    billing_result = None
    if state.is_step_completed(OnboardingStep.STRIPE_SUBSCRIPTION_CREATED):
        assert state.stripe_customer_id is not None
        assert state.stripe_subscription_id is not None
        # Product ID is not stored in state, but we can use empty string as fallback
        billing_result = BillingResult(
            stripe_customer_id=state.stripe_customer_id,
            stripe_subscription_id=state.stripe_subscription_id,
            product_id="",  # Not stored in state, will be handled by step logic
        )

    organization_result = None
    if state.is_step_completed(OnboardingStep.ORGANIZATION_CREATED):
        assert state.organization_id is not None
        assert analytics_store is not None, "analytics_store required for OrganizationResult"
        organization_result = OrganizationResult(
            organization_id=state.organization_id, analytics_store=analytics_store
        )

    return (
        slack_team_result,
        channel_setup_result,
        compass_channels_result,
        contextstore_result,
        billing_result,
        organization_result,
    )


async def log_final_analytics(
    organization_result: OrganizationResult,
    compass_channels_result: CompassChannelsResult,
    slack_team_result: SlackTeamResult,
    contextstore_result: ContextstoreResult,
    email: str,
    organization: str,
) -> None:
    """Log final analytics events for governance channel creation and contextstore repo creation."""
    # Log governance channel creation - send to both systems
    await log_analytics_event_unified(
        analytics_store=organization_result.analytics_store,
        event_type=AnalyticsEventType.GOVERNANCE_CHANNEL_CREATED,
        bot_id=f"onboarding-{organization_result.organization_id}",
        channel_id=compass_channels_result.governance_channel_id,
        user_id=None,
        thread_ts=None,
        message_ts=None,
        metadata={
            "organization_id": organization_result.organization_id,
            "channel_name": compass_channels_result.governance_channel_name,
            "team_id": slack_team_result.team_id,
            "contextstore_repo": contextstore_result.contextstore_repo_name,
        },
        user_email=email,
        organization_name=organization,
        organization_id=organization_result.organization_id,
        team_id=slack_team_result.team_id,
        channel_name=compass_channels_result.governance_channel_name,
    )

    # Log contextstore repository creation - send to both systems
    await log_analytics_event_unified(
        analytics_store=organization_result.analytics_store,
        event_type=AnalyticsEventType.CONTEXTSTORE_REPO_CREATED,
        bot_id=f"onboarding-{organization_result.organization_id}",
        channel_id=None,
        user_id=None,
        thread_ts=None,
        message_ts=None,
        metadata={
            "repo_name": contextstore_result.contextstore_repo_name,
            "repo_url": contextstore_result.repo_result.get("repo_url"),
            "organization_id": organization_result.organization_id,
            "user_email": email,
            "team_domain": slack_team_result.team_domain,
        },
        user_email=email,
        organization_name=organization,
        organization_id=organization_result.organization_id,
    )


@sync_to_async
def create_contextstore_repository(
    logger: logging.Logger,
    agent: "AsyncAgent",
    github_auth_source: GithubAuthSource,
    team_name: str,
    user_email: str,
) -> dict:
    """Create a contextstore GitHub repository for the team.

    Args:
        logger: Logger instance for logging
        agent: AsyncAgent instance for getting company info
        github_auth_source: GitHub authentication source
        team_name: Team name
        user_email: User email to invite as collaborator

    Returns:
        Dictionary with 'success' boolean and either 'repo_url' or 'error' message
    """
    try:
        repo_name = f"{team_name}-context"
        create_repository(github_auth_source, repo_name)

        async def get_company_info():
            email_domain = user_email.split("@")[1]
            return await get_company_info_from_domain(agent, email_domain)

        company_info = None
        try:
            company_info = asyncio.run(get_company_info())
        except Exception as e:
            logger.error(f"Failed to get company info: {e}")

        # Initialize the repository with contextstore files
        project_name = f"{team_name}/compass"
        initialized_repo = initialize_contextstore_repository(
            github_auth_source, repo_name, project_name, "dagster-compass", company_info
        )

        return {
            "success": True,
            "repo_url": initialized_repo.html_url,
            "repo_name": initialized_repo.github_config.repo_name,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
