"""
Schema change organization for database storage.

This module organizes database schema changes into separate classes for better
maintainability and testability. Supports both SQLite and PostgreSQL.
"""

import os
from abc import ABC, abstractmethod
from typing import Any

import structlog

from csbot.slackbot.storage.utils import ConnectionType, is_postgresql

logger = structlog.get_logger(__name__)


def _safe_execute(cursor: Any, query: str, params: Any = None) -> None:
    """Execute SQL safely for both psycopg and SQLite cursors."""
    if params is not None:
        cursor.execute(query, params)  # type: ignore[arg-type]
    else:
        cursor.execute(query)  # type: ignore[arg-type]


class SchemaChange(ABC):
    """Represents a single schema change operation."""

    @abstractmethod
    def apply(self, conn: ConnectionType) -> None:
        """Apply this schema change to the connection."""
        pass

    @abstractmethod
    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if this schema change needs to be applied."""
        pass

    def _get_serial_primary_key(self, conn: ConnectionType) -> str:
        """Get the appropriate serial primary key syntax."""
        return "SERIAL PRIMARY KEY" if is_postgresql(conn) else "INTEGER PRIMARY KEY AUTOINCREMENT"

    def _get_bigint_type(self, conn: ConnectionType) -> str:
        """Get the appropriate big integer type."""
        return "BIGINT" if is_postgresql(conn) else "INTEGER"

    def _check_column_exists(self, conn: ConnectionType, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        cursor = conn.cursor()
        if is_postgresql(conn):
            _safe_execute(
                cursor,
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """,
                (table_name, column_name),
            )
            return cursor.fetchone() is not None
        else:
            _safe_execute(cursor, f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            return column_name in column_names

    def _check_table_exists(self, conn: ConnectionType, table_name: str) -> bool:
        """Check if a table exists in the database."""
        cursor = conn.cursor()
        if is_postgresql(conn):
            _safe_execute(
                cursor,
                "SELECT table_name FROM information_schema.tables WHERE table_name = %s",
                (table_name,),
            )
            return cursor.fetchone() is not None
        else:
            _safe_execute(
                cursor,
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
                (table_name,),
            )
            return cursor.fetchone() is not None

    def _check_index_exists(self, conn: ConnectionType, index_name: str) -> bool:
        """Check if an index exists in the database."""
        cursor = conn.cursor()
        if is_postgresql(conn):
            _safe_execute(
                cursor,
                "SELECT indexname FROM pg_indexes WHERE indexname = %s",
                (index_name,),
            )
            return cursor.fetchone() is not None
        else:
            _safe_execute(
                cursor,
                "SELECT name FROM sqlite_master WHERE type='index' AND name = ?",
                (index_name,),
            )
            return cursor.fetchone() is not None


class CreateKvTable(SchemaChange):
    """Create the main kv table with database-appropriate schema."""

    def apply(self, conn: ConnectionType) -> None:
        bigint_type = self._get_bigint_type(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS kv (
                bot_id TEXT,
                family TEXT,
                key TEXT,
                value TEXT,
                expires_at_seconds {bigint_type},
                PRIMARY KEY (bot_id, family, key)
            )
        """,
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "kv")


class AddDeletedAtColumn(SchemaChange):
    """Add deleted_at_seconds column if missing."""

    def apply(self, conn: ConnectionType) -> None:
        bigint_type = self._get_bigint_type(conn)
        _safe_execute(
            conn.cursor(), f"ALTER TABLE kv ADD COLUMN deleted_at_seconds {bigint_type} DEFAULT -1"
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "kv", "deleted_at_seconds")


class CreateKvIndexes(SchemaChange):
    """Create indexes on kv table."""

    def __init__(self, include_deleted_at: bool = False):
        self.include_deleted_at = include_deleted_at

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(
            conn.cursor(),
            """
            CREATE INDEX IF NOT EXISTS idx_kv_expires_at_seconds ON kv (expires_at_seconds)
        """,
        )

        if self.include_deleted_at:
            _safe_execute(
                conn.cursor(),
                """
                CREATE INDEX IF NOT EXISTS idx_kv_deleted_at_seconds ON kv (deleted_at_seconds)
            """,
            )

    def is_needed(self, conn: ConnectionType) -> bool:
        if not self._check_index_exists(conn, "idx_kv_expires_at_seconds"):
            return True
        if self.include_deleted_at and not self._check_index_exists(
            conn, "idx_kv_deleted_at_seconds"
        ):
            return True
        return False


class CreateAnalyticsTable(SchemaChange):
    """Create analytics table with all indexes."""

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS analytics (
                id {serial_pk},
                bot_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                channel_id TEXT,
                user_id TEXT,
                thread_ts TEXT,
                message_ts TEXT,
                metadata TEXT,
                tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Create all analytics indexes
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_analytics_bot_id ON analytics (bot_id)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics (event_type)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics (created_at)",
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "analytics")


class CreateBotInstancesTable(SchemaChange):
    """Create bot_instances table to store bot configuration.

    Each bot instance is a single instance of a bot running in a single channel.
    Each of these instances is backed by a context store, and can have
    multiple connections to different warehouses, and multiple MCP server
    configurations - see below for more information on these tables.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS bot_instances (
                id {serial_pk},
                channel_name TEXT NOT NULL,
                bot_email TEXT NOT NULL,
                contextstore_github_repo TEXT,
                governance_alerts_channel TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Create indexes for efficient lookups
        index_statements = [
            (
                "CREATE INDEX IF NOT EXISTS idx_bot_instances_channel_name "
                "ON bot_instances (channel_name)"
            ),
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "bot_instances")


class CreateConnectionsTable(SchemaChange):
    """Create connections table to store database connections for each bot instance.

    Each connection has a name, a URL (which may contain jinja templating to e.g. pull
    secrets from the Render secret store), and an optional init_sql statement to run on the
    connection when it is created - useful for temporary duckdb warehouses for test
    instances.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS connections (
                id {serial_pk},
                bot_instance_id INTEGER NOT NULL,
                connection_name TEXT NOT NULL,
                url TEXT NOT NULL,
                init_sql TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_instance_id) REFERENCES bot_instances (id) ON DELETE CASCADE,
                UNIQUE (bot_instance_id, connection_name)
            )
        """,
        )
        # Create indexes for efficient lookups if bot_instance_id column exists
        if self._check_column_exists(conn, "connections", "bot_instance_id"):
            index_statements = [
                (
                    "CREATE INDEX IF NOT EXISTS idx_connections_bot_instance_connection "
                    "ON connections (bot_instance_id, connection_name)"
                ),
            ]
        else:
            index_statements = []

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "connections")


class AddInitSqlColumn(SchemaChange):
    """Add init_sql column to connections table if missing."""

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(conn.cursor(), "ALTER TABLE connections ADD COLUMN init_sql TEXT")

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "connections", "init_sql")


