"""General-purpose Slack API utility functions.

This module provides reusable Slack API operations that can be used throughout
the codebase for various Slack integrations.
"""

import json
import random
import re
import string
from urllib.parse import urlencode

import aiohttp

from csbot.slackbot.bot_server.bot_server import CompassBotServer
from csbot.slackbot.slackbot_analytics import (
    SlackbotAnalyticsStore,
)

MAX_SLACK_TEAM_NAME_LENGTH = 21


async def post_slack_api(
    endpoint: str,
    token: str,
    payload: dict | None = None,
) -> dict:
    """Make a POST request to a Slack API endpoint.

    Args:
        endpoint: Slack API endpoint (e.g., "admin.teams.create")
        token: Slack API token
        payload: Optional payload data for the request

    Returns:
        Dictionary with 'success' boolean and either response data or 'error' message
    """
    url = f"https://slack.com/api/{endpoint}"

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data=urlencode(payload or {}),
            ) as response:
                response.raise_for_status()
                result = await response.json()

                if result.get("ok"):
                    return {"success": True, **result}
                else:
                    error = result.get("error", "Unknown error")
                    detail = result.get("detail", "")
                    error_msg = f"{error}: {detail}" if detail else error
                    return {"success": False, "error": error_msg}

    except aiohttp.ClientError as e:
        return {"success": False, "error": f"Network error: {e}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid response from Slack API"}


async def lookup_user_id_by_email(client, email: str, logger) -> str | None:
    """Look up a Slack user ID by email address.

    This function attempts to resolve an email address to a Slack user ID using
    the Slack API's users.lookupByEmail method. This is useful for pre-generating
    welcome messages and other user-specific content when only an email is available.

    Args:
        client: Slack AsyncWebClient instance
        email: Email address to look up
        logger: Logger instance for logging

    Returns:
        User ID if found, None otherwise
    """
    if not client:
        logger.debug("No Slack client available for email lookup")
        return None

    try:
        logger.info(f"Attempting to resolve email {email} to user_id")
        user_lookup_response = await client.users_lookupByEmail(email=email)
        if user_lookup_response.get("ok") and "user" in user_lookup_response:
            user_id = user_lookup_response["user"]["id"]
            logger.info(f"Resolved email {email} to user_id {user_id}")
            return user_id
        logger.debug(f"No user found for email {email}")
        return None
    except Exception as e:
        logger.debug(f"Could not resolve email {email} to user_id: {e}")
        return None


def generate_urlsafe_team_name(team_name: str) -> str:
    """Generate a URL-safe team name from a team name.

    Removes non-ASCII characters to ensure compatibility with Slack channel names.
    Slack channel names can only contain lowercase letters, numbers, hyphens, and underscores.
    """
    # First convert to lowercase
    team_name = team_name.lower()
    # Remove non-ASCII characters by keeping only ASCII letters, numbers, spaces, hyphens, underscores
    team_name = re.sub(r"[^a-z0-9\s\-_]", "", team_name)
    # Replace spaces and underscores with hyphens
    team_name = re.sub(r"[\s_]+", "-", team_name)
    # Collapse multiple hyphens and strip leading/trailing hyphens
    return re.sub(r"-+", "-", team_name).strip("-")


def generate_team_domain(team_name: str) -> str:
    """Generate a team domain from a team name.

    Converts team name to lowercase, replaces spaces and special characters
    with hyphens, removes multiple consecutive hyphens, and truncates to
    21 characters maximum as required by Slack.

    Slack domains must be ASCII-only (lowercase letters, numbers, and hyphens).
    """
    base = generate_urlsafe_team_name(team_name)
    random_nonce = generate_nonce(5)
    base_length = MAX_SLACK_TEAM_NAME_LENGTH - 6  # nonce length + 1
    return f"{base[:base_length]}-{random_nonce}"


def generate_team_description(team_name: str) -> str:
    """Generate a team description from a team name."""
    return f"Team workspace for {team_name}"


