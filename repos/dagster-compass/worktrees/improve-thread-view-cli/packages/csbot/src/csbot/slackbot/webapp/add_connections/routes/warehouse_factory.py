"""Generic factory methods for warehouse connection endpoints"""

import asyncio
import json
import re
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, NamedTuple

import jwt
import structlog
from aiohttp import BodyPartReader, web

from csbot.agents.factory import create_agent_from_config
from csbot.agents.messages import AgentTextMessage
from csbot.slackbot.bot_server.bot_server import BotKey
from csbot.slackbot.slackbot_core import AIConfig
from csbot.slackbot.webapp.add_connections.models import (
    CompassWarehouseConfig,
    TableInfo,
)
from csbot.slackbot.webapp.add_connections.routes.shared import get_unauthorized_message
from csbot.slackbot.webapp.security import ensure_token_is_valid

if TYPE_CHECKING:
    from csbot.agents.messages import AgentMessage
    from csbot.slackbot.channel_bot.bot import CompassBotServer
    from csbot.slackbot.webapp.add_connections.models import ListTablesResult


class ConnectionTokenData(NamedTuple):
    """Data stored in connection JWT token.

    Stores warehouse connection configuration for later use during channel selection.
    No bot_id needed - channel/bot selection happens after this token is created.
    """

    warehouse_url: str
    warehouse_type: str
    connection_name: str
    table_names: list[str]

    def to_jwt(self, secret: str, expiry_seconds: int = 3600) -> str:
        """Encode connection data as JWT token.

        Args:
            secret: JWT secret key for encoding
            expiry_seconds: Token expiration time in seconds (default 1 hour)

        Returns:
            Encoded JWT token string
        """
        payload = {
            "warehouse_url": self.warehouse_url,
            "warehouse_type": self.warehouse_type,
            "connection_name": self.connection_name,
            "table_names": self.table_names,
            "exp": int(time.time()) + expiry_seconds,
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    @classmethod
    def from_jwt(cls, token: str, secret: str) -> "ConnectionTokenData":
        """Decode connection data from JWT token.

        Args:
            token: JWT token string to decode
            secret: JWT secret key for decoding

        Returns:
            ConnectionTokenData instance

        Raises:
            jwt.InvalidTokenError: If token is invalid or expired
            ValueError: If required fields are missing from token
        """
        payload = jwt.decode(token, secret, algorithms=["HS256"])

        # Validate required fields
        required_fields = ["warehouse_url", "warehouse_type", "connection_name"]
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            raise ValueError(f"Missing required fields in token: {', '.join(missing_fields)}")

        return cls(
            warehouse_url=payload["warehouse_url"],
            warehouse_type=payload["warehouse_type"],
            connection_name=payload["connection_name"],
            table_names=payload.get("table_names", []),
        )


logger = structlog.get_logger(__name__)

WarehouseConfigFactory = Callable[[dict[str, str]], CompassWarehouseConfig]
MAX_TABLE_COLUMNS = 150

# Limit number of tables we recommend to minimize the onboarding time
MAX_RECOMMENDED_ONBOARDING_TABLES = 25


async def parse_request_data(request: web.Request) -> dict[str, str]:
    """Parse request data from either JSON or multipart form encoding.

    Args:
        request: The aiohttp request object

    Returns:
        Dictionary of parsed data from either JSON or form submission
    """
    content_type = request.headers.get("Content-Type", "")

    if "application/json" in content_type:
        # Parse JSON body
        return await request.json()
    else:
        # Parse multipart form data
        reader = await request.multipart()
        form_data = {}

        async for field in reader:
            if isinstance(field, BodyPartReader) and field.name:
                form_data[field.name] = await field.text()

        return form_data


class ConnectionCreationResult(NamedTuple):
    """Result of creating a warehouse connection."""

    success: bool
    connection_name: str


async def get_table_recommendations(ai_config: AIConfig, tables: list[TableInfo]) -> set[str]:
    """Use AI to recommend priority tables based on business value"""
    if not tables:
        return set()

    try:
        # Format table list for AI analysis
        table_list = []
        for table in tables[:2048]:  # Limit to avoid token overflow
            if table.description:
                table_list.append(f"- {table.name}: {table.description}")
            else:
                table_list.append(f"- {table.name}")

        table_text = "\n".join(table_list)

        # Create AI prompt for table analysis
        system_prompt = f"""You are an expert data analyst helping identify the most valuable tables for business analytics.

Focus on tables that contain:
1. Sales data (revenue, deals, transactions, orders, purchases)
2. Customer data (users, accounts, contacts, demographics)
3. Support data (tickets, issues, feedback, satisfaction)
4. Marketing data (campaigns, leads, conversions, attribution)
5. Usage/product analytics (events, sessions, features, adoption)
6. Financial data (billing, subscriptions, payments, accounting)
7. Operational data (inventory, logistics, performance metrics)

Prioritize tables that are likely to:
- Drive business decisions
- Track key performance indicators
- Enable revenue analysis
- Support customer insights
- Measure product success

Limit the number of recommended tables to a maximum of {MAX_RECOMMENDED_ONBOARDING_TABLES}, taking the highest priority tables. It is acceptable to return fewer than {MAX_RECOMMENDED_ONBOARDING_TABLES}.

Return ONLY a JSON array of table names that are high priority for business analytics. No explanations, just the JSON array."""

        user_message = f"Analyze these tables and return the names of high-priority tables for business analytics:\n\n{table_text}"

        # Get AI recommendations
        messages: list[AgentMessage] = [AgentTextMessage(role="user", content=user_message)]

        # Create AnthropicAgent for this request
        agent = create_agent_from_config(ai_config)
        response = await agent.create_completion(
            model=agent.model,
            system=system_prompt,
            messages=messages,
            max_tokens=32000,
        )

        # Parse JSON response
        try:
            match = re.search(r"(\[.*?\])", response, re.DOTALL)
            if not match:
                raise ValueError("No JSON found")
            recommended_tables = json.loads(match.group(1).strip())
            if not isinstance(recommended_tables, list):
                raise ValueError("JSON is not a list")
            return set(recommended_tables)
        except Exception:
            import traceback

            traceback.print_exc()
            logger.warning("Failed to parse AI table recommendations JSON", response=response)

        # Clean up agent
        await agent.close()

    except Exception as e:
        logger.warning("Failed to get AI table recommendations", error=str(e))

    return set()


async def test_connection(logs: list[str], warehouse_config: CompassWarehouseConfig):
    logs.append("🔄 Running basic connection test...")
    logs.append("  SQL: SELECT 1")
    await asyncio.to_thread(warehouse_config.run_sql_query, "SELECT 1")
    logs.append("📈 Basic connection test successful.")


def create_connection_test_endpoint(
    bot_server: "CompassBotServer", warehouse_config_factory: WarehouseConfigFactory
) -> Callable[[web.Request], Any]:
    """Create a basic connection test endpoint (SELECT 1)"""

    async def handle_basic_test(request: web.Request) -> web.Response:
        await ensure_token_is_valid(
            bot_server,
            get_unauthorized_message,
            request,
            require_user=False,
        )

        try:
            data = await parse_request_data(request)

            # Create warehouse config
            try:
                warehouse_config = warehouse_config_factory(data)
            except Exception as e:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"Invalid configuration: {str(e)}",
                        "logs": [],
                    }
                )

            # Test basic connection (SELECT 1)
            logs = []
            try:
                await test_connection(logs, warehouse_config)
                # Generate connection name for the frontend
                connection_name = warehouse_config.get_connection_name()
                return web.json_response(
                    {"success": True, "logs": logs, "connection_name": connection_name}
                )
            except Exception as e:
                bot_server.logger.error(f"Basic connection test failed: {e}", exc_info=True)
                logs.append("Basic connection test failed")
                return web.json_response(
                    {"success": False, "error": "Connection test failed", "logs": logs}
                )

        except Exception as e:
            bot_server.logger.error(f"Invalid form data in basic test: {e}", exc_info=True)
            return web.json_response({"success": False, "error": "Invalid form data", "logs": []})

    return handle_basic_test