class AddSlackTeamIdColumn(SchemaChange):
    """Add slack_team_id column to bot_instances table if missing."""

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(conn.cursor(), "ALTER TABLE bot_instances ADD COLUMN slack_team_id TEXT")

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "bot_instances", "slack_team_id")


class CreateSlackBotTokensTable(SchemaChange):
    """Create slack_bot_tokens table to store Slack bot tokens by team."""

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS slack_bot_tokens (
                id {serial_pk},
                slack_team_id TEXT NOT NULL UNIQUE,
                bot_token_env_var_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Create index for efficient lookups
        index_statements = [
            (
                "CREATE INDEX IF NOT EXISTS idx_slack_bot_tokens_team_id "
                "ON slack_bot_tokens (slack_team_id)"
            ),
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "slack_bot_tokens")


class CreateReferralTokensTable(SchemaChange):
    """Create referral_tokens table to store referral tokens.

    Each token is a string with a nullable consumed_by_instance_id column
    to track which bot instance consumed the token.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS referral_tokens (
                id {serial_pk},
                token TEXT NOT NULL UNIQUE,
                consumed_by_instance_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                consumed_at TIMESTAMP,
                FOREIGN KEY (consumed_by_instance_id) REFERENCES bot_instances (id) ON DELETE SET NULL
            )
        """,
        )

        # Create indexes for efficient lookups
        index_statements = [
            ("CREATE INDEX IF NOT EXISTS idx_referral_tokens_token ON referral_tokens (token)"),
            (
                "CREATE INDEX IF NOT EXISTS idx_referral_tokens_consumed_by "
                "ON referral_tokens (consumed_by_instance_id)"
            ),
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "referral_tokens")


class CreateUsageTrackingTable(SchemaChange):
    """Create usage_tracking table to store answer counts for pricing model.

    Tracks the number of answers (streaming_reply_to_thread_with_ai invocations)
    per bot for pricing purposes.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        bigint_type = self._get_bigint_type(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS usage_tracking (
                id {serial_pk},
                bot_id TEXT NOT NULL,
                answer_count {bigint_type} NOT NULL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (bot_id)
            )
        """,
        )

        # Only create indexes if monthly migration hasn't run yet
        # The monthly migration will create its own indexes
        has_month = self._check_column_exists(conn, "usage_tracking", "month")
        has_year = self._check_column_exists(conn, "usage_tracking", "year")

        if not has_month and not has_year:
            # Create indexes for the original structure
            index_statements = [
                ("CREATE INDEX IF NOT EXISTS idx_usage_tracking_bot_id ON usage_tracking (bot_id)"),
                (
                    "CREATE INDEX IF NOT EXISTS idx_usage_tracking_last_updated "
                    "ON usage_tracking (last_updated)"
                ),
            ]

            for index_sql in index_statements:
                _safe_execute(conn.cursor(), index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "usage_tracking")


class AddSqlDialectColumn(SchemaChange):
    """Add additional_sql_dialect column to connections table if missing."""

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(
            conn.cursor(), "ALTER TABLE connections ADD COLUMN additional_sql_dialect TEXT NULL"
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "connections", "additional_sql_dialect")


class CreateOrganizationsTable(SchemaChange):
    """Create organizations table and add organization_id column to bot_instances table."""

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        cursor = conn.cursor()

        # Create organizations table
        _safe_execute(
            cursor,
            f"""
            CREATE TABLE IF NOT EXISTS organizations (
                organization_id {serial_pk},
                organization_name TEXT NOT NULL,
                organization_industry TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Create index for efficient lookups
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations (organization_name)",
        ]

        for index_sql in index_statements:
            _safe_execute(cursor, index_sql)

        # Add organization_id column to bot_instances if it doesn't exist
        if not self._check_column_exists(conn, "bot_instances", "organization_id"):
            _safe_execute(cursor, "ALTER TABLE bot_instances ADD COLUMN organization_id INTEGER")

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "organizations")


class MakeOrganizationIdRequired(SchemaChange):
    """Make organization_id column NOT NULL and add foreign key constraint to organizations table.

    This change should be applied after the PopulateOrganizationsFromBotInstances data migration
    has run to ensure all bot_instances have valid organization_id values.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        if is_postgresql(conn):
            # PostgreSQL: Add NOT NULL constraint and foreign key
            _safe_execute(
                cursor, "ALTER TABLE bot_instances ALTER COLUMN organization_id SET NOT NULL"
            )
            _safe_execute(
                cursor,
                """
                ALTER TABLE bot_instances
                ADD CONSTRAINT fk_bot_instances_organization_id
                FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE
            """,
            )
            # Add index for efficient lookups by organization_id
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_bot_instances_organization_id
                ON bot_instances (organization_id)
            """,
            )
        else:
            # SQLite doesn't support adding constraints to existing columns easily
            # We need to recreate the table with the constraints

            # Get current table schema (excluding organization_id)
            _safe_execute(cursor, "PRAGMA table_info(bot_instances)")
            columns_info = cursor.fetchall()

            # Build column definitions for new table
            column_defs = []
            for col in columns_info:
                col_name = col[1]
                col_type = col[2]
                col_notnull = col[3]
                col_default = col[4]
                col_pk = col[5]

                if col_name == "organization_id":
                    # Make organization_id NOT NULL
                    column_defs.append(f"{col_name} {col_type} NOT NULL")
                elif col_pk:
                    # Preserve primary key
                    column_defs.append(f"{col_name} {col_type} PRIMARY KEY AUTOINCREMENT")
                else:
                    # Regular column
                    col_def = f"{col_name} {col_type}"
                    if col_notnull:
                        col_def += " NOT NULL"
                    if col_default is not None:
                        col_def += f" DEFAULT {col_default}"
                    column_defs.append(col_def)

            # Add foreign key constraint
            column_defs.append(
                "FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE"
            )

            # Create new table with constraints
            columns_sql = ",\n                ".join(column_defs)
            _safe_execute(
                cursor,
                f"""
                CREATE TABLE bot_instances_new (
                {columns_sql}
                )
            """,
            )

            # Copy data from old table
            _safe_execute(cursor, "INSERT INTO bot_instances_new SELECT * FROM bot_instances")

            # Drop old table and rename new one
            _safe_execute(cursor, "DROP TABLE bot_instances")
            _safe_execute(cursor, "ALTER TABLE bot_instances_new RENAME TO bot_instances")

            # Recreate indexes
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_bot_instances_channel_name
                ON bot_instances (channel_name)
            """,
            )
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_bot_instances_organization_id
                ON bot_instances (organization_id)
            """,
            )

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if organization_id column exists and is nullable."""
        if not self._check_column_exists(conn, "bot_instances", "organization_id"):
            return False  # Column doesn't exist, can't make it required

        cursor = conn.cursor()

        if is_postgresql(conn):
            # Check if column allows NULL values
            _safe_execute(
                cursor,
                """
                SELECT is_nullable FROM information_schema.columns
                WHERE table_name = 'bot_instances' AND column_name = 'organization_id'
            """,
            )
            result = cursor.fetchone()
            return result and result[0] == "YES"  # Returns True if nullable # type: ignore
        else:
            # For SQLite, check table schema
            _safe_execute(cursor, "PRAGMA table_info(bot_instances)")
            columns = cursor.fetchall()
            for col in columns:
                if col[1] == "organization_id":
                    return col[3] == 0  # Returns True if NOT NULL is 0 (nullable)
            return False