async def create_slack_team(
    admin_token: str,
    team_name: str,
    team_domain: str,
    team_description: str | None = None,
) -> dict:
    """Create a new Slack team using the admin.teams.create API.

    Args:
        admin_token: Slack API token with admin.teams:write scope
        team_name: Name of the team to create
        team_domain: Team domain (max 21 chars)
        team_description: Team description. If None, generated from team_name

    Returns:
        Dictionary with 'success' boolean and either 'team_id' or 'error' message
    """
    # Generate description if not provided
    if team_description is None:
        team_description = generate_team_description(team_name)

    # Validate team domain length
    if len(team_domain) > 21:
        return {"success": False, "error": "team domain must be 21 characters or fewer"}

    payload = {
        "team_name": team_name,
        "team_domain": team_domain,
        "team_description": team_description,
        "team_discoverability": "invite_only",
    }

    result = await post_slack_api("admin.teams.create", admin_token, payload)
    if not result["success"] and result.get("error") == "name_taken_in_org":
        # retry with a new team name/domain, because who cares it's not visible
        nonce = generate_nonce(3)
        substr_length = MAX_SLACK_TEAM_NAME_LENGTH - 4  # new nonce + 1
        team_name = f"{team_name[:substr_length]} {nonce}"
        team_domain = f"{team_domain}-{nonce}"
        payload = {**payload, "team_name": team_name, "team_domain": team_domain}
        result = await post_slack_api("admin.teams.create", admin_token, payload)

    if result["success"]:
        return {
            "success": True,
            "team_id": result.get("team"),
            "team_name": team_name,
            "team_domain": team_domain,
            "team_description": team_description,
        }
    else:
        return result


async def create_channel(
    admin_token: str,
    team_id: str,
    channel_name: str,
    is_private: bool = False,
) -> dict:
    """Create a Slack channel using the conversations.create API.

    Args:
        admin_token: Slack API token with admin.conversations:write scope
        team_id: ID of the team to create the channel in
        channel_name: Name of the channel to create
        is_private: Whether the channel should be private

    Returns:
        Dictionary with 'success' boolean and either 'channel_id' or 'error' message
    """
    payload = {
        "team_id": team_id,
        "name": channel_name,
        "is_private": str(is_private).lower(),
    }

    result = await post_slack_api("conversations.create", admin_token, payload)

    if result["success"]:
        channel = result.get("channel", {})
        return {
            "success": True,
            "channel_id": channel.get("id"),
            "channel_name": channel_name,
            "is_private": is_private,
        }
    else:
        return result


async def get_all_channels(
    org_bot_token: str,
    team_id: str,
) -> dict:
    """Get all channel IDs from a Slack team.

    Args:
        org_bot_token: Slack API token with appropriate scopes
        team_id: ID of the Slack team to get channels from

    Returns:
        Dictionary with 'success' boolean and either 'channel_ids' or 'error' message
    """
    payload = {
        "team_id": team_id,  # Required for Enterprise Grid workspaces
        "types": "public_channel",
        "exclude_archived": "true",
        "limit": "100",
    }

    result = await post_slack_api("conversations.list", org_bot_token, payload)

    if result["success"]:
        channels = result.get("channels", [])
        all_channel_ids = [channel["id"] for channel in channels]
        all_channel_names = [channel["name"] for channel in channels]
        # Create a mapping of channel names to IDs for easier lookup
        channel_name_to_id = {channel["name"]: channel["id"] for channel in channels}

        return {
            "success": True,
            "channel_ids": ",".join(all_channel_ids),
            "channel_names": all_channel_names,
            "channel_name_to_id": channel_name_to_id,
        }
    else:
        return result


async def approve_app_for_team(
    admin_token: str,
    app_id: str,
    team_id: str,
) -> dict:
    """Approve a Slack app for a specific team using the admin.apps.approve API.

    Args:
        admin_token: Slack API token with admin.apps:write scope
        app_id: ID of the Slack app to approve
        team_id: ID of the Slack team to approve the app for

    Returns:
        Dictionary with 'success' boolean and either success data or 'error' message
    """
    payload = {
        "app_id": app_id,
        "team_id": team_id,
    }

    result = await post_slack_api("admin.apps.approve", admin_token, payload)

    if result["success"]:
        return {
            "success": True,
            "app_id": app_id,
            "team_id": team_id,
        }
    else:
        return result


async def get_bot_user_id(
    bot_token: str,
) -> dict:
    """Get the bot's user ID using the auth.test API.

    Args:
        bot_token: Slack bot token

    Returns:
        Dictionary with 'success' boolean and either 'user_id' or 'error' message
    """
    result = await post_slack_api("auth.test", bot_token)

    if result["success"]:
        return {
            "success": True,
            "user_id": result.get("user_id"),
            "bot_id": result.get("bot_id"),
        }
    else:
        return result


