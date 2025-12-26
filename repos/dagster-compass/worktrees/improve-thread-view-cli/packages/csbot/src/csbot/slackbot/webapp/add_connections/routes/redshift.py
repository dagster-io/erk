from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.add_connections.models import (
    RedshiftWarehouseConfig,
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
    from csbot.slackbot.bot_server.bot_server import CompassBotServer


def redshift_config_factory(form_data: dict[str, str]) -> RedshiftWarehouseConfig:
    """Create Redshift warehouse config from form data"""
    # Debug: Log the form data to understand what's being submitted
    print(f"DEBUG: Redshift form data keys: {list(form_data.keys())}")
    print(f"DEBUG: Redshift form data: {form_data}")

    # Extract database name from form data
    database = form_data.get("database")

    # If no database field, try to extract from a table name if that's what we have
    if not database and "tables" in form_data:
        table_name = form_data["tables"]
        # Extract database part from fully qualified table name (database.schema.table)
        if "." in table_name:
            database = table_name.split(".")[0]
        else:
            database = table_name

    if not database:
        raise ValueError("Database name is required but not provided in form data")

    return RedshiftWarehouseConfig(
        host=form_data["host"],
        port=int(form_data["port"]) if form_data.get("port") else 5439,
        username=form_data["username"],
        password=form_data["password"],
        database=database,
    )


def add_onboarding_redshift_routes(app: web.Application, bot_server: "CompassBotServer"):
    # Create API endpoint handlers for React
    handle_redshift_test_connection = create_connection_test_endpoint(
        bot_server, redshift_config_factory
    )
    handle_redshift_discover_schemas = create_discover_schemas_endpoint(
        bot_server, redshift_config_factory
    )
    handle_redshift_discover_tables = create_discover_tables_endpoint(
        bot_server, redshift_config_factory
    )
    handle_redshift_test_table = create_test_table_endpoint(
        bot_server, redshift_config_factory, get_sql_dialect_from_compass_warehouse_config
    )
    handle_redshift_save = create_save_connection_endpoint(
        bot_server, redshift_config_factory, "Redshift"
    )

    app.router.add_post(
        "/api/onboarding/connections/redshift/test-connection", handle_redshift_test_connection
    )
    app.router.add_post(
        "/api/onboarding/connections/redshift/test-table", handle_redshift_test_table
    )
    app.router.add_post(
        "/api/onboarding/connections/redshift/discover-schemas", handle_redshift_discover_schemas
    )
    app.router.add_post(
        "/api/onboarding/connections/redshift/discover-tables", handle_redshift_discover_tables
    )
    app.router.add_post("/api/onboarding/connections/redshift/save", handle_redshift_save)
