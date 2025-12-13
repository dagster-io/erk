"""Copy bot and its connections from one environment to another."""

import asyncio
import os
import re
import traceback

import click
import psycopg
from psycopg.rows import dict_row
from slack_sdk.web.async_client import AsyncWebClient

from csbot.slackbot.slack_utils import get_bot_user_id, invite_bot_to_channel
from csbot.slackbot.slackbot_secrets import RenderSecretStore

from .database_config import (
    Environment,
    build_connection_string,
    get_database_password,
)


async def get_channel_id_from_name(
    slack_client: AsyncWebClient, channel_name: str, team_id: str
) -> str | None:
    """Get channel ID from channel name using Slack API.

    Args:
        slack_client: Slack client with appropriate token
        channel_name: Name of the channel (without #)
        team_id: Slack team ID

    Returns:
        Channel ID if found, None otherwise
    """
    try:
        # List all channels and find matching name
        cursor = None
        while True:
            response = await slack_client.conversations_list(
                types="public_channel,private_channel", limit=200, cursor=cursor, team_id=team_id
            )

            if not response.get("ok"):
                return None

            channels = response.get("channels", [])
            for channel in channels:
                if channel.get("name") == channel_name:
                    return channel.get("id")

            # Check if there are more pages
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return None

    except Exception:
        return None


async def invite_bot_to_channels(
    target_bot_token: str,
    slack_admin_token: str,
    channel_name: str,
    governance_alerts_channel: str | None,
    team_id: str,
) -> None:
    """Invite bot to main channel and governance alerts channel.

    Args:
        target_bot_token: Bot token for target environment
        slack_admin_token: Admin token with invite permissions
        channel_name: Main channel name
        governance_alerts_channel: Governance alerts channel name (optional)
        team_id: Slack team ID
    """
    # Get bot user ID
    click.echo()
    click.echo("Getting bot user ID...")
    bot_info = await get_bot_user_id(target_bot_token)

    if not bot_info.get("success"):
        click.echo(f"❌ Failed to get bot user ID: {bot_info.get('error')}", err=True)
        raise ValueError("Failed to get bot user ID")

    bot_user_id = bot_info.get("user_id")
    if not bot_user_id:
        raise ValueError("No user_id in bot info response")

    click.echo(f"Bot User ID: {bot_user_id}")

    # Create admin client to look up channel IDs
    admin_client = AsyncWebClient(token=slack_admin_token)

    # Get main channel ID
    click.echo(f"Looking up channel ID for '{channel_name}'...")
    main_channel_id = await get_channel_id_from_name(admin_client, channel_name, team_id)

    if not main_channel_id:
        click.echo(f"❌ Could not find channel '{channel_name}'", err=True)
        raise ValueError(f"Channel '{channel_name}' not found")

    click.echo(f"Found main channel ID: {main_channel_id}")

    # Invite bot to main channel
    click.echo(f"Inviting bot to main channel '{channel_name}'...")
    result = await invite_bot_to_channel(slack_admin_token, main_channel_id, bot_user_id)

    if result.get("success"):
        click.echo("✅ Successfully invited bot to main channel")
    else:
        error = result.get("error", "unknown error")
        click.echo(f"⚠️  Failed to invite bot to main channel: {error}")

    # Invite bot to governance alerts channel if specified
    if governance_alerts_channel:
        click.echo(f"Looking up channel ID for '{governance_alerts_channel}'...")
        governance_channel_id = await get_channel_id_from_name(
            admin_client, governance_alerts_channel, team_id
        )

        if not governance_channel_id:
            click.echo(f"⚠️  Could not find governance channel '{governance_alerts_channel}'")
        else:
            click.echo(f"Found governance channel ID: {governance_channel_id}")
            click.echo(f"Inviting bot to governance channel '{governance_alerts_channel}'...")
            result = await invite_bot_to_channel(
                slack_admin_token, governance_channel_id, bot_user_id
            )

            if result.get("success"):
                click.echo("✅ Successfully invited bot to governance channel")
            else:
                error = result.get("error", "unknown error")
                click.echo(f"⚠️  Failed to invite bot to governance channel: {error}")