class RemoveOrganizationColumnsFromBotInstances(SchemaChange):
    """Remove organization_name and organization_industry columns from bot_instances table.

    These columns are now redundant since organization data is stored in the organizations table
    and referenced via organization_id foreign key.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        if is_postgresql(conn):
            # PostgreSQL supports dropping columns directly
            if self._check_column_exists(conn, "bot_instances", "organization_name"):
                _safe_execute(cursor, "ALTER TABLE bot_instances DROP COLUMN organization_name")

            if self._check_column_exists(conn, "bot_instances", "organization_industry"):
                _safe_execute(cursor, "ALTER TABLE bot_instances DROP COLUMN organization_industry")
        else:
            # SQLite doesn't support DROP COLUMN, so we need to recreate the table

            # Get current table schema
            _safe_execute(cursor, "PRAGMA table_info(bot_instances)")
            columns_info = cursor.fetchall()

            # Build column definitions excluding the organization columns
            column_defs = []
            for col in columns_info:
                col_name = col[1]
                col_type = col[2]
                col_notnull = col[3]
                col_default = col[4]
                col_pk = col[5]

                # Skip the organization columns we want to remove
                if col_name in ("organization_name", "organization_industry"):
                    continue

                if col_name == "organization_id":
                    # Preserve NOT NULL and foreign key constraint
                    column_defs.append(f"{col_name} {col_type} NOT NULL")
                elif col_pk:
                    # Preserve primary key
                    column_defs.append(f"{col_name} {col_type} PRIMARY KEY AUTOINCREMENT")
                else:
                    # Regular column
                    col_def = f"{col_name} {col_type}"
                    if col_notnull:
                        col_def += " NOT NULL"
                    if col_default is not None:
                        col_def += f" DEFAULT {col_default}"
                    column_defs.append(col_def)

            # Add foreign key constraint
            column_defs.append(
                "FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE"
            )

            # Create new table without the organization columns
            columns_sql = ",\n                ".join(column_defs)
            _safe_execute(
                cursor,
                f"""
                CREATE TABLE bot_instances_new (
                {columns_sql}
                )
            """,
            )

            # Copy data from old table (excluding organization columns)
            select_columns = []
            for col in columns_info:
                col_name = col[1]
                if col_name not in ("organization_name", "organization_industry"):
                    select_columns.append(col_name)

            select_sql = ", ".join(select_columns)
            _safe_execute(
                cursor,
                f"INSERT INTO bot_instances_new ({select_sql}) SELECT {select_sql} FROM bot_instances",
            )

            # Drop old table and rename new one
            _safe_execute(cursor, "DROP TABLE bot_instances")
            _safe_execute(cursor, "ALTER TABLE bot_instances_new RENAME TO bot_instances")

            # Recreate indexes
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_bot_instances_channel_name
                ON bot_instances (channel_name)
            """,
            )
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_bot_instances_organization_id
                ON bot_instances (organization_id)
            """,
            )

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if either organization column still exists."""
        return self._check_column_exists(
            conn, "bot_instances", "organization_name"
        ) or self._check_column_exists(conn, "bot_instances", "organization_industry")


class AddStripeCustomerIdColumn(SchemaChange):
    """Add stripe_customer_id column to organizations table if missing."""

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(conn.cursor(), "ALTER TABLE organizations ADD COLUMN stripe_customer_id TEXT")

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "organizations", "stripe_customer_id")


class AddStripeSubscriptionIdColumn(SchemaChange):
    """Add stripe_subscription_id column to organizations table if missing."""

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(
            conn.cursor(), "ALTER TABLE organizations ADD COLUMN stripe_subscription_id TEXT"
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "organizations", "stripe_subscription_id")


class CreatePlanLimitsTable(SchemaChange):
    """Create plan_limits table to store cached plan information per organization.

    This table caches plan limits from Stripe to avoid API calls during usage validation.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        bigint_type = self._get_bigint_type(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS plan_limits (
                id {serial_pk},
                organization_id INTEGER NOT NULL,
                cached_base_num_answers {bigint_type} NOT NULL,
                cached_allow_overage BOOLEAN NOT NULL DEFAULT FALSE,
                cached_num_channels INTEGER NOT NULL,
                cached_allow_additional_channels BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE,
                UNIQUE (organization_id)
            )
        """,
        )

        # Create index for efficient lookups
        index_statements = [
            (
                "CREATE INDEX IF NOT EXISTS idx_plan_limits_organization_id "
                "ON plan_limits (organization_id)"
            ),
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "plan_limits")


