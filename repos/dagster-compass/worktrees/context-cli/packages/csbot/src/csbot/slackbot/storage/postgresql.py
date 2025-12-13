import json
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager, contextmanager
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

import jinja2
import psycopg
import psycopg_pool

from csbot.csbot_client.csbot_profile import ConnectionProfile
from csbot.slackbot.config import DatabaseConfig
from csbot.slackbot.envelope_encryption import KekProvider
from csbot.utils.check_async_context import ensure_not_in_async_context
from csbot.utils.misc import normalize_channel_name
from csbot.utils.sync_to_async import sync_to_async

from ...utils.time import SecondsNow, system_seconds_now
from .interface import (
    PLAN_LIMITS_TTL_SECONDS,
    BotInstanceType,
    ConnectionDetails,
    ContextStatus,
    ContextStatusType,
    ContextUpdateType,
    InviteTokenData,
    Organization,
    OrganizationUsageData,
    OrgUser,
    PlanLimits,
    ReferralTokenStatus,
    SlackbotInstanceStorage,
    SlackbotStorage,
    SqlConnectionFactory,
)
from .schema_changes import SchemaManager

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import BotKey
    from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
    from csbot.slackbot.slackbot_models import PrInfo
    from csbot.slackbot.storage.onboarding_state import OnboardingState, ProspectorDataType


@contextmanager
def maybe_setup_rds_connection_pooling(db_config: DatabaseConfig):
    if not db_config.use_iam_auth:
        yield
        return

    from aws_advanced_python_wrapper.connection_provider import ConnectionProviderManager
    from aws_advanced_python_wrapper.sql_alchemy_connection_provider import (
        SqlAlchemyPooledConnectionProvider,
    )

    def pool_config(*args, **kwargs):
        return {
            "pool_size": 10,
            "max_overflow": 20,
            "timeout": 30,
            "recycle": 600,
        }

    provider = SqlAlchemyPooledConnectionProvider(pool_config)
    ConnectionProviderManager.set_connection_provider(provider)
    try:
        yield
    finally:
        ConnectionProviderManager.release_resources()


def _get_iam_auth_pool_context_v2(db_config: DatabaseConfig):
    import boto3
    from sqlalchemy import create_engine, event

    client = boto3.client("rds")
    engine = create_engine(
        "postgresql+psycopg:///",
        pool_size=10,  # Keep 10 connections in the pool
        max_overflow=20,  # Allow up to 20 additional connections
        pool_timeout=30,  # Wait 30 seconds for a connection
        pool_recycle=600,
    )  # connection params will be set by the event callback
    parsed = urlparse(db_config.database_uri)

    @event.listens_for(engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):
        token = client.generate_db_auth_token(
            DBHostname=parsed.hostname,
            Port=parsed.port or 5432,
            DBUsername=parsed.username,
            Region="us-west-2",
        )

        # set up db connection parameters, alternatively we can get these from boto3 describe_db_instances
        cparams["host"] = parsed.hostname
        cparams["port"] = parsed.port
        cparams["user"] = parsed.username
        cparams["password"] = token
        cparams["dbname"] = parsed.path.lstrip("/")
        cparams["sslmode"] = "require"

    @contextmanager
    def pool_context():
        with engine.connect() as connection:
            yield cast("psycopg.Connection", connection.connection)

    return pool_context


def _get_iam_auth_pool_context(
    db_config: DatabaseConfig,
) -> Callable[[], AbstractContextManager[psycopg.Connection]]:
    from aws_advanced_python_wrapper import AwsWrapperConnection

    parsed = urlparse(db_config.database_uri)
    assert parsed.hostname
    assert parsed.username

    @contextmanager
    def pool_context():
        conn = AwsWrapperConnection.connect(
            psycopg.connect,
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            sslmode="require",
            plugins="iam",
        )
        try:
            yield cast("psycopg.Connection", conn)
        finally:
            conn.close()

    return pool_context


def _get_basic_pool_context(
    uri: str,
) -> Callable[[], AbstractContextManager[psycopg.Connection]]:
    parsed = urlparse(uri)
    connection_params = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username,
        "password": parsed.password,
    }

    # Create connection pool for production use
    pool = psycopg_pool.ConnectionPool(
        min_size=1,
        max_size=20,  # min and max connections
        kwargs=connection_params,
        open=True,
    )
    return pool.connection


class PostgresqlConnectionFactory(SqlConnectionFactory):
    def __init__(
        self,
        conn_ctx_manager: Callable[[], AbstractContextManager[psycopg.Connection]],
        seconds_now: SecondsNow = system_seconds_now,
    ):
        """Initialize PostgresqlConnectionFactory.

        NOTE: Do not call this constructor directly. Use factory methods instead:
        - PostgresqlConnectionFactory.from_database_url() for database connections
        """
        self._conn_ctx_manager = conn_ctx_manager
        self.seconds_now = seconds_now

    def supports_analytics(self) -> bool:
        """Check if the connection factory supports analytics."""
        return True

    @classmethod
    def from_db_config(
        cls, db_config: DatabaseConfig, seconds_now: SecondsNow = system_seconds_now
    ) -> "PostgresqlConnectionFactory":
        """Create a PostgresqlConnectionFactory from a DATABASE_URL."""

        if db_config.use_iam_auth:
            pool_context = _get_iam_auth_pool_context(db_config)
        elif db_config.use_iam_auth_v2:
            pool_context = _get_iam_auth_pool_context_v2(db_config)
        else:
            pool_context = _get_basic_pool_context(db_config.database_uri)

        factory = cls(pool_context, seconds_now)

        if db_config.initialize_db:
            with factory.with_conn() as conn:
                factory._initialize_database(conn)
        else:
            # Verify schema is up to date
            from csbot.slackbot.storage.schema_changes import SchemaManager

            with factory.with_conn() as conn:
                schema_manager = SchemaManager()
                unapplied_changes = schema_manager.list_unapplied_changes(conn)
                if unapplied_changes:
                    raise RuntimeError(
                        f"Database schema is not up to date. "
                        f"Unapplied schema changes: {', '.join(unapplied_changes)}. "
                        f"Set initialize_db=True in database config to apply schema changes."
                    )

        return factory

    def with_conn(self) -> AbstractContextManager[psycopg.Connection]:
        """Get a context manager for database connections."""

        ensure_not_in_async_context()

        @contextmanager
        def managed_connection():
            with self._conn_ctx_manager() as conn:
                yield conn

        return managed_connection()

    def _initialize_database(self, conn: psycopg.Connection) -> None:
        """Initialize database schema and clean up expired entries."""
        # Apply all schema changes in organized fashion
        schema_manager = SchemaManager()
        schema_manager.apply_all_changes(conn)

        conn.commit()


