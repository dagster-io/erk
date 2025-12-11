"""Custom exceptions for onboarding flow."""


class OnboardingStepError(Exception):
    """Base exception for onboarding step failures.

    Attributes:
        message: Technical error message for logging
        user_facing_message: User-friendly error message for response
    """

    def __init__(self, message: str, user_facing_message: str | None = None):
        self.message = message
        self.user_facing_message = user_facing_message if user_facing_message else message
        super().__init__(message)


class OnboardingInProgressError(OnboardingStepError):
    """Raised when initiating an onboarding already in progress"""

    pass


class SlackTeamCreationError(OnboardingStepError):
    """Raised when Slack team creation fails."""

    pass


class ChannelSetupError(OnboardingStepError):
    """Raised when channel setup (creation or admin invites) fails."""

    pass


class BotSetupError(OnboardingStepError):
    """Raised when bot setup (ID retrieval or channel invites) fails."""

    pass


class ContextstoreCreationError(OnboardingStepError):
    """Raised when contextstore repository creation fails."""

    pass


class BillingSetupError(OnboardingStepError):
    """Raised when Stripe billing setup fails."""

    pass


class OrganizationCreationError(OnboardingStepError):
    """Raised when organization or TOS recording fails."""

    pass


class BotInstanceCreationError(OnboardingStepError):
    """Raised when bot instance creation or configuration fails."""

    pass


class SlackConnectError(OnboardingStepError):
    """Raised when Slack Connect invitation fails."""

    pass