class UpdateUsageTrackingToMonthly(SchemaChange):
    """Update usage_tracking table to track by month instead of cumulative totals.

    Changes the table structure from tracking cumulative answer_count per bot_id
    to tracking monthly usage with unique combinations of bot_id, month, year.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        # First, check if we need to migrate existing data
        _safe_execute(cursor, "SELECT COUNT(*) FROM usage_tracking")
        result = cursor.fetchone()
        existing_rows = result[0] if result else 0

        if is_postgresql(conn):
            # PostgreSQL implementation
            if existing_rows > 0:
                # Create temporary table with monthly structure
                _safe_execute(
                    cursor,
                    """
                    CREATE TABLE usage_tracking_new (
                        id SERIAL PRIMARY KEY,
                        bot_id TEXT NOT NULL,
                        month INTEGER NOT NULL,
                        year INTEGER NOT NULL,
                        answer_count BIGINT NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (bot_id, month, year)
                    )
                """,
                )

                # Migrate existing data to current month/year
                _safe_execute(
                    cursor,
                    """
                    INSERT INTO usage_tracking_new (bot_id, month, year, answer_count, created_at, updated_at)
                    SELECT
                        bot_id,
                        EXTRACT(MONTH FROM CURRENT_TIMESTAMP)::INTEGER,
                        EXTRACT(YEAR FROM CURRENT_TIMESTAMP)::INTEGER,
                        answer_count,
                        created_at,
                        last_updated
                    FROM usage_tracking
                """,
                )

                # Drop old table and rename new one
                _safe_execute(cursor, "DROP TABLE usage_tracking")
                _safe_execute(cursor, "ALTER TABLE usage_tracking_new RENAME TO usage_tracking")
            else:
                # No existing data, just drop and recreate
                _safe_execute(cursor, "DROP TABLE IF EXISTS usage_tracking")
                _safe_execute(
                    cursor,
                    """
                    CREATE TABLE usage_tracking (
                        id SERIAL PRIMARY KEY,
                        bot_id TEXT NOT NULL,
                        month INTEGER NOT NULL,
                        year INTEGER NOT NULL,
                        answer_count BIGINT NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (bot_id, month, year)
                    )
                """,
                )

            # Create indexes for efficient lookups
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_usage_tracking_bot_id_month_year
                ON usage_tracking (bot_id, year, month)
            """,
            )
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_usage_tracking_year_month
                ON usage_tracking (year, month)
            """,
            )

        else:
            # SQLite implementation
            if existing_rows > 0:
                # Create temporary table with monthly structure
                _safe_execute(
                    cursor,
                    """
                    CREATE TABLE usage_tracking_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bot_id TEXT NOT NULL,
                        month INTEGER NOT NULL,
                        year INTEGER NOT NULL,
                        answer_count INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (bot_id, month, year)
                    )
                """,
                )

                # Migrate existing data to current month/year using strftime
                _safe_execute(
                    cursor,
                    """
                    INSERT INTO usage_tracking_new (bot_id, month, year, answer_count, created_at, updated_at)
                    SELECT
                        bot_id,
                        CAST(strftime('%m', 'now') AS INTEGER),
                        CAST(strftime('%Y', 'now') AS INTEGER),
                        answer_count,
                        created_at,
                        last_updated
                    FROM usage_tracking
                """,
                )

                # Drop old table and rename new one
                _safe_execute(cursor, "DROP TABLE usage_tracking")
                _safe_execute(cursor, "ALTER TABLE usage_tracking_new RENAME TO usage_tracking")
            else:
                # No existing data, just drop and recreate
                _safe_execute(cursor, "DROP TABLE IF EXISTS usage_tracking")
                _safe_execute(
                    cursor,
                    """
                    CREATE TABLE usage_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bot_id TEXT NOT NULL,
                        month INTEGER NOT NULL,
                        year INTEGER NOT NULL,
                        answer_count INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (bot_id, month, year)
                    )
                """,
                )

            # Create indexes for efficient lookups
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_usage_tracking_bot_id_month_year
                ON usage_tracking (bot_id, year, month)
            """,
            )
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_usage_tracking_year_month
                ON usage_tracking (year, month)
            """,
            )

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if we need to update the usage_tracking table structure."""
        # Check if the new monthly columns exist
        has_month = self._check_column_exists(conn, "usage_tracking", "month")
        has_year = self._check_column_exists(conn, "usage_tracking", "year")

        # If both month and year columns exist, migration is not needed
        if has_month and has_year:
            return False

        # If neither exists, we need migration
        if not has_month and not has_year:
            return True

        # If only one exists, something is wrong - we should still migrate
        return True


class CreateBonusAnswerGrantsTable(SchemaChange):
    """Create bonus_answer_grants table to track bonus answers granted to organizations.

    This table tracks bonus answer allocations that can be earned through referrals,
    promotions, or other incentive programs.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        bigint_type = self._get_bigint_type(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS bonus_answer_grants (
                id {serial_pk},
                organization_id INTEGER NOT NULL,
                answer_count {bigint_type} NOT NULL,
                grant_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE
            )
        """,
        )

        # Create indexes for efficient lookups
        index_statements = [
            (
                "CREATE INDEX IF NOT EXISTS idx_bonus_answer_grants_organization_id "
                "ON bonus_answer_grants (organization_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_bonus_answer_grants_grant_date "
                "ON bonus_answer_grants (grant_date)"
            ),
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "bonus_answer_grants")


class AddBonusAnswerCountColumn(SchemaChange):
    """Add bonus_answer_count column to usage_tracking table if missing."""

    def apply(self, conn: ConnectionType) -> None:
        bigint_type = self._get_bigint_type(conn)
        _safe_execute(
            conn.cursor(),
            f"ALTER TABLE usage_tracking ADD COLUMN bonus_answer_count {bigint_type} DEFAULT 0",
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "usage_tracking", "bonus_answer_count")


