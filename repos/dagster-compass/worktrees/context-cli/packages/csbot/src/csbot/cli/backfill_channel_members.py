"""CLI command to backfill org_users table with existing channel members.

This command initializes a bot server and iterates through all bot instances,
fetching channel members from Slack and ensuring each member has an org_user
record linked to the channel. Bot users are excluded from processing.
"""

import asyncio
from pathlib import Path
from typing import Any

import click
import structlog
from dotenv import find_dotenv, load_dotenv

from csbot.slackbot.bot_server.bot_server import CompassBotServer, create_secret_store
from csbot.slackbot.channel_bot.personalization import get_cached_user_info
from csbot.slackbot.initialize import initialize_dynamic_compass_bot_server_for_repl
from csbot.slackbot.slackbot_core import load_bot_server_config_from_path


async def backfill_channel_members(bot_server: CompassBotServer) -> dict[str, int]:
    """Backfill org_users table for existing channel members.

    This function processes bots grouped by organization, handling governance channels
    first to ensure admin users are properly marked with is_org_admin=True.

    Args:
        bot_server: Initialized bot server instance

    Returns:
        Dictionary with statistics about the backfill operation
    """
    logger = structlog.get_logger(__name__)
    logger.info("Starting channel member backfill")

    # Group bots by organization ID
    bots_by_org: dict[int, list[tuple[Any, Any]]] = {}
    for bot_key, bot_instance in bot_server.bots.items():
        org_id = bot_instance.bot_config.organization_id
        if org_id not in bots_by_org:
            bots_by_org[org_id] = []
        bots_by_org[org_id].append((bot_key, bot_instance))

    total_bots = len(bot_server.bots)
    total_members_processed = 0
    total_bots_skipped = 0
    total_errors = 0
    total_orgs = len(bots_by_org)

    # Process each organization
    for org_idx, (org_id, org_bots) in enumerate(bots_by_org.items(), start=1):
        logger.info(
            f"Processing organization {org_idx}/{total_orgs}",
            extra={"organization_id": org_id, "bot_count": len(org_bots)},
        )

        # Separate governance and non-governance bots
        governance_bots = []
        non_governance_bots = []

        for bot_key, bot_instance in org_bots:
            if bot_instance.has_admin_support:
                governance_bots.append((bot_key, bot_instance))
            else:
                non_governance_bots.append((bot_key, bot_instance))

        logger.info(
            f"Organization {org_id}: {len(governance_bots)} governance bots, {len(non_governance_bots)} non-governance bots",
            extra={
                "organization_id": org_id,
                "governance_bot_count": len(governance_bots),
                "non_governance_bot_count": len(non_governance_bots),
            },
        )

        # Process governance bots first
        for bot_key, bot_instance in governance_bots:
            result = await _process_bot_channel(
                bot_server=bot_server,
                bot_key=bot_key,
                bot_instance=bot_instance,
                is_governance=True,
                logger=logger,
            )
            total_members_processed += result["members_processed"]
            total_bots_skipped += result["bots_skipped"]
            total_errors += result["errors"]

        # Process non-governance bots
        for bot_key, bot_instance in non_governance_bots:
            result = await _process_bot_channel(
                bot_server=bot_server,
                bot_key=bot_key,
                bot_instance=bot_instance,
                is_governance=False,
                logger=logger,
            )
            total_members_processed += result["members_processed"]
            total_bots_skipped += result["bots_skipped"]
            total_errors += result["errors"]

    logger.info(
        "Channel member backfill completed",
        extra={
            "total_bots": total_bots,
            "total_members_processed": total_members_processed,
            "total_bots_skipped": total_bots_skipped,
            "total_errors": total_errors,
        },
    )

    return {
        "total_bots": total_bots,
        "total_members_processed": total_members_processed,
        "total_bots_skipped": total_bots_skipped,
        "total_errors": total_errors,
    }


