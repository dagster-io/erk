import logging
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.personalization import EnrichedPerson
    from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore


from csbot.slackbot.slackbot_analytics import AnalyticsEventType


class StepEventType(Enum):
    """Step event types that correspond to analytics events."""

    # Compass channel welcome messages
    USER_COMPASS_WELCOME = "user_compass_welcome"
    COMPASS_CHANNEL_WELCOME = "compass_channel_welcome"

    # Governance channel welcome messages
    USER_GOVERNANCE_WELCOME = "user_governance_welcome"
    GOVERNANCE_CHANNEL_WELCOME = "governance_channel_welcome"


# Mapping from (StepEventType, status) to AnalyticsEventType
# status can be: "started", "success", "error"
STEP_TO_ANALYTICS_MAP: dict[tuple[StepEventType, str], AnalyticsEventType] = {
    # Compass channel welcome messages
    (StepEventType.USER_COMPASS_WELCOME, "started"): AnalyticsEventType.WELCOME_MESSAGE_STARTED,
    (StepEventType.USER_COMPASS_WELCOME, "success"): AnalyticsEventType.WELCOME_MESSAGE_SENT,
    (StepEventType.USER_COMPASS_WELCOME, "error"): AnalyticsEventType.WELCOME_MESSAGE_ERROR,
    (
        StepEventType.COMPASS_CHANNEL_WELCOME,
        "started",
    ): AnalyticsEventType.CHANNEL_COMPASS_WELCOME_STARTED,
    (
        StepEventType.COMPASS_CHANNEL_WELCOME,
        "success",
    ): AnalyticsEventType.CHANNEL_COMPASS_WELCOME_SENT,
    (
        StepEventType.COMPASS_CHANNEL_WELCOME,
        "error",
    ): AnalyticsEventType.CHANNEL_COMPASS_WELCOME_ERROR,
    # Governance channel welcome messages
    (
        StepEventType.USER_GOVERNANCE_WELCOME,
        "started",
    ): AnalyticsEventType.GOVERNANCE_WELCOME_STARTED,
    (StepEventType.USER_GOVERNANCE_WELCOME, "success"): AnalyticsEventType.GOVERNANCE_WELCOME_SENT,
    (StepEventType.USER_GOVERNANCE_WELCOME, "error"): AnalyticsEventType.GOVERNANCE_WELCOME_ERROR,
    (
        StepEventType.GOVERNANCE_CHANNEL_WELCOME,
        "started",
    ): AnalyticsEventType.CHANNEL_GOVERNANCE_WELCOME_STARTED,
    (
        StepEventType.GOVERNANCE_CHANNEL_WELCOME,
        "success",
    ): AnalyticsEventType.CHANNEL_GOVERNANCE_WELCOME_SENT,
    (
        StepEventType.GOVERNANCE_CHANNEL_WELCOME,
        "error",
    ): AnalyticsEventType.CHANNEL_GOVERNANCE_WELCOME_ERROR,
}


class BotProtocol(Protocol):
    """Protocol for bot instances that can be used with StepContext.

    This allows StepContext to work with different bot types as long as they
    provide the required attributes.
    """

    logger: logging.Logger
    analytics_store: "SlackbotAnalyticsStore"

    def get_bot_id(self) -> str:
        """Return the bot identifier."""
        ...

    def get_organization_name(self) -> str:
        """Return the organization name."""
        ...

    def get_organization_id(self) -> int | None:
        """Return the organization ID."""
        ...

    def get_team_id(self) -> str | None:
        """Return the team ID."""
        ...


