import json
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

from csbot.utils.sync_to_async import sync_to_async

from .storage.interface import SqlConnectionFactory
from .storage.postgresql import PostgresqlConnectionFactory

# Import for type hints
if TYPE_CHECKING:
    from .channel_bot.personalization import EnrichedPerson

# Grant amount per user for slack member incentive
USER_GRANT_AMOUNT = 5


class AnalyticsEventType(Enum):
    NEW_CONVERSATION = "new_conversation"
    NEW_REPLY = "new_reply"
    USER_JOINED_CHANNEL = "user_joined_channel"
    TOKEN_USAGE = "token_usage"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"

    # Onboarding events
    ORGANIZATION_CREATED = "organization_created"
    GOVERNANCE_CHANNEL_CREATED = "governance_channel_created"
    FIRST_DATASET_SYNC = "first_dataset_sync"
    ADDITIONAL_CHANNEL_CREATED = "additional_channel_created"

    # Admin/setup events
    ADMIN_COMMAND_USED = "admin_command_used"
    CONNECTION_MANAGEMENT_ACCESSED = "connection_management_accessed"
    CONTEXTSTORE_REPO_CREATED = "contextstore_repo_created"
    SLACK_CONNECT_INVITE_SENT = "slack_connect_invite_sent"

    # User engagement milestones
    FIRST_SUCCESSFUL_QUERY = "first_successful_query"

    # Compass channel welcome messages (user and channel)
    WELCOME_MESSAGE_SENT = "welcome_message_sent"
    WELCOME_MESSAGE_STARTED = "welcome_message_started"
    WELCOME_MESSAGE_ERROR = "welcome_message_error"
    CHANNEL_COMPASS_WELCOME_SENT = "channel_compass_welcome_sent"
    CHANNEL_COMPASS_WELCOME_STARTED = "channel_compass_welcome_started"
    CHANNEL_COMPASS_WELCOME_ERROR = "channel_compass_welcome_error"

    # Governance channel welcome messages (user and channel)
    GOVERNANCE_WELCOME_SENT = "governance_welcome_sent"
    GOVERNANCE_WELCOME_STARTED = "governance_welcome_started"
    GOVERNANCE_WELCOME_ERROR = "governance_welcome_error"
    CHANNEL_GOVERNANCE_WELCOME_SENT = "channel_governance_welcome_sent"
    CHANNEL_GOVERNANCE_WELCOME_STARTED = "channel_governance_welcome_started"
    CHANNEL_GOVERNANCE_WELCOME_ERROR = "channel_governance_welcome_error"

    # Billing events
    ANSWER_GENERATED = "answer_generated"

    # User interaction events
    BUTTON_CLICKED = "button_clicked"
    MODAL_OPENED = "modal_opened"
    SLACK_MODAL_INTERACTION = "slack_modal_interaction"
    MODAL_CANCELLED = "modal_cancelled"

    # Error and drop-off events
    ERROR_OCCURRED = "error_occurred"
    API_ERROR = "api_error"
    TIMEOUT_ERROR = "timeout_error"
    PLAN_LIMIT_REACHED = "plan_limit_reached"
    ONBOARDING_ABANDONED = "onboarding_abandoned"
    CONNECTION_SETUP_FAILED = "connection_setup_failed"
    CONNECTION_SETUP_SUCCEEDED = "connection_setup_succeeded"
    QUERY_FAILED = "query_failed"

    # Advanced engagement events
    QUERY_WITH_RESULTS = "query_with_results"
    QUERY_NO_RESULTS = "query_no_results"
    REPEAT_USER_QUERY = "repeat_user_query"
    HELP_ACCESSED = "help_accessed"
    SLASH_COMMAND_USED = "slash_command_used"

    # Business events
    PLAN_UPGRADED = "plan_upgraded"
    PLAN_DOWNGRADED = "plan_downgraded"
    PAYMENT_METHOD_ADDED = "payment_method_added"
    BILLING_ISSUE = "billing_issue"
    TEAM_MEMBER_INVITED = "team_member_invited"
    COWORKER_INVITED = "coworker_invited"

    # GitHub integration events
    PR_APPROVED = "pr_approved"
    PR_REJECTED = "pr_rejected"
    GITHUB_INTEGRATION_USED = "github_integration_used"

    # Community mode events
    COMMUNITY_MODE_QUOTA_EXCEEDED = "community_mode_quota_exceeded"

    # Growth
    REFERRAL_LINK_GENERATED = "referral_link_generated"
    REFERRAL_LINK_COPIED = "referral_link_copied"
    TRY_IT_CLICKED = "try_it_clicked"