class CreateTosRecordsTable(SchemaChange):
    """Create tos_records table to track terms of service acceptance submissions.

    This table records when companies accept the terms of service during onboarding,
    storing the email, organization ID, organization name, and datetime of acceptance.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS tos_records (
                id {serial_pk},
                email TEXT NOT NULL,
                organization_id INTEGER NOT NULL,
                organization_name TEXT NOT NULL,
                accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        # Create indexes for efficient lookups
        index_statements = [
            (
                "CREATE INDEX IF NOT EXISTS idx_tos_records_organization_id "
                "ON tos_records (organization_id)"
            ),
            ("CREATE INDEX IF NOT EXISTS idx_tos_records_email ON tos_records (email)"),
            ("CREATE INDEX IF NOT EXISTS idx_tos_records_accepted_at ON tos_records (accepted_at)"),
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "tos_records")


class AddOrganizationIdToConnections(SchemaChange):
    """Add organization_id column to connections table if missing."""

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(conn.cursor(), "ALTER TABLE connections ADD COLUMN organization_id INTEGER")

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "connections", "organization_id")


class CreateBotToConnectionsTable(SchemaChange):
    """Create bot_to_connections table to map bot keys to connection names by organization.

    This table maps a (organization_id, bot_id) pair to a connection_name, allowing
    different bots within the same organization to use different database connections.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS bot_to_connections (
                id {serial_pk},
                organization_id INTEGER NOT NULL,
                bot_id TEXT NOT NULL,
                connection_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE,
                UNIQUE (organization_id, bot_id, connection_name)
            )
        """,
        )

        # Create indexes for efficient lookups
        index_statements = [
            (
                "CREATE INDEX IF NOT EXISTS idx_bot_to_connections_org_bot "
                "ON bot_to_connections (organization_id, bot_id)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_bot_to_connections_org_id "
                "ON bot_to_connections (organization_id)"
            ),
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "bot_to_connections")


class DropBotInstanceIdFromConnections(SchemaChange):
    """Drop bot_instance_id column and related constraints from connections table.

    This change removes the bot_instance_id column since connections are now accessed
    through the bot_to_connections mapping table instead of directly by bot_instance_id.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        if is_postgresql(conn):
            # PostgreSQL: Drop foreign key constraint first, then column
            # First check if constraint exists and drop it
            _safe_execute(
                cursor,
                """
                SELECT constraint_name FROM information_schema.table_constraints
                WHERE table_name = 'connections' AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%bot_instance_id%'
            """,
            )
            constraints = cursor.fetchall()
            for constraint in constraints:
                _safe_execute(cursor, f"ALTER TABLE connections DROP CONSTRAINT {constraint[0]}")

            # Drop the column
            _safe_execute(cursor, "ALTER TABLE connections DROP COLUMN bot_instance_id")

            # Drop the old unique constraint if it exists
            _safe_execute(
                cursor,
                """
                SELECT constraint_name FROM information_schema.table_constraints
                WHERE table_name = 'connections' AND constraint_type = 'UNIQUE'
                AND constraint_name LIKE '%bot_instance_id%'
            """,
            )
            unique_constraints = cursor.fetchall()
            for constraint in unique_constraints:
                _safe_execute(cursor, f"ALTER TABLE connections DROP CONSTRAINT {constraint[0]}")

            # Add new unique constraint on (organization_id, connection_name)
            _safe_execute(
                cursor,
                """
                ALTER TABLE connections ADD CONSTRAINT connections_org_name_unique
                UNIQUE (organization_id, connection_name)
            """,
            )
        else:
            # SQLite doesn't support dropping columns easily, so recreate the table
            _safe_execute(cursor, "PRAGMA table_info(connections)")
            columns_info = cursor.fetchall()

            # Build column definitions excluding bot_instance_id
            column_defs = []
            for col in columns_info:
                col_name = col[1]
                col_type = col[2]
                col_notnull = col[3]
                col_default = col[4]
                col_pk = col[5]

                # Skip bot_instance_id column
                if col_name == "bot_instance_id":
                    continue

                if col_pk:
                    column_defs.append(f"{col_name} {col_type} PRIMARY KEY AUTOINCREMENT")
                else:
                    col_def = f"{col_name} {col_type}"
                    if col_notnull:
                        col_def += " NOT NULL"
                    if col_default is not None:
                        col_def += f" DEFAULT {col_default}"
                    column_defs.append(col_def)

            # Add unique constraint on (organization_id, connection_name)
            column_defs.append("UNIQUE (organization_id, connection_name)")

            # Create new table without bot_instance_id
            columns_sql = ",\n                ".join(column_defs)
            _safe_execute(
                cursor,
                f"""
                CREATE TABLE connections_new (
                {columns_sql}
                )
            """,
            )

            # Copy data from old table (excluding bot_instance_id)
            select_columns = []
            for col in columns_info:
                col_name = col[1]
                if col_name != "bot_instance_id":
                    select_columns.append(col_name)

            select_sql = ", ".join(select_columns)
            _safe_execute(
                cursor,
                f"INSERT INTO connections_new ({select_sql}) SELECT {select_sql} FROM connections",
            )

            # Drop old table and rename new one
            _safe_execute(cursor, "DROP TABLE connections")
            _safe_execute(cursor, "ALTER TABLE connections_new RENAME TO connections")

            # Recreate indexes (excluding the old bot_instance_id index)
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_connections_organization_id
                ON connections (organization_id)
            """,
            )

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if bot_instance_id column still exists in connections table."""
        return self._check_column_exists(conn, "connections", "bot_instance_id")


class AddChannelLimitColumns(SchemaChange):
    """Add cached_num_channels and cached_allow_additional_channels columns to plan_limits table if missing."""

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        # Add cached_num_channels column if missing
        if not self._check_column_exists(conn, "plan_limits", "cached_num_channels"):
            _safe_execute(
                cursor,
                "ALTER TABLE plan_limits ADD COLUMN cached_num_channels INTEGER NOT NULL DEFAULT 1",
            )

        # Add cached_allow_additional_channels column if missing
        if not self._check_column_exists(conn, "plan_limits", "cached_allow_additional_channels"):
            _safe_execute(
                cursor,
                "ALTER TABLE plan_limits ADD COLUMN cached_allow_additional_channels BOOLEAN NOT NULL DEFAULT FALSE",
            )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(
            conn, "plan_limits", "cached_num_channels"
        ) or not self._check_column_exists(conn, "plan_limits", "cached_allow_additional_channels")


class CreateChannelMappingTable(SchemaChange):
    """Create channel_mapping table to store mappings between team_id, normalized_channel_name, and channel_id."""

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(
            conn.cursor(),
            """
            CREATE TABLE IF NOT EXISTS channel_mapping (
                team_id TEXT NOT NULL,
                normalized_channel_name TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, normalized_channel_name)
            )
        """,
        )

        # Create indexes for efficient lookups
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_channel_mapping_team_id ON channel_mapping (team_id)",
            "CREATE INDEX IF NOT EXISTS idx_channel_mapping_channel_id ON channel_mapping (channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_channel_mapping_team_channel_id ON channel_mapping (team_id, channel_id)",
        ]

        for index_sql in index_statements:
            cursor = conn.cursor()
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "channel_mapping")


class CreateOnboardingStateTable(SchemaChange):
    """Create onboarding_state table to track onboarding progress and enable idempotency.

    This table allows the onboarding flow to be idempotent by tracking which steps
    have been completed. If onboarding fails partway through, it can resume from
    the last successful step instead of starting over.

    Uses a simplified schema with a single JSON column (background_onboarding_data) to
    store all state fields, keeping only lookup keys (email, organization_name) and
    timestamps as separate columns.

    Primary lookup: (email, organization_name) via UNIQUE constraint
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        serial_pk = self._get_serial_primary_key(conn)
        _safe_execute(
            cursor,
            f"""
            CREATE TABLE IF NOT EXISTS onboarding_state (
                id {serial_pk},
                email TEXT NOT NULL,
                organization_name TEXT NOT NULL,
                background_onboarding_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email, organization_name)
            )
        """,
        )

        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_onboarding_state_email ON onboarding_state(email)",
            "CREATE INDEX IF NOT EXISTS idx_onboarding_state_organization ON onboarding_state(organization_name)",
        ]
        for index_sql in index_statements:
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "onboarding_state")


class AddInstanceTypeToBotInstances(SchemaChange):
    """Add instance_type column to bot_instances table to support per-channel type configuration.

    This allows organizations to have both standard and prospector bot instances,
    enabling mixed-mode deployments where some channels are prospector-focused while
    others use standard data warehouse connections.

    Defaults to 'standard' for backward compatibility with existing instances.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        # Add instance_type column with default value
        _safe_execute(
            cursor,
            """
            ALTER TABLE bot_instances
            ADD COLUMN instance_type TEXT DEFAULT 'standard'
        """,
        )

        # Backfill existing rows explicitly (for databases that don't apply default to existing rows)
        _safe_execute(
            cursor,
            """
            UPDATE bot_instances
            SET instance_type = 'standard'
            WHERE instance_type IS NULL
        """,
        )

        # Create index for efficient filtering by instance type
        _safe_execute(
            cursor,
            """
            CREATE INDEX IF NOT EXISTS idx_bot_instances_instance_type
            ON bot_instances (instance_type)
        """,
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "bot_instances", "instance_type")


