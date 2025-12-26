import asyncio
from abc import ABC, abstractmethod
from typing import Any, TypedDict

import structlog
from ddtrace.trace import tracer
from sqlalchemy import Engine, create_engine, text

from csbot.contextengine.contextstore_protocol import (
    AddContextResult,
    DatasetSearchResultWithConnectionSqlDialect,
    SearchContextResult,
    UserCronJob,
)
from csbot.contextengine.protocol import ContextEngineProtocol
from csbot.csbot_client.csbot_profile import ConnectionProfile, ProjectProfile
from csbot.slackbot.usercron.models import (
    AddUserCronJobResult,
    DeleteUserCronJobResult,
    UpdateUserCronJobResult,
)
from csbot.slackbot.webapp.add_connections.models import (
    CompassWarehouseConfig,
    JsonConfig,
    compass_warehouse_config_from_json_config,
    get_sql_dialect_from_compass_warehouse_config,
)
from csbot.utils.check_async_context import ensure_not_in_async_context
from csbot.utils.json_utils import safe_json_dumps
from csbot.utils.tracing import try_set_tag

logger = structlog.get_logger(__name__)


class SqlClient(ABC):
    dialect: str

    @abstractmethod
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        pass


class WarehouseConfigSqlClient(SqlClient):
    dialect: str

    def __init__(self, config: CompassWarehouseConfig):
        self.config = config
        self.dialect = get_sql_dialect_from_compass_warehouse_config(config)

    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        return self.config.run_sql_query(query)


class SqlalchemyClient(SqlClient):
    def __init__(self, engine: Engine, init_sql: list[str], additional_sql_dialect: str | None):
        self.engine = engine
        self.dialect = get_sql_dialect_from_url(str(engine.url), additional_sql_dialect)
        self.init_sql = init_sql

    @tracer.wrap()
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        """
        Run a SQL query against the warehouse

        Args:
            query: SQL query to execute

        Returns:
            List of dictionaries containing query results

        Raises:
            Exception: If query execution fails
        """

        # figure out rbac with datadog
        # try_set_tag("query", query)

        ensure_not_in_async_context()

        statement = text(query)
        with self.engine.connect().execution_options(stream_results=True) as conn:
            for sql in self.init_sql:
                conn.execute(text(sql))
            result = conn.execute(statement)
            return [dict(row) for row in result.mappings()]

    def __del__(self):
        self.engine.dispose()


def get_connection_profile(profile: ProjectProfile, connection_name: str) -> ConnectionProfile:
    connection_profile = profile.connections.get(connection_name)
    if not connection_profile:
        raise KeyError(
            f"Connection '{connection_name}' not found (available "
            f"connections: {list(profile.connections.keys())})"
        )
    return connection_profile


def get_sql_client(
    profile: ProjectProfile,
    connection_name: str,
) -> SqlClient:
    """
    Get a SQL connection using external browser authentication.

    Args:
        connection_name: Name of the connection to query

    Returns:
        SQLAlchemy engine object

    Raises:
        KeyError: If connection not found in config
        ValueError: If required connection parameters are missing
    """
    # Find the project in the profile
    connection_profile = get_connection_profile(profile, connection_name)
    return get_sql_client_from_connection_profile(connection_profile)


def get_sql_client_from_connection_profile(connection_profile: ConnectionProfile) -> SqlClient:
    if connection_profile.url.startswith("jsonconfig:"):
        json_config = JsonConfig.from_url(connection_profile.url)
        compass_warehouse_config = compass_warehouse_config_from_json_config(json_config)
        return WarehouseConfigSqlClient(compass_warehouse_config)
    else:
        engine = create_engine(connection_profile.url, connect_args=connection_profile.connect_args)
        return SqlalchemyClient(
            engine, connection_profile.init_sql, connection_profile.additional_sql_dialect
        )


