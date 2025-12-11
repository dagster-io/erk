from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine, Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

from pydantic import BaseModel

from csbot.slackbot.storage.onboarding_state import (
    BotInstanceType,
    OnboardingState,
    ProspectorDataType,
)
from csbot.utils.misc import normalize_channel_name

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import BotKey
    from csbot.slackbot.slackbot_core import CompassBotSingleChannelConfig
    from csbot.slackbot.slackbot_models import PrInfo
    from csbot.slackbot.storage.onboarding_state import OnboardingState

PLAN_LIMITS_TTL_SECONDS = 180 * 60  # 3 hours
CRONJOB_PR_TITLE_PREFIX = "CRONJOB UPDATE:"


class ContextUpdateType(Enum):
    """Type of context update for tracking GitHub PR/issue events."""

    SCHEDULED_ANALYSIS = "SCHEDULED_ANALYSIS"
    CONTEXT_UPDATE = "CONTEXT_UPDATE"
    DATA_REQUEST = "DATA_REQUEST"


class ContextStatusType(Enum):
    """Status of a context update (PR/issue)."""

    OPEN = "OPEN"
    MERGED = "MERGED"
    CLOSED = "CLOSED"


class ReferralTokenStatus(NamedTuple):
    """Status of a referral token validation check."""

    is_valid: bool
    has_been_consumed: bool
    is_single_use: bool


class ContextStatus(NamedTuple):
    """Context status entry for tracking GitHub PRs/issues."""

    organization_id: int
    repo_name: str
    update_type: ContextUpdateType
    github_url: str
    title: str
    description: str
    status: ContextStatusType
    created_at: int
    updated_at: int
    github_updated_at: int
    pr_info: "PrInfo | None"


class PlanLimits(BaseModel):
    """Cached plan limits for an organization."""

    base_num_answers: int
    allow_overage: bool
    num_channels: int
    allow_additional_channels: bool


class Organization(BaseModel):
    """Organization data model."""

    organization_id: int
    organization_name: str
    organization_industry: str | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    has_governance_channel: bool
    contextstore_github_repo: str | None


class OrgUser(BaseModel):
    """Organization user data model."""

    id: int
    slack_user_id: str
    email: str | None
    organization_id: int
    is_org_admin: bool
    name: str | None


class OrganizationUsageData(BaseModel):
    """Organization data with bot count and usage metrics."""

    organization_id: int
    organization_name: str
    organization_industry: str | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    bot_count: int
    current_usage: int
    bonus_answers: int


class InviteTokenData(BaseModel):
    """Invite token data with consumption information.

    Attributes:
        id: Unique token identifier
        token: The token string
        created_at: Timestamp when token was created
        consumed_at: Timestamp when token was consumed (None if not consumed)
        consumed_by_instance_id: Bot instance ID that consumed the token (None if not consumed)
        organization_name: Name of organization from bot instance (None if not consumed)
        organization_id: Organization ID from bot instance (None if not consumed)
        consumed_by_organization_ids: List of organization IDs that consumed the token (for multi-use customer-customer referrals)
        issued_by_organization_id: Organization ID that issued/created the token (for customer-customer referrals)
        is_single_use: Whether the token can only be used once
        consumer_bonus_answers: Number of bonus answers granted when this token is consumed
    """

    id: int
    token: str
    created_at: str
    consumed_at: str | None
    consumed_by_instance_id: int | None
    organization_name: str | None
    organization_id: int | None
    consumed_by_organization_ids: list[int]
    issued_by_organization_id: int | None
    is_single_use: bool
    consumer_bonus_answers: int


class ConnectionDetails(BaseModel):
    """Connection details for an organization.

    Attributes:
        connection_name: Name of the connection
        connection_type: SQL dialect (e.g., 'snowflake', 'postgres')
        bot_ids: List of bot IDs using this connection
        channel_names: List of channel names using this connection
    """

    connection_name: str
    connection_type: str | None
    bot_ids: list[str]
    channel_names: list[str]


