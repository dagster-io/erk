from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.add_connections.models import (
    BigQueryWarehouseConfig,
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


def bigquery_config_factory(form_data: dict[str, str]) -> BigQueryWarehouseConfig:
    """Create BigQuery warehouse config from form data"""
    # Cast location to BigQueryLocation type
    location = form_data["location"]
    # Note: In a real implementation, you might want to validate this is a valid location
    return BigQueryWarehouseConfig.from_location_and_service_account_json(
        location=location,  # type: ignore
        service_account_json_string=form_data["service_account_json_string"],
    )


def add_onboarding_bigquery_routes(app: web.Application, bot_server: "CompassBotServer"):
    # Create API endpoint handlers for React
    handle_bigquery_test_connection = create_connection_test_endpoint(
        bot_server, bigquery_config_factory
    )
    handle_bigquery_discover_schemas = create_discover_schemas_endpoint(
        bot_server, bigquery_config_factory
    )
    handle_bigquery_discover_tables = create_discover_tables_endpoint(
        bot_server, bigquery_config_factory
    )
    handle_bigquery_test_table = create_test_table_endpoint(
        bot_server, bigquery_config_factory, get_sql_dialect_from_compass_warehouse_config
    )
    handle_bigquery_save = create_save_connection_endpoint(
        bot_server, bigquery_config_factory, "BigQuery"
    )

    app.router.add_post(
        "/api/onboarding/connections/bigquery/test-connection", handle_bigquery_test_connection
    )
    app.router.add_post(
        "/api/onboarding/connections/bigquery/test-table", handle_bigquery_test_table
    )
    app.router.add_post(
        "/api/onboarding/connections/bigquery/discover-schemas", handle_bigquery_discover_schemas
    )
    app.router.add_post(
        "/api/onboarding/connections/bigquery/discover-tables", handle_bigquery_discover_tables
    )
    app.router.add_post("/api/onboarding/connections/bigquery/save", handle_bigquery_save)