async def _process_bot_channel(
    bot_server: CompassBotServer,
    bot_key: Any,
    bot_instance: Any,
    is_governance: bool,
    logger: Any,
) -> dict[str, int]:
    """Process a single bot channel and its members.

    Args:
        bot_server: Bot server instance
        bot_key: Bot key identifier
        bot_instance: Bot instance
        is_governance: Whether this is a governance channel
        logger: Logger instance

    Returns:
        Dictionary with processing statistics
    """
    channel_name = bot_key.channel_name
    team_id = bot_key.team_id
    organization_id = bot_instance.bot_config.organization_id

    logger.info(
        f"Processing {'governance' if is_governance else 'non-governance'} bot",
        extra={
            "channel_name": channel_name,
            "team_id": team_id,
            "organization_id": organization_id,
            "is_governance": is_governance,
        },
    )

    members_processed = 0
    bots_skipped = 0
    errors = 0

    # Check if bot has a Slack client
    if not hasattr(bot_instance, "client"):
        logger.warning(
            "Bot instance has no Slack client, skipping",
            extra={"channel_name": channel_name},
        )
        return {"members_processed": 0, "bots_skipped": 1, "errors": 0}

    # Get channel ID from kv_store
    channel_id = await bot_instance.kv_store.get_channel_id(channel_name)
    if not channel_id:
        logger.warning(
            "Bot instance has no channel_id, skipping",
            extra={"channel_name": channel_name},
        )
        return {"members_processed": 0, "bots_skipped": 1, "errors": 0}

    # Fetch channel members from Slack
    try:
        response = await bot_instance.client.conversations_members(channel=channel_id)
        member_ids = response.get("members", [])

        if not isinstance(member_ids, list):
            logger.error(
                "Invalid response from Slack API",
                extra={"channel_name": channel_name, "response": response},
            )
            return {"members_processed": 0, "bots_skipped": 0, "errors": 1}

        logger.info(
            f"Found {len(member_ids)} members in channel",
            extra={"channel_name": channel_name, "member_count": len(member_ids)},
        )

        # Process each member
        for member_id in member_ids:
            if not isinstance(member_id, str):
                logger.warning(
                    "Invalid member_id type",
                    extra={"member_id": member_id, "type": type(member_id)},
                )
                continue

            try:
                # Check if user is a bot - we only want to process human users
                # Use cached user info to reduce API calls
                user = await get_cached_user_info(
                    client=bot_instance.client,
                    kv_store=bot_instance.kv_store,
                    user_id=member_id,
                )

                # If we got None, retry once after a delay (likely rate limited)
                if user is None:
                    logger.warning(
                        "Failed to get user info, retrying after 5s",
                        extra={
                            "channel_name": channel_name,
                            "user_id": member_id,
                        },
                    )
                    await asyncio.sleep(5)
                    user = await get_cached_user_info(
                        client=bot_instance.client,
                        kv_store=bot_instance.kv_store,
                        user_id=member_id,
                    )

                # If still None after retry, skip this user
                if user is None:
                    logger.warning(
                        "Failed to get user info after retry, skipping",
                        extra={
                            "channel_name": channel_name,
                            "user_id": member_id,
                        },
                    )
                    errors += 1
                    continue

                # Skip bot users
                if user.is_bot:
                    logger.debug(
                        "Skipping bot user",
                        extra={
                            "channel_name": channel_name,
                            "user_id": member_id,
                        },
                    )
                    continue

                # Process org user with governance-aware logic
                await _ensure_org_user(
                    bot_server=bot_server,
                    bot_instance=bot_instance,
                    user_id=member_id,
                    is_governance=is_governance,
                    logger=logger,
                )
                members_processed += 1

                logger.info(
                    "Successfully processed member",
                    extra={
                        "channel_name": channel_name,
                        "user_id": member_id,
                        "is_governance": is_governance,
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to process member",
                    extra={
                        "channel_name": channel_name,
                        "user_id": member_id,
                        "error": str(e),
                    },
                )
                errors += 1

    except Exception as e:
        logger.error(
            "Failed to fetch members for channel",
            extra={
                "channel_name": channel_name,
                "error": str(e),
            },
        )
        return {"members_processed": 0, "bots_skipped": 0, "errors": 1}

    return {
        "members_processed": members_processed,
        "bots_skipped": bots_skipped,
        "errors": errors,
    }


async def _ensure_org_user(
    bot_server: CompassBotServer,
    bot_instance: Any,
    user_id: str,
    is_governance: bool,
    logger: Any,
) -> None:
    """Ensure org user exists with proper admin status and create channel link.

    For governance channels: Always set is_org_admin=True, overwriting existing False values
    For non-governance channels: Set is_org_admin=False only if user doesn't exist yet

    Args:
        bot_server: Bot server instance
        bot_instance: Bot instance
        user_id: Slack user ID
        is_governance: Whether this is a governance channel
        logger: Logger instance
    """
    organization_id = bot_instance.bot_config.organization_id

    # Check if org user already exists
    org_user = await bot_server.bot_manager.storage.get_org_user_by_slack_user_id(
        slack_user_id=user_id,
        organization_id=organization_id,
    )

    if org_user:
        if is_governance and not org_user.is_org_admin:
            # Override admin status for governance channels
            logger.info(
                f"Updating org user {org_user.id} to admin status for governance channel",
                extra={
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "org_user_id": org_user.id,
                },
            )
            await bot_server.bot_manager.storage.update_org_user_admin_status(
                slack_user_id=user_id,
                organization_id=organization_id,
                is_org_admin=True,
            )
            # Refresh org_user to get updated admin status
            org_user = await bot_server.bot_manager.storage.get_org_user_by_slack_user_id(
                slack_user_id=user_id,
                organization_id=organization_id,
            )

        if org_user and not org_user.email:
            # Fetch user info to get email and name
            user_info = await get_cached_user_info(
                client=bot_instance.client,
                kv_store=bot_instance.kv_store,
                user_id=user_id,
            )

            if user_info and user_info.email:
                # Only update if we have a valid email from Slack
                email = user_info.email
                real_name = user_info.real_name

                # Update email and name using raw storage access
                storage = bot_server.bot_manager.storage
                if hasattr(storage, "_sql_conn_factory"):
                    from csbot.slackbot.storage.postgresql import sync_to_async

                    @sync_to_async
                    def update_email_and_name():
                        with storage._sql_conn_factory.with_conn() as conn:  # type: ignore
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                UPDATE org_users
                                SET email = %s, name = %s
                                WHERE id = %d
                                """,
                                (email, real_name, org_user.id),
                            )
                            conn.commit()

                    await update_email_and_name()

                    logger.info(
                        f"Updated org user {org_user.id} with email and name",
                        extra={
                            "user_id": user_id,
                            "organization_id": organization_id,
                            "org_user_id": org_user.id,
                            "email": email,
                        },
                    )
            elif not user_info or not user_info.email:
                logger.warning(
                    f"Skipping email update for org user {org_user.id} - no valid email from Slack",
                    extra={
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "org_user_id": org_user.id,
                    },
                )
    else:
        # User doesn't exist - create with appropriate admin status
        user_info = await get_cached_user_info(
            client=bot_instance.client,
            kv_store=bot_instance.kv_store,
            user_id=user_id,
        )

        if not user_info:
            logger.warning(
                "Failed to get user info when creating org user",
                extra={
                    "user_id": user_id,
                    "organization_id": organization_id,
                },
            )
            return

        # Create org user with info from SlackUserInfo
        org_user = await bot_server.bot_manager.storage.add_org_user(
            slack_user_id=user_id,
            email=user_info.email,
            organization_id=organization_id,
            is_org_admin=is_governance,  # Set admin status based on governance
            name=user_info.real_name,
        )

        logger.info(
            f"Created org user {org_user.id if org_user else 'None'} with is_org_admin={is_governance}",
            extra={
                "user_id": user_id,
                "organization_id": organization_id,
                "is_governance": is_governance,
            },
        )


@click.command(name="backfill-channel-members")
@click.argument("config_file", type=click.Path(exists=True))
def backfill_channel_members_command(config_file: str) -> None:
    """Backfill org_users table with existing channel members from Slack.

    This command initializes a bot server and processes all bot instances,
    fetching channel members from Slack and ensuring each human member has
    an org_user record. Bot users are automatically excluded.

    \b
    CONFIG_FILE: Path to csbot configuration YAML file (e.g., compassbot.config.yaml)

    \b
    Examples:
      compass-dev backfill-channel-members config/compassbot.config.yaml
      compass-dev backfill-channel-members config/staging.csbot.config.yaml

    \b
    Note: This command requires Redis, valid Slack tokens, and database connectivity.
    """
    # Load environment variables
    load_dotenv(find_dotenv(usecwd=True), override=True)

    async def run_backfill() -> None:
        logger = structlog.get_logger(__name__)
        logger.info("Loading configuration", extra={"config_path": config_file})

        # Load configuration
        config = load_bot_server_config_from_path(config_file)
        secret_store = create_secret_store(config)
        config_root = Path(config_file).parent.absolute()

        logger.info("Initializing bot server")
        click.echo("Initializing bot server...")

        async with initialize_dynamic_compass_bot_server_for_repl(
            config=config,
            secret_store=secret_store,
            config_root=config_root,
        ) as bot_server:
            if not bot_server.bots:
                logger.error("No bots found in bot server")
                click.echo("Error: No bots found in bot server", err=True)
                return

            logger.info(f"Found {len(bot_server.bots)} bots to process")
            click.echo(f"Found {len(bot_server.bots)} bots to process")
            click.echo("Starting backfill...")

            # Run backfill
            stats = await backfill_channel_members(bot_server)

            # Display results
            click.echo("\n" + "=" * 50)
            click.echo("Backfill completed!")
            click.echo("=" * 50)
            click.echo(f"Total bots processed: {stats['total_bots']}")
            click.echo(f"Bots skipped: {stats['total_bots_skipped']}")
            click.echo(f"Members processed: {stats['total_members_processed']}")
            click.echo(f"Errors encountered: {stats['total_errors']}")

            if stats["total_errors"] > 0:
                click.echo(
                    "\nWarning: Some errors occurred during backfill. Check logs for details.",
                    err=True,
                )

        logger.info("Backfill command completed")

    # Run the async command
    asyncio.run(run_backfill())
