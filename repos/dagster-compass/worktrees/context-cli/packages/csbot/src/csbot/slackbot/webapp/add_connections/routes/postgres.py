"""PostgreSQL warehouse connection routes"""

from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.webapp.add_connections.models import (
    PostgresWarehouseConfig,
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


def postgres_config_factory(form_data: dict[str, str]) -> PostgresWarehouseConfig:
    """Create PostgreSQL warehouse config from form data"""
    return PostgresWarehouseConfig(
        host=form_data["host"],
        port=int(form_data["port"]) if form_data.get("port") else 5432,
        username=form_data["username"],
        password=form_data["password"],
        database=form_data["database"],
    )


def add_onboarding_postgres_routes(app: web.Application, bot_server: "CompassBotServer"):
    # Create API endpoint handlers for React
    handle_postgres_test_connection = create_connection_test_endpoint(
        bot_server, postgres_config_factory
    )
    handle_postgres_discover_schemas = create_discover_schemas_endpoint(
        bot_server, postgres_config_factory
    )
    handle_postgres_discover_tables = create_discover_tables_endpoint(
        bot_server, postgres_config_factory
    )
    handle_postgres_test_table = create_test_table_endpoint(
        bot_server, postgres_config_factory, get_sql_dialect_from_compass_warehouse_config
    )
    handle_postgres_save = create_save_connection_endpoint(
        bot_server, postgres_config_factory, "PostgreSQL"
    )

    app.router.add_post(
        "/api/onboarding/connections/postgres/test-connection", handle_postgres_test_connection
    )
    app.router.add_post(
        "/api/onboarding/connections/postgres/test-table", handle_postgres_test_table
    )
    app.router.add_post(
        "/api/onboarding/connections/postgres/discover-schemas", handle_postgres_discover_schemas
    )
    app.router.add_post(
        "/api/onboarding/connections/postgres/discover-tables", handle_postgres_discover_tables
    )
    app.router.add_post("/api/onboarding/connections/postgres/save", handle_postgres_save)