async def list_schemas(warehouse_config: CompassWarehouseConfig) -> list[str]:
    return await asyncio.to_thread(warehouse_config.list_schemas)


def create_discover_schemas_endpoint(
    bot_server: "CompassBotServer",
    warehouse_config_factory: WarehouseConfigFactory,
) -> Callable[[web.Request], Any]:
    """Create schema discovery endpoint"""

    async def handle_discover_schemas(request: web.Request) -> web.Response:
        await ensure_token_is_valid(
            bot_server,
            get_unauthorized_message,
            request,
            require_user=False,
        )

        try:
            data = await parse_request_data(request)

            # Create warehouse config
            try:
                warehouse_config = warehouse_config_factory(data)
            except Exception as e:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"Invalid configuration: {str(e)}",
                    }
                )

            # Discover schemas
            try:
                schemas = await list_schemas(warehouse_config)
                return web.json_response({"success": True, "schemas": schemas})
            except Exception as e:
                bot_server.logger.error(f"Failed to discover schemas: {e}", exc_info=True)
                return web.json_response({"success": False, "error": "Failed to discover schemas"})

        except Exception as e:
            bot_server.logger.error(f"Invalid form data in discover schemas: {e}", exc_info=True)
            return web.json_response({"success": False, "error": "Invalid form data"})

    return handle_discover_schemas