# Set of error event types (events ending in _error or specific error events)
ERROR_EVENT_TYPES = {
    AnalyticsEventType.WELCOME_MESSAGE_ERROR.value,
    AnalyticsEventType.CHANNEL_COMPASS_WELCOME_ERROR.value,
    AnalyticsEventType.GOVERNANCE_WELCOME_ERROR.value,
    AnalyticsEventType.CHANNEL_GOVERNANCE_WELCOME_ERROR.value,
    AnalyticsEventType.ERROR_OCCURRED.value,
    AnalyticsEventType.API_ERROR.value,
    AnalyticsEventType.TIMEOUT_ERROR.value,
    AnalyticsEventType.PLAN_LIMIT_REACHED.value,
    AnalyticsEventType.ONBOARDING_ABANDONED.value,
    AnalyticsEventType.CONNECTION_SETUP_FAILED.value,
    AnalyticsEventType.QUERY_FAILED.value,
    AnalyticsEventType.BILLING_ISSUE.value,
}


def _is_conn_factory_postgresql(conn_factory: SqlConnectionFactory) -> bool:
    return isinstance(conn_factory, PostgresqlConnectionFactory)


class SlackbotAnalyticsStore:
    def __init__(self, sql_conn_factory: SqlConnectionFactory):
        self.sql_conn_factory = sql_conn_factory

    def _get_placeholder(self) -> str:
        """Get the appropriate parameter placeholder for the database type."""
        if _is_conn_factory_postgresql(self.sql_conn_factory):
            return "%s"  # psycopg uses %s for all parameters
        else:
            return "?"  # SQLite uses ? for parameters

    def _standardize_metadata_structure(
        self,
        metadata: dict[str, Any] | str | None,
        user_real_name: str | None = None,
        user_timezone: str | None = None,
        user_email: str | None = None,
        organization_id: int | None = None,
        organization_name: str | None = None,
        bot_id: str | None = None,
    ) -> dict[str, Any]:
        """Standardize metadata structure with consistent organization, user, and bot info.

        Args:
            metadata: Original metadata (can be dict or JSON string)
            user_real_name: User's real name
            user_timezone: User's timezone
            user_email: User's email
            organization_id: Organization ID
            organization_name: Organization name
            bot_id: Bot identifier

        Returns:
            Standardized metadata dictionary
        """
        # Parse metadata if provided
        enhanced_metadata: dict[str, Any] = {}
        if metadata:
            try:
                enhanced_metadata = json.loads(metadata) if isinstance(metadata, str) else metadata
            except (json.JSONDecodeError, TypeError):
                enhanced_metadata = {"raw_metadata": metadata}

        # Add user information to metadata in standardized structure
        user_info: dict[str, str] = {}
        if user_real_name:
            user_info["real_name"] = user_real_name
        if user_timezone:
            user_info["timezone"] = user_timezone
        if user_email:
            user_info["email"] = user_email

        if user_info:
            enhanced_metadata["user_info"] = user_info

        # Add organization information to metadata in standardized structure
        if organization_id is not None:
            organization_info: dict[str, str | int] = {"id": organization_id}
            if organization_name:
                organization_info["name"] = organization_name
            enhanced_metadata["organization"] = organization_info

        # Add bot information to metadata in standardized structure
        if bot_id:
            enhanced_metadata["bot_id"] = bot_id

        return enhanced_metadata

    @sync_to_async
    def log_analytics_event(
        self,
        bot_id: str,
        event_type: AnalyticsEventType,
        organization_name: str,
        channel_id: str | None = None,
        user_id: str | None = None,
        thread_ts: str | None = None,
        message_ts: str | None = None,
        metadata: str | None = None,
        tokens_used: int | None = None,
        user_real_name: str | None = None,
        user_timezone: str | None = None,
        user_email: str | None = None,
        organization_id: int | None = None,
        onboarding_type: str | None = None,
    ) -> None:
        """Log an analytics event to the database."""
        if not self.sql_conn_factory.supports_analytics():
            return

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Standardize metadata structure
            enhanced_metadata = self._standardize_metadata_structure(
                metadata=metadata,
                user_real_name=user_real_name,
                user_timezone=user_timezone,
                user_email=user_email,
                organization_id=organization_id,
                organization_name=organization_name,
                bot_id=bot_id,
            )

            # Convert back to JSON string
            final_metadata = json.dumps(enhanced_metadata) if enhanced_metadata else None

            # Build SQL with appropriate placeholders
            placeholders = ", ".join(self._get_placeholder() for _ in range(9))
            sql = f"""
                INSERT INTO analytics
                (bot_id, event_type, channel_id, user_id, thread_ts,
                message_ts, metadata, tokens_used, onboarding_type)
                VALUES ({placeholders})
                """

            cursor.execute(
                sql,
                (
                    bot_id,
                    event_type.value,
                    channel_id,
                    user_id,
                    thread_ts,
                    message_ts,
                    final_metadata,
                    tokens_used,
                    onboarding_type,
                ),
            )
            conn.commit()

        # Probabilistically cleanup old data (1% chance)
        if random.random() < 0.01:
            self._cleanup_old_analytics()

    async def log_analytics_event_with_enriched_user(
        self,
        bot_id: str,
        event_type: AnalyticsEventType,
        organization_name: str,
        channel_id: str | None = None,
        user_id: str | None = None,
        thread_ts: str | None = None,
        message_ts: str | None = None,
        metadata: dict[str, Any] | str | None = None,
        tokens_used: int | None = None,
        enriched_person: "EnrichedPerson | None" = None,
        user_email: str | None = None,
        organization_id: int | None = None,
        onboarding_type: str | None = None,
    ) -> None:
        """Log an analytics event with enriched user information.

        Args:
            bot_id: Bot identifier
            event_type: Type of analytics event
            channel_id: Slack channel ID
            user_id: Slack user ID
            thread_ts: Thread timestamp
            message_ts: Message timestamp
            metadata: Additional metadata (can be dict or JSON string)
            tokens_used: Number of tokens consumed
            enriched_person: EnrichedPerson object with user details
            user_email: User email if available separately
        """
        user_real_name = None
        user_timezone = None

        if enriched_person:
            user_real_name = enriched_person.real_name
            user_timezone = enriched_person.timezone
            # Extract email from enriched_person if not provided explicitly
            if user_email is None and enriched_person.email:
                user_email = enriched_person.email

        return await self.log_analytics_event(
            bot_id=bot_id,
            event_type=event_type,
            channel_id=channel_id,
            user_id=user_id,
            thread_ts=thread_ts,
            message_ts=message_ts,
            metadata=json.dumps(metadata) if isinstance(metadata, dict) else metadata,
            tokens_used=tokens_used,
            user_real_name=user_real_name,
            user_timezone=user_timezone,
            user_email=user_email,
            organization_id=organization_id,
            organization_name=organization_name,
            onboarding_type=onboarding_type,
        )

    def _extract_user_info_from_metadata(self, metadata: str | None) -> dict[str, Any] | None:
        """Extract user information from analytics metadata.

        Args:
            metadata: JSON metadata string from analytics record

        Returns:
            Dictionary with user information or None if not available
        """
        if not metadata:
            return None

        try:
            metadata_dict = json.loads(metadata)
            return metadata_dict.get("user_info")
        except (json.JSONDecodeError, TypeError):
            return None

    def _cleanup_old_analytics(self, retention_days: int = 180) -> int:
        """Delete analytics data older than the specified retention period.

        Args:
            retention_days: Number of days to retain analytics data (default: 180)

        Returns:
            Number of rows deleted
        """
        if not self.sql_conn_factory.supports_analytics():
            return 0

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Delete old records with appropriate placeholder
            placeholder = self._get_placeholder()
            sql = f"DELETE FROM analytics WHERE created_at < {placeholder}"
            cursor.execute(sql, (cutoff_date.isoformat(),))

            deleted_count = cursor.rowcount
            conn.commit()

            return deleted_count

    @sync_to_async
    def get_analytics_data(
        self,
        bot_id: str | None,
        days: int = 180,
    ) -> list[dict[str, Any]]:
        """Get raw analytics data with optional filtering.

        Args:
            days: Number of days of data to retrieve (default: 180)
        """
        if not self.sql_conn_factory.supports_analytics():
            return []

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()

            # Calculate date threshold
            threshold_date = datetime.now() - timedelta(days=days)

            # Build query with appropriate placeholder
            placeholder = self._get_placeholder()
            if bot_id:
                query = f"""
                    SELECT
                        id, bot_id, event_type, channel_id, user_id, thread_ts,
                        message_ts, metadata, tokens_used, created_at
                    FROM analytics
                    WHERE created_at >= {placeholder}
                    AND bot_id = {placeholder}
                """
                params = [threshold_date.isoformat(), bot_id]
            else:
                query = f"""
                    SELECT
                        id, bot_id, event_type, channel_id, user_id, thread_ts,
                        message_ts, metadata, tokens_used, created_at
                    FROM analytics
                    WHERE created_at >= {placeholder}
                """
                params = [threshold_date.isoformat()]

            query += " ORDER BY created_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            fieldnames = [
                "id",
                "bot_id",
                "event_type",
                "channel_id",
                "user_id",
                "thread_ts",
                "message_ts",
                "metadata",
                "tokens_used",
                "created_at",
            ]

            analytics_data = []
            for row in rows:
                record = dict(zip(fieldnames, row))

                # Extract user information from metadata if available
                user_info = self._extract_user_info_from_metadata(record.get("metadata"))
                if user_info:
                    record["user_info"] = user_info

                analytics_data.append(record)

            return analytics_data

    @sync_to_async
    def increment_answer_count(self, bot_id: str) -> None:
        """Increment the answer count for a bot in the usage tracking table.

        This tracks the number of answers (streaming_reply_to_thread_with_ai invocations)
        for pricing purposes, organized by month.
        """
        if not self.sql_conn_factory.supports_analytics():
            return

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            if _is_conn_factory_postgresql(self.sql_conn_factory):
                # PostgreSQL - use UPSERT with ON CONFLICT for current month/year
                sql = f"""
                    INSERT INTO usage_tracking
                    (bot_id, month, year, answer_count, bonus_answer_count, created_at, updated_at)
                    VALUES (
                        {placeholder},
                        EXTRACT(MONTH FROM CURRENT_TIMESTAMP)::INTEGER,
                        EXTRACT(YEAR FROM CURRENT_TIMESTAMP)::INTEGER,
                        1,
                        0,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (bot_id, month, year)
                    DO UPDATE SET
                        answer_count = usage_tracking.answer_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (bot_id,))
            else:
                # SQLite - use INSERT OR REPLACE with a subquery for current month/year
                sql = f"""
                    INSERT OR REPLACE INTO usage_tracking
                    (bot_id, month, year, answer_count, bonus_answer_count, created_at, updated_at)
                    VALUES (
                        {placeholder},
                        CAST(strftime('%m', 'now') AS INTEGER),
                        CAST(strftime('%Y', 'now') AS INTEGER),
                        COALESCE((
                            SELECT answer_count
                            FROM usage_tracking
                            WHERE bot_id = {placeholder}
                            AND month = CAST(strftime('%m', 'now') AS INTEGER)
                            AND year = CAST(strftime('%Y', 'now') AS INTEGER)
                        ), 0) + 1,
                        COALESCE((
                            SELECT bonus_answer_count
                            FROM usage_tracking
                            WHERE bot_id = {placeholder}
                            AND month = CAST(strftime('%m', 'now') AS INTEGER)
                            AND year = CAST(strftime('%Y', 'now') AS INTEGER)
                        ), 0),
                        COALESCE((
                            SELECT created_at
                            FROM usage_tracking
                            WHERE bot_id = {placeholder}
                            AND month = CAST(strftime('%m', 'now') AS INTEGER)
                            AND year = CAST(strftime('%Y', 'now') AS INTEGER)
                        ), CURRENT_TIMESTAMP),
                        CURRENT_TIMESTAMP
                    )
                """
                cursor.execute(sql, (bot_id, bot_id, bot_id, bot_id))

            conn.commit()

    @sync_to_async
    def increment_bonus_answer_count(self, bot_id: str) -> None:
        """Increment the bonus answer count for a bot in the usage tracking table.

        This tracks the number of bonus answers consumed when usage exceeds plan limits,
        organized by month.
        """
        if not self.sql_conn_factory.supports_analytics():
            return

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            if _is_conn_factory_postgresql(self.sql_conn_factory):
                # PostgreSQL - use UPSERT with ON CONFLICT for current month/year
                sql = f"""
                    INSERT INTO usage_tracking
                    (bot_id, month, year, answer_count, bonus_answer_count, created_at, updated_at)
                    VALUES (
                        {placeholder},
                        EXTRACT(MONTH FROM CURRENT_TIMESTAMP)::INTEGER,
                        EXTRACT(YEAR FROM CURRENT_TIMESTAMP)::INTEGER,
                        0,
                        1,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (bot_id, month, year)
                    DO UPDATE SET
                        bonus_answer_count = COALESCE(usage_tracking.bonus_answer_count, 0) + 1,
                        updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (bot_id,))
            else:
                # SQLite - use INSERT OR REPLACE with a subquery for current month/year
                sql = f"""
                    INSERT OR REPLACE INTO usage_tracking
                    (bot_id, month, year, answer_count, bonus_answer_count, created_at, updated_at)
                    VALUES (
                        {placeholder},
                        CAST(strftime('%m', 'now') AS INTEGER),
                        CAST(strftime('%Y', 'now') AS INTEGER),
                        COALESCE((
                            SELECT answer_count
                            FROM usage_tracking
                            WHERE bot_id = {placeholder}
                            AND month = CAST(strftime('%m', 'now') AS INTEGER)
                            AND year = CAST(strftime('%Y', 'now') AS INTEGER)
                        ), 0),
                        COALESCE((
                            SELECT bonus_answer_count
                            FROM usage_tracking
                            WHERE bot_id = {placeholder}
                            AND month = CAST(strftime('%m', 'now') AS INTEGER)
                            AND year = CAST(strftime('%Y', 'now') AS INTEGER)
                        ), 0) + 1,
                        COALESCE((
                            SELECT created_at
                            FROM usage_tracking
                            WHERE bot_id = {placeholder}
                            AND month = CAST(strftime('%m', 'now') AS INTEGER)
                            AND year = CAST(strftime('%Y', 'now') AS INTEGER)
                        ), CURRENT_TIMESTAMP),
                        CURRENT_TIMESTAMP
                    )
                """
                cursor.execute(sql, (bot_id, bot_id, bot_id, bot_id))

            conn.commit()

    @sync_to_async
    def insert_usage_tracking_data(
        self, bot_id: str, month: int, year: int, answer_count: int
    ) -> None:
        """Insert usage tracking data for a specific month/year (for testing).

        Args:
            bot_id: Bot ID to insert data for
            month: Month (1-12)
            year: Year (e.g., 2024)
            answer_count: Number of answers for this month
        """
        if not self.sql_conn_factory.supports_analytics():
            return

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            # Insert data for the specified month/year
            placeholders = ", ".join(placeholder for _ in range(4))
            sql = f"""
                INSERT INTO usage_tracking
                (bot_id, month, year, answer_count, created_at, updated_at)
                VALUES ({placeholders}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            cursor.execute(
                sql,
                (bot_id, month, year, answer_count),
            )
            conn.commit()

    @sync_to_async
    def get_usage_tracking_data(
        self, bot_id: str | None, *, include_bonus_answers: bool
    ) -> list[dict[str, Any]]:
        """Get usage tracking data for pricing model.

        Args:
            bot_id: Optional bot ID to filter by. If None, returns data for all bots.
            include_bonus_answers: If True, includes bonus_answer_count in the answer_count field

        Returns:
            List of dictionaries with usage tracking data including monthly breakdown
        """
        if not self.sql_conn_factory.supports_analytics():
            return []

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            if include_bonus_answers:
                answer_count_select = (
                    "COALESCE(answer_count, 0) + COALESCE(bonus_answer_count, 0) AS answer_count"
                )
            else:
                answer_count_select = "answer_count"

            if bot_id:
                query = f"""
                    SELECT bot_id, month, year, {answer_count_select}, created_at, updated_at
                    FROM usage_tracking
                    WHERE bot_id = {placeholder}
                    ORDER BY year DESC, month DESC
                """
                params = [bot_id]
            else:
                query = f"""
                    SELECT bot_id, month, year, {answer_count_select}, created_at, updated_at
                    FROM usage_tracking
                    ORDER BY year DESC, month DESC, updated_at DESC
                """
                params = []

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            fieldnames = ["bot_id", "month", "year", "answer_count", "created_at", "updated_at"]
            return [dict(zip(fieldnames, row)) for row in rows]

    @sync_to_async
    def get_organization_usage_for_month(
        self, org_id: int, month: int, year: int, *, include_bonus_answers: bool
    ) -> int:
        """Get total usage for all bots in an organization for a specific month.

        Args:
            org_id: The organization ID to get usage for
            month: Month (1-12)
            year: Year (e.g., 2024)
            include_bonus_answers: If True, includes bonus_answer_count in the total

        Returns:
            Total answer count for all bots in the organization for the specified month
        """
        from csbot.slackbot.bot_server.bot_server import BotKey

        if not self.sql_conn_factory.supports_analytics():
            return 0

        total_usage = 0

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            # Get bot IDs for this organization first
            cursor.execute(
                f"SELECT DISTINCT slack_team_id, channel_name FROM bot_instances WHERE organization_id = {placeholder}",
                [org_id],
            )
            bot_instance_rows = cursor.fetchall()

            # For each bot instance, construct bot_id and get usage
            for team_id, channel_name in bot_instance_rows:
                bot_id = BotKey.from_channel_name(team_id, channel_name).to_bot_id()

                # Query usage_tracking table for this bot_id, month, and year
                if include_bonus_answers:
                    cursor.execute(
                        f"SELECT COALESCE(answer_count, 0) + COALESCE(bonus_answer_count, 0) FROM usage_tracking WHERE bot_id = {placeholder} AND month = {placeholder} AND year = {placeholder}",
                        [bot_id, month, year],
                    )
                else:
                    cursor.execute(
                        f"SELECT answer_count FROM usage_tracking WHERE bot_id = {placeholder} AND month = {placeholder} AND year = {placeholder}",
                        [bot_id, month, year],
                    )
                result = cursor.fetchone()
                if result:
                    total_usage += result[0] or 0

        return total_usage

    @sync_to_async
    def get_usage_tracking_data_for_month(
        self, bot_id: str, month: int, year: int, *, include_bonus_answers: bool
    ) -> int:
        """Get usage tracking data for a specific month.

        Args:
            bot_id: Bot ID to get usage for
            month: Month (1-12)
            year: Year (e.g., 2024)
            include_bonus_answers: If True, includes bonus_answer_count in the total

        Returns:
            Number of answers for the specified month/year, or 0 if no data exists
        """
        if not self.sql_conn_factory.supports_analytics():
            return 0

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            if include_bonus_answers:
                query = f"""
                    SELECT COALESCE(answer_count, 0) + COALESCE(bonus_answer_count, 0)
                    FROM usage_tracking
                    WHERE bot_id = {placeholder} AND month = {placeholder} AND year = {placeholder}
                """
            else:
                query = f"""
                    SELECT answer_count
                    FROM usage_tracking
                    WHERE bot_id = {placeholder} AND month = {placeholder} AND year = {placeholder}
                """
            params = [bot_id, month, year]

            cursor.execute(query, params)
            row = cursor.fetchone()

            return row[0] if row else 0

    @sync_to_async
    def get_organization_bonus_answer_grants(self, org_id: int) -> int:
        """Get total bonus answers granted to an organization.

        Args:
            org_id: The organization ID to get bonus grants for

        Returns:
            Total bonus answer count granted to the organization
        """
        if not self.sql_conn_factory.supports_analytics():
            return 0

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            query = f"""
                SELECT COALESCE(SUM(answer_count), 0)
                FROM bonus_answer_grants
                WHERE organization_id = {placeholder}
            """
            params = [org_id]

            cursor.execute(query, params)
            row = cursor.fetchone()

            # Convert to int to ensure JSON serialization compatibility (Postgres SUM returns Decimal)
            return int(row[0]) if row else 0

    @sync_to_async
    def get_organization_bonus_answers_consumed(self, org_id: int) -> int:
        """Get total bonus answers consumed by all bots in an organization across all time periods.

        Args:
            org_id: The organization ID to get bonus consumption for

        Returns:
            Total bonus answer count consumed by all bots in the organization
        """
        from csbot.slackbot.bot_server.bot_server import BotKey

        if not self.sql_conn_factory.supports_analytics():
            return 0

        total_consumed = 0

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            # Get bot IDs for this organization first
            cursor.execute(
                f"SELECT DISTINCT slack_team_id, channel_name FROM bot_instances WHERE organization_id = {placeholder}",
                [org_id],
            )
            bot_instance_rows = cursor.fetchall()

            # For each bot instance, construct bot_id and get total bonus consumption across all months
            for team_id, channel_name in bot_instance_rows:
                bot_id = BotKey.from_channel_name(team_id, channel_name).to_bot_id()

                # Query usage_tracking table for this bot_id's total bonus_answer_count across all time periods
                cursor.execute(
                    f"SELECT COALESCE(SUM(bonus_answer_count), 0) FROM usage_tracking WHERE bot_id = {placeholder}",
                    [bot_id],
                )
                result = cursor.fetchone()
                if result:
                    # Convert to int to ensure JSON serialization compatibility (Postgres SUM returns Decimal)
                    total_consumed += int(result[0] or 0)

        return total_consumed

    @sync_to_async
    def create_bonus_answer_grant(self, org_id: int, answer_count: int, reason: str) -> None:
        """Create a bonus answer grant for an organization.

        Args:
            org_id: The organization ID to grant bonus answers to
            answer_count: Number of bonus answers to grant
            reason: Reason for the grant (e.g., "slack member incentive")
        """
        if not self.sql_conn_factory.supports_analytics():
            return

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            placeholders = ", ".join(placeholder for _ in range(3))
            sql = f"""
                INSERT INTO bonus_answer_grants
                (organization_id, answer_count, reason)
                VALUES ({placeholders})
            """
            cursor.execute(sql, (org_id, answer_count, reason))
            conn.commit()

    @sync_to_async
    def get_bonus_grants_by_reason(self, org_id: int, reason: str) -> int:
        """Get total bonus answers granted to an organization for a specific reason.

        Args:
            org_id: The organization ID to get bonus grants for
            reason: The reason to filter by

        Returns:
            Total bonus answer count granted to the organization for the specified reason
        """
        if not self.sql_conn_factory.supports_analytics():
            return 0

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            query = f"""
                SELECT COALESCE(SUM(answer_count), 0)
                FROM bonus_answer_grants
                WHERE organization_id = {placeholder} AND reason = {placeholder}
            """
            params = [org_id, reason]

            cursor.execute(query, params)
            row = cursor.fetchone()

            return row[0] if row else 0

    @sync_to_async
    def get_organization_usage_tracking_data(
        self, org_id: int, *, include_bonus_answers: bool
    ) -> list[dict[str, Any]]:
        """Get usage tracking data for all bots in an organization.

        Args:
            org_id: The organization ID to get usage for
            include_bonus_answers: If True, includes bonus_answer_count in the answer_count field

        Returns:
            List of dictionaries with usage tracking data including monthly breakdown for all bots in org
        """
        from csbot.slackbot.bot_server.bot_server import BotKey

        if not self.sql_conn_factory.supports_analytics():
            return []

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            # Get bot IDs for this organization first
            cursor.execute(
                f"SELECT DISTINCT slack_team_id, channel_name FROM bot_instances WHERE organization_id = {placeholder}",
                [org_id],
            )
            bot_instance_rows = cursor.fetchall()

            # Build list of bot_ids for this organization
            bot_ids = []
            for team_id, channel_name in bot_instance_rows:
                bot_id = BotKey.from_channel_name(team_id, channel_name).to_bot_id()
                bot_ids.append(bot_id)

            if not bot_ids:
                return []

            # Create placeholders for the IN clause
            bot_id_placeholders = ", ".join(placeholder for _ in bot_ids)

            if include_bonus_answers:
                answer_count_select = (
                    "COALESCE(answer_count, 0) + COALESCE(bonus_answer_count, 0) AS answer_count"
                )
            else:
                answer_count_select = "COALESCE(answer_count, 0) AS answer_count"

            sql = f"""
                SELECT 
                    bot_id,
                    month,
                    year,
                    {answer_count_select},
                    created_at,
                    updated_at
                FROM usage_tracking
                WHERE bot_id IN ({bot_id_placeholders})
                ORDER BY year DESC, month DESC, bot_id
            """

            cursor.execute(sql, bot_ids)
            rows = cursor.fetchall()

            return [
                {
                    "bot_id": row[0],
                    "month": row[1],
                    "year": row[2],
                    # Convert to int to ensure JSON serialization compatibility (Postgres COALESCE returns Decimal)
                    "answer_count": int(row[3]) if row[3] is not None else 0,
                    "created_at": row[4],
                    "updated_at": row[5],
                }
                for row in rows
            ]

    @sync_to_async
    def get_organization_analytics_data(
        self, org_id: int, days: int | None = None
    ) -> list[dict[str, Any]]:
        """Get analytics event data for all bots in an organization.

        Args:
            org_id: The organization ID to get analytics for
            days: Optional number of days to look back. If None, returns all data.

        Returns:
            List of dictionaries with analytics event data for all bots in the organization
        """
        from csbot.slackbot.bot_server.bot_server import BotKey

        if not self.sql_conn_factory.supports_analytics():
            return []

        with self.sql_conn_factory.with_conn() as conn:
            cursor = conn.cursor()
            placeholder = self._get_placeholder()

            # Get bot IDs for this organization first
            cursor.execute(
                f"SELECT DISTINCT slack_team_id, channel_name FROM bot_instances WHERE organization_id = {placeholder}",
                [org_id],
            )
            bot_instance_rows = cursor.fetchall()

            # Build list of bot_ids for this organization
            bot_ids = []
            for team_id, channel_name in bot_instance_rows:
                bot_id = BotKey.from_channel_name(team_id, channel_name).to_bot_id()
                bot_ids.append(bot_id)

            if not bot_ids:
                return []

            # Create placeholders for the IN clause
            bot_id_placeholders = ", ".join(placeholder for _ in bot_ids)

            # Build the query with optional date filtering
            query_params = bot_ids.copy()
            date_filter = ""
            if days is not None:
                date_filter = f" AND created_at >= datetime('now', '-{days} days')"
                if _is_conn_factory_postgresql(self.sql_conn_factory):
                    date_filter = f" AND created_at >= NOW() - INTERVAL '{days} days'"

            sql = f"""
                SELECT 
                    id,
                    bot_id,
                    event_type,
                    channel_id,
                    user_id,
                    thread_ts,
                    message_ts,
                    metadata,
                    tokens_used,
                    created_at
                FROM analytics
                WHERE bot_id IN ({bot_id_placeholders}){date_filter}
                ORDER BY created_at DESC
            """

            cursor.execute(sql, query_params)
            rows = cursor.fetchall()

            analytics_data = []
            for row in rows:
                record = {
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

                # Extract user information from metadata if available
                user_info = self._extract_user_info_from_metadata(record.get("metadata"))
                if user_info:
                    record["user_info"] = user_info

                analytics_data.append(record)

            return analytics_data


# Global unified logging function for use across all modules
async def log_analytics_event_unified(
    analytics_store: SlackbotAnalyticsStore,
    event_type: AnalyticsEventType,
    bot_id: str,
    organization_name: str,
    channel_id: str | None = None,
    user_id: str | None = None,
    thread_ts: str | None = None,
    message_ts: str | None = None,
    metadata: dict[str, Any] | str | None = None,
    tokens_used: int | None = None,
    enriched_person: "EnrichedPerson | None" = None,
    user_email: str | None = None,
    # Enhanced context for Segment
    organization_id: int | None = None,
    channel_name: str | None = None,
    team_id: str | None = None,
    send_to_segment: bool = True,
    onboarding_type: str | None = None,
) -> None:
    """Log analytics event to both Analytics DB and Segment (unified logging).

    This function sends events to both the Analytics DB and Segment by default,
    making it easy to ensure all important events are captured in both systems.

    Use this function for any new events to ensure they go to both systems:

    ```python
    from csbot.slackbot.slackbot_analytics import log_analytics_event_unified, AnalyticsEventType

    await log_analytics_event_unified(
        analytics_store=analytics_store,
        event_type=AnalyticsEventType.YOUR_EVENT,
        bot_id="your_bot_id",
        organization_name="Acme Corp",
        organization_id=12345,
        metadata={"key": "value"}
    )
    ```

    Args:
        analytics_store: Analytics store instance
        event_type: Type of analytics event
        bot_id: Bot identifier
        channel_id: Slack channel ID
        user_id: Slack user ID
        thread_ts: Thread timestamp
        message_ts: Message timestamp
        metadata: Event metadata (dict or JSON string)
        tokens_used: Number of tokens used
        enriched_person: Enriched user information
        user_email: User email (for Segment identification)
        organization_name: Organization name (for Segment context)
        organization_id: Organization ID (for Segment context)
        channel_name: Channel name (for Segment context)
        team_id: Team/workspace ID (for Segment context)
        send_to_segment: Whether to send to Segment (default: True)
    """
    # Extract email from enriched_person if not provided explicitly
    if user_email is None and enriched_person and enriched_person.email:
        user_email = enriched_person.email

    # Always log to Analytics DB
    await analytics_store.log_analytics_event_with_enriched_user(
        bot_id=bot_id,
        event_type=event_type,
        channel_id=channel_id,
        user_id=user_id,
        thread_ts=thread_ts,
        message_ts=message_ts,
        metadata=metadata,
        tokens_used=tokens_used,
        enriched_person=enriched_person,
        user_email=user_email,
        organization_id=organization_id,
        organization_name=organization_name,
        onboarding_type=onboarding_type,
    )

    # Also send to Segment (if enabled)
    if send_to_segment:
        from csbot.slackbot.segment_analytics import track_event

        track_event(
            event_type=event_type,
            bot_id=bot_id,
            channel_id=channel_id,
            user_id=user_id,
            thread_ts=thread_ts,
            message_ts=message_ts,
            metadata=json.dumps(metadata) if isinstance(metadata, dict) else metadata,
            tokens_used=tokens_used,
            enriched_person=enriched_person,
            # Enhanced context
            organization_name=organization_name,
            organization_id=organization_id,
            channel_name=channel_name,
            team_id=team_id,
            onboarding_type=onboarding_type,
        )