class CreateBotInstanceIcpTable(SchemaChange):
    """Create bot_instance_icp table to store ICP for prospector bot instances.

    This table stores the Ideal Customer/Candidate Profile (ICP) for prospector-type
    bot instances. The ICP is injected into the system prompt to customize the AI assistant's
    behavior for recruiting/prospecting use cases.

    One-to-one relationship with bot_instances table, but only populated for prospector instances.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()
        serial_pk = self._get_serial_primary_key(conn)

        _safe_execute(
            cursor,
            f"""
            CREATE TABLE IF NOT EXISTS bot_instance_icp (
                id {serial_pk},
                bot_instance_id INTEGER NOT NULL UNIQUE,
                icp_text TEXT NOT NULL,
                data_types TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_instance_id) REFERENCES bot_instances (id) ON DELETE CASCADE
            )
        """,
        )

        # Create index for efficient lookups by bot_instance_id
        _safe_execute(
            cursor,
            """
            CREATE INDEX IF NOT EXISTS idx_bot_instance_icp_bot_instance_id
            ON bot_instance_icp (bot_instance_id)
        """,
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "bot_instance_icp")


class AddOnboardingTypeColumn(SchemaChange):
    """Add onboarding_type column to analytics table if missing.

    This column stores the type of onboarding flow used (e.g., 'standard', 'prospector')
    for organization_created and other onboarding-related analytics events.
    """

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(conn.cursor(), "ALTER TABLE analytics ADD COLUMN onboarding_type TEXT")

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "analytics", "onboarding_type")


class AddOrganizationIdsToReferralTokens(SchemaChange):
    """Add consumed_by_organization_ids, issued_by_organization_id, is_single_use, and consumer_bonus_answers columns to referral_tokens table.

    These columns enable customer-customer referral tracking by linking referral tokens
    to both the issuing organization and the consuming organizations (as a JSON array).
    The is_single_use column tracks whether a token can only be used once.
    The consumer_bonus_answers column specifies the number of bonus answers granted when consumed.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()
        bigint_type = self._get_bigint_type(conn)

        # Add consumed_by_organization_ids column (JSON array of org IDs)
        if not self._check_column_exists(conn, "referral_tokens", "consumed_by_organization_ids"):
            _safe_execute(
                cursor,
                "ALTER TABLE referral_tokens ADD COLUMN consumed_by_organization_ids TEXT DEFAULT '[]'",
            )

        # Add issued_by_organization_id column
        if not self._check_column_exists(conn, "referral_tokens", "issued_by_organization_id"):
            _safe_execute(
                cursor, "ALTER TABLE referral_tokens ADD COLUMN issued_by_organization_id INTEGER"
            )

        # Add is_single_use column - defaults to TRUE for existing tokens
        if not self._check_column_exists(conn, "referral_tokens", "is_single_use"):
            if is_postgresql(conn):
                _safe_execute(
                    cursor,
                    "ALTER TABLE referral_tokens ADD COLUMN is_single_use BOOLEAN DEFAULT TRUE",
                )
            else:
                _safe_execute(
                    cursor, "ALTER TABLE referral_tokens ADD COLUMN is_single_use INTEGER DEFAULT 1"
                )

        # Add consumer_bonus_answers column - defaults to 150 for existing tokens
        if not self._check_column_exists(conn, "referral_tokens", "consumer_bonus_answers"):
            _safe_execute(
                cursor,
                f"ALTER TABLE referral_tokens ADD COLUMN consumer_bonus_answers {bigint_type} DEFAULT 150",
            )

        # Create index for efficient lookups
        _safe_execute(
            cursor,
            """
            CREATE INDEX IF NOT EXISTS idx_referral_tokens_issued_by_org
            ON referral_tokens (issued_by_organization_id)
        """,
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        # Check if any of the new columns are missing
        return (
            not self._check_column_exists(conn, "referral_tokens", "consumed_by_organization_ids")
            or not self._check_column_exists(conn, "referral_tokens", "issued_by_organization_id")
            or not self._check_column_exists(conn, "referral_tokens", "is_single_use")
            or not self._check_column_exists(conn, "referral_tokens", "consumer_bonus_answers")
        )


class AddFeatureFlagsToOrganizations(SchemaChange):
    """Add has_governance_channel boolean column to organizations table.

    Adds a simple boolean column to track whether an organization has a governance channel.
    Defaults to TRUE for backward compatibility with existing organizations.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        # Add has_governance_channel column with default TRUE (backward compatible)
        _safe_execute(
            cursor, "ALTER TABLE organizations ADD COLUMN has_governance_channel INTEGER DEFAULT 1"
        )

        # Backfill existing rows explicitly (for databases that don't apply default to existing rows)
        _safe_execute(
            cursor,
            """
            UPDATE organizations
            SET has_governance_channel = 1
            WHERE has_governance_channel IS NULL
        """,
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "organizations", "has_governance_channel")


class AddContextstoreRepoToOrganizations(SchemaChange):
    """Add contextstore_github_repo column to organizations table.

    This column stores the GitHub repository path for the organization's context store.
    Previously stored in JWT tokens, now centralized in the organizations table.
    """

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(
            conn.cursor(), "ALTER TABLE organizations ADD COLUMN contextstore_github_repo TEXT"
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "organizations", "contextstore_github_repo")


class AddDataDocumentationRepoToConnections(SchemaChange):
    """Add data_documentation_contextstore_github_repo column to connections table.

    This optional column stores a GitHub repository path for shared dataset documentation
    that should be merged with the organization's primary context store. When present,
    a CompositeContextStoreProvider will be used to combine the mutable org-specific
    context store with the read-only shared dataset documentation store.
    """

    def apply(self, conn: ConnectionType) -> None:
        _safe_execute(
            conn.cursor(),
            "ALTER TABLE connections ADD COLUMN data_documentation_contextstore_github_repo TEXT",
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(
            conn, "connections", "data_documentation_contextstore_github_repo"
        )


class CreateGithubMonitorEventsTable(SchemaChange):
    """Create context_status table for tracking GitHub PR/issue events.

    This table stores context updates (PRs, issues, scheduled analyses) for display
    in the web UI, replacing the previous Slack notification approach. Events are
    tracked at the organization level since multiple bot instances share a context repo.

    Uses enum types for update_type (SCHEDULED_ANALYSIS, CONTEXT_UPDATE, DATA_REQUEST)
    and status (OPEN, MERGED, CLOSED).
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()
        serial_pk = self._get_serial_primary_key(conn)
        bigint_type = self._get_bigint_type(conn)

        # Use TEXT with CHECK constraints for both PostgreSQL and SQLite
        # Python enums handle type safety at the application level
        _safe_execute(
            cursor,
            f"""
            CREATE TABLE context_status (
                id {serial_pk},
                organization_id INTEGER NOT NULL,
                repo_name TEXT NOT NULL,
                update_type TEXT NOT NULL CHECK(update_type IN ('SCHEDULED_ANALYSIS', 'CONTEXT_UPDATE', 'DATA_REQUEST')),
                github_url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL CHECK(status IN ('OPEN', 'MERGED', 'CLOSED')),
                created_at {bigint_type} NOT NULL,
                updated_at {bigint_type} NOT NULL,
                github_updated_at {bigint_type} NOT NULL,
                acted_by_user_id TEXT,
                acted_at {bigint_type},
                pr_info TEXT
            )
        """,
        )

        # Create indexes for efficient queries
        _safe_execute(
            cursor,
            """
            CREATE INDEX idx_context_status_org_status_updated
            ON context_status (organization_id, status, updated_at DESC)
        """,
        )

        _safe_execute(
            cursor,
            """
            CREATE INDEX idx_context_status_repo_status
            ON context_status (repo_name, status)
        """,
        )

    def is_needed(self, conn: ConnectionType) -> bool:
        # CREATE TABLE IF NOT EXISTS is not used, so we need to check manually
        cursor = conn.cursor()
        if is_postgresql(conn):
            _safe_execute(
                cursor,
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_name = 'context_status'
            """,
            )
            return cursor.fetchone() is None
        else:
            _safe_execute(
                cursor,
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='context_status'
            """,
            )
            return cursor.fetchone() is None


class CreateEncryptedDeksTable(SchemaChange):
    """Create encrypted_deks table to store per-organization encrypted DEKs.

    This table stores one DEK per organization, encrypted using AWS KMS with
    encryption context {"organization": organization_id} for additional security.
    Each organization's DEK is used to encrypt all connection URLs for that organization.
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        blob_type = "BYTEA" if is_postgresql(conn) else "BLOB"
        _safe_execute(
            conn.cursor(),
            f"""
            CREATE TABLE IF NOT EXISTS encrypted_deks (
                id {serial_pk},
                organization_id INTEGER NOT NULL UNIQUE,
                encrypted_dek {blob_type} NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE
            )
        """,
        )

        index_statements = [
            (
                "CREATE INDEX IF NOT EXISTS idx_encrypted_deks_organization_id "
                "ON encrypted_deks (organization_id)"
            ),
        ]

        for index_sql in index_statements:
            _safe_execute(conn.cursor(), index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "encrypted_deks")


class AddEncryptedUrlColumn(SchemaChange):
    """Add encrypted_url column to connections table.

    This column stores the encrypted connection URL using envelope encryption.
    The URL is encrypted with a DEK, and the DEK is encrypted with a KEK.
    """

    def apply(self, conn: ConnectionType) -> None:
        conn.cursor().execute("ALTER TABLE connections ADD COLUMN encrypted_url TEXT")

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_column_exists(conn, "connections", "encrypted_url")


class CreateOrgUsersTable(SchemaChange):
    """Create org_users and org_channels tables.

    org_users: Tracks users associated with organizations, including their Slack user ID,
    email, organization membership, admin status, and name.

    org_channels: Links org_users to channels (bot_ids), tracking channel membership.

    Unique constraints:
    - org_users: (slack_user_id, organization_id)
    - org_channels: (org_user_id, bot_id)
    """

    def apply(self, conn: ConnectionType) -> None:
        serial_pk = self._get_serial_primary_key(conn)
        cursor = conn.cursor()

        # Create org_users table
        _safe_execute(
            cursor,
            f"""
            CREATE TABLE IF NOT EXISTS org_users (
                id {serial_pk},
                slack_user_id TEXT NOT NULL,
                email TEXT,
                organization_id INTEGER NOT NULL,
                is_org_admin INTEGER NOT NULL DEFAULT 0,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE,
                UNIQUE (slack_user_id, organization_id)
            )
        """,
        )

        # Create org_channels table
        _safe_execute(
            cursor,
            f"""
            CREATE TABLE IF NOT EXISTS org_channels (
                id {serial_pk},
                org_user_id INTEGER NOT NULL,
                bot_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (org_user_id) REFERENCES org_users (id) ON DELETE CASCADE,
                UNIQUE (org_user_id, bot_id)
            )
        """,
        )

        # Create indexes for org_users
        org_users_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_org_users_organization_id ON org_users (organization_id)",
            "CREATE INDEX IF NOT EXISTS idx_org_users_slack_user_id ON org_users (slack_user_id)",
            "CREATE INDEX IF NOT EXISTS idx_org_users_email ON org_users (email)",
        ]

        for index_sql in org_users_indexes:
            _safe_execute(cursor, index_sql)

        # Create indexes for org_channels
        org_channels_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_org_channels_org_user_id ON org_channels (org_user_id)",
            "CREATE INDEX IF NOT EXISTS idx_org_channels_bot_id ON org_channels (bot_id)",
        ]

        for index_sql in org_channels_indexes:
            _safe_execute(cursor, index_sql)

    def is_needed(self, conn: ConnectionType) -> bool:
        return not self._check_table_exists(conn, "org_users")


class MakeOrgUserEmailNullable(SchemaChange):
    """Make email column nullable in org_users table.

    This migration allows org_users to have no email address, supporting
    scenarios where users authenticate without providing an email.
    """

    def apply(self, conn: ConnectionType) -> None:
        cursor = conn.cursor()

        if is_postgresql(conn):
            # PostgreSQL: Drop NOT NULL constraint
            _safe_execute(cursor, "ALTER TABLE org_users ALTER COLUMN email DROP NOT NULL")
        else:
            # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
            _safe_execute(cursor, "PRAGMA table_info(org_users)")
            columns_info = cursor.fetchall()

            # Build column definitions with email as nullable
            column_defs = []
            for col in columns_info:
                col_name = col[1]
                col_type = col[2]
                col_notnull = col[3]
                col_default = col[4]
                col_pk = col[5]

                if col_name == "email":
                    # Make email nullable (remove NOT NULL)
                    column_defs.append(f"{col_name} {col_type}")
                elif col_pk:
                    # Preserve primary key
                    column_defs.append(f"{col_name} {col_type} PRIMARY KEY AUTOINCREMENT")
                else:
                    # Regular column
                    col_def = f"{col_name} {col_type}"
                    if col_notnull:
                        col_def += " NOT NULL"
                    if col_default is not None:
                        col_def += f" DEFAULT {col_default}"
                    column_defs.append(col_def)

            # Add foreign key and unique constraints
            column_defs.append(
                "FOREIGN KEY (organization_id) REFERENCES organizations (organization_id) ON DELETE CASCADE"
            )
            column_defs.append("UNIQUE (slack_user_id, organization_id)")

            # Create new table with email as nullable
            columns_sql = ",\n                ".join(column_defs)
            _safe_execute(
                cursor,
                f"""
                CREATE TABLE org_users_new (
                {columns_sql}
                )
            """,
            )

            # Copy data from old table
            select_columns = [col[1] for col in columns_info]
            select_sql = ", ".join(select_columns)
            _safe_execute(
                cursor,
                f"INSERT INTO org_users_new ({select_sql}) SELECT {select_sql} FROM org_users",
            )

            # Drop old table and rename new one
            _safe_execute(cursor, "DROP TABLE org_users")
            _safe_execute(cursor, "ALTER TABLE org_users_new RENAME TO org_users")

            # Recreate indexes
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_org_users_organization_id ON org_users (organization_id)
            """,
            )
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_org_users_slack_user_id ON org_users (slack_user_id)
            """,
            )
            _safe_execute(
                cursor,
                """
                CREATE INDEX IF NOT EXISTS idx_org_users_email ON org_users (email)
            """,
            )

    def is_needed(self, conn: ConnectionType) -> bool:
        """Check if email column is currently NOT NULL."""
        if not self._check_column_exists(conn, "org_users", "email"):
            return False  # Column doesn't exist, can't make it nullable

        cursor = conn.cursor()

        if is_postgresql(conn):
            # Check if column allows NULL values
            _safe_execute(
                cursor,
                """
                SELECT is_nullable FROM information_schema.columns
                WHERE table_name = 'org_users' AND column_name = 'email'
            """,
            )
            result = cursor.fetchone()
            if result is None:
                return False
            return result[0] == "NO"  # Returns True if NOT NULL
        else:
            # For SQLite, check table schema
            _safe_execute(cursor, "PRAGMA table_info(org_users)")
            columns = cursor.fetchall()
            for col in columns:
                if col[1] == "email":
                    return col[3] == 1  # Returns True if NOT NULL is 1 (not nullable)
            return False


class SchemaManager:
    """Manages all schema changes in organized fashion."""

    def __init__(self):
        # Define the sequence of schema changes
        self.base_changes = [
            CreateKvTable(),
            AddDeletedAtColumn(),
            CreateAnalyticsTable(),
            CreateBotInstancesTable(),
            CreateConnectionsTable(),
            AddInitSqlColumn(),
            AddSlackTeamIdColumn(),
            CreateSlackBotTokensTable(),
            CreateReferralTokensTable(),
            CreateUsageTrackingTable(),
            AddSqlDialectColumn(),
            CreateOrganizationsTable(),
            MakeOrganizationIdRequired(),
            RemoveOrganizationColumnsFromBotInstances(),
            AddStripeCustomerIdColumn(),
            AddStripeSubscriptionIdColumn(),
            UpdateUsageTrackingToMonthly(),
            CreatePlanLimitsTable(),
            CreateBonusAnswerGrantsTable(),
            AddBonusAnswerCountColumn(),
            CreateTosRecordsTable(),
            AddOrganizationIdToConnections(),
            CreateBotToConnectionsTable(),
            DropBotInstanceIdFromConnections(),
            AddChannelLimitColumns(),
            CreateChannelMappingTable(),
            CreateOnboardingStateTable(),
            AddInstanceTypeToBotInstances(),
            CreateBotInstanceIcpTable(),
            AddOnboardingTypeColumn(),
            AddOrganizationIdsToReferralTokens(),
            AddFeatureFlagsToOrganizations(),
            AddContextstoreRepoToOrganizations(),
            AddDataDocumentationRepoToConnections(),
            CreateGithubMonitorEventsTable(),
            CreateEncryptedDeksTable(),
            AddEncryptedUrlColumn(),
            CreateOrgUsersTable(),
            MakeOrgUserEmailNullable(),
        ]

    def apply_all_changes(self, conn: ConnectionType) -> None:
        """Apply all schema changes. Caller is responsible for transaction management."""
        try:
            # Apply base schema changes
            for change in self.base_changes:
                if change.is_needed(conn):
                    if os.getenv("COMPASS_ENV"):
                        logger.info(f"Applying schema change {change.__class__.__name__}")
                    change.apply(conn)

            # Handle index creation with conditional logic
            # Check if deleted_at column exists (either was there or just added)
            has_deleted_at = CreateKvTable()._check_column_exists(conn, "kv", "deleted_at_seconds")

            # Create kv indexes (conditionally include deleted_at index)
            kv_indexes = CreateKvIndexes(include_deleted_at=has_deleted_at)
            if kv_indexes.is_needed(conn):
                kv_indexes.apply(conn)

        except Exception as e:
            raise RuntimeError(f"Database migration failed: {e}") from e

    def list_unapplied_changes(self, conn: ConnectionType) -> list[str]:
        """List all schema changes that still need to be applied.

        Args:
            conn: Database connection

        Returns:
            List of class names for changes that need to be applied
        """
        unapplied = []

        for change in self.base_changes:
            if change.is_needed(conn):
                unapplied.append(change.__class__.__name__)

        # Check conditional index creation
        has_deleted_at = CreateKvTable()._check_column_exists(conn, "kv", "deleted_at_seconds")
        kv_indexes = CreateKvIndexes(include_deleted_at=has_deleted_at)
        if kv_indexes.is_needed(conn):
            unapplied.append(kv_indexes.__class__.__name__)

        return unapplied
