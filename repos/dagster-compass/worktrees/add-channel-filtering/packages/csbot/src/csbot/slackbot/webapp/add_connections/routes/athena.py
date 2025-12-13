from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.add_connections.models import (
    AthenaWarehouseConfig,
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


def athena_config_factory(form_data: dict[str, str]) -> AthenaWarehouseConfig:
    """Create Athena warehouse config from form data"""
    return AthenaWarehouseConfig(
        aws_access_key_id=form_data["aws_access_key_id"],
        aws_secret_access_key=form_data["aws_secret_access_key"],
        region=form_data["region"],
        s3_staging_dir=form_data["s3_staging_dir"],
        query_engine=form_data["query_engine"],  # type: ignore
    )


def add_onboarding_athena_routes(app: web.Application, bot_server: "CompassBotServer"):
    # Create API endpoint handlers for React
    handle_athena_test_connection = create_connection_test_endpoint(
        bot_server, athena_config_factory
    )
    handle_athena_discover_schemas = create_discover_schemas_endpoint(
        bot_server, athena_config_factory
    )
    handle_athena_discover_tables = create_discover_tables_endpoint(
        bot_server, athena_config_factory
    )
    handle_athena_test_table = create_test_table_endpoint(
        bot_server, athena_config_factory, get_sql_dialect_from_compass_warehouse_config
    )
    handle_athena_save = create_save_connection_endpoint(
        bot_server, athena_config_factory, "Athena"
    )

    app.router.add_post(
        "/api/onboarding/connections/athena/test-connection", handle_athena_test_connection
    )
    app.router.add_post("/api/onboarding/connections/athena/test-table", handle_athena_test_table)
    app.router.add_post(
        "/api/onboarding/connections/athena/discover-schemas", handle_athena_discover_schemas
    )
    app.router.add_post(
        "/api/onboarding/connections/athena/discover-tables", handle_athena_discover_tables
    )
    app.router.add_post("/api/onboarding/connections/athena/save", handle_athena_save)
