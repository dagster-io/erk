from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.add_connections.models import (
    DatabricksOAuthCredential,
    DatabricksPersonalAccessTokenCredential,
    DatabricksWarehouseConfig,
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


def databricks_config_factory(form_data: dict[str, str]) -> DatabricksWarehouseConfig:
    """Create Databricks warehouse config from form data"""
    credential_type = form_data.get("credential_type")
    if credential_type == "personal_access_token":
        credential = DatabricksPersonalAccessTokenCredential(
            type="personal_access_token",
            personal_access_token=form_data["personal_access_token"],
        )
    elif credential_type == "oauth":
        credential = DatabricksOAuthCredential(
            type="oauth",
            client_id=form_data["client_id"],
            client_secret=form_data["client_secret"],
        )
    else:
        raise ValueError("Invalid credential type. Must be 'personal_access_token' or 'oauth'")

    return DatabricksWarehouseConfig(
        server_hostname=form_data["server_hostname"],
        http_path=form_data["http_path"],
        credential=credential,
    )


def add_onboarding_databricks_routes(app: web.Application, bot_server: "CompassBotServer"):
    # Create API endpoint handlers for React
    handle_databricks_test_connection = create_connection_test_endpoint(
        bot_server, databricks_config_factory
    )
    handle_databricks_discover_schemas = create_discover_schemas_endpoint(
        bot_server, databricks_config_factory
    )
    handle_databricks_discover_tables = create_discover_tables_endpoint(
        bot_server, databricks_config_factory
    )
    handle_databricks_test_table = create_test_table_endpoint(
        bot_server, databricks_config_factory, get_sql_dialect_from_compass_warehouse_config
    )
    handle_databricks_save = create_save_connection_endpoint(
        bot_server, databricks_config_factory, "Databricks"
    )

    app.router.add_post(
        "/api/onboarding/connections/databricks/test-connection", handle_databricks_test_connection
    )
    app.router.add_post(
        "/api/onboarding/connections/databricks/test-table", handle_databricks_test_table
    )
    app.router.add_post(
        "/api/onboarding/connections/databricks/discover-schemas",
        handle_databricks_discover_schemas,
    )
    app.router.add_post(
        "/api/onboarding/connections/databricks/discover-tables", handle_databricks_discover_tables
    )
    app.router.add_post("/api/onboarding/connections/databricks/save", handle_databricks_save)