async def list_tables(
    bot_server: "CompassBotServer",
    warehouse_config: CompassWarehouseConfig,
    selected_schemas: list[str] | None,
) -> dict[str, Any]:
    result: ListTablesResult = await asyncio.to_thread(
        warehouse_config.list_tables, selected_schemas
    )

    table_infos = sorted(result.all_tables, key=lambda t: t.name)

    # Get AI recommendations for priority tables
    try:
        # Get API key from config
        api_config = bot_server.config.ai_config
        recommended_table_names = await get_table_recommendations(api_config, table_infos)
    except Exception as e:
        # token overflow most likely
        logger.warning("Failed to get table recommendations", error=str(e))
        recommended_table_names = set()

    # Create table data with recommendations
    recommended_tables = []
    regular_tables = []

    for table in table_infos:
        table_data = {
            "name": table.name,
            "description": table.description,
            "recommended": table.name in recommended_table_names,
        }
        if table.name in recommended_table_names:
            recommended_tables.append(table_data)
        else:
            regular_tables.append(table_data)

    # Prepare schema warnings for failed schemas
    schema_warnings = []
    for schema_result in result.schema_results:
        if not schema_result.success:
            schema_warnings.append(
                {"schema": schema_result.schema_name, "error": schema_result.error}
            )

    # Sort recommended tables first, then regular tables
    return {
        "tables": recommended_tables + regular_tables,
        "schema_warnings": schema_warnings,
        "success": result.success,
        "error": result.error,
    }


def create_discover_tables_endpoint(
    bot_server: "CompassBotServer",
    warehouse_config_factory: WarehouseConfigFactory,
) -> Callable[[web.Request], Any]:
    """Create table discovery endpoint"""

    async def handle_discover_tables(request: web.Request) -> web.Response:
        await ensure_token_is_valid(
            bot_server,
            get_unauthorized_message,
            request,
            require_user=False,
        )

        try:
            data = await parse_request_data(request)

            # Create warehouse config
            try:
                warehouse_config = warehouse_config_factory(data)
            except Exception as e:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"Invalid configuration: {str(e)}",
                    }
                )

            # Discover tables
            try:
                # Check if selected schemas were provided
                selected_schemas = None
                if "selected_schemas" in data:
                    # If from JSON, selected_schemas is already parsed; if from form, it's JSON string
                    selected_schemas_value = data["selected_schemas"]
                    if isinstance(selected_schemas_value, str):
                        selected_schemas = json.loads(selected_schemas_value)
                    else:
                        selected_schemas = selected_schemas_value

                result = await list_tables(bot_server, warehouse_config, selected_schemas)

                return web.json_response(result)
            except Exception as e:
                bot_server.logger.error(f"Failed to discover tables: {e}", exc_info=True)
                return web.json_response({"success": False, "error": "Failed to discover tables"})

        except Exception as e:
            bot_server.logger.error(f"Invalid form data in discover tables: {e}", exc_info=True)
            return web.json_response({"success": False, "error": "Invalid form data"})

    return handle_discover_tables


async def test_table(
    logs: list[str],
    warehouse_config: CompassWarehouseConfig,
    table_name: str,
    get_sql_dialect: Callable[[CompassWarehouseConfig], str],
) -> int:
    # Test table access
    dialect = get_sql_dialect(warehouse_config)
    if dialect == "bigquery":
        sql_query = f"SELECT * FROM `{table_name}` LIMIT 1"
    else:
        sql_query = f"SELECT * FROM {table_name} LIMIT 1"

    logs.append(f"Testing table access: {table_name}")
    logs.append(f"SQL: {sql_query}")

    result = await asyncio.to_thread(warehouse_config.run_sql_query, sql_query)
    num_columns = len(result[0]) if result else 0
    logs.append(
        f"Query returned {len(result)} row{'' if len(result) == 1 else 's'} with {num_columns} column{'' if num_columns == 1 else 's'}"
    )
    return num_columns