class SqlConnectionFactory(ABC):
    """Abstract base class for SQL connection factories."""

    @abstractmethod
    def with_conn(self) -> Any:
        """Get a context manager for database connections."""
        pass

    @abstractmethod
    def supports_analytics(self) -> bool:
        """Check if the connection factory supports analytics."""
        pass


class PlanManager(Protocol):
    async def set_plan_limits(
        self,
        organization_id: int,
        base_num_answers: int,
        allow_overage: bool,
        num_channels: int,
        allow_additional_channels: bool,
    ) -> None: ...


class SlackbotStorage(ABC):
    """Abstract base class for Slackbot storage implementations with token management."""

    @abstractmethod
    async def is_referral_token_valid(self, token: str) -> ReferralTokenStatus:
        """Check if a referral token is valid and whether it has been consumed.

        Args:
            token: The referral token string to validate

        Returns:
            ReferralTokenStatus with is_valid and has_been_consumed flags
        """
        pass

    @abstractmethod
    async def mark_referral_token_consumed(
        self, token: str, instance_id: int, timestamp: float | None = None
    ) -> None:
        """Mark a referral token as consumed by a specific bot instance.

        Automatically appends the bot instance's organization ID to consumed_by_organization_ids.

        Args:
            token: The referral token string to mark as consumed
            instance_id: The ID of the bot instance consuming the token
            timestamp: Unix timestamp when consumed (defaults to current time)
        """
        pass

    @abstractmethod
    async def get_bot_instance_by_token(self, token: str) -> dict | None:
        """Get bot instance information by referral token.

        Args:
            token: The referral token to look up

        Returns:
            dict with bot instance info if token was consumed, None otherwise
            Bot instance dict contains: id, channel_name, contextstore_github_repo, etc.
        """
        pass

    @abstractmethod
    def for_instance(self, bot_id: str) -> "SlackbotInstanceStorage":
        """Create a SlackbotInstanceStorage for a specific bot instance.

        Args:
            bot_id: The bot ID for the instance storage

        Returns:
            A SlackbotInstanceStorage implementation for the given bot ID
        """
        pass

    @abstractmethod
    async def create_bot_instance(
        self,
        channel_name: str,
        governance_alerts_channel: str,
        contextstore_github_repo: str,
        slack_team_id: str,
        bot_email: str,
        organization_id: int,
        instance_type: BotInstanceType = BotInstanceType.STANDARD,
        icp_text: str | None = None,
        data_types: list[ProspectorDataType] | None = None,
    ) -> int:
        """Create a new bot instance and return its ID.

        Args:
            channel_name: Name of the Slack channel
            governance_alerts_channel: Name of the governance alerts channel
            contextstore_github_repo: GitHub repository for context store
            slack_team_id: Slack team ID
            bot_email: Email address of the bot
            organization_id: ID of the organization
            instance_type: Type of bot instance (standard or prospector), defaults to standard
            icp_text: ICP text for prospector instances, optional
            data_types: List of data types for prospector instances (e.g., sales, recruiting, investing), optional

        Returns:
            The ID of the created bot instance
        """
        pass

    @abstractmethod
    async def delete_bot_instance(self, organization_id: int, bot_id: "BotKey") -> None:
        """Delete a bot instance by organization ID and bot ID.

        Args:
            organization_id: ID of the organization
            bot_id: ID of the bot instance to delete
        """
        pass

    @abstractmethod
    async def update_organization_industry(self, organization_id: int, industry: str) -> None:
        """Update the industry for an organization.

        Args:
            organization_id: The organization ID
            industry: New industry to set
        """
        pass

    @abstractmethod
    async def update_bot_instance_icp(self, bot_instance_id: int, icp_text: str) -> None:
        """Update ICP (Ideal Customer/Candidate Profile) for a bot instance.

        Args:
            bot_instance_id: The bot instance ID
            icp_text: The ICP text to store
        """
        pass

    @abstractmethod
    async def add_connection(
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
            organization_id: The organization ID
            connection_name: Name of the connection
            url: Connection URL
            additional_sql_dialect: Additional SQL dialect to use for the connection
            data_documentation_contextstore_github_repo: Optional GitHub repo path for shared dataset docs
            plaintext_url: if provided, this will be encrypted and then store in encrypted_url column
        """
        pass

    @abstractmethod
    async def add_bot_connection(
        self, organization_id: int, bot_id: str, connection_name: str
    ) -> None:
        """Add a mapping between a bot and a connection.

        Args:
            organization_id: The organization ID
            bot_id: The bot ID (format: "slack_team_id-channel_name")
            connection_name: Name of the connection to map to the bot
        """
        pass

    @abstractmethod
    async def remove_bot_connection(
        self, organization_id: int, bot_id: str, connection_name: str
    ) -> None:
        """Remove a mapping between a bot and a connection.

        Args:
            organization_id: The organization ID
            bot_id: The bot ID (format: "slack_team_id-channel_name")
            connection_name: Name of the connection to unmap from the bot
        """
        pass

    @abstractmethod
    async def get_connection_names_for_bot(self, organization_id: int, bot_id: str) -> list[str]:
        """Get all connection names for a bot.

        Args:
            organization_id: The organization ID
            bot_id: The bot ID (format: "slack_team_id-channel_name")

        Returns:
            List of connection names for the organization
        """
        pass

    @abstractmethod
    async def get_organization_connections_with_details(
        self, organization_id: int
    ) -> list[ConnectionDetails]:
        """Get all connections for an organization with detailed information.

        Args:
            organization_id: The organization ID

        Returns:
            List of ConnectionDetails with connection information
        """
        pass

    @abstractmethod
    async def reconcile_bot_connection(
        self, organization_id: int, bot_id: str, connection_names: list[str]
    ) -> None:
        """Reconcile bot connections to match the provided list.

        This method ensures that the bot is connected to exactly the connections
        specified in connection_names. It will add missing connections and remove
        any existing connections not in the list.

        Args:
            organization_id: The organization ID
            bot_id: The bot ID (format: "slack_team_id-channel_name")
            connection_names: List of connection names the bot should be connected to
        """
        pass

    @abstractmethod
    async def get_connection_names_for_organization(self, organization_id: int) -> list[str]:
        """Get all connection names for an organization.

        Args:
            organization_id: The organization ID

        Returns:
            List of connection names for the organization
        """
        pass

    @abstractmethod
    async def create_organization(
        self,
        name: str,
        has_governance_channel: bool,
        contextstore_github_repo: str,
        industry: str | None = None,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
    ) -> int:
        """Create a new organization and return its ID.

        Args:
            name: Name of the organization
            industry: Industry of the organization (optional)
            stripe_customer_id: Stripe customer ID (optional)
            stripe_subscription_id: Stripe subscription ID (optional)
            has_governance_channel: Whether organization has governance channel (defaults to True for backward compatibility)
            contextstore_github_repo: GitHub repository for context store in 'owner/repo' format (optional)

        Returns:
            The ID of the created organization
        """
        pass

    @abstractmethod
    async def record_tos_acceptance(
        self, email: str, organization_id: int, organization_name: str
    ) -> None:
        """Record terms of service acceptance for an organization.

        Args:
            email: Email address of the person accepting the terms
            organization_id: ID of the organization
            organization_name: Name of the organization
        """
        pass

    @abstractmethod
    async def load_bot_instances(
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

        Returns:
            Dictionary mapping bot keys to their configurations
        """
        pass

    @abstractmethod
    async def get_plan_limits(self, organization_id: int) -> PlanLimits | None:
        """Get cached plan limits for an organization.

        Args:
            organization_id: The organization ID

        Returns:
            CachedPlanLimits with plan limits data or None if no plan limits are cached for this organization.
        """
        pass

    @abstractmethod
    async def set_plan_limits(
        self,
        organization_id: int,
        base_num_answers: int,
        allow_overage: bool,
        num_channels: int,
        allow_additional_channels: bool,
    ) -> None:
        """Set cached plan limits for an organization (insert or update).

        Args:
            organization_id: The organization ID
            base_num_answers: Number of answers included in the plan
            allow_overage: Whether overage is allowed for this plan
            num_channels: Number of channels allowed in the plan
            allow_additional_channels: Whether additional channels are allowed
        """
        pass

    @abstractmethod
    async def get_organization_by_id(self, organization_id: int) -> Organization | None:
        """Get organization information by ID.

        Args:
            organization_id: The organization ID

        Returns:
            Organization object if found, None otherwise
        """
        pass

    @abstractmethod
    async def list_organizations(self) -> list[Organization]:
        """List all organizations with their Stripe information.

        Returns:
            List of Organization objects containing:
            - organization_id: int
            - organization_name: str
            - organization_industry: str | None
            - stripe_customer_id: str | None
            - stripe_subscription_id: str | None
        """
        pass

    @abstractmethod
    def list_organizations_with_usage_data(
        self,
        month: int,
        year: int,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str | None = None,
        order: str | None = None,
    ) -> list[OrganizationUsageData]:
        """List organizations with bot count and usage data for the specified month/year.

        Args:
            month: Month (1-12) to get usage data for
            year: Year to get usage data for
            limit: Maximum number of results to return
            offset: Number of results to skip
            sort_by: Field to sort by (e.g. 'name', 'usage', 'id')
            order: Sort order ('asc' or 'desc')

        Returns:
            List of OrganizationUsageData objects containing:
            - organization_id: int
            - organization_name: str
            - organization_industry: str | None
            - stripe_customer_id: str | None
            - stripe_subscription_id: str | None
            - bot_count: int - Number of bots for this organization
            - current_usage: int - Answer count for the month (excluding bonus)
            - bonus_answers: int - Bonus answer count for the month
        """
        pass

    @abstractmethod
    def get_analytics_for_organization(
        self,
        organization_id: int,
        limit: int = 50,
        offset: int = 0,
        event_types: list[str] | None = None,
    ) -> Coroutine[Any, Any, tuple[list[dict[str, Any]], int, str]]:
        """Get analytics events for a specific organization.

        Args:
            organization_id: The organization ID to get analytics for
            limit: Maximum number of events to return
            offset: Number of events to skip (for pagination)
            event_types: Optional list of event types to filter by. If None, returns all events.

        Returns:
            Tuple of (analytics_events, total_count, organization_name) where:
            - analytics_events: List of dictionaries containing:
                - id: int - Event ID
                - bot_id: str - Bot instance ID
                - event_type: str - Type of event
                - channel_id: str | None - Slack channel ID
                - user_id: str | None - Slack user ID
                - thread_ts: str | None - Thread timestamp
                - message_ts: str | None - Message timestamp
                - metadata: str | None - Additional metadata JSON
                - tokens_used: int | None - Number of tokens used
                - created_at: datetime - When the event was created
            - total_count: int - Total number of events for this organization
            - organization_name: str - Name of the organization
        """
        pass

    @abstractmethod
    async def list_invite_tokens(self) -> list[InviteTokenData]:
        """List all invite tokens with consumption information.

        Returns:
            List of InviteTokenData objects containing:
            - id: int - Token ID
            - token: str - The token string
            - created_at: str - When token was created
            - consumed_at: str | None - When token was consumed (if consumed)
            - consumed_by_instance_id: int | None - Bot instance ID that consumed it
            - organization_name: str | None - Organization name (if consumed)
            - organization_id: int | None - Organization ID (if consumed)
            - consumed_by_organization_ids: list[int] - List of organization IDs that consumed the token
            - issued_by_organization_id: int | None - Organization ID that issued the token
            - is_single_use: bool - Whether the token can only be used once
            - consumer_bonus_answers: int - Number of bonus answers granted when consumed
        """
        pass

    @abstractmethod
    def create_invite_token(
        self, token: str, *, is_single_use: bool, consumer_bonus_answers: int
    ) -> None:
        """Create a new invite token.

        Args:
            token: The token string to create
            is_single_use: Whether token can only be used once (False = multi-use)
            consumer_bonus_answers: Number of bonus answers to grant
        """
        pass

    @abstractmethod
    async def set_channel_mapping(
        self, team_id: str, normalized_channel_name: str, channel_id: str
    ) -> None:
        """Set a mapping between team_id, normalized_channel_name, and channel_id.

        Args:
            team_id: Slack team ID
            normalized_channel_name: Normalized channel name (lowercase, no # prefix)
            channel_id: Channel ID
        """
        pass

    @abstractmethod
    async def get_channel_id_by_name(
        self, team_id: str, normalized_channel_name: str
    ) -> str | None:
        """Get channel ID by team_id and normalized channel name.

        Args:
            team_id: Slack team ID
            normalized_channel_name: Normalized channel name (lowercase, no # prefix)

        Returns:
            Channel ID if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_channel_name_by_id(self, team_id: str, channel_id: str) -> str | None:
        """Get normalized channel name by team_id and channel ID.

        Args:
            team_id: Slack team ID
            channel_id: Channel ID

        Returns:
            Normalized channel name if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_channel_mapping(self, team_id: str, normalized_channel_name: str) -> None:
        """Delete a channel mapping by team_id and normalized channel name.

        Args:
            team_id: Slack team ID
            normalized_channel_name: Normalized channel name (lowercase, no # prefix)
        """
        pass

    # Onboarding state management (simple CRUD operations)
    @abstractmethod
    async def get_onboarding_state(
        self, email: str, organization_name: str
    ) -> "OnboardingState | None":
        """Get existing onboarding state.

        Args:
            email: User email
            organization_name: Organization name

        Returns:
            OnboardingState if exists, None otherwise
        """
        pass

    @abstractmethod
    async def get_onboarding_state_by_organization_id(
        self, organization_id: int
    ) -> "OnboardingState | None":
        """Get existing onboarding state by organization ID.

        Args:
            organization_id: Organization ID to look up

        Returns:
            OnboardingState if exists, None otherwise
        """
        pass

    @abstractmethod
    async def create_onboarding_state(self, state: "OnboardingState") -> "OnboardingState":
        """Create a new onboarding state record.

        Args:
            state: OnboardingState instance to create

        Returns:
            OnboardingState with id populated
        """
        pass

    @abstractmethod
    async def update_onboarding_state(self, state: "OnboardingState") -> None:
        """Update existing onboarding state in database.

        Args:
            state: OnboardingState instance with updated values (must have id set)
        """
        pass

    @abstractmethod
    async def list_onboarding_states(
        self, limit: int = 50, cursor: int | None = None
    ) -> list["OnboardingState"]:
        """List onboarding states with cursor-based pagination, ordered by most recent first.

        Args:
            limit: Maximum number of results to return
            cursor: ID of the last item from previous page (for pagination).
                   If None, returns the first page starting from most recent.

        Returns:
            List of OnboardingState objects ordered by id DESC (most recent first)
        """
        pass

    # Context status management (GitHub PRs/issues tracking)
    @abstractmethod
    async def upsert_context_status(
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
        """Insert or update a context status entry.

        Args:
            organization_id: Organization ID
            repo_name: GitHub repository name (e.g., "dagster-compass/context-repo")
            update_type: Type of update (SCHEDULED_ANALYSIS, CONTEXT_UPDATE, DATA_REQUEST)
            github_url: GitHub URL for the PR or issue (unique identifier)
            title: PR or issue title
            description: PR or issue description
            status: Current status (OPEN, MERGED, CLOSED)
            created_at: Unix timestamp when event was created
            updated_at: Unix timestamp when event was last updated
            github_updated_at: Unix timestamp from GitHub's updated_at field
            pr_info: PrInfo object with metadata (bot_id, type)
        """
        pass

    @abstractmethod
    async def get_context_status(
        self,
        organization_id: int,
        status: ContextStatusType | None = None,
        update_type: ContextUpdateType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ContextStatus]:
        """Get context status entries for an organization.

        Args:
            organization_id: Organization ID to filter by
            status: Optional status filter (OPEN, MERGED, CLOSED)
            update_type: Optional update type filter (SCHEDULED_ANALYSIS, CONTEXT_UPDATE, DATA_REQUEST)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of ContextStatus objects
        """
        pass

    # Organization user management
    @abstractmethod
    async def add_org_user(
        self,
        slack_user_id: str,
        email: str | None,
        organization_id: int,
        is_org_admin: bool = False,
        name: str | None = None,
    ) -> OrgUser:
        """Add a user to an organization.

        Args:
            slack_user_id: Slack user ID
            email: User email address (optional)
            organization_id: Organization ID
            is_org_admin: Whether user is an admin (default False)
            name: Optional user's real name

        Returns:
            The created or existing OrgUser

        Note:
            Uses INSERT ON CONFLICT to handle duplicate entries.
            If a user with the same (slack_user_id, organization_id) already exists,
            returns the existing user.
        """
        pass

    @abstractmethod
    async def update_org_user_admin_status(
        self,
        slack_user_id: str,
        organization_id: int,
        is_org_admin: bool,
    ) -> None:
        """Update admin status for an organization user.

        Args:
            slack_user_id: Slack user ID
            organization_id: Organization ID
            is_org_admin: New admin status

        Raises:
            ValueError: If user not found for the given slack_user_id and organization_id
        """
        pass

    @abstractmethod
    async def get_org_users(
        self, organization_id: int, cursor: int | None = None, limit: int = 50
    ) -> list[OrgUser]:
        """Get users for an organization with cursor-based pagination.

        Args:
            organization_id: Organization ID
            cursor: Optional cursor (org_user id) to fetch users after this id
            limit: Maximum number of users to return (default 50)

        Returns:
            List of OrgUser objects ordered by id (ascending)
        """
        pass

    @abstractmethod
    async def get_org_user_by_slack_user_id(
        self, slack_user_id: str, organization_id: int
    ) -> OrgUser | None:
        """Get a user by slack_user_id and organization_id.

        Args:
            slack_user_id: Slack user ID
            organization_id: Organization ID

        Returns:
            OrgUser object if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_org_user_by_email(self, email: str, organization_id: int) -> OrgUser | None:
        """Get a user by email and organization_id.

        Args:
            email: User email address
            organization_id: Organization ID

        Returns:
            OrgUser object if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_org_user_by_id(self, org_user_id: int) -> OrgUser | None:
        """Get a user by org_user_id.

        Args:
            org_user_id: Organization user ID

        Returns:
            OrgUser object if found, None otherwise
        """
        pass


class SlackbotInstanceStorage(SlackbotStorage):
    """Abstract base class for Slackbot instance storage implementations."""

    @property
    @abstractmethod
    def sql_conn_factory(self) -> SqlConnectionFactory:
        """Get the SQL connection factory used by this storage implementation."""
        pass

    @abstractmethod
    async def get(self, family: str, key: str) -> str | None:
        """Get a value by family and key."""
        pass

    @abstractmethod
    async def set(
        self, family: str, key: str, value: str, expiry_seconds: int | None = None
    ) -> None:
        """Set a value by family and key with optional expiry."""
        pass

    @abstractmethod
    async def exists(self, family: str, key: str) -> bool:
        """Check if a key exists in the given family."""
        pass

    @abstractmethod
    async def get_and_set(
        self,
        family: str,
        key: str,
        value_factory: Callable[[str | None], str | None],
        expiry_seconds: int | None = None,
    ) -> None:
        """Get a value by family and key, and set a new value by family and key with optional expiry.

        Provides transactional semantics. If the key does not exist, the value_factory is called with
        None and the result is set as the new value. If the key exists, the value_factory is called
        with the existing value and the result is set as the new value. If the value_factory returns
        None, the key is deleted.
        """
        pass

    @abstractmethod
    async def delete(self, family: str, key: str) -> None:
        """Delete a value by family and key."""
        pass

    @abstractmethod
    async def list(self, family: str) -> list[str]:
        """List all keys for a given family.

        Args:
            family: The family to list keys for

        Returns:
            List of keys in the family (excluding expired or deleted keys)
        """
        pass

    async def get_channel_id(self, channel_name: str) -> str | None:
        """Get the channel ID for a given channel name."""
        return await self.get("channel_name_to_id", normalize_channel_name(channel_name))