async def copy_bots_impl(
    slack_team_id: str,
    source_env: Environment,
    target_env: Environment,
    target_organization_id: int | None,
    dry_run: bool,
    copy_organization: bool,
    source_render_service_id: str,
    source_render_api_key: str,
    target_render_service_id: str,
    target_render_api_key: str,
    source_secret_encryption_key: str,
    target_secret_encryption_key: str,
    target_bot_token: str,
    slack_admin_token: str,
) -> None:
    """Copy all bots for a slack_team_id from source environment to target environment.

    Args:
        slack_team_id: Slack team ID to identify the bots
        source_env: Source environment ('staging' or 'prod')
        target_env: Target environment ('staging' or 'prod')
        target_organization_id: Organization ID to use in target environment (required if not copying organization)
        dry_run: If True, only show what would be copied without making changes
        copy_organization: If True, copy the organization row and use source organization_id
        source_render_service_id: Render service ID for source environment
        source_render_api_key: Render API key for source environment
        target_render_service_id: Render service ID for target environment
        target_render_api_key: Render API key for target environment
        source_secret_encryption_key: Encryption key for source environment secrets
        target_secret_encryption_key: Encryption key for target environment secrets
        target_bot_token: Bot token for target environment (for invitations)
        slack_admin_token: Admin token for inviting bot to channels
    """
    # Get database passwords
    source_password = get_database_password(source_env)
    target_password = get_database_password(target_env)

    # Build connection strings
    source_conn_string = build_connection_string(source_env, source_password)
    target_conn_string = build_connection_string(target_env, target_password)

    # Connect to source database to fetch all data first
    source_conn = psycopg.connect(source_conn_string)

    try:
        with source_conn.cursor(row_factory=dict_row) as source_cursor:
            # Find all bot instances for this team
            source_cursor.execute(
                """
                SELECT * FROM bot_instances
                WHERE slack_team_id = %s
                """,
                (slack_team_id,),
            )
            bot_instances = source_cursor.fetchall()

            if not bot_instances:
                raise ValueError(f"No bots found with slack_team_id={slack_team_id}")

            # Deduplicate by channel_name (keep first occurrence)
            seen_channels = set()
            unique_bot_instances = []
            duplicates = []
            for bot in bot_instances:
                if bot["channel_name"] not in seen_channels:
                    seen_channels.add(bot["channel_name"])
                    unique_bot_instances.append(bot)
                else:
                    duplicates.append(bot["channel_name"])

            if duplicates:
                click.echo(f"⚠️  Found {len(duplicates)} duplicate bot(s), deduplicating:")
                for dup in duplicates:
                    click.echo(f"    - {dup}")

            bot_instances = unique_bot_instances
            click.echo(f"Found {len(bot_instances)} unique bot(s) in {source_env}")
            for bot in bot_instances:
                click.echo(f"  - {bot['channel_name']}")

            # Get organization from first bot (all bots in same team have same org)
            source_org_id = bot_instances[0]["organization_id"]
            click.echo(f"Source organization_id: {source_org_id}")

            # Get the organization
            source_cursor.execute(
                """
                SELECT * FROM organizations
                WHERE organization_id = %s
                """,
                (source_org_id,),
            )
            organization = source_cursor.fetchone()
            if not organization:
                raise ValueError(f"Organization with id={source_org_id} not found")
            click.echo(
                f"Found organization: {organization['organization_name']} (id: {source_org_id})"
            )

            # Get all connections for this organization
            source_cursor.execute(
                """
                SELECT * FROM connections
                WHERE organization_id = %s
                """,
                (source_org_id,),
            )
            connections = source_cursor.fetchall()
            click.echo(f"Found {len(connections)} connections to copy")

            # Get bot_to_connections and KV entries for all bots
            all_bot_to_connections = []
            all_kv_entries = []

            for bot in bot_instances:
                bot_id = f"{slack_team_id}-{bot['channel_name']}"

                # Get bot_to_connections mappings
                source_cursor.execute(
                    """
                    SELECT * FROM bot_to_connections
                    WHERE bot_id = %s
                    """,
                    (bot_id,),
                )
                btc = source_cursor.fetchall()
                all_bot_to_connections.extend(btc)

                # Get KV entries
                source_cursor.execute(
                    """
                    SELECT * FROM kv
                    WHERE bot_id = %s
                    """,
                    (bot_id,),
                )
                kv = source_cursor.fetchall()
                all_kv_entries.extend(kv)

            click.echo(f"Found {len(all_bot_to_connections)} bot_to_connections mappings")
            click.echo(f"Found {len(all_kv_entries)} KV entries")

    finally:
        source_conn.close()

    # Extract secret keys from connection URLs
    source_secret_store = RenderSecretStore(source_render_service_id, source_render_api_key)
    target_secret_store = RenderSecretStore(target_render_service_id, target_render_api_key)

    secret_keys_to_copy = []
    for conn in connections:
        url = conn["url"]
        # Extract secret key from template: {{ pull_from_secret_manager_to_string('key') }}
        match = re.search(r"pull_from_secret_manager_to_string\(['\"]([^'\"]+)['\"]\)", url)
        if match:
            secret_key = match.group(1)
            secret_keys_to_copy.append((conn["connection_name"], secret_key))
        else:
            click.echo(f"No secret found in connection: {conn['url']}")

    click.echo(f"Found {len(secret_keys_to_copy)} secrets to copy")

    # Get channel information for bot invitations
    click.echo()
    click.echo("Preparing bot invitations...")

    # Get bot user ID
    bot_info = await get_bot_user_id(target_bot_token)
    if not bot_info.get("success"):
        raise ValueError(f"Failed to get bot user ID: {bot_info.get('error')}")

    bot_user_id = bot_info.get("user_id")
    if not bot_user_id:
        raise ValueError("No user_id in bot info response")

    click.echo(f"Bot User ID: {bot_user_id}")

    # Look up channel IDs for all bots
    admin_client = AsyncWebClient(token=slack_admin_token)
    channel_ids = {}

    for bot in bot_instances:
        channel_name = bot["channel_name"]
        click.echo(f"Looking up channel ID for '{channel_name}'...")
        channel_id = await get_channel_id_from_name(admin_client, channel_name, slack_team_id)
        if not channel_id:
            raise ValueError(f"Could not find channel '{channel_name}'")
        channel_ids[channel_name] = channel_id
        click.echo(f"  Found: {channel_id}")

    # Look up governance channel (shared across all bots in same team)
    governance_channel_id = None
    governance_channel_name = bot_instances[0]["governance_alerts_channel"]
    if governance_channel_name:
        click.echo(f"Looking up governance channel ID for '{governance_channel_name}'...")
        governance_channel_id = await get_channel_id_from_name(
            admin_client, governance_channel_name, slack_team_id
        )
        if not governance_channel_id:
            raise ValueError(f"Could not find governance channel '{governance_channel_name}'")
        click.echo(f"  Found: {governance_channel_id}")

    if dry_run:
        click.echo()
        click.echo("🔍 DRY RUN - No changes will be made")
        click.echo()
        click.echo("Would copy to target environment:")
        if copy_organization:
            click.echo("  Target organization ID: (will be auto-generated)")
        else:
            if target_organization_id is None:
                raise ValueError("--target-org-id is required when not using --copy-organization")
            click.echo(f"  Target organization ID: {target_organization_id}")
        click.echo()
        if copy_organization:
            click.echo("Organization to copy:")
            click.echo(f"  - Name: {organization['organization_name']}")
            click.echo(f"  - Industry: {organization['organization_industry']}")
            click.echo(f"  - Stripe Customer ID: {organization['stripe_customer_id']}")
            click.echo(f"  - Stripe Subscription ID: {organization['stripe_subscription_id']}")
            click.echo()
        else:
            click.echo("Organization will NOT be copied (using existing organization)")
            click.echo()
        click.echo(f"Secrets to copy ({len(secret_keys_to_copy)}):")
        for conn_name, secret_key in secret_keys_to_copy:
            click.echo(f"  - {conn_name}: {secret_key}")
        click.echo()
        click.echo(f"Connections to copy ({len(connections)}):")
        for conn in connections:
            click.echo(f"  - {conn['connection_name']}")
        click.echo()
        click.echo(f"Bot instances to copy ({len(bot_instances)}):")
        for bot in bot_instances:
            click.echo(f"  - {bot['channel_name']}")
        click.echo()
        click.echo(f"Bot-to-connection mappings ({len(all_bot_to_connections)}):")
        for btc in all_bot_to_connections:
            click.echo(f"  - {btc['bot_id']} -> {btc['connection_name']}")
        click.echo()
        click.echo(f"KV entries to copy ({len(all_kv_entries)}):")
        if all_kv_entries:
            # Group by bot_id and family
            by_bot = {}
            for kv in all_kv_entries:
                if kv["bot_id"] not in by_bot:
                    by_bot[kv["bot_id"]] = {}
                family = kv["family"]
                if family not in by_bot[kv["bot_id"]]:
                    by_bot[kv["bot_id"]][family] = 0
                by_bot[kv["bot_id"]][family] += 1
            for bot_id, families in by_bot.items():
                total = sum(families.values())
                click.echo(f"  - {bot_id}: {total} entries")
        else:
            click.echo("  (none)")
        click.echo()
        click.echo("Bot invitations:")
        click.echo(f"  Bot User ID: {bot_user_id}")
        for bot in bot_instances:
            channel_id = channel_ids[bot["channel_name"]]
            click.echo(f"  - {bot['channel_name']}: {channel_id}")
        if governance_channel_id:
            click.echo(
                f"  - Governance channel: {governance_channel_name} ({governance_channel_id})"
            )
        click.echo()
        click.echo("Run without --dry-run to execute the copy operation")
        return

    # Now insert everything into target database in a single transaction
    target_conn = psycopg.connect(target_conn_string)

    try:
        with target_conn.cursor(row_factory=dict_row) as target_cursor:
            # Copy organization to target environment if requested
            if copy_organization:
                target_cursor.execute(
                    """
                    INSERT INTO organizations (
                        organization_name, organization_industry,
                        stripe_customer_id, stripe_subscription_id
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING organization_id
                    """,
                    (
                        organization["organization_name"],
                        organization["organization_industry"],
                        organization["stripe_customer_id"],
                        organization["stripe_subscription_id"],
                    ),
                )
                org_result = target_cursor.fetchone()
                if not org_result:
                    raise ValueError("Failed to insert organization")
                final_target_org_id = org_result["organization_id"]
                click.echo(
                    f"Copied organization '{organization['organization_name']}' (new id: {final_target_org_id})"
                )
            else:
                if target_organization_id is None:
                    raise ValueError(
                        "--target-org-id is required when not using --copy-organization"
                    )
                final_target_org_id = target_organization_id
                click.echo(f"Using existing organization_id: {final_target_org_id}")

            # Copy secrets from source to target (now that we have final_target_org_id)
            click.echo("Copying secrets...")
            for conn_name, secret_key in secret_keys_to_copy:
                try:
                    # Check if secret already exists in target
                    old_key = os.environ.get("SECRET_ENCRYPTION_KEY")
                    os.environ["SECRET_ENCRYPTION_KEY"] = target_secret_encryption_key
                    try:
                        await target_secret_store.get_secret_contents(
                            final_target_org_id, secret_key
                        )
                        click.echo(
                            f"  ✓ Secret already exists in target for '{conn_name}': {secret_key}"
                        )
                        continue
                    except Exception:
                        pass
                    finally:
                        if old_key is None:
                            os.environ.pop("SECRET_ENCRYPTION_KEY", None)
                        else:
                            os.environ["SECRET_ENCRYPTION_KEY"] = old_key

                    # Get secret from source (with source encryption key)
                    old_key = os.environ.get("SECRET_ENCRYPTION_KEY")
                    os.environ["SECRET_ENCRYPTION_KEY"] = source_secret_encryption_key
                    try:
                        secret_contents = await source_secret_store.get_secret_contents(
                            source_org_id, secret_key
                        )
                    finally:
                        if old_key is None:
                            os.environ.pop("SECRET_ENCRYPTION_KEY", None)
                        else:
                            os.environ["SECRET_ENCRYPTION_KEY"] = old_key

                    # Store in target with the final target org ID (with target encryption key)
                    old_key = os.environ.get("SECRET_ENCRYPTION_KEY")
                    os.environ["SECRET_ENCRYPTION_KEY"] = target_secret_encryption_key
                    try:
                        await target_secret_store.store_secret(
                            final_target_org_id, secret_key, secret_contents
                        )
                    finally:
                        if old_key is None:
                            os.environ.pop("SECRET_ENCRYPTION_KEY", None)
                        else:
                            os.environ["SECRET_ENCRYPTION_KEY"] = old_key

                    click.echo(f"  Copied secret for connection '{conn_name}': {secret_key}")
                except Exception as e:
                    click.echo(f"  ❌ Failed to copy secret for '{conn_name}': {e}")
                    traceback.print_exc()
                    raise

            # Copy connections to target environment
            for conn in connections:
                # Insert connection into target
                target_cursor.execute(
                    """
                    INSERT INTO connections (
                        organization_id, connection_name, url, init_sql, additional_sql_dialect
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        final_target_org_id,
                        conn["connection_name"],
                        conn["url"],
                        conn["init_sql"],
                        conn["additional_sql_dialect"],
                    ),
                )
                click.echo(f"  Copied connection '{conn['connection_name']}')")

            # Copy all bot instances to target
            click.echo("Copying bot instances...")
            for bot in bot_instances:
                target_cursor.execute(
                    """
                    INSERT INTO bot_instances (
                        organization_id, slack_team_id, channel_name, bot_email,
                        contextstore_github_repo, governance_alerts_channel
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        final_target_org_id,
                        bot["slack_team_id"],
                        bot["channel_name"],
                        bot["bot_email"],
                        bot["contextstore_github_repo"],
                        bot["governance_alerts_channel"],
                    ),
                )
                click.echo(f"  Copied bot_instance: {bot['channel_name']}")

            # Copy bot_to_connections with bot_id and connection_name
            click.echo("Copying bot_to_connections...")
            for btc in all_bot_to_connections:
                target_cursor.execute(
                    """
                    INSERT INTO bot_to_connections (
                        bot_id, connection_name, organization_id
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (btc["bot_id"], btc["connection_name"], final_target_org_id),
                )
            click.echo(f"  Copied {len(all_bot_to_connections)} mappings")

            # Copy KV entries
            click.echo("Copying KV entries...")
            for kv in all_kv_entries:
                target_cursor.execute(
                    """
                    INSERT INTO kv (
                        bot_id, family, key, value, expires_at_seconds
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (kv["bot_id"], kv["family"], kv["key"], kv["value"], kv["expires_at_seconds"]),
                )
            if all_kv_entries:
                click.echo(f"  Copied {len(all_kv_entries)} KV entries")

            # Commit the transaction
            target_conn.commit()
            click.echo()
            click.echo(
                f"✅ Successfully copied {len(bot_instances)} bot(s) from {source_env} to {target_env} with organization_id={final_target_org_id}"
            )
            click.echo(f"   Organization: {organization['organization_name']}")
            click.echo(f"   Slack Team ID: {slack_team_id}")
            if copy_organization:
                click.echo("   Copied organization")
            click.echo(f"   Copied {len(secret_keys_to_copy)} secrets")
            click.echo(f"   Copied {len(connections)} connections")
            click.echo(f"   Copied {len(bot_instances)} bot instances")
            click.echo(f"   Copied {len(all_bot_to_connections)} bot-to-connection mappings")
            click.echo(f"   Copied {len(all_kv_entries)} KV entries")

    except Exception as e:
        target_conn.rollback()
        click.echo(f"\n❌ Transaction rolled back due to error: {e}")
        traceback.print_exc()
        raise
    finally:
        target_conn.close()

    # Invite bot to all channels
    click.echo()
    click.echo("Inviting bot to channels...")

    # Invite to each bot's main channel
    for bot in bot_instances:
        channel_name = bot["channel_name"]
        channel_id = channel_ids[channel_name]
        click.echo(f"Inviting bot to '{channel_name}' ({channel_id})...")
        result = await invite_bot_to_channel(slack_admin_token, channel_id, bot_user_id)
        if result.get("success"):
            click.echo("  ✅ Successfully invited")
        else:
            error = result.get("error", "unknown error")
            raise ValueError(f"Failed to invite bot to channel '{channel_name}': {error}")

    # Invite to governance channel (once, shared across all bots)
    if governance_channel_id:
        click.echo(
            f"Inviting bot to governance channel '{governance_channel_name}' ({governance_channel_id})..."
        )
        result = await invite_bot_to_channel(slack_admin_token, governance_channel_id, bot_user_id)
        if result.get("success"):
            click.echo("  ✅ Successfully invited")
        else:
            error = result.get("error", "unknown error")
            raise ValueError(f"Failed to invite bot to governance channel: {error}")


@click.command()
@click.option(
    "--slack-team-id",
    required=True,
    help="Slack team ID to identify the bots to copy",
)
@click.option(
    "--source",
    type=click.Choice(["staging", "prod"]),
    required=True,
    help="Source environment to copy from",
)
@click.option(
    "--target",
    type=click.Choice(["staging", "prod"]),
    required=True,
    help="Target environment to copy to",
)
@click.option(
    "--target-org-id",
    type=int,
    help="Organization ID to use in target environment (required if not using --copy-organization)",
)
@click.option(
    "--copy-organization",
    is_flag=True,
    help="Copy the organization row (uses source organization_id)",
)
@click.option(
    "--source-render-service-id",
    required=True,
    help="Render service ID for source environment",
)
@click.option(
    "--source-render-api-key",
    required=True,
    help="Render API key for source environment",
)
@click.option(
    "--target-render-service-id",
    required=True,
    help="Render service ID for target environment",
)
@click.option(
    "--target-render-api-key",
    required=True,
    help="Render API key for target environment",
)
@click.option(
    "--source-secret-encryption-key",
    required=True,
    help="Secret encryption key for source environment",
)
@click.option(
    "--target-secret-encryption-key",
    required=True,
    help="Secret encryption key for target environment",
)
@click.option(
    "--target-bot-token",
    required=True,
    help="Target environment bot token (for inviting bot to channels)",
)
@click.option(
    "--slack-admin-token",
    required=True,
    help="Slack admin token with admin.conversations:write scope (for inviting bot)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be copied without making any changes",
)
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm the copy operation",
)
def copy_bot(
    slack_team_id: str,
    source: Environment,
    target: Environment,
    target_org_id: int | None,
    copy_organization: bool,
    source_render_service_id: str,
    source_render_api_key: str,
    target_render_service_id: str,
    target_render_api_key: str,
    source_secret_encryption_key: str,
    target_secret_encryption_key: str,
    target_bot_token: str,
    slack_admin_token: str,
    dry_run: bool,
    confirm: bool,
) -> None:
    """Copy all bots for a Slack team from one environment to another.

    This command copies ALL bots with the given slack_team_id:
    - Organization row (if --copy-organization is used)
    - All connections for the organization
    - All bot_instances rows
    - All bot_to_connections mappings
    - All KV entries
    - Invites bot to all channels

    Examples:
        # Copy with existing organization
        compass-dev copy-bot \\
            --slack-team-id T01234567 \\
            --source staging \\
            --target prod \\
            --target-org-id 42 \\
            --source-render-service-id srv-... \\
            --target-render-service-id srv-... \\
            --source-render-api-key rnd_... \\
            --target-render-api-key rnd_... \\
            --source-secret-encryption-key key1 \\
            --target-secret-encryption-key key2 \\
            --target-bot-token xoxb-... \\
            --slack-admin-token xoxp-... \\
            --confirm

        # Copy with organization (uses source org ID)
        compass-dev copy-bot \\
            --slack-team-id T01234567 \\
            --source staging \\
            --target prod \\
            --copy-organization \\
            --source-render-service-id srv-... \\
            --target-render-service-id srv-... \\
            --source-render-api-key rnd_... \\
            --target-render-api-key rnd_... \\
            --source-secret-encryption-key key1 \\
            --target-secret-encryption-key key2 \\
            --target-bot-token xoxb-... \\
            --slack-admin-token xoxp-... \\
            --confirm
    """
    if source == target:
        click.echo("❌ Error: Source and target environments must be different", err=True)
        raise click.Abort()

    # Validate that target_org_id is provided if not copying organization
    if not copy_organization and target_org_id is None:
        click.echo(
            "❌ Error: --target-org-id is required when not using --copy-organization", err=True
        )
        raise click.Abort()

    if not dry_run and not confirm:
        click.echo("⚠️  This will copy the bot and all its connections to a new environment.")
        click.echo(f"   Source: {source}")
        click.echo(f"   Target: {target}")
        click.echo(f"   Target organization ID: {target_org_id}")
        click.echo()
        click.echo("   Add --confirm flag to proceed with the copy operation.")
        click.echo("   Or add --dry-run to see what would be copied.")
        raise click.Abort()

    try:
        asyncio.run(
            copy_bots_impl(
                slack_team_id,
                source,
                target,
                target_org_id,
                dry_run,
                copy_organization,
                source_render_service_id,
                source_render_api_key,
                target_render_service_id,
                target_render_api_key,
                source_secret_encryption_key,
                target_secret_encryption_key,
                target_bot_token,
                slack_admin_token,
            )
        )
    except ValueError as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}", err=True)
        traceback.print_exc()
        raise click.Abort()