def create_test_table_endpoint(
    bot_server: "CompassBotServer",
    warehouse_config_factory: WarehouseConfigFactory,
    get_sql_dialect: Callable[[CompassWarehouseConfig], str],
) -> Callable[[web.Request], Any]:
    """Create individual table test endpoint"""

    async def handle_test_table(request: web.Request) -> web.Response:
        await ensure_token_is_valid(
            bot_server,
            get_unauthorized_message,
            request,
            require_user=False,
        )

        try:
            data = await parse_request_data(request)

            # Create warehouse config
            try:
                warehouse_config = warehouse_config_factory(data)
            except Exception as e:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"Invalid configuration: {str(e)}",
                        "logs": [],
                    }
                )

            table_name = data["table_name"]
            logs = []

            try:
                num_columns = await test_table(logs, warehouse_config, table_name, get_sql_dialect)

                if num_columns > MAX_TABLE_COLUMNS:
                    logs.append(
                        f"❌ We're currently limiting imports to tables with fewer than {MAX_TABLE_COLUMNS} columns"
                    )
                    return web.json_response(
                        {
                            "success": False,
                            "error": f"Table has too many columns ({num_columns})",
                            "logs": logs,
                            "num_columns": num_columns,
                        }
                    )

                logs.append(f"✅ Table {table_name} access successful")
                return web.json_response(
                    {"success": True, "logs": logs, "num_columns": num_columns}
                )
            except Exception as e:
                bot_server.logger.error(f"Table {table_name} access failed: {e}", exc_info=True)
                logs.append(f"❌ Table {table_name} access failed")
                return web.json_response(
                    {"success": False, "error": "Table access test failed", "logs": logs}
                )

        except Exception as e:
            bot_server.logger.error(f"Invalid form data in table test: {e}", exc_info=True)
            return web.json_response({"success": False, "error": "Invalid form data", "logs": []})

    return handle_test_table


async def create_connection_from_warehouse_config(
    bot_server: "CompassBotServer",
    warehouse_config: CompassWarehouseConfig,
    warehouse_type: str,
    bot_id: str,
    table_names: list[str] | None = None,
) -> ConnectionCreationResult:
    """Helper method to create a connection from warehouse config.

    Handles storing the secret, adding the connection, triggering bot updates,
    and syncing datasets.
    """
    connection_name = warehouse_config.get_connection_name()

    # Get organization_id from bot_id
    bot_key = await bot_server.canonicalize_bot_key(BotKey.from_bot_id(bot_id))
    org_id = bot_server.bots[bot_key].bot_config.organization_id

    # Get organization ID for the bot
    organization_id = bot_server.bots[bot_key].bot_config.organization_id

    # Choose between encrypted URLs or Render secrets based on config
    if bot_server.config.db_config.use_encrypted_connection_urls:
        await bot_server.bot_manager.storage.add_connection(
            organization_id,
            connection_name,
            url="",
            additional_sql_dialect=None,
            plaintext_url=warehouse_config.to_url(),
        )
    else:
        # Legacy: Store in Render secrets and use Jinja template
        secret_key = f"{connection_name}_{warehouse_type}_url.txt"
        await bot_server.bot_manager.secret_store.store_secret(
            org_id=org_id,
            key=secret_key,
            contents=warehouse_config.to_url(),
        )

        # Construct connection URL using Jinja2 templating
        connection_url = "{{ pull_from_secret_manager_to_string('" + secret_key + "') }}"

        # Add the connection with Jinja template
        await bot_server.bot_manager.storage.add_connection(
            organization_id, connection_name, connection_url, None
        )
    await bot_server.bot_manager.storage.add_bot_connection(
        organization_id, bot_id, connection_name
    )
    # Trigger targeted bot discovery to load the connection (faster than full discovery)
    await bot_server.bot_manager.discover_and_update_bots_for_keys([bot_key])

    # Trigger dataset sync for the added tables if table names provided
    if table_names:
        from csbot.slackbot.webapp.add_connections.dataset_sync import (
            sync_datasets_after_connection,
        )

        asyncio.create_task(
            sync_datasets_after_connection(
                bot_key,
                bot_server,
                connection_name,
                table_names,
                bot_server.logger,
                warehouse_type,
            )
        )

    return ConnectionCreationResult(
        success=True,
        connection_name=connection_name,
    )


