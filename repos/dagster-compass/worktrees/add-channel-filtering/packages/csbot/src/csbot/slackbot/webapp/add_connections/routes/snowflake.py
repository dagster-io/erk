from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.add_connections.models import (
    SnowflakePasswordCredential,
    SnowflakePrivateKeyCredential,
    SnowflakeWarehouseConfig,
    get_sql_dialect_from_compass_warehouse_config,
)
from csbot.slackbot.webapp.add_connections.routes.warehouse_factory import (
    create_connection_test_endpoint,
    create_discover_schemas_endpoint,
    create_discover_tables_endpoint,
    create_save_connection_endpoint,
    create_test_table_endpoint,
)

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassBotServer


def snowflake_config_factory(form_data: dict[str, str]) -> SnowflakeWarehouseConfig:
    """Create Snowflake warehouse config from form data"""
    # Build credential object
    if form_data.get("credential_type") == "password":
        credential = SnowflakePasswordCredential(type="password", password=form_data["password"])
    elif form_data.get("credential_type") == "private_key":
        credential = SnowflakePrivateKeyCredential(
            type="private_key",
            private_key_file=form_data["private_key_file"],
            key_password=form_data.get("key_password") or None,
        )
    else:
        raise ValueError("Invalid credential type")

    return SnowflakeWarehouseConfig(
        account_id=form_data["account_id"],
        username=form_data["username"],
        credential=credential,
        warehouse=form_data["warehouse"],
        role=form_data["role"],
        region=form_data["region"],
    )


def add_onboarding_snowflake_routes(app: web.Application, bot_server: "CompassBotServer"):
    # Create API endpoint handlers for React
    handle_snowflake_test_connection = create_connection_test_endpoint(
        bot_server, snowflake_config_factory
    )
    handle_snowflake_discover_schemas = create_discover_schemas_endpoint(
        bot_server, snowflake_config_factory
    )
    handle_snowflake_discover_tables = create_discover_tables_endpoint(
        bot_server, snowflake_config_factory
    )
    handle_snowflake_test_table = create_test_table_endpoint(
        bot_server, snowflake_config_factory, get_sql_dialect_from_compass_warehouse_config
    )
    handle_snowflake_save = create_save_connection_endpoint(
        bot_server, snowflake_config_factory, "Snowflake"
    )

    app.router.add_post(
        "/api/onboarding/connections/snowflake/test-connection", handle_snowflake_test_connection
    )
    app.router.add_post(
        "/api/onboarding/connections/snowflake/test-table", handle_snowflake_test_table
    )
    app.router.add_post(
        "/api/onboarding/connections/snowflake/discover-schemas", handle_snowflake_discover_schemas
    )
    app.router.add_post(
        "/api/onboarding/connections/snowflake/discover-tables", handle_snowflake_discover_tables
    )
    app.router.add_post("/api/onboarding/connections/snowflake/save", handle_snowflake_save)