async def invite_bot_to_channel(
    admin_token: str,
    channel: str,
    bot_user_id: str,
) -> dict:
    """Invite the bot user to a Slack channel using the conversations.invite API.

    Args:
        admin_token: Slack admin token with admin.conversations:write scope
        channel: Channel ID to invite the bot to
        bot_user_id: Bot's user ID to invite

    Returns:
        Dictionary with 'success' boolean and either success data or 'error' message
    """
    payload = {
        "channel": channel,
        "users": bot_user_id,
    }

    result = await post_slack_api("conversations.invite", admin_token, payload)

    if result["success"]:
        return {
            "success": True,
            "channel": channel,
            "user_id": bot_user_id,
        }
    else:
        # Handle the case where the bot is already in the channel - this is not actually an error
        if result.get("error") == "already_in_channel":
            return {
                "success": True,
                "channel": channel,
                "user_id": bot_user_id,
                "was_already_in_channel": True,
            }
        else:
            return result


async def create_slack_connect_channel(
    bot_token: str,
    channel: str,
    emails: list[str],
) -> dict:
    """Create a Slack Connect channel using the conversations.inviteShared API.

    Args:
        bot_token: Slack bot token with channels:write scope
        channel: Channel ID to share externally
        emails: List of email addresses to invite to the shared channel

    Returns:
        Dictionary with 'success' boolean and either success data or 'error' message
    """
    payload = {
        "channel": channel,
        "emails": ",".join(emails),
    }

    result = await post_slack_api("conversations.inviteShared", bot_token, payload)

    if result["success"]:
        return {
            "success": True,
            "channel": channel,
            "emails": emails,
            "invite_id": result.get("invite_id"),
        }
    else:
        return result


async def create_slack_connect_channel_from_user_id(
    bot_token: str, channel: str, user_id: str
) -> dict:
    """Create a Slack Connect channel using the conversations.inviteShared API.

    Args:
        bot_token: Slack bot token with channels:write scope
        channel: Channel ID to share externally
        user_id: User ID to invite to the shared channel

    Returns:
        Dictionary with 'success' boolean and either success data or 'error' message
    """
    payload = {
        "channel": channel,
        "user_ids": user_id,
    }

    result = await post_slack_api("conversations.inviteShared", bot_token, payload)

    if result["success"]:
        return {
            "success": True,
            "channel": channel,
            "user_id": user_id,
            "invite_id": result.get("invite_id"),
        }
    else:
        return result


async def send_slack_connect_invite_to_channel(
    channel_id: str,
    user_ids: list[str],
    bot_server_config,
    logger,
    channel_name: str = "channel",
) -> list[dict]:
    """Send Slack Connect invites to specified users for a channel.

    Args:
        channel_id: Slack channel ID to invite users to
        user_ids: List of user IDs to invite
        bot_server_config: Bot server config containing dev tools token
        logger: Logger instance
        channel_name: Channel name for logging purposes

    Returns:
        List of result dictionaries from invite attempts
    """
    if not bot_server_config.compass_dev_tools_bot_token:
        logger.error("No compass dev tools bot token configured for Slack Connect")
        return [{"success": False, "error": "No dev tools bot token configured"}]

    org_bot_token = bot_server_config.compass_dev_tools_bot_token.get_secret_value()
    if not org_bot_token:
        logger.error("No organization bot token available for Slack Connect")
        return [{"success": False, "error": "Empty dev tools bot token"}]

    logger.info(
        f"Sending Slack Connect invites to {len(user_ids)} users for channel {channel_name}"
    )

    # Send invites to all users
    connect_results = []
    for user_id in user_ids:
        result = await create_slack_connect_channel_from_user_id(
            bot_token=org_bot_token,
            channel=channel_id,
            user_id=user_id,
        )
        connect_results.append(result)

        if result["success"]:
            logger.info(
                f"Successfully sent Slack Connect invite to user {user_id} for channel {channel_name}"
            )
        else:
            logger.error(
                f"Failed to send Slack Connect invite to user {user_id}: {result.get('error', 'Unknown error')}"
            )

    return connect_results


