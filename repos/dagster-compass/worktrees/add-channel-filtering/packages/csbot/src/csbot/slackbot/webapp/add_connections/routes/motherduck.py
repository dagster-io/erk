"""MotherDuck warehouse connection routes"""

from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.add_connections.models import (
    MotherduckWarehouseConfig,
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


def motherduck_config_factory(form_data: dict[str, str]) -> MotherduckWarehouseConfig:
    """Create MotherDuck warehouse config from form data"""
    return MotherduckWarehouseConfig(
        database_name=form_data["database_name"],
        access_token=form_data["access_token"],
    )


def add_onboarding_motherduck_routes(app: web.Application, bot_server: "CompassBotServer"):
    # Create factory-generated endpoints
    handle_motherduck_test_connection = create_connection_test_endpoint(
        bot_server, motherduck_config_factory
    )
    handle_motherduck_discover_schemas = create_discover_schemas_endpoint(
        bot_server, motherduck_config_factory
    )
    handle_motherduck_discover_tables = create_discover_tables_endpoint(
        bot_server, motherduck_config_factory
    )
    handle_motherduck_test_table = create_test_table_endpoint(
        bot_server, motherduck_config_factory, get_sql_dialect_from_compass_warehouse_config
    )
    handle_motherduck_save = create_save_connection_endpoint(
        bot_server, motherduck_config_factory, "MotherDuck"
    )

    # Mirror API routes under /api/* for React
    app.router.add_post(
        "/api/onboarding/connections/motherduck/test-connection", handle_motherduck_test_connection
    )
    app.router.add_post(
        "/api/onboarding/connections/motherduck/test-table", handle_motherduck_test_table
    )
    app.router.add_post(
        "/api/onboarding/connections/motherduck/discover-schemas",
        handle_motherduck_discover_schemas,
    )
    app.router.add_post(
        "/api/onboarding/connections/motherduck/discover-tables", handle_motherduck_discover_tables
    )
    app.router.add_post("/api/onboarding/connections/motherduck/save", handle_motherduck_save)
