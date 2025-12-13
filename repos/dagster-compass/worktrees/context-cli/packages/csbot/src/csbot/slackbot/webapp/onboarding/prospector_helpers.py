"""Shared helper functions for prospector connection management."""

from typing import TYPE_CHECKING

from csbot.slackbot.slackbot_core import PROSPECTOR_CONNECTION_NAME
from csbot.slackbot.webapp.add_connections.models import (
    JsonConfig,
    compass_warehouse_config_from_json_config,
)

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


async def create_prospector_connection_for_organization(
    bot_server: "CompassBotServer",
    organization_id: int,
) -> None:
    """Create prospector connection for an organization.

    This function creates the shared prospector connection with credentials
    stored in secrets and documentation in the shared prospector contextstore.

    Args:
        bot_server: The bot server instance
        organization_id: The organization to create the connection for

    Raises:
        ValueError: If prospector configuration is missing
    """
    if not bot_server.config.prospector_contextstore_repo:
        raise ValueError("Missing prospector contextstore repo config")

    if not bot_server.config.prospector_data_connection:
        raise ValueError("Missing prospector data connection config")

    # Check if connection already exists
    existing_connections = (
        await bot_server.bot_manager.storage.get_connection_names_for_organization(organization_id)
    )

    if PROSPECTOR_CONNECTION_NAME in existing_connections:
        bot_server.logger.info(f"Prospector connection already exists for org {organization_id}")
        return

    # Convert prospector config to warehouse config
    prospector_config = bot_server.config.prospector_data_connection
    json_config = JsonConfig(type=prospector_config.type, config=prospector_config.config)
    warehouse_config = compass_warehouse_config_from_json_config(json_config)

    bot_server.logger.info(f"Creating prospector connection for org {organization_id}")

    if bot_server.config.db_config.use_encrypted_connection_urls:
        await bot_server.bot_manager.storage.add_connection(
            organization_id=organization_id,
            connection_name=PROSPECTOR_CONNECTION_NAME,
            url="",
            additional_sql_dialect=None,
            data_documentation_contextstore_github_repo=bot_server.config.prospector_contextstore_repo,
            plaintext_url=warehouse_config.to_url(),
        )
    else:
        # Store as secret and use template
        secret_key = f"{PROSPECTOR_CONNECTION_NAME}_{prospector_config.type}_url.txt"
        await bot_server.bot_manager.secret_store.store_secret(
            organization_id, secret_key, warehouse_config.to_url()
        )

        # Create connection URL template
        connection_url = "{{ pull_from_secret_manager_to_string('" + secret_key + "') }}"

        await bot_server.bot_manager.storage.add_connection(
            organization_id=organization_id,
            connection_name=PROSPECTOR_CONNECTION_NAME,
            url=connection_url,
            additional_sql_dialect=None,
            data_documentation_contextstore_github_repo=bot_server.config.prospector_contextstore_repo,
        )

    bot_server.logger.info(f"Created prospector connection for org {organization_id}")