async def invite_user_to_slack_team(
    admin_token: str,
    team_id: str,
    email: str,
    channel_ids: str,
) -> dict:
    """Invite a user to a Slack team using the admin.users.invite API.

    Args:
        admin_token: Slack API token with admin.users:write scope
        team_id: ID of the Slack team to invite the user to
        email: Email address of the user to invite
        channel_ids: Comma-separated list of channel IDs to join (empty for default channels)

    Returns:
        Dictionary with 'success' boolean and either 'user_id' or 'error' message

    Note:
        This API only works on Enterprise Grid workspaces. For regular workspaces,
        users must be invited through the Slack UI or other invitation methods.
    """
    payload = {
        "team_id": team_id,
        "email": email,
        "channel_ids": channel_ids,  # Required parameter for admin.users.invite
    }

    result = await post_slack_api("admin.users.invite", admin_token, payload)

    if result["success"]:
        return {
            "success": True,
            "user_id": result.get("user", {}).get("id"),
            "email": email,
            "team_id": team_id,
        }
    else:
        return result


async def archive_channel(
    admin_token: str,
    channel_id: str,
) -> dict:
    """Archive a Slack channel using the conversations.archive API.

    Args:
        admin_token: Slack API token with conversations:write scope
        channel_id: ID of the channel to archive

    Returns:
        Dictionary with 'success' boolean and either success data or 'error' message
    """
    payload = {
        "channel": channel_id,
    }

    result = await post_slack_api("conversations.archive", admin_token, payload)

    if result["success"]:
        return {
            "success": True,
            "channel": channel_id,
        }
    else:
        return result


async def _send_channel_creation_welcome_message(channel_id: str, compass_bot_token: str, logger):
    """Send welcome message to newly created channel.

    Args:
        channel_id: ID of the channel to send welcome message to
        compass_bot_token: Compass bot token for sending message
        logger: Logger instance for operation logging
    """
    from slack_sdk.errors import SlackApiError

    from csbot.slackbot.slack_client import create_slack_client
    from csbot.slackbot.welcome import send_compass_pinned_welcome_message

    try:
        client = create_slack_client(token=compass_bot_token)
        await send_compass_pinned_welcome_message(client, channel_id, logger)
        logger.info(f"Successfully sent channel creation welcome message to {channel_id}")
    except SlackApiError as e:
        # Don't fail the entire channel creation if welcome message fails
        logger.warning(
            f"Failed to send channel creation welcome message to {channel_id}: {e.response.get('error', str(e))}"
        )


async def _mark_onboarding_step_if_exists(storage, organization_id: int, step_name: str, logger):
    """Mark an onboarding step as completed if onboarding state exists for the organization.

    This is a best-effort operation - if no onboarding state exists or the update fails,
    it logs a warning but doesn't fail the calling operation.

    Args:
        storage: Storage instance for database operations
        organization_id: Organization ID to look up onboarding state
        step_name: Name of the OnboardingStep enum value (e.g., "BOT_INSTANCE_CREATED")
        logger: Logger instance for operation logging
    """
    try:
        from csbot.slackbot.storage.onboarding_state import OnboardingStep

        # Get onboarding state for this organization
        onboarding_state = await storage.get_onboarding_state_by_organization_id(organization_id)

        if not onboarding_state:
            # No onboarding state exists - this is normal for orgs created before onboarding tracking
            logger.debug(
                f"No onboarding state found for organization {organization_id}, skipping step {step_name}"
            )
            return

        # Get the step enum value
        step = OnboardingStep(step_name.lower())

        # Check if already completed
        if step in onboarding_state.completed_steps:
            logger.debug(f"Onboarding step {step_name} already completed for org {organization_id}")
            return

        # Mark step as completed
        updated_state = onboarding_state.with_step(step)
        await storage.update_onboarding_state(updated_state)
        logger.info(f"Marked onboarding step {step_name} as completed for org {organization_id}")

    except Exception as e:
        # Log warning but don't fail the calling operation
        logger.warning(
            f"Failed to mark onboarding step {step_name} for org {organization_id}: {e}",
            exc_info=True,
        )