def get_sql_dialect_from_unresolved_url(url: str) -> str | None:
    """Extract SQL dialect from an unresolved URL with template variables.

    Handles URLs like:
    - {{ pull_from_secret_manager_to_string('snowflake_svc_compass_user_snowflake_url.txt') }} -> 'snowflake'
    - {{ pull_from_secret_manager_to_string('postgres_prod_url.txt') }} -> 'postgres'

    Returns the first word from the secret key prefix.
    Returns None if the dialect cannot be determined.
    """
    import re

    # Match pattern: {{ pull_from_secret_manager_to_string('<prefix>_...') }} and extract first word
    match = re.search(r"pull_from_secret_manager_to_string\(['\"]([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None


def get_sql_dialect_from_url(url: str, additional_sql_dialect: str | None) -> str:
    """Get the SQL dialect from a URL.

    Returns 'unknown' if the dialect cannot be determined.
    """
    if additional_sql_dialect:
        return additional_sql_dialect

    # Try to extract from unresolved template URL
    dialect = get_sql_dialect_from_unresolved_url(url)
    if dialect:
        return dialect

    # Try standard URL parsing
    try:
        parsed_dialect = url.split(":")[0]
        # Validate it's not a template variable prefix
        if (
            parsed_dialect
            and not parsed_dialect.startswith("{{")
            and not parsed_dialect.startswith("{")
        ):
            return parsed_dialect
    except Exception:
        pass

    return "unknown"


class ContextStoreClient:
    def __init__(
        self,
        contextstore: ContextEngineProtocol,
        profile: ProjectProfile,
    ):
        self.profile = profile
        self.contextstore = contextstore

    @tracer.wrap()
    async def search_datasets(
        self, query: str, full: bool
    ) -> list[DatasetSearchResultWithConnectionSqlDialect]:
        """Enumerate available datasets that can be queried via SQL, with queryText for full-text
        search to find the desired dataset. Returns a dictionary where the key is the table name
        and the value contains the connection name (which you can use to query the data via sql),
        and the docs markdown if full=True. Pass "*" as the query to search all datasets (note:
        this only works when full=False, so you may want to do a follow-up search where you
        search for the name of the desired datasets with full=True to get the docs)."""
        # figure out rbac with datadog
        # try_set_tag("query", query)
        result = await self.contextstore.search_datasets(query, full)
        rv = []
        connections = self.profile.connections
        for dataset in result:
            dialect = "<dataset not available to this user>"
            if dataset.connection in connections:
                client = get_sql_client_from_connection_profile(connections[dataset.connection])
                dialect = client.dialect

            rv.append(
                DatasetSearchResultWithConnectionSqlDialect(
                    connection=dataset.connection,
                    table=dataset.table,
                    docs_markdown=dataset.docs_markdown,
                    connection_sql_dialect=dialect,
                )
            )
        return rv

    async def get_cron_jobs(self) -> dict[str, UserCronJob]:
        """Get all scheduled analysis jobs."""
        return await self.contextstore.get_cron_jobs()

    async def add_cron_job(
        self,
        cron_job_name: str,
        cron_string: str,
        question: str,
        thread: str,
        attribution: str | None,
    ) -> AddUserCronJobResult:
        """Add or edits a scheduled analysis job. When the user asks you to always do
        something at a recurring time, or to schedule an analysis, call this method. The "thread"
        argument serves as the introductory message of the thread that kicks off the scheduled
        analysis. It should summarize what the analysis is and end with a thread emoji, and you
        should tell the user about the review request that was created. Explain that their team
        will need to review the request before the scheduled report will start running.

        IMPORTANT: Do not suggest that users check the status via the link, as some users may not
        have access to view it. Simply mention that the team will review the request.

        When talking to users, use plain language terms like "report," "summary," or "update"
        instead of technical terms like "scheduled analysis" or "cron job."

        The "question" argument should contain all of the information the user has provided to
        you to run the analysis.
        """
        return await self.contextstore.add_cron_job(
            cron_job_name, cron_string, question, thread, attribution
        )

    async def update_cron_job(
        self,
        cron_job_name: str,
        additional_context: str,
        attribution: str | None,
    ) -> UpdateUserCronJobResult:
        """Update a scheduled analysis job by appending additional context.
        This is only available in threads that were created by a scheduled analysis execution.

        Args:
            cron_job_name: The name of the scheduled analysis to update
            additional_context: Additional context to append to the analysis question

        Returns:
            UpdateCronJobResult with the review request URL for the team to review.

            IMPORTANT: Do not suggest that users check the status via the link, as some users may not
            have access to view it. Simply mention that the team will review the request.
            When talking to users, refer to this as updating a "report" or "summary" rather than
            a "scheduled analysis."
        """
        return await self.contextstore.update_cron_job(
            cron_job_name, additional_context, attribution
        )

    async def delete_cron_job(
        self, cron_job_name: str, attribution: str | None
    ) -> DeleteUserCronJobResult:
        """Delete a scheduled analysis job.

        Args:
            cron_job_name: The name of the scheduled analysis to delete

        Returns:
            DeleteCronJobResult with the review request URL for the team to review.

            IMPORTANT: Do not suggest that users check the status via the link, as some users may not
            have access to view it. Simply mention that the team will review the request.
            When talking to users, refer to this as removing a "report" or "summary" rather than
            deleting a "scheduled analysis."
        """
        return await self.contextstore.delete_cron_job(cron_job_name, attribution)

    async def add_context(
        self,
        topic: str,
        incorrect_understanding: str,
        correct_understanding: str,
        attribution: str | None,
    ) -> AddContextResult:
        return await self.contextstore.add_context(
            topic,
            incorrect_understanding,
            correct_understanding,
            attribution,
        )

    async def search_context(self, query: str) -> list[SearchContextResult]:
        """Search through recorded user feedback and business definitions to find clarifications
        about a specific topic. You should usually run this before issuing any SQL query."""
        return await self.contextstore.search_context(query)

    async def get_system_prompt(self) -> str | None:
        """Get the system prompt for the project."""
        return await self.contextstore.get_system_prompt()


class RunSqlQueryResult(TypedDict):
    error: str | None
    ok: list[dict[str, Any]] | None


class CSBotClient(ContextStoreClient):
    @tracer.wrap()
    async def run_sql_query(
        self,
        connection: str,
        query: str,
        did_you_call_search_context: bool,
        description: str,
        max_size: float = 50000 * 3.5,
    ) -> RunSqlQueryResult:
        """Run a SQL query on a data warehouse connection. Be sure to call search_context()
        before calling this method to be sure that you get any relevant context from user feedback
        on this topic. If the user gives you feedback that information from this query was wrong
        or confusing, be sure to call add_context() to record this feedback to correct future
        queries.

        Args:
            connection: The connection name to run the query against
            query: The SQL query to execute
            did_you_call_search_context: Whether search_context() was called before this method
            description: A single sentence describing what the query is doing. Must be exactly one sentence and start with a verb ending in "ing", and end with an ellipsis, and be properly capitalized and written professionally.
            max_size: if positive, results over this amount will be rejected. if negative, no maximum
            size is enforce. The reason for the default is:
            It's about 3-4 bytes per token on average, and the context window is usually 250k tokens, so
            let's limit to 50k estimated tokens
        """

        try_set_tag("connection", connection)
        # figure out rbac with datadog
        # try_set_tag("query", query)
        if not did_you_call_search_context:
            raise Exception("You must call search_context() before calling this method.")

        results = await asyncio.to_thread(self._run_sql_query_sync, connection, query)
        # It's about 3-4 bytes per token on average, and the context window is usually 250k tokens,
        # so
        # let's limit to 50k estimated tokens
        if max_size > 0 and len(safe_json_dumps(results)) > max_size:
            return {
                "error": "Query result was too large. Please refine your query.",
                "ok": None,
            }
        return {"error": None, "ok": results}

    def _run_sql_query_sync(self, connection: str, query: str) -> list[dict[str, Any]]:
        sql_client = get_sql_client(self.profile, connection)
        logger.info(f"Running SQL query of length {len(query)}")
        results = sql_client.run_sql_query(query)
        logger.info(f"SQL query returned {len(results)} rows")
        return results