async def create_connection_from_url(
    bot_server: "CompassBotServer",
    warehouse_url: str,
    warehouse_type: str,
    bot_ids: list[str],
    connection_name: str,
    table_names: list[str] | None = None,
) -> ConnectionCreationResult:
    """Helper method to create a connection from warehouse URL and attach to multiple bots.

    Handles storing the secret, adding the connection, attaching to all specified bots,
    triggering bot updates, and syncing datasets.

    Args:
        bot_server: Bot server instance
        warehouse_url: Connection URL for the warehouse
        warehouse_type: Type of warehouse (e.g., "snowflake", "bigquery")
        bot_ids: List of bot IDs to attach the connection to
        connection_name: Name for the connection
        table_names: Optional list of table names to sync

    Returns:
        ConnectionCreationResult with success status and connection details
    """
    if not bot_ids:
        raise ValueError("At least one bot_id must be provided")

    # Get organization_id from first bot_id
    first_bot_key = await bot_server.canonicalize_bot_key(BotKey.from_bot_id(bot_ids[0]))
    org_id = bot_server.bots[first_bot_key].bot_config.organization_id

    # Choose between encrypted URLs or Render secrets based on config
    if bot_server.config.db_config.use_encrypted_connection_urls:
        await bot_server.bot_manager.storage.add_connection(
            org_id,
            connection_name,
            url="",
            additional_sql_dialect=None,
            plaintext_url=warehouse_url,
        )
    else:
        # Legacy: Store in Render secrets and use Jinja template
        secret_key = f"{connection_name}_{warehouse_type}_url.txt"
        await bot_server.bot_manager.secret_store.store_secret(
            org_id=org_id,
            key=secret_key,
            contents=warehouse_url,
        )

        # Construct connection URL using Jinja2 templating
        connection_url = "{{ pull_from_secret_manager_to_string('" + secret_key + "') }}"

        # Add the connection to storage with Jinja template
        await bot_server.bot_manager.storage.add_connection(
            org_id, connection_name, connection_url, None
        )

    # Attach connection to all specified bots
    bot_keys = []
    for bot_id in bot_ids:
        await bot_server.bot_manager.storage.add_bot_connection(org_id, bot_id, connection_name)
        bot_keys.append(BotKey.from_bot_id(bot_id))

    # Trigger targeted bot discovery for all affected bots (faster than full discovery)
    await bot_server.bot_manager.discover_and_update_bots_for_keys(bot_keys)

    # Trigger dataset sync for the added tables if table names provided
    # Use first bot for sync task
    if table_names:
        from csbot.slackbot.webapp.add_connections.dataset_sync import (
            sync_datasets_after_connection,
        )

        asyncio.create_task(
            sync_datasets_after_connection(
                first_bot_key,
                bot_server,
                connection_name,
                table_names,
                bot_server.logger,
                warehouse_type,
            )
        )

    return ConnectionCreationResult(
        success=True,
        connection_name=connection_name,
    )


def create_save_connection_endpoint(
    bot_server: "CompassBotServer",
    warehouse_config_factory: WarehouseConfigFactory,
    warehouse_type: str,
) -> Callable[[web.Request], Any]:
    """Create connection save endpoint - stores config for later use, doesn't create connection yet"""

    async def handle_save_connection(request: web.Request) -> web.Response:
        await ensure_token_is_valid(
            bot_server,
            get_unauthorized_message,
            request,
            require_user=False,
        )

        try:
            data = await parse_request_data(request)

            # Extract table_names separately
            table_names_value = data.get("table_names")
            if table_names_value:
                # If from JSON, table_names is already parsed; if from form, it's JSON string
                if isinstance(table_names_value, str):
                    table_names = json.loads(table_names_value)
                else:
                    table_names = table_names_value
            else:
                table_names = []

            # Remove table_names from form_data
            form_data = {k: v for k, v in data.items() if k != "table_names"}

            # Create warehouse config to validate the data
            try:
                warehouse_config = warehouse_config_factory(form_data)
            except Exception as e:
                return web.json_response(
                    {
                        "success": False,
                        "error": f"Invalid configuration: {str(e)}",
                    }
                )

            # Store config data for later retrieval by channel selection handler
            connection_name = warehouse_config.get_connection_name()

            # Encode connection config in a JWT token for the response
            # This keeps state on the client side instead of in-memory
            # No bot_id needed - channel/bot selection happens later
            token_data = ConnectionTokenData(
                warehouse_url=warehouse_config.to_url(),
                warehouse_type=warehouse_type,
                connection_name=connection_name,
                table_names=table_names,
            )

            connection_token = token_data.to_jwt(
                secret=bot_server.config.jwt_secret.get_secret_value(),
                expiry_seconds=3600,  # Expires in 1 hour
            )

            return web.json_response(
                {
                    "success": True,
                    "connection_name": connection_name,
                    "connection_token": connection_token,
                }
            )

        except Exception as e:
            bot_server.logger.error(f"Invalid form data in save connection: {e}", exc_info=True)
            return web.json_response({"success": False, "error": "Invalid form data"})

    return handle_save_connection