async def create_channel_and_bot_instance(
    bot_server: CompassBotServer,
    channel_name: str,
    user_id: str,
    team_id: str,
    organization_id: int,
    storage,
    governance_bot,
    contextstore_github_repo: str | None,
    dev_tools_bot_token: str,
    admin_token: str,
    compass_bot_token: str,
    logger,
    token: str | None,
    has_valid_token: bool,
    pending_invite_user_id: str | None = None,
    pending_invite_email: str | None = None,
    instance_type=None,
    icp_text: str | None = None,
    data_types: list | None = None,
) -> dict:
    """Create a Slack channel and corresponding bot instance with full setup.

    Bot behavior depends on organization's has_governance_channel feature flag:
    - If has_governance_channel=False: Creates "combined" bot where governance_alerts_channel == channel_name
      (same channel handles both Q&A and governance functions)
    - If has_governance_channel=True: Creates bot with separate governance channel (traditional model)

    This utility function handles the complete flow of:
    1. Checking organization feature flags
    2. Checking if channel already exists
    3. Creating new Slack channel if needed
    4. Retrieving bot user IDs
    5. Inviting both dev tools and compass bots to channel
    6. Creating bot instance in database (combined or separate governance based on flag)
    7. Triggering bot discovery
    8. Optionally storing pending invite for dataset sync to handle

    Args:
        channel_name: Name of the channel to create (normalized)
        user_id: Slack user ID for notifications
        team_id: Slack team ID
        organization_id: Organization ID (integer) for database operations
        storage: Bot storage instance for database operations
        governance_bot: Governance bot instance for contextstore repo reference
        contextstore_github_repo: Context store GitHub repo in 'owner/repo' format (required)
        dev_tools_bot_token: Dev tools bot token for channel operations
        admin_token: Admin token for channel creation
        compass_bot_token: Compass bot token for bot operations
        logger: Logger instance for operation logging
        token: Referral token (optional)
        has_valid_token: Whether the token is valid
        pending_invite_user_id: Optional user ID to invite after dataset sync completes.
            If provided, the invite will be deferred until first dataset sync.
            If None, no automatic invite will be sent (caller handles invite).
        pending_invite_email: Optional email to invite after dataset sync completes.
            Used for onboarding flow when user_id doesn't exist yet.
            Will send Slack Connect invite by email instead of user_id.
        instance_type: Optional bot instance type (e.g., BotInstanceType.STANDARD).
            If None, uses default behavior based on governance channel.
        icp_text: Optional ICP (Ideal Customer/Candidate Profile) text for prospector bots.
        data_types: Optional list of ProspectorDataType enums for prospector bots.

    Returns:
        Dictionary with 'success' boolean and either success data or 'error' message
        Success data includes 'channel_id', 'channel_name', 'bot_created', 'slack_connect_sent'
    """
    # Governance channel notifications disabled - not needed for core functionality
    message_stream = None

    try:
        # Check organization feature flags to determine bot type
        logger.info(f"Checking organization {organization_id} feature flags")
        organizations = await storage.list_organizations()
        organization = next(
            (org for org in organizations if org.organization_id == organization_id), None
        )

        if not organization:
            error_msg = f"Organization {organization_id} not found"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # Determine governance channel based on feature flag
        has_governance_channel = organization.has_governance_channel
        if has_governance_channel:
            # Traditional model: use existing governance bot's alerts channel
            if governance_bot:
                governance_alerts_channel = governance_bot.governance_alerts_channel
                logger.info(
                    f"Organization has separate governance channel: {governance_alerts_channel}"
                )
            else:
                # No governance bot yet - shouldn't happen with has_governance_channel=True
                error_msg = "Organization requires governance channel but no governance bot exists"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
        else:
            # Combined model: governance_alerts_channel == channel_name
            governance_alerts_channel = channel_name
            logger.info(
                f"Organization uses combined bot model: governance_alerts_channel = {channel_name}"
            )
        # Check if channel already exists first
        logger.info(f"Checking if Slack channel {channel_name} already exists")
        channels_result = await get_all_channels(
            org_bot_token=dev_tools_bot_token,
            team_id=team_id,
        )

        channel_id = None
        if channels_result["success"]:
            channel_name_to_id = channels_result.get("channel_name_to_id", {})
            if channel_name in channel_name_to_id:
                # Channel exists, use its ID from Slack API response
                channel_id = channel_name_to_id[channel_name]
                logger.info(f"Channel {channel_name} already exists with ID {channel_id}")
        else:
            # Channel check failed, log warning but continue with creation attempt
            logger.warning(
                f"Failed to check existing channels: {channels_result.get('error', 'Unknown error')}"
            )

        if not channel_id:
            # Create the Slack channel
            logger.info(f"Creating new Slack channel: {channel_name}")
            channel_result = await create_channel(
                admin_token=admin_token,
                team_id=team_id,
                channel_name=channel_name,
                is_private=False,
            )

            if not channel_result["success"]:
                error_msg = f"Failed to create Slack channel: {channel_result.get('error', 'Unknown error')}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

            channel_id = channel_result["channel_id"]
            logger.info(f"Successfully created channel {channel_name} with ID {channel_id}")
        else:
            logger.info(f"Using existing channel {channel_name} with ID {channel_id}")

        # Get bot user IDs for channel invitations
        logger.info("Retrieving bot user IDs for channel invitations")
        dev_tools_bot_auth_result = await get_bot_user_id(dev_tools_bot_token)
        if not dev_tools_bot_auth_result["success"]:
            error_msg = f"Failed to get dev tools bot user ID: {dev_tools_bot_auth_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        compass_bot_auth_result = await get_bot_user_id(compass_bot_token)
        if not compass_bot_auth_result["success"]:
            error_msg = f"Failed to get compass bot user ID: {compass_bot_auth_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        dev_tools_bot_user_id = dev_tools_bot_auth_result["user_id"]
        compass_bot_user_id = compass_bot_auth_result["user_id"]
        logger.info(
            f"Retrieved bot user IDs - Dev tools: {dev_tools_bot_user_id}, "
            f"Compass: {compass_bot_user_id}"
        )

        # Invite both bots to the newly created channel
        logger.info(f"Inviting bots to channel {channel_name}")

        # Invite dev tools bot to channel
        dev_tools_invite_result = await invite_bot_to_channel(
            admin_token, channel_id, dev_tools_bot_user_id
        )
        if not dev_tools_invite_result["success"]:
            error_msg = f"Failed to invite dev tools bot to channel: {dev_tools_invite_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        elif dev_tools_invite_result.get("was_already_in_channel"):
            logger.info("Dev tools bot was already in the channel - continuing")

        # Invite compass bot to channel
        compass_invite_result = await invite_bot_to_channel(
            admin_token, channel_id, compass_bot_user_id
        )
        if not compass_invite_result["success"]:
            error_msg = f"Failed to invite compass bot to channel: {compass_invite_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        elif compass_invite_result.get("was_already_in_channel"):
            logger.info("Compass bot was already in the channel - continuing")

        logger.info(f"Successfully invited both bots to channel {channel_name}")

        # Create the new bot instance in database
        # Bot type determined by organization's has_governance_channel flag (set above)
        # contextstore_github_repo must be provided - no placeholders allowed
        if not contextstore_github_repo:
            error_msg = "Context store GitHub repository must be provided to create bot instance"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        bot_type_desc = (
            "combined" if governance_alerts_channel == channel_name else "separate governance"
        )
        logger.info(
            f"Creating {bot_type_desc} bot instance: channel={channel_name}, "
            f"governance_alerts_channel={governance_alerts_channel}, "
            f"contextstore={contextstore_github_repo}"
        )

        # Build bot instance parameters
        bot_instance_params = {
            "channel_name": channel_name,
            "governance_alerts_channel": governance_alerts_channel,
            "contextstore_github_repo": contextstore_github_repo,
            "slack_team_id": team_id,
            "bot_email": "compassbot@dagster.io",  # Default email pattern
            "organization_id": organization_id,
        }

        # Add prospector-specific parameters if provided
        if instance_type is not None:
            bot_instance_params["instance_type"] = instance_type
        if icp_text is not None:
            bot_instance_params["icp_text"] = icp_text
        if data_types is not None:
            bot_instance_params["data_types"] = data_types

        compass_instance_id = await storage.create_bot_instance(**bot_instance_params)

        # Mark onboarding step: BOT_INSTANCE_CREATED
        await _mark_onboarding_step_if_exists(
            storage, organization_id, "BOT_INSTANCE_CREATED", logger
        )

        # Mark token as consumed (if token was provided)
        if token:
            await bot_server.bot_manager.storage.mark_referral_token_consumed(
                token, compass_instance_id
            )

        # Grant bonus answers if a valid token was used
        if has_valid_token and token:
            await grant_bonus_answers(
                organization_id=organization.organization_id,
                token=token,
                bot_server=bot_server,
            )

        # Pre-cache the channel mapping to avoid race conditions
        bot_server.channel_id_to_name[channel_id] = channel_name

        # Trigger targeted bot discovery to register only this new instance (faster than full discovery)
        from csbot.slackbot.bot_server.bot_server import BotKey

        bot_key_for_mapping = BotKey(team_id=team_id, channel_name=channel_name)
        await bot_server.bot_manager.discover_and_update_bots_for_keys([bot_key_for_mapping])

        # Store channel name to ID mapping in KV store for the new bot instance
        bot_instance_for_mapping = bot_server.bots.get(bot_key_for_mapping)
        if bot_instance_for_mapping:
            await bot_instance_for_mapping.associate_channel_id(channel_id, channel_name)

        # Mark onboarding step: CHANNELS_ASSOCIATED
        await _mark_onboarding_step_if_exists(
            storage, organization_id, "CHANNELS_ASSOCIATED", logger
        )

        # Send welcome message to the newly created channel
        await _send_channel_creation_welcome_message(
            channel_id=channel_id, compass_bot_token=compass_bot_token, logger=logger
        )

        # Store pending invite and message stream if provided
        if pending_invite_user_id or pending_invite_email or message_stream:
            from csbot.slackbot.bot_server.bot_server import BotKey

            bot_key = BotKey(team_id=team_id, channel_name=channel_name)
            bot_instance = bot_server.bots.get(bot_key)
            if bot_instance:
                if pending_invite_user_id:
                    await bot_instance.kv_store.set(
                        "pending_invites", "user_ids", pending_invite_user_id
                    )
                    logger.info(
                        f"Stored pending invite for user {pending_invite_user_id} in channel {channel_name}"
                    )
                if pending_invite_email:
                    await bot_instance.kv_store.set(
                        "pending_invites", "emails", pending_invite_email
                    )
                    logger.info(
                        f"Stored pending invite for email {pending_invite_email} in channel {channel_name}"
                    )
                if message_stream:
                    # Store message stream metadata to finish it after dataset sync
                    import json

                    message_metadata = json.dumps(
                        {
                            "channel_id": message_stream.channel_id,
                            "message_ts": message_stream.message_ts,
                            "user_id": user_id,
                        }
                    )
                    await bot_instance.kv_store.set(
                        "pending_invites", "message_stream_metadata", message_metadata
                    )
                    logger.info(
                        f"Stored pending message stream for channel {channel_name} to finish after dataset sync"
                    )
            else:
                logger.warning(
                    f"Could not find bot instance to store pending invite for {channel_name}"
                )

        return {
            "success": True,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "bot_created": True,
            "slack_connect_sent": False,  # Will be sent after data processing completes
            "message_stream": message_stream,  # Allow caller to update message
        }

    except Exception as e:
        logger.error(f"Error in channel and bot instance creation flow: {e}", exc_info=True)

        return {"success": False, "error": str(e)}