class SlackbotPostgresqlStorage(SlackbotStorage):
    def __init__(
        self,
        sql_conn_factory: SqlConnectionFactory,
        kek_provider: KekProvider,
        seconds_now: SecondsNow = system_seconds_now,
    ):
        self._sql_conn_factory = sql_conn_factory
        self._kek_provider = kek_provider
        self.seconds_now = seconds_now
        self._cached_org_deks: dict[int, bytes] = {}

    @sync_to_async
    def is_referral_token_valid(self, token: str) -> ReferralTokenStatus:  # type: ignore[override]
        """Check if a referral token is valid and whether it has been consumed."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT consumed_by_instance_id, is_single_use FROM referral_tokens
                WHERE token = %s
                """,
                (token,),
            )
            result = cursor.fetchone()

            if result is None:
                return ReferralTokenStatus(
                    is_valid=False, has_been_consumed=False, is_single_use=False
                )

            consumed_by_instance_id = result[0]
            is_single_use = bool(result[1])
            has_been_consumed = consumed_by_instance_id is not None

            return ReferralTokenStatus(
                is_valid=True, has_been_consumed=has_been_consumed, is_single_use=is_single_use
            )

    @sync_to_async
    def mark_referral_token_consumed(  # type: ignore[override]
        self, token: str, instance_id: int, timestamp: float | None = None
    ) -> None:
        """Mark a referral token as consumed by a specific bot instance.

        Automatically appends the bot instance's organization ID to consumed_by_organization_ids.
        """
        import json

        if timestamp is None:
            timestamp = self.seconds_now()

        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Get the organization ID for this bot instance
            cursor.execute(
                "SELECT organization_id FROM bot_instances WHERE id = %s", (instance_id,)
            )
            org_result = cursor.fetchone()
            if org_result is None:
                # Bot instance not found, silently return
                return
            org_id = org_result[0]

            # Get current consumed_by_organization_ids
            cursor.execute(
                "SELECT consumed_by_organization_ids FROM referral_tokens WHERE token = %s",
                (token,),
            )
            token_result = cursor.fetchone()
            if token_result is None:
                # Token not found, silently return
                return

            current_ids = json.loads(token_result[0]) if token_result[0] else []

            # Append new org ID if not already present
            if org_id not in current_ids:
                current_ids.append(org_id)

            # Update the token
            cursor.execute(
                """
                UPDATE referral_tokens
                SET
                    consumed_by_instance_id = %s,
                    consumed_at = to_timestamp(%s),
                    consumed_by_organization_ids = %s
                WHERE token = %s
                """,
                (instance_id, timestamp, json.dumps(current_ids), token),
            )
            conn.commit()

    @sync_to_async
    def get_bot_instance_by_token(self, token: str) -> dict | None:  # type: ignore[override]
        """Get bot instance information by referral token."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT bi.id, bi.channel_name, bi.bot_email, bi.contextstore_github_repo,
                       bi.governance_alerts_channel, bi.slack_team_id
                FROM bot_instances bi
                JOIN referral_tokens rt ON bi.id = rt.consumed_by_instance_id
                WHERE rt.token = %s
                """,
                (token,),
            )
            result = cursor.fetchone()

            if result is None:
                return None

            return {
                "id": result[0],
                "channel_name": result[1],
                "bot_email": result[2],
                "contextstore_github_repo": result[3],
                "governance_alerts_channel": result[4],
                "slack_team_id": result[5],
            }

    def for_instance(self, bot_id: str) -> "SlackbotInstancePostgresqlStorage":
        """Create a SlackbotInstancePostgresqlStorage for a specific bot instance."""
        return SlackbotInstancePostgresqlStorage(
            self._sql_conn_factory, self._kek_provider, bot_id, self.seconds_now
        )

    @sync_to_async
    def create_bot_instance(  # type: ignore[override]
        self,
        channel_name: str,
        governance_alerts_channel: str,
        contextstore_github_repo: str,
        slack_team_id: str,
        bot_email: str,
        organization_id: int,
        instance_type: BotInstanceType = BotInstanceType.STANDARD,
        icp_text: str | None = None,
        data_types: list["ProspectorDataType"] | None = None,
    ) -> int:
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO bot_instances
                (channel_name, bot_email, governance_alerts_channel, contextstore_github_repo, slack_team_id, organization_id, instance_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    channel_name,
                    bot_email,
                    governance_alerts_channel,
                    contextstore_github_repo,
                    slack_team_id,
                    organization_id,
                    instance_type.value,
                ),
            )
            instance_id = cursor.fetchone()[0]

            if icp_text or data_types:
                data_types_json = (
                    json.dumps([dt.value for dt in data_types]) if data_types else "[]"
                )
                cursor.execute(
                    "INSERT INTO bot_instance_icp (bot_instance_id, icp_text, data_types) VALUES (%s, %s, %s)",
                    (instance_id, icp_text, data_types_json),
                )

            conn.commit()
            return instance_id

    @sync_to_async
    def delete_bot_instance(self, organization_id: int, bot_key: "BotKey") -> None:  # type: ignore[override]
        """Delete a bot instance by organization ID and bot ID."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM bot_instances
                WHERE organization_id = %s AND slack_team_id = %s AND (channel_name = %s OR channel_name = %s)
                """,
                (
                    organization_id,
                    bot_key.team_id,
                    bot_key.channel_name,
                    f"#{bot_key.channel_name}",
                ),
            )
            conn.commit()

    @sync_to_async
    def update_organization_industry(self, organization_id: int, industry: str) -> None:  # type: ignore[override]
        """Update the industry for an organization."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE organizations
                SET organization_industry = %s
                WHERE organization_id = %s
                """,
                (industry, organization_id),
            )

            if cursor.rowcount == 0:
                raise ValueError(f"Organization not found for organization_id: {organization_id}")

            conn.commit()

    @sync_to_async
    def update_bot_instance_icp(self, bot_instance_id: int, icp_text: str) -> None:  # type: ignore[override]
        """Update ICP for a bot instance using UPSERT."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO bot_instance_icp (bot_instance_id, icp_text)
                   VALUES (%s, %s)
                   ON CONFLICT (bot_instance_id)
                   DO UPDATE SET icp_text = EXCLUDED.icp_text, updated_at = CURRENT_TIMESTAMP""",
                (bot_instance_id, icp_text),
            )
            conn.commit()

    @sync_to_async
    def add_connection(  # type: ignore[override]
        self,
        organization_id: int,
        connection_name: str,
        url: str,
        additional_sql_dialect: str | None,
        data_documentation_contextstore_github_repo: str | None = None,
        plaintext_url: str | None = None,
    ) -> None:
        """Add a connection for an organization.

        Args:
            organization_id: Organization ID
            connection_name: Name of the connection
            url: Connection URL (Jinja template if plaintext_url is None)
            additional_sql_dialect: Optional SQL dialect
            data_documentation_contextstore_github_repo: Optional context repo
            plaintext_url: Optional plaintext URL (will be encrypted before being stored in db)
        """
        if plaintext_url:
            encrypted_url = self._encrypt_url(organization_id, plaintext_url)
        else:
            encrypted_url = None
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert or update the connection using ON CONFLICT
            cursor.execute(
                """
                INSERT INTO connections
                (connection_name, url, additional_sql_dialect, organization_id, data_documentation_contextstore_github_repo, encrypted_url)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, connection_name)
                DO UPDATE SET url = EXCLUDED.url, additional_sql_dialect = EXCLUDED.additional_sql_dialect, data_documentation_contextstore_github_repo = EXCLUDED.data_documentation_contextstore_github_repo, encrypted_url = EXCLUDED.encrypted_url, updated_at = CURRENT_TIMESTAMP
                """,
                (
                    connection_name,
                    url,
                    additional_sql_dialect,
                    organization_id,
                    data_documentation_contextstore_github_repo,
                    encrypted_url,
                ),
            )

            conn.commit()

    def _encrypt_url(self, organization_id: int, url: str) -> str:
        from csbot.slackbot.envelope_encryption import (
            encrypt_connection_url,
            get_or_create_organization_dek,
        )

        with self._sql_conn_factory.with_conn() as conn:
            dek = get_or_create_organization_dek(conn, organization_id, self._kek_provider)
            conn.commit()

        # Encrypt the URL
        return encrypt_connection_url(url, dek)

    @sync_to_async
    def add_bot_connection(  # type: ignore[override]
        self, organization_id: int, bot_id: str, connection_name: str
    ) -> None:
        """Add a mapping between a bot and a connection."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Insert or update the bot_to_connections mapping
            cursor.execute(
                """
                INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (organization_id, bot_id, connection_name) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP
                """,
                (organization_id, bot_id, connection_name),
            )

            conn.commit()

    @sync_to_async
    def remove_bot_connection(  # type: ignore[override]
        self, organization_id: int, bot_id: str, connection_name: str
    ) -> None:
        """Remove a mapping between a bot and a connection."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Delete the bot_to_connections mapping
            cursor.execute(
                """
                DELETE FROM bot_to_connections
                WHERE organization_id = %s AND bot_id = %s AND connection_name = %s
                """,
                (organization_id, bot_id, connection_name),
            )

            conn.commit()

    @sync_to_async
    def reconcile_bot_connection(  # type: ignore[override]
        self, organization_id: int, bot_id: str, connection_names: list[str]
    ) -> None:
        """Reconcile bot connections to match the provided list."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Get current connections for the bot
            cursor.execute(
                """
                SELECT connection_name
                FROM bot_to_connections
                WHERE organization_id = %s AND bot_id = %s
                """,
                (organization_id, bot_id),
            )
            current_connections = {row[0] for row in cursor.fetchall()}
            desired_connections = set(connection_names)

            # Add missing connections
            connections_to_add = desired_connections - current_connections
            for connection_name in connections_to_add:
                cursor.execute(
                    """
                    INSERT INTO bot_to_connections (organization_id, bot_id, connection_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (organization_id, bot_id, connection_name) DO UPDATE SET
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (organization_id, bot_id, connection_name),
                )

            # Remove extra connections
            connections_to_remove = current_connections - desired_connections
            for connection_name in connections_to_remove:
                cursor.execute(
                    """
                    DELETE FROM bot_to_connections
                    WHERE organization_id = %s AND bot_id = %s AND connection_name = %s
                    """,
                    (organization_id, bot_id, connection_name),
                )

            conn.commit()

    @sync_to_async
    def get_connection_names_for_organization(  # type: ignore[override]
        self, organization_id: int
    ) -> list[str]:
        """Get all connection names for an organization."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT connection_name FROM connections WHERE organization_id = %s ORDER BY connection_name",
                (organization_id,),
            )
            results = cursor.fetchall()
            return [row[0] for row in results]

    @sync_to_async
    def get_connection_names_for_bot(  # type: ignore[override]
        self, organization_id: int, bot_id: str
    ) -> list[str]:
        """Get all connection names for a bot."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT connection_name FROM bot_to_connections WHERE organization_id = %s AND bot_id = %s ORDER BY connection_name",
                (organization_id, bot_id),
            )
            results = cursor.fetchall()
            return [row[0] for row in results]

    @sync_to_async
    def get_organization_connections_with_details(  # type: ignore[override]
        self, organization_id: int
    ) -> list[ConnectionDetails]:
        """Get all connections for an organization with detailed information."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    c.connection_name,
                    c.additional_sql_dialect,
                    c.url,
                    ARRAY_AGG(DISTINCT btc.bot_id ORDER BY btc.bot_id) FILTER (WHERE btc.bot_id IS NOT NULL) as bot_ids
                FROM connections c
                LEFT JOIN bot_to_connections btc ON c.connection_name = btc.connection_name AND c.organization_id = btc.organization_id
                WHERE c.organization_id = %s
                GROUP BY c.connection_name, c.additional_sql_dialect, c.url
                ORDER BY c.connection_name
                """,
                (organization_id,),
            )
            results = cursor.fetchall()
            connections = []
            for row in results:
                connection_name, additional_sql_dialect, connection_url, bot_ids = row

                # Determine connection type from additional_sql_dialect or URL
                from csbot.csbot_client.csbot_client import get_sql_dialect_from_url

                connection_type = get_sql_dialect_from_url(connection_url, additional_sql_dialect)

                # Extract channel names from bot_ids
                channel_names = []
                if bot_ids:
                    for bot_id in bot_ids:
                        # bot_id format is "slack_team_id-channel_name"
                        parts = bot_id.split("-", 1)
                        if len(parts) == 2:
                            channel_names.append(parts[1])
                connections.append(
                    ConnectionDetails(
                        connection_name=connection_name,
                        connection_type=connection_type,
                        bot_ids=bot_ids or [],
                        channel_names=channel_names,
                    )
                )
            return connections

    @sync_to_async
    def create_organization(  # type: ignore[override]
        self,
        name: str,
        has_governance_channel: bool,
        contextstore_github_repo: str,
        industry: str | None = None,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
    ) -> int:
        """Create a new organization and return its ID."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO organizations (organization_name, organization_industry, stripe_customer_id, stripe_subscription_id, has_governance_channel, contextstore_github_repo)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING organization_id
                """,
                (
                    name,
                    industry,
                    stripe_customer_id,
                    stripe_subscription_id,
                    1 if has_governance_channel else 0,
                    contextstore_github_repo,
                ),
            )
            organization_id = cursor.fetchone()[0]
            conn.commit()
            return organization_id

    @sync_to_async
    def record_tos_acceptance(  # type: ignore[override]
        self, email: str, organization_id: int, organization_name: str
    ) -> None:
        """Record terms of service acceptance for an organization."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tos_records (email, organization_id, organization_name) VALUES (%s, %s, %s)",
                (email, organization_id, organization_name),
            )
            conn.commit()

    @sync_to_async
    def get_plan_limits(self, organization_id: int) -> PlanLimits | None:  # type: ignore[override]
        """Get cached plan limits for an organization if not expired."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            current_time = self.seconds_now()
            cursor.execute(
                """
                SELECT cached_base_num_answers, cached_allow_overage, cached_num_channels, cached_allow_additional_channels
                FROM plan_limits
                WHERE organization_id = %s
                AND updated_at > to_timestamp(%s)
                """,
                (organization_id, current_time - PLAN_LIMITS_TTL_SECONDS),
            )
            result = cursor.fetchone()

            if result is None:
                return None

            base_num_answers, allow_overage, num_channels, allow_additional_channels = result
            return PlanLimits(
                base_num_answers=base_num_answers,
                allow_overage=allow_overage,
                num_channels=num_channels,
                allow_additional_channels=allow_additional_channels,
            )

    @sync_to_async
    def set_plan_limits(  # type: ignore[override]
        self,
        organization_id: int,
        base_num_answers: int,
        allow_overage: bool,
        num_channels: int,
        allow_additional_channels: bool,
    ) -> None:
        """Set cached plan limits for an organization (insert or update)."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO plan_limits (organization_id, cached_base_num_answers, cached_allow_overage,
                                       cached_num_channels, cached_allow_additional_channels)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (organization_id)
                DO UPDATE SET
                    cached_base_num_answers = EXCLUDED.cached_base_num_answers,
                    cached_allow_overage = EXCLUDED.cached_allow_overage,
                    cached_num_channels = EXCLUDED.cached_num_channels,
                    cached_allow_additional_channels = EXCLUDED.cached_allow_additional_channels,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    organization_id,
                    base_num_answers,
                    allow_overage,
                    num_channels,
                    allow_additional_channels,
                ),
            )
            conn.commit()

    @sync_to_async
    def load_bot_instances(  # type: ignore[override]
        self,
        template_context: dict[str, Any],
        get_template_context_for_org: Callable[[int], dict[str, Any]],
        bot_keys: Sequence["BotKey"] | None = None,
    ) -> dict[str, "CompassBotSingleChannelConfig"]:
        """Load bot instances from database with Jinja2 template processing.

        Args:
            template_context: Global template context for Jinja2 processing
            get_template_context_for_org: Function to get per-organization template context
            bot_keys: Optional list of bot keys to filter by. If None, load all instances.
        """
        from csbot.slackbot.bot_server.bot_server import BotKey
        from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig

        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Build query with optional bot key filter
            if bot_keys:
                # Build WHERE clause to match team_id and channel_name pairs
                # Each bot key contributes: (slack_team_id = %s AND (channel_name = %s OR governance_alerts_channel = %s))
                conditions = []
                params = []
                for bot_key in bot_keys:
                    conditions.append(
                        "(bi.slack_team_id = %s AND (bi.channel_name = %s OR bi.governance_alerts_channel = %s))"
                    )
                    params.append(bot_key.team_id)
                    normalized_channel = normalize_channel_name(bot_key.channel_name)
                    params.append(normalized_channel)
                    params.append(normalized_channel)

                where_clause = " OR ".join(conditions)
                query = f"""
                    SELECT bi.id, bi.channel_name, bi.bot_email, o.contextstore_github_repo,
                           bi.governance_alerts_channel, bi.slack_team_id, bi.organization_id,
                           o.organization_name, o.organization_industry,
                           o.stripe_customer_id, o.stripe_subscription_id,
                           bi.instance_type, icp.icp_text, icp.data_types
                    FROM bot_instances bi
                    JOIN organizations o ON bi.organization_id = o.organization_id
                    LEFT JOIN bot_instance_icp icp ON bi.id = icp.bot_instance_id
                    WHERE {where_clause}
                """
                cursor.execute(query, tuple(params))
            else:
                cursor.execute("""
                    SELECT bi.id, bi.channel_name, bi.bot_email, o.contextstore_github_repo,
                           bi.governance_alerts_channel, bi.slack_team_id, bi.organization_id,
                           o.organization_name, o.organization_industry,
                           o.stripe_customer_id, o.stripe_subscription_id,
                           bi.instance_type, icp.icp_text, icp.data_types
                    FROM bot_instances bi
                    JOIN organizations o ON bi.organization_id = o.organization_id
                    LEFT JOIN bot_instance_icp icp ON bi.id = icp.bot_instance_id
                """)

            bot_rows = cursor.fetchall()

            if not bot_rows:
                return {}

        bots = {}
        for (
            bot_instance_id,
            channel_name,
            bot_email,
            contextstore_github_repo,
            governance_alerts_channel,
            slack_team_id,
            organization_id,
            organization_name,
            organization_industry,
            stripe_customer_id,
            stripe_subscription_id,
            instance_type,
            icp_text,
            data_types_json,
        ) in bot_rows:
            # Load connections for this bot - construct bot_id directly to avoid circular import
            bot_id = BotKey.from_channel_name(slack_team_id, channel_name).to_bot_id()
            connections, data_documentation_repos = self._load_connections(
                organization_id,
                bot_id=bot_id,
                template_context=template_context,
                get_template_context_for_org=get_template_context_for_org,
            )

            # Parse data types JSON if present
            from csbot.slackbot.storage.onboarding_state import ProspectorDataType

            data_types = []
            if data_types_json:
                data_type_values = json.loads(data_types_json)
                data_types = [ProspectorDataType(dt) for dt in data_type_values]

            from csbot.slackbot.slackbot_core import OrganizationConfig

            organization_config = OrganizationConfig(
                organization_id=organization_id,
                organization_name=organization_name,
                organization_industry=organization_industry,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                contextstore_github_repo=contextstore_github_repo,
            )

            bot_config = CompassBotSingleChannelConfig(
                channel_name=channel_name,
                bot_email=bot_email,
                connections=connections,
                governance_alerts_channel=governance_alerts_channel,
                team_id=slack_team_id,
                organization=organization_config,
                instance_type=BotInstanceType.from_db_value(instance_type)
                if instance_type
                else BotInstanceType.STANDARD,
                icp_text=icp_text,
                prospector_data_types=data_types,
                data_documentation_repos=data_documentation_repos,
            )

            bots[f"{slack_team_id}-{channel_name}"] = bot_config

        return bots

    def _load_connections(
        self,
        organization_id: int,
        bot_id: str,
        template_context: dict[str, Any],
        get_template_context_for_org: Callable[[int], dict[str, Any]],
    ) -> tuple[dict[str, ConnectionProfile], set[str]]:
        """Load connections for a bot with Jinja2 template processing.

        Uses the bot_to_connections table to map bot_id to connection_name,
        then looks up the connection details from the connections table.

        Returns:
            Tuple of (connections dict, set of data documentation repos)
        """
        from csbot.slackbot.envelope_encryption import (
            decrypt_connection_url,
            get_or_create_organization_dek,
        )

        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Load connections via bot_to_connections mapping, including documentation repos
            cursor.execute(
                """
                SELECT btc.connection_name, c.url, c.encrypted_url, c.init_sql, c.additional_sql_dialect,
                       c.data_documentation_contextstore_github_repo
                FROM bot_to_connections btc
                JOIN connections c ON btc.connection_name = c.connection_name AND btc.organization_id = c.organization_id
                WHERE btc.organization_id = %s AND btc.bot_id = %s
            """,
                (organization_id, bot_id),
            )
            connection_rows = cursor.fetchall()
            connections = {}
            data_documentation_repos = set()

            # Get the organization's DEK if any connections use encryption (with caching)
            dek = None
            has_encrypted = any(row[2] for row in connection_rows)
            if has_encrypted:
                if organization_id not in self._cached_org_deks:
                    self._cached_org_deks[organization_id] = get_or_create_organization_dek(
                        conn, organization_id, self._kek_provider
                    )
                dek = self._cached_org_deks[organization_id]

            # Create Jinja2 environment for template processing
            jinja_env = jinja2.Environment(
                loader=jinja2.BaseLoader(), undefined=jinja2.StrictUndefined
            )

            for (
                connection_name,
                url_template,
                encrypted_url,
                init_sql_template,
                additional_sql_dialect,
                data_doc_repo,
            ) in connection_rows:
                # Decrypt URL if encrypted_url exists
                if encrypted_url:
                    if not dek:
                        raise ValueError("Organization DEK not found but encrypted URLs exist")
                    url = decrypt_connection_url(encrypted_url, dek)
                else:
                    # Fallback to old templating system for backward compatibility during migration
                    url = jinja_env.from_string(url_template or "").render(
                        get_template_context_for_org(organization_id)
                    )

                # Process init_sql template (stored as JSON list)
                init_sql_list = []
                if init_sql_template:
                    # Parse JSON list of SQL commands and ensure it's a list of strings
                    init_sql_commands = json.loads(init_sql_template)
                    assert isinstance(init_sql_commands, list) and all(
                        isinstance(cmd, str) for cmd in init_sql_commands
                    ), "init_sql_template must decode to a list of strings"

                    # Apply template processing to each command
                    init_sql_list = [
                        jinja_env.from_string(cmd).render(template_context)
                        for cmd in init_sql_commands
                    ]

                connections[connection_name] = ConnectionProfile(
                    url=url, init_sql=init_sql_list, additional_sql_dialect=additional_sql_dialect
                )

                # Collect non-None data documentation repos
                if data_doc_repo:
                    data_documentation_repos.add(data_doc_repo)

            return connections, data_documentation_repos

    @sync_to_async
    def get_organization_by_id(  # type: ignore[override]
        self, organization_id: int
    ) -> Organization | None:
        """Get organization information by ID."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT organization_id, organization_name, organization_industry,
                       stripe_customer_id, stripe_subscription_id, has_governance_channel,
                       contextstore_github_repo
                FROM organizations
                WHERE organization_id = %s
                """,
                (organization_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            return Organization(
                organization_id=row[0],
                organization_name=row[1],
                organization_industry=row[2],
                stripe_customer_id=row[3],
                stripe_subscription_id=row[4],
                has_governance_channel=bool(row[5]),
                contextstore_github_repo=row[6],
            )

    @sync_to_async
    def list_organizations(self) -> list[Organization]:  # type: ignore[override]
        """List all organizations with their Stripe information."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT organization_id, organization_name, organization_industry,
                       stripe_customer_id, stripe_subscription_id, has_governance_channel,
                       contextstore_github_repo
                FROM organizations
                ORDER BY organization_name
                """
            )
            results = cursor.fetchall()

            return [
                Organization(
                    organization_id=row[0],
                    organization_name=row[1],
                    organization_industry=row[2],
                    stripe_customer_id=row[3],
                    stripe_subscription_id=row[4],
                    has_governance_channel=bool(row[5]),
                    contextstore_github_repo=row[6],
                )
                for row in results
            ]

    def list_organizations_with_usage_data(
        self,
        month: int,
        year: int,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str | None = None,
        order: str | None = None,
    ) -> list[OrganizationUsageData]:  # type: ignore[override]
        """List organizations with bot count and usage data for the specified month/year."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Map sort_by values to SQL columns
            sort_column_map = {
                "id": "o.organization_id",
                "name": "o.organization_name",
                "usage": "current_usage",
                "bot_count": "bot_count",
            }

            # Default sort: usage descending
            sort_column = sort_column_map.get(sort_by or "usage", "current_usage")
            sort_order = "DESC" if (order or "desc").lower() == "desc" else "ASC"

            cursor.execute(
                """
                SELECT
                    o.organization_id,
                    o.organization_name,
                    o.organization_industry,
                    o.stripe_customer_id,
                    o.stripe_subscription_id,
                    COALESCE(bot_count.count, 0) as bot_count,
                    COALESCE(usage.answer_count, 0) as current_usage,
                    COALESCE(usage.bonus_answer_count, 0) as bonus_answers
                FROM organizations o
                LEFT JOIN (
                    SELECT organization_id, COUNT(*) as count
                    FROM bot_instances
                    WHERE organization_id IS NOT NULL
                    GROUP BY organization_id
                ) bot_count ON o.organization_id = bot_count.organization_id
                LEFT JOIN (
                    SELECT
                        bi.organization_id,
                        SUM(COALESCE(ut.answer_count, 0)) as answer_count,
                        SUM(COALESCE(ut.bonus_answer_count, 0)) as bonus_answer_count
                    FROM bot_instances bi
                    LEFT JOIN usage_tracking ut ON (bi.slack_team_id || '-' || bi.channel_name) = ut.bot_id
                        AND ut.month = %s AND ut.year = %s
                    WHERE bi.organization_id IS NOT NULL
                    GROUP BY bi.organization_id
                ) usage ON o.organization_id = usage.organization_id
                ORDER BY """
                + sort_column
                + " "
                + sort_order
                + (f" LIMIT {limit}" if limit is not None else "")
                + (f" OFFSET {offset}" if offset is not None else ""),
                (month, year),
            )
            results = cursor.fetchall()

            return [
                OrganizationUsageData(
                    organization_id=row[0],
                    organization_name=row[1],
                    organization_industry=row[2],
                    stripe_customer_id=row[3],
                    stripe_subscription_id=row[4],
                    bot_count=row[5],
                    current_usage=row[6],
                    bonus_answers=row[7],
                )
                for row in results
            ]

    @sync_to_async
    def get_analytics_for_organization(
        self,
        organization_id: int,
        limit: int = 50,
        offset: int = 0,
        event_types: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], int, str]:
        """Get analytics events for a specific organization."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Get organization name
            cursor.execute(
                "SELECT organization_name FROM organizations WHERE organization_id = %s",
                (organization_id,),
            )
            org_row = cursor.fetchone()
            if not org_row:
                return [], 0, "Unknown Organization"

            organization_name = org_row[0]

            # Get total count of analytics events for this organization
            # Handle three bot_id formats:
            # 1. Regular bot instances: "slack_team_id-channel_name"
            # 2. Onboarding events with org_id (after org created): "onboarding-{organization_id}"
            # 3. Onboarding events with sanitized org_name (before org created): "onboarding-{sanitized_org_name}"
            #    where sanitized_org_name is the lowercase, URL-safe version of organization_name
            #    Use case-insensitive matching to handle any legacy inconsistencies

            # Generate the sanitized organization name for matching
            from csbot.slackbot.slack_utils import generate_urlsafe_team_name

            sanitized_org_name = generate_urlsafe_team_name(organization_name)

            # Build event_type filter clause if provided
            event_type_filter = ""
            count_params: tuple[int | str | list[str], ...] = (
                organization_id,
                organization_id,
                sanitized_org_name,
            )
            query_params: tuple[int | str | list[str], ...] = (
                organization_id,
                organization_id,
                sanitized_org_name,
                limit,
                offset,
            )

            if event_types:
                event_type_filter = "AND a.event_type = ANY(%s)"
                count_params = (organization_id, organization_id, sanitized_org_name, event_types)
                query_params = (
                    organization_id,
                    organization_id,
                    sanitized_org_name,
                    event_types,
                    limit,
                    offset,
                )

            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM analytics a
                LEFT JOIN bot_instances bi ON a.bot_id = (bi.slack_team_id || '-' || bi.channel_name)
                WHERE (bi.organization_id = %s
                   OR a.bot_id = ('onboarding-' || %s)
                   OR LOWER(a.bot_id) = LOWER('onboarding-' || %s))
                {event_type_filter}
                """,
                count_params,
            )
            total_count = cursor.fetchone()[0]

            # Get paginated analytics events
            cursor.execute(
                f"""
                SELECT
                    a.id,
                    a.bot_id,
                    a.event_type,
                    a.channel_id,
                    a.user_id,
                    a.thread_ts,
                    a.message_ts,
                    a.metadata,
                    a.tokens_used,
                    a.created_at
                FROM analytics a
                LEFT JOIN bot_instances bi ON (
                    a.bot_id = (bi.slack_team_id || '-' || bi.channel_name)
                    OR a.bot_id = (bi.slack_team_id || '-' || bi.governance_alerts_channel)
                )
                WHERE (bi.organization_id = %s
                   OR a.bot_id = ('onboarding-' || %s)
                   OR LOWER(a.bot_id) = LOWER('onboarding-' || %s))
                {event_type_filter}
                ORDER BY a.created_at DESC
                LIMIT %s OFFSET %s
                """,
                query_params,
            )
            results = cursor.fetchall()

            analytics_events = [
                {
                    "id": row[0],
                    "bot_id": row[1],
                    "event_type": row[2],
                    "channel_id": row[3],
                    "user_id": row[4],
                    "thread_ts": row[5],
                    "message_ts": row[6],
                    "metadata": row[7],
                    "tokens_used": row[8],
                    "created_at": row[9],
                }
                for row in results
            ]

            return analytics_events, total_count, organization_name

    @sync_to_async
    def list_invite_tokens(self) -> list[InviteTokenData]:  # type: ignore[override]
        """List all invite tokens with consumption information."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    rt.id,
                    rt.token,
                    rt.created_at,
                    rt.consumed_at,
                    rt.consumed_by_instance_id,
                    o.organization_name,
                    o.organization_id,
                    rt.consumed_by_organization_ids,
                    rt.issued_by_organization_id,
                    rt.is_single_use,
                    rt.consumer_bonus_answers
                FROM referral_tokens rt
                LEFT JOIN bot_instances bi ON rt.consumed_by_instance_id = bi.id
                LEFT JOIN organizations o ON bi.organization_id = o.organization_id
                ORDER BY rt.created_at DESC
                """
            )
            results = cursor.fetchall()

            import json

            return [
                InviteTokenData(
                    id=row[0],
                    token=row[1],
                    created_at=str(row[2]) if row[2] else "",
                    consumed_at=str(row[3]) if row[3] else None,
                    consumed_by_instance_id=row[4],
                    organization_name=row[5],
                    organization_id=row[6],
                    consumed_by_organization_ids=json.loads(row[7]) if row[7] else [],
                    issued_by_organization_id=row[8],
                    is_single_use=bool(row[9]),
                    consumer_bonus_answers=row[10] if row[10] is not None else 150,
                )
                for row in results
            ]

    def create_invite_token(
        self, token: str, *, is_single_use: bool, consumer_bonus_answers: int
    ) -> None:  # type: ignore[override]
        """Create a new invite token."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO referral_tokens (token, is_single_use, consumer_bonus_answers) VALUES (%s, %s, %s)",
                (token, is_single_use, consumer_bonus_answers),
            )
            conn.commit()

    @sync_to_async
    def set_channel_mapping(  # type: ignore[override]
        self, team_id: str, normalized_channel_name: str, channel_id: str
    ) -> None:
        """Set a mapping between team_id, normalized_channel_name, and channel_id."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO channel_mapping
                (team_id, normalized_channel_name, channel_id, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (team_id, normalized_channel_name)
                DO UPDATE SET
                    channel_id = EXCLUDED.channel_id,
                    updated_at = EXCLUDED.updated_at
                """,
                (team_id, normalized_channel_name, channel_id),
            )
            conn.commit()

    @sync_to_async
    def get_channel_id_by_name(  # type: ignore[override]
        self, team_id: str, normalized_channel_name: str
    ) -> str | None:
        """Get channel ID by team_id and normalized channel name."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT channel_id
                FROM channel_mapping
                WHERE team_id = %s AND normalized_channel_name = %s
                """,
                (team_id, normalized_channel_name),
            )
            result = cursor.fetchone()
            return result[0] if result else None

    @sync_to_async
    def get_channel_name_by_id(  # type: ignore[override]
        self, team_id: str, channel_id: str
    ) -> str | None:
        """Get normalized channel name by team_id and channel ID."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT normalized_channel_name
                FROM channel_mapping
                WHERE team_id = %s AND channel_id = %s
                """,
                (team_id, channel_id),
            )
            result = cursor.fetchone()
            return result[0] if result else None

    @sync_to_async
    def delete_channel_mapping(  # type: ignore[override]
        self, team_id: str, normalized_channel_name: str
    ) -> None:
        """Delete a channel mapping by team_id and normalized channel name."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM channel_mapping
                WHERE team_id = %s AND normalized_channel_name = %s
                """,
                (team_id, normalized_channel_name),
            )
            conn.commit()

    @sync_to_async
    def get_onboarding_state(  # type: ignore[override]
        self, email: str, organization_name: str
    ) -> "OnboardingState | None":
        """Get existing onboarding state.

        Args:
            email: User email
            organization_name: Organization name

        Returns:
            OnboardingState if exists, None otherwise
        """
        from csbot.slackbot.storage.onboarding_state import OnboardingState

        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, email, organization_name, background_onboarding_data, created_at, updated_at
                FROM onboarding_state
                WHERE email = %s AND organization_name = %s
                """,
                (email, organization_name),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return OnboardingState.from_db_row(row)

    @sync_to_async
    def get_onboarding_state_by_organization_id(  # type: ignore[override]
        self, organization_id: int
    ) -> "OnboardingState | None":
        """Get existing onboarding state by organization ID.

        Args:
            organization_id: Organization ID to look up

        Returns:
            OnboardingState if exists, None otherwise
        """
        from csbot.slackbot.storage.onboarding_state import OnboardingState

        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, email, organization_name, background_onboarding_data, created_at, updated_at
                FROM onboarding_state
                WHERE background_onboarding_data::jsonb->>'organization_id' = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (str(organization_id),),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return OnboardingState.from_db_row(row)

    @sync_to_async
    def get_onboarding_state_by_id(  # type: ignore[override]
        self, state_id: int
    ) -> "OnboardingState | None":
        """Get onboarding state by ID.

        Args:
            state_id: Onboarding state ID

        Returns:
            OnboardingState if exists, None otherwise
        """
        from csbot.slackbot.storage.onboarding_state import OnboardingState

        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, email, organization_name, background_onboarding_data, created_at, updated_at
                FROM onboarding_state
                WHERE id = %s
                """,
                (state_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return OnboardingState.from_db_row(row)

    @sync_to_async
    def create_onboarding_state(  # type: ignore[override]
        self, state: "OnboardingState"
    ) -> "OnboardingState":
        """Create a new onboarding state record.

        Args:
            state: OnboardingState instance to create

        Returns:
            OnboardingState with id populated
        """
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            db_dict = state.to_db_dict()

            cursor.execute(
                """
                INSERT INTO onboarding_state (email, organization_name, background_onboarding_data)
                VALUES (%s, %s, %s)
                RETURNING id, created_at, updated_at
                """,
                (
                    db_dict["email"],
                    db_dict["organization_name"],
                    db_dict["background_onboarding_data"],
                ),
            )

            row = cursor.fetchone()
            conn.commit()

            # Return state with populated id, created_at, and updated_at
            return state.model_copy(
                update={"id": row[0], "created_at": row[1], "updated_at": row[2]}
            )

    @sync_to_async
    def update_onboarding_state(self, state: "OnboardingState") -> None:  # type: ignore[override]
        """Update existing onboarding state in database.

        Args:
            state: OnboardingState instance with updated values (must have id set)
        """
        if state.id is None:
            raise ValueError("Cannot update onboarding state without an id")

        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            db_dict = state.to_db_dict()

            cursor.execute(
                """
                UPDATE onboarding_state
                SET background_onboarding_data = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (db_dict["background_onboarding_data"], state.id),
            )
            conn.commit()

    @sync_to_async
    def list_onboarding_states(  # type: ignore[override]
        self, limit: int = 50, cursor: int | None = None
    ) -> list["OnboardingState"]:
        """List onboarding states with cursor-based pagination, ordered by most recent first."""
        from csbot.slackbot.storage.onboarding_state import OnboardingState

        with self._sql_conn_factory.with_conn() as conn:
            db_cursor = conn.cursor()

            if cursor is None:
                # First page - no cursor
                db_cursor.execute(
                    """
                    SELECT id, email, organization_name, background_onboarding_data, created_at, updated_at
                    FROM onboarding_state
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            else:
                # Subsequent pages - use cursor
                db_cursor.execute(
                    """
                    SELECT id, email, organization_name, background_onboarding_data, created_at, updated_at
                    FROM onboarding_state
                    WHERE id < %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (cursor, limit),
                )
            rows = db_cursor.fetchall()

            return [OnboardingState.from_db_row(row) for row in rows]

    @sync_to_async
    def upsert_context_status(  # type: ignore[override]
        self,
        organization_id: int,
        repo_name: str,
        update_type: ContextUpdateType,
        github_url: str,
        title: str,
        description: str,
        status: ContextStatusType,
        created_at: int,
        updated_at: int,
        github_updated_at: int,
        pr_info: "PrInfo | None",
    ) -> None:
        pr_info_json = pr_info.model_dump_json() if pr_info else None
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO context_status (
                    organization_id, repo_name, update_type, github_url,
                    title, description, status,
                    created_at, updated_at, github_updated_at, pr_info
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (github_url)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at,
                    github_updated_at = EXCLUDED.github_updated_at
                """,
                (
                    organization_id,
                    repo_name,
                    update_type.value,
                    github_url,
                    title,
                    description,
                    status.value,
                    created_at,
                    updated_at,
                    github_updated_at,
                    pr_info_json,
                ),
            )
            conn.commit()

    @sync_to_async
    def get_context_status(  # type: ignore[override]
        self,
        organization_id: int,
        status: ContextStatusType | None = None,
        update_type: ContextUpdateType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ContextStatus]:
        from csbot.slackbot.slackbot_models import PrInfo

        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Build query with optional filters
            query = """
                SELECT
                    organization_id, repo_name, update_type, github_url,
                    title, description, status,
                    created_at, updated_at, github_updated_at, pr_info
                FROM context_status
                WHERE organization_id = %s
            """
            params: list[Any] = [organization_id]

            if status is not None:
                query += " AND status = %s"
                params.append(status.value)

            if update_type is not None:
                query += " AND update_type = %s"
                params.append(update_type.value)

            query += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert rows to ContextStatus objects
            results: list[ContextStatus] = []
            for row in rows:
                pr_info_obj = PrInfo.model_validate_json(row[10]) if row[10] else None
                results.append(
                    ContextStatus(
                        organization_id=row[0],
                        repo_name=row[1],
                        update_type=ContextUpdateType(row[2]),
                        github_url=row[3],
                        title=row[4],
                        description=row[5],
                        status=ContextStatusType(row[6]),
                        created_at=row[7],
                        updated_at=row[8],
                        github_updated_at=row[9],
                        pr_info=pr_info_obj,
                    )
                )
            return results

    @sync_to_async
    def add_org_user(  # type: ignore[override]
        self,
        slack_user_id: str,
        email: str | None,
        organization_id: int,
        is_org_admin: bool = False,
        name: str | None = None,
    ) -> OrgUser:
        """Add a user to an organization."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO org_users (slack_user_id, email, organization_id, is_org_admin, name)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (slack_user_id, organization_id) DO NOTHING
                RETURNING id, slack_user_id, email, organization_id, is_org_admin, name
                """,
                (slack_user_id, email, organization_id, 1 if is_org_admin else 0, name),
            )
            row = cursor.fetchone()

            # If no row returned due to conflict, fetch the existing user within the transaction
            if row is None:
                cursor.execute(
                    """
                    SELECT id, slack_user_id, email, organization_id, is_org_admin, name
                    FROM org_users
                    WHERE slack_user_id = %s AND organization_id = %s
                    """,
                    (slack_user_id, organization_id),
                )
                row = cursor.fetchone()

            conn.commit()

            # Row must exist since we just inserted or it already existed
            assert row is not None
            return OrgUser(
                id=row[0],
                slack_user_id=row[1],
                email=row[2],
                organization_id=row[3],
                is_org_admin=bool(row[4]),
                name=row[5],
            )

    @sync_to_async
    def update_org_user_admin_status(  # type: ignore[override]
        self,
        slack_user_id: str,
        organization_id: int,
        is_org_admin: bool,
    ) -> None:
        """Update admin status for an organization user."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE org_users
                SET is_org_admin = %s
                WHERE slack_user_id = %s AND organization_id = %s
                """,
                (1 if is_org_admin else 0, slack_user_id, organization_id),
            )

            if cursor.rowcount == 0:
                raise ValueError(
                    f"User not found for slack_user_id={slack_user_id} and organization_id={organization_id}"
                )

            conn.commit()

    @sync_to_async
    def get_org_users(  # type: ignore[override]
        self, organization_id: int, cursor: int | None = None, limit: int = 50
    ) -> list[OrgUser]:
        """Get users for an organization with cursor-based pagination."""
        with self._sql_conn_factory.with_conn() as conn:
            db_cursor = conn.cursor()

            if cursor is None:
                db_cursor.execute(
                    """
                    SELECT id, slack_user_id, email, organization_id, is_org_admin, name
                    FROM org_users
                    WHERE organization_id = %s
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (organization_id, limit),
                )
            else:
                db_cursor.execute(
                    """
                    SELECT id, slack_user_id, email, organization_id, is_org_admin, name
                    FROM org_users
                    WHERE organization_id = %s AND id > %s
                    ORDER BY id ASC
                    LIMIT %s
                    """,
                    (organization_id, cursor, limit),
                )
            rows = db_cursor.fetchall()

            return [
                OrgUser(
                    id=row[0],
                    slack_user_id=row[1],
                    email=row[2],
                    organization_id=row[3],
                    is_org_admin=bool(row[4]),
                    name=row[5],
                )
                for row in rows
            ]

    @sync_to_async
    def get_org_user_by_slack_user_id(  # type: ignore[override]
        self, slack_user_id: str, organization_id: int
    ) -> OrgUser | None:
        """Get a user by slack_user_id and organization_id."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, slack_user_id, email, organization_id, is_org_admin, name
                FROM org_users
                WHERE slack_user_id = %s AND organization_id = %s
                """,
                (slack_user_id, organization_id),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return OrgUser(
                id=row[0],
                slack_user_id=row[1],
                email=row[2],
                organization_id=row[3],
                is_org_admin=bool(row[4]),
                name=row[5],
            )

    @sync_to_async
    def get_org_user_by_email(  # type: ignore[override]
        self, email: str, organization_id: int
    ) -> OrgUser | None:
        """Get a user by email and organization_id."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, slack_user_id, email, organization_id, is_org_admin, name
                FROM org_users
                WHERE email = %s AND organization_id = %s
                """,
                (email, organization_id),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return OrgUser(
                id=row[0],
                slack_user_id=row[1],
                email=row[2],
                organization_id=row[3],
                is_org_admin=bool(row[4]),
                name=row[5],
            )

    @sync_to_async
    def get_org_user_by_id(  # type: ignore[override]
        self, org_user_id: int
    ) -> OrgUser | None:
        """Get a user by org_user_id."""
        with self._sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, slack_user_id, email, organization_id, is_org_admin, name
                FROM org_users
                WHERE id = %s
                """,
                (org_user_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return OrgUser(
                id=row[0],
                slack_user_id=row[1],
                email=row[2],
                organization_id=row[3],
                is_org_admin=bool(row[4]),
                name=row[5],
            )


class SlackbotInstancePostgresqlStorage(SlackbotPostgresqlStorage, SlackbotInstanceStorage):  # type: ignore[override]
    def __init__(
        self,
        sql_conn_factory: SqlConnectionFactory,
        kek_provider: KekProvider,
        bot_id: str,
        time: SecondsNow = system_seconds_now,
    ):
        super().__init__(sql_conn_factory, kek_provider, time)
        self.bot_id = bot_id

    @property
    def sql_conn_factory(self) -> SqlConnectionFactory:
        """Get the SQL connection factory used by this storage implementation."""
        return self._sql_conn_factory

    @sync_to_async
    def get(self, family: str, key: str) -> str | None:  # type: ignore[override]
        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            current_time = self.seconds_now()

            # Single atomic operation: get value if not deleted and not expired
            cursor.execute(
                """
                SELECT value FROM kv
                WHERE bot_id = %s AND family = %s AND key = %s
                AND (expires_at_seconds = -1 OR expires_at_seconds > %s)
                """,
                (self.bot_id, family, key, current_time),
            )
            result = cursor.fetchone()
            return result[0] if result else None

    @sync_to_async
    def set(  # type: ignore[override]
        self, family: str, key: str, value: str, expiry_seconds: int | None = None
    ) -> None:
        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO kv
                (bot_id, family, key, value, expires_at_seconds, deleted_at_seconds)
                VALUES (%s, %s, %s, %s, %s, -1)
                ON CONFLICT (bot_id, family, key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    expires_at_seconds = EXCLUDED.expires_at_seconds,
                    deleted_at_seconds = -1
                """,
                (
                    self.bot_id,
                    family,
                    key,
                    value,
                    (
                        self.seconds_now() + expiry_seconds
                        if expiry_seconds and expiry_seconds > 0
                        else -1
                    ),
                ),
            )
            conn.commit()

    @sync_to_async
    def exists(self, family: str, key: str) -> bool:  # type: ignore[override]
        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            current_time = self.seconds_now()

            # Single atomic operation: check if key exists and is not deleted and not expired
            cursor.execute(
                """
                SELECT 1 FROM kv
                WHERE bot_id = %s AND family = %s AND key = %s
                AND (expires_at_seconds = -1 OR expires_at_seconds > %s)
                """,
                (self.bot_id, family, key, current_time),
            )
            result = cursor.fetchone()
            return result is not None

    @sync_to_async
    def get_and_set(  # type: ignore[override]
        self,
        family: str,
        key: str,
        value_factory: Callable[[str | None], str | None],
        expiry_seconds: int | None = None,
    ) -> None:
        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            current_time = self.seconds_now()

            # Start transaction
            cursor.execute("BEGIN")
            try:
                # Get current value if not deleted and not expired
                cursor.execute(
                    """
                    SELECT value FROM kv
                    WHERE bot_id = %s AND family = %s AND key = %s
                    AND (expires_at_seconds = -1 OR expires_at_seconds > %s)
                    """,
                    (self.bot_id, family, key, current_time),
                )
                result = cursor.fetchone()
                current_value = result[0] if result else None

                # Call value factory to get new value
                new_value = value_factory(current_value)

                if new_value is None:
                    # Delete the key if value_factory returned None
                    cursor.execute(
                        """
                        UPDATE kv SET expires_at_seconds = %s
                        WHERE bot_id = %s AND family = %s AND key = %s
                        """,
                        (current_time, self.bot_id, family, key),
                    )
                else:
                    # Set the new value
                    expires_at = (
                        current_time + expiry_seconds
                        if expiry_seconds and expiry_seconds > 0
                        else -1
                    )
                    cursor.execute(
                        """
                        INSERT INTO kv
                        (bot_id, family, key, value, expires_at_seconds, deleted_at_seconds)
                        VALUES (%s, %s, %s, %s, %s, -1)
                        ON CONFLICT (bot_id, family, key)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            expires_at_seconds = EXCLUDED.expires_at_seconds,
                            deleted_at_seconds = -1
                        """,
                        (self.bot_id, family, key, new_value, expires_at),
                    )

                # Commit transaction
                cursor.execute("COMMIT")
            except Exception:
                # Rollback on error
                cursor.execute("ROLLBACK")
                raise

    @sync_to_async
    def delete(self, family: str, key: str) -> None:  # type: ignore[override]
        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            # Soft delete: set expires_at_seconds to current time
            cursor.execute(
                """
                UPDATE kv SET expires_at_seconds = %s
                WHERE bot_id = %s AND family = %s AND key = %s
                """,
                (self.seconds_now(), self.bot_id, family, key),
            )
            conn.commit()

    @sync_to_async
    def list(self, family: str) -> list[str]:  # type: ignore[override]
        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            current_time = self.seconds_now()

            # Get all keys for the family that are not deleted and not expired
            cursor.execute(
                """
                SELECT key FROM kv
                WHERE bot_id = %s AND family = %s
                AND deleted_at_seconds = -1
                AND (expires_at_seconds = -1 OR expires_at_seconds > %s)
                ORDER BY key
                """,
                (self.bot_id, family, current_time),
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]
