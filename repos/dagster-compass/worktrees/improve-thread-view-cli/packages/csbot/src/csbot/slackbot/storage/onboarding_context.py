"""Onboarding context manager for business logic around onboarding state."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from csbot.slackbot.storage.onboarding_state import OnboardingState, OnboardingStep

if TYPE_CHECKING:
    from csbot.slackbot.slackbot_analytics import SlackbotAnalyticsStore
    from csbot.slackbot.storage.interface import SlackbotStorage


class OnboardingBotAdapter:
    """Adapter that makes onboarding context compatible with BotProtocol for StepContext.

    This allows StepContext to be used during onboarding by providing the required
    bot-like interface, while ensuring analytics events have consistent format with
    other onboarding analytics events (using bot_id like "onboarding-{org_id}").
    """

    def __init__(
        self,
        logger: logging.Logger,
        analytics_store: "SlackbotAnalyticsStore",
        organization_name: str,
        organization_id: int | None = None,
        team_id: str | None = None,
    ):
        """Initialize onboarding bot adapter.

        Args:
            logger: Logger for step execution
            analytics_store: Analytics store for event logging
            organization_name: Organization name
            organization_id: Organization ID (if available)
            team_id: Slack team ID (if available)
        """
        self.logger = logger
        self.analytics_store = analytics_store
        self._organization_name = organization_name
        self._organization_id = organization_id
        self._team_id = team_id

    def get_bot_id(self) -> str:
        """Return bot identifier for analytics (matches onboarding event format)."""
        if self._organization_id:
            return f"onboarding-{self._organization_id}"
        return f"onboarding-{self._organization_name}"

    def get_organization_name(self) -> str:
        """Return organization name."""
        return self._organization_name

    def get_organization_id(self) -> int | None:
        """Return organization ID if available."""
        return self._organization_id

    def get_team_id(self) -> str | None:
        """Return team ID if available."""
        return self._team_id


class OnboardingContext:
    """Business logic layer for managing onboarding state.

    Wraps storage and provides high-level operations for onboarding flow.
    Can be used as an async context manager to automatically handle processing state.
    """

    def __init__(
        self,
        analytics_store: "SlackbotAnalyticsStore",
        logger: logging.Logger,
        storage: "SlackbotStorage",
        email: str,
        organization_name: str,
        state: OnboardingState | None = None,
    ):
        """Initialize onboarding context.

        Args:
            analytics_store: Analytics store for event logging
            logger: Logger for step execution
            storage: Storage instance for state persistence
            email: User email for onboarding
            organization_name: Organization name for onboarding
            state: Current onboarding state (if None, will be loaded/created)
        """
        self.analytics_store = analytics_store
        self.logger = logger
        self.storage = storage
        self.email = email
        self.organization_name = organization_name
        self._state = state
        self._state_loaded = state is not None
        self.is_duplicate_request = (
            False  # Flag to indicate if this is a duplicate/concurrent request
        )

    @property
    def state(self) -> OnboardingState:
        """Get the onboarding state.

        Returns:
            OnboardingState instance

        Raises:
            AssertionError: If state hasn't been initialized yet
        """
        assert self._state is not None, "State must be initialized before access"
        return self._state

    @state.setter
    def state(self, value: OnboardingState) -> None:
        """Set the onboarding state."""
        self._state = value

    def create_bot_adapter(self) -> OnboardingBotAdapter:
        """Create a BotProtocol-compatible adapter for use with StepContext.

        This allows StepContext to be used during onboarding, with analytics events
        formatted consistently with other onboarding events.

        Returns:
            OnboardingBotAdapter that implements BotProtocol

        Example:
            async with StepContext(
                step=StepEventType.COMPASS_CHANNEL_WELCOME,
                bot=ctx.create_bot_adapter()
            ) as step_context:
                await send_welcome_message(...)
        """
        return OnboardingBotAdapter(
            logger=self.logger,
            analytics_store=self.analytics_store,
            organization_name=self.organization_name,
            organization_id=self.state.organization_id if self._state else None,
            team_id=self.state.slack_team_id if self._state else None,
        )

    async def __aenter__(self) -> "OnboardingContext":
        """Enter async context manager - load/create state and start processing.

        Detects duplicate/concurrent requests by checking if processing_started_at
        is already set on an existing state.
        """
        if not self._state_loaded:
            self._state = await self.storage.get_onboarding_state(
                self.email, self.organization_name
            )
            if self._state is None:
                # No existing state - this is a fresh onboarding request
                self._state = OnboardingState(
                    email=self.email,
                    organization_name=self.organization_name,
                    completed_steps=[OnboardingStep.INITIALIZED],
                )
                self._state = await self.storage.create_onboarding_state(self._state)
            else:
                # State already exists - check if processing is already in progress
                if self._state.processing_started_at is not None:
                    # Another request is already processing this onboarding
                    self.is_duplicate_request = True
                    self.logger.warning(
                        f"Duplicate onboarding request detected for {self.organization_name} - "
                        f"processing started at {self._state.processing_started_at}"
                    )
                    # Don't call start_processing() - we'll return early
                    self._state_loaded = True
                    return self
            self._state_loaded = True

        # Only start processing if this is not a duplicate request
        if not self.is_duplicate_request:
            await self.start_processing()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager - handle errors and clear processing flag.

        Note: This method does not suppress exceptions - they propagate normally.
        """
        if exc_type is not None:
            # Log error to onboarding state
            error_message = str(exc_val) if exc_val else "Unknown error"
            await self.mark_error(error_message)

        await self.end_processing()
        return None

    async def mark_step_completed(self, step: OnboardingStep, **fields) -> None:
        """Mark a step as completed and update additional fields.

        Args:
            step: The step to mark as completed
            **fields: Additional fields to update (e.g., slack_team_id="T123")
        """
        self.state = self.state.with_step(step, **fields)
        await self.storage.update_onboarding_state(self.state)

    async def mark_completed(self) -> None:
        """Mark the entire onboarding as completed."""
        self.state = self.state.with_step(
            OnboardingStep.COMPLETED,
            completed_at=datetime.now(),
            processing_started_at=None,
        )
        await self.storage.update_onboarding_state(self.state)

    async def mark_error(self, error_message: str) -> None:
        """Mark onboarding as failed with an error message."""
        self.state = self.state.model_copy(
            update={
                "error_message": error_message,
                "processing_started_at": None,
                "updated_at": datetime.now(),
            }
        )
        await self.storage.update_onboarding_state(self.state)

    async def start_processing(self) -> None:
        """Mark onboarding as currently being processed."""
        self.state = self.state.model_copy(
            update={
                "processing_started_at": datetime.now(),
                "updated_at": datetime.now(),
            }
        )
        await self.storage.update_onboarding_state(self.state)

    async def end_processing(self) -> None:
        """Clear the processing flag."""
        self.state = self.state.model_copy(
            update={
                "processing_started_at": None,
                "updated_at": datetime.now(),
            }
        )
        await self.storage.update_onboarding_state(self.state)