async def delete_channel_and_bot_instance(
    bot_server: CompassBotServer,
    channel_name: str,
    bot_id: str,
    organization_id: int,
    storage,
    governance_bot,
    governance_alerts_channel: str,
    logger,
    user_id: str | None = None,
) -> dict:
    """Delete a bot instance and send notification to governance channel.

    This utility function handles the complete flow of:
    1. Sending initial notification to governance channel
    2. Deleting bot instance from database
    3. Triggering bot discovery to update the bot list
    4. Updating notification with success message

    Args:
        channel_name: Name of the channel being deleted
        bot_id: Bot ID to delete
        organization_id: Organization ID (integer) for database operations
        storage: Bot storage instance for database operations
        governance_bot: Governance bot instance for bot server access
        governance_alerts_channel: Governance alerts channel name
        logger: Logger instance for operation logging
        user_id: Slack user ID who initiated the deletion (optional)

    Returns:
        Dictionary with 'success' boolean and either success data or 'error' message
    """
    # Import SlackstreamMessage and BlockKit components for notifications
    try:
        from csbot.slackbot.slackbot_blockkit import SectionBlock, TextObject
        from csbot.slackbot.slackbot_slackstream import SlackstreamMessage
    except ImportError as e:
        logger.error(f"Failed to import SlackstreamMessage components: {e}")
        return {"success": False, "error": "Failed to import notification components"}

    # Initialize message_stream for governance notifications
    message_stream = None

    # Send initial notification to governance channel using SlackstreamMessage
    try:
        governance_channel_id = await governance_bot.kv_store.get_channel_id(
            governance_alerts_channel
        )
        if governance_channel_id:
            # Create initial "in progress" message
            if user_id:
                initial_text = f"⏳ <@{user_id}> is removing Compass channel `{channel_name}`..."
            else:
                initial_text = f"⏳ Compass channel `{channel_name}` is being removed..."

            initial_blocks = [SectionBlock(text=TextObject.mrkdwn(initial_text))]

            # Post initial message and get SlackstreamMessage for updates
            message_stream = await SlackstreamMessage.post_message(
                client=governance_bot.client,
                channel_id=governance_channel_id,
                blocks=initial_blocks,
            )

            logger.info(
                f"Posted initial notification to governance channel for channel deletion: {channel_name}"
            )
        else:
            logger.warning(f"Could not find governance channel ID for {governance_alerts_channel}")
    except Exception as e:
        # Don't fail the entire operation if notification fails
        logger.warning(f"Failed to send initial governance channel notification: {e}")

    try:
        from csbot.slackbot.bot_server.bot_server import BotKey

        logger.info(f"Deleting bot instance for channel {channel_name}")

        # Delete the bot instance from database
        bot_key = BotKey.from_bot_id(bot_id)
        await storage.delete_bot_instance(organization_id, bot_key)
        logger.info(f"Successfully deleted bot instance {bot_id}")

        # Trigger targeted bot discovery to update the bot list (faster than full discovery)
        await bot_server.bot_manager.discover_and_update_bots_for_keys([bot_key])

        # Update notification message with success
        if message_stream:
            try:
                # Update message with final success state
                if user_id:
                    final_text = f"🗑️ <@{user_id}> has removed Compass channel `{channel_name}`"
                else:
                    final_text = f"🗑️ Compass channel `{channel_name}` has been removed"

                final_blocks = [SectionBlock(text=TextObject.mrkdwn(final_text))]
                await message_stream.update(final_blocks)
                await message_stream.finish()

                logger.info(
                    f"Updated governance channel notification with success for channel deletion {channel_name}"
                )
            except Exception as e:
                # Don't fail the entire operation if notification fails
                logger.warning(f"Failed to update governance channel notification: {e}")

        return {
            "success": True,
            "channel_name": channel_name,
            "bot_id": bot_id,
        }

    except Exception as e:
        logger.error(f"Error in channel and bot instance deletion flow: {e}", exc_info=True)

        # Update notification message with failure
        if message_stream:
            try:
                # Update message with failure state
                if user_id:
                    error_text = f"❌ <@{user_id}> failed to remove Compass channel `{channel_name}`: {str(e)}"
                else:
                    error_text = f"❌ Failed to remove Compass channel `{channel_name}`: {str(e)}"

                error_blocks = [SectionBlock(text=TextObject.mrkdwn(error_text))]
                await message_stream.update(error_blocks)
                await message_stream.finish()

                logger.info(
                    f"Updated governance channel notification with error for channel deletion {channel_name}"
                )
            except Exception as notification_e:
                # Don't fail the entire operation if notification fails
                logger.warning(
                    f"Failed to update governance channel notification with error: {notification_e}"
                )

        return {"success": False, "error": str(e)}