class StepContext:
    """Context manager for tracking step execution with analytics logging.

    This context manager automatically logs step lifecycle events (start, success, error)
    to both application logs and analytics. It eliminates the need for explicit
    try/except blocks with manual logging in each case.

    The context manager uses a minimal constructor that takes a bot instance and step type.
    All event-specific metadata (channel_id, user_id, enriched_person, etc.) should be
    added via add_metadata() or helper functions like add_slack_event_metadata().

    Example usage:
        async with StepContext(
            step=StepEventType.USER_COMPASS_WELCOME,
            bot=self,
        ) as ctx:
            ctx.add_slack_event_metadata(
                channel_id=channel,
                user_id=user,
                enriched_person=enriched_person
            )
            ctx.add_metadata(message_type="ephemeral")
            await send_welcome_message(...)
    """

    def __init__(
        self,
        step: StepEventType,
        bot: BotProtocol,
    ):
        """Initialize step context.

        Args:
            step: The step event type being tracked
            bot: Bot instance that provides logger, analytics_store, and organization context
        """
        self.step = step
        self.bot = bot
        self.logger = bot.logger
        self.analytics_store = bot.analytics_store

        # Metadata that will be accumulated and sent to analytics
        self.metadata: dict[str, Any] = {}

        # Analytics-specific fields (extracted when logging to analytics)
        self._channel_id: str | None = None
        self._user_id: str | None = None
        self._enriched_person: EnrichedPerson | None = None
        self._user_email: str | None = None

        # Error tracking (set via mark_error())
        self._error_message: str | None = None

    async def __aenter__(self) -> "StepContext":
        await self.log_step_start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if exc_type is not None:
            # Exception was raised - log error
            error_message = str(exc_val) if exc_val else "Unknown error"
            await self.log_step_error(error_message, exc_tb)
        elif self._error_message is not None:
            # Error was explicitly marked via mark_error()
            await self.log_step_error(self._error_message, traceback=None)
        else:
            # Normal success case
            await self.log_step_success()
        # Return None to propagate exceptions (do not suppress them)
        return None

    async def log_step_start(self) -> None:
        """Log step start to application logs and analytics."""
        self.logger.info(f"Started step {self.step.value}: {self.metadata}")

        event_type = STEP_TO_ANALYTICS_MAP.get((self.step, "started"))
        if event_type:
            await self._log_to_analytics(event_type)

    async def log_step_error(self, error_message: str, traceback: Any) -> None:
        self.logger.error(
            f"Failed step {self.step.value} with error: {error_message}\n"
            f"Traceback: {traceback}\n"
            f"Metadata: {self.metadata}"
        )

        error_metadata = {
            **self.metadata,
            "error_message": error_message,
            "error_type": type(error_message).__name__ if error_message else "Unknown",
        }

        event_type = STEP_TO_ANALYTICS_MAP.get((self.step, "error"))
        if event_type:
            await self._log_to_analytics(event_type, metadata=error_metadata)

    async def log_step_success(self) -> None:
        """Log step success to application logs and analytics."""
        self.logger.info(f"Completed step {self.step.value}: {self.metadata}")

        event_type = STEP_TO_ANALYTICS_MAP.get((self.step, "success"))
        if event_type:
            await self._log_to_analytics(event_type)

    def mark_error(self, error_message: str) -> None:
        """Mark this step as failed with an error message.

        When a step is marked as an error, an error analytics event will be logged
        on context exit instead of a success event. Use this when you want to handle
        an error condition gracefully without raising an exception.

        Args:
            error_message: Human-readable error message describing what went wrong

        Example:
            async with StepContext(step=StepEventType.USER_COMPASS_WELCOME, bot=self) as ctx:
                ctx.add_slack_event_metadata(channel_id=channel, user_id=user)
                if not user:
                    ctx.mark_error("No user ID available for welcome message")
                    return
                await send_welcome_message(...)
        """
        self._error_message = error_message

    def add_metadata(self, **kwargs: Any) -> None:
        """Add arbitrary metadata to be included in analytics events.

        This method allows adding call-site-specific metadata to the step context.

        Args:
            **kwargs: Metadata key-value pairs to add
        """
        self.metadata = {
            **self.metadata,
            **kwargs,
        }

    def add_slack_event_metadata(
        self,
        channel_id: str | None = None,
        user_id: str | None = None,
        enriched_person: "EnrichedPerson | None" = None,
        user_email: str | None = None,
    ) -> None:
        """Add Slack-specific event metadata for analytics.

        This is a convenience method for adding common Slack event fields
        that are used by the analytics logging system.

        Args:
            channel_id: Slack channel ID
            user_id: Slack user ID
            enriched_person: Enriched person information
            user_email: User email address
        """
        if channel_id is not None:
            self._channel_id = channel_id
        if user_id is not None:
            self._user_id = user_id
        if enriched_person is not None:
            self._enriched_person = enriched_person
        if user_email is not None:
            self._user_email = user_email

    async def _log_to_analytics(
        self, event_type: AnalyticsEventType, metadata: dict[str, Any] | None = None
    ) -> None:
        """Log event to analytics store.

        Args:
            event_type: The analytics event type to log
            metadata: Optional metadata dict (uses self.metadata if not provided)
        """
        from csbot.slackbot.slackbot_analytics import log_analytics_event_unified

        # Extract user_email from enriched_person if available and not explicitly set
        user_email = self._user_email
        if user_email is None and self._enriched_person and self._enriched_person.email:
            user_email = self._enriched_person.email

        await log_analytics_event_unified(
            analytics_store=self.analytics_store,
            event_type=event_type,
            bot_id=self.bot.get_bot_id(),
            organization_name=self.bot.get_organization_name(),
            channel_id=self._channel_id,
            user_id=self._user_id,
            metadata=metadata or self.metadata,
            enriched_person=self._enriched_person,
            user_email=user_email,
            organization_id=self.bot.get_organization_id(),
            team_id=self.bot.get_team_id(),
        )


def extract_slack_event_metadata(event: dict[str, Any]) -> dict[str, str | None]:
    """Extract common Slack event fields for use with add_slack_event_metadata.

    This helper function extracts channel_id and user_id from a Slack event dict.

    Args:
        event: Slack event dictionary

    Returns:
        Dictionary with channel_id and user_id keys

    Example:
        async with StepContext(step=StepEventType.WELCOME_MESSAGE, bot=self) as ctx:
            ctx.add_slack_event_metadata(**extract_slack_event_metadata(event))
    """
    return {
        "channel_id": event.get("channel"),
        "user_id": event.get("user"),
    }