def generate_nonce(length: int = 5) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


async def grant_bonus_answers(
    organization_id: int, token: str, bot_server: "CompassBotServer"
) -> None:
    # Get the token details to find the bonus amount
    invite_tokens = await bot_server.bot_manager.storage.list_invite_tokens()
    token_data = next((t for t in invite_tokens if t.token == token), None)

    if token_data:
        # Only grant bonus if token has a positive bonus amount configured
        analytics_store = SlackbotAnalyticsStore(bot_server.sql_conn_factory)
        if token_data.consumer_bonus_answers > 0:
            bonus_amount = token_data.consumer_bonus_answers

            await analytics_store.create_bonus_answer_grant(
                organization_id,
                bonus_amount,
                "sign-up bonus",
            )
            bot_server.logger.info(
                f"Granted {bonus_amount} bonus answers to organization "
                f"{organization_id} for using referral token"
            )

        if token_data.issued_by_organization_id is not None:
            # Current bonus answers amount is hard coded to 100
            bonus_amount = 100

            await analytics_store.create_bonus_answer_grant(
                token_data.issued_by_organization_id,
                bonus_amount,
                "Referral bonus",
            )
            bot_server.logger.info(
                f"Granted {bonus_amount} bonus answers to organization "
                f"{token_data.issued_by_organization_id} "
                f"because their referral token was successfully used "
                f"to create an account by organization {organization_id}"
            )
