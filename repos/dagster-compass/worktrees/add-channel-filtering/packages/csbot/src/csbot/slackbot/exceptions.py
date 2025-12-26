"""User-facing exceptions with rich error context for web forms."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


class IUserFacingError(ABC):
    """Abstract base class for all user-facing errors that should be displayed to users."""

    @property
    @abstractmethod
    def title(self) -> str:
        """Short, user-friendly error title."""
        pass

    @property
    @abstractmethod
    def message(self) -> str:
        """Primary error message for the user."""
        pass

    @property
    @abstractmethod
    def error_type(self) -> str:
        """Classification of error type for styling/icons."""
        pass


class BotUserFacingError(Exception, IUserFacingError):
    """User-facing error that occurs within bot context and knows which bot to use for response.

    This error type should be used when we have a specific bot instance that should handle
    the error response, eliminating the need to guess which bot to use from a channel lookup.

    Attributes:
        source_bot: The bot instance that should handle this error
        title: Short, user-friendly error title
        message: Primary error message for the user
        error_type: Classification of error type for styling/icons
    """

    def __init__(
        self,
        source_bot: "CompassChannelBaseBotInstance",
        title: str,
        message: str,
        error_type: str = "bot_error",
    ):
        self.source_bot = source_bot
        self._title = title
        self._message = message
        self._error_type = error_type

        # Call parent with the main message
        super().__init__(message)

    @property
    def title(self) -> str:
        return self._title

    @property
    def message(self) -> str:
        return self._message

    @property
    def error_type(self) -> str:
        return self._error_type


class UserFacingError(Exception):
    """Exception for errors that should be displayed to users with rich context.

    This exception type indicates that processing should halt and a meaningful
    error message should be displayed to the user. It carries enough context
    to generate rich HTML error pages with detailed information.

    Attributes:
        title: Short, user-friendly error title
        message: Primary error message for the user
        details: Technical details for debugging (optional)
        context: Additional context data for error templates
        error_type: Classification of error type for styling/icons
        suggested_actions: List of suggested actions the user can take
        support_info: Information to include when contacting support
    """

    def __init__(
        self,
        title: str,
        message: str,
        *,
        details: str | None = None,
        context: dict[str, Any] | None = None,
        error_type: str = "configuration",
        suggested_actions: list[str] | None = None,
        support_info: dict[str, Any] | None = None,
    ):
        self.title = title
        self.message = message
        self.details = details
        self.context = context or {}
        self.error_type = error_type
        self.suggested_actions = suggested_actions or []
        self.support_info = support_info or {}

        # Call parent with the main message
        super().__init__(message)

    def get_error_context(self) -> dict[str, Any]:
        """Get complete error context for template rendering."""
        return {
            "title": self.title,
            "message": self.message,
            "details": self.details,
            "error_type": self.error_type,
            "suggested_actions": self.suggested_actions,
            "support_info": self.support_info,
            **self.context,
        }

    def get_support_details(self) -> str:
        """Get formatted support details for error reporting."""
        lines = []
        lines.append(f"Error Type: {self.error_type}")
        lines.append(f"Title: {self.title}")
        lines.append(f"Message: {self.message}")

        if self.details:
            lines.append(f"Technical Details: {self.details}")

        if self.context:
            lines.append("Context:")
            for key, value in self.context.items():
                lines.append(f"  {key}: {value}")

        if self.support_info:
            lines.append("Support Information:")
            for key, value in self.support_info.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    @classmethod
    def bot_configuration_error(
        cls,
        *,
        team_id: str,
        organization: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> "UserFacingError":
        """Create a bot configuration error with standard context."""
        context = {
            "team_id": team_id,
        }
        if organization:
            context["organization"] = organization
        if additional_context:
            context.update(additional_context)

        support_info = {
            "error_category": "bot_configuration",
            "team_id": team_id,
            "root_cause": "No bot instance configured for Slack workspace",
        }

        return cls(
            title="Bot Not Configured",
            message=f"No Compass bot is configured for this Slack workspace (Team ID: {team_id}).",
            details=f"The system attempted to process a Slack event for team {team_id}, but no bot instance is configured for this workspace.",
            context=context,
            error_type="configuration",
            suggested_actions=[
                "Contact your administrator to configure the Compass bot for this workspace",
                "Ensure the bot setup process was completed successfully",
                "Check if the workspace was created through the proper onboarding flow",
            ],
            support_info=support_info,
        )

    @classmethod
    def onboarding_error(
        cls,
        *,
        step: str,
        organization: str,
        team_id: str | None = None,
        error_details: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> "UserFacingError":
        """Create an onboarding-specific error with context."""
        context = {
            "step": step,
            "organization": organization,
        }
        if team_id:
            context["team_id"] = team_id
        if additional_context:
            context.update(additional_context)

        support_info = {
            "error_category": "onboarding",
            "failed_step": step,
            "organization": organization,
        }
        if team_id:
            support_info["team_id"] = team_id
        if error_details:
            support_info["error_details"] = error_details

        return cls(
            title="Account Setup Failed",
            message=f"We encountered an error during {step} for your organization.",
            details=error_details,
            context=context,
            error_type="onboarding",
            suggested_actions=[
                "Contact support with the error details below",
                "Try the setup process again",
                "Check if your organization name conflicts with existing workspaces",
            ],
            support_info=support_info,
        )

    @classmethod
    def slack_api_error(
        cls,
        *,
        operation: str,
        slack_error: str,
        organization: str | None = None,
        team_id: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> "UserFacingError":
        """Create a Slack API error with context."""
        context = {
            "operation": operation,
            "slack_error": slack_error,
        }
        if organization:
            context["organization"] = organization
        if team_id:
            context["team_id"] = team_id
        if additional_context:
            context.update(additional_context)

        support_info = {
            "error_category": "slack_api",
            "failed_operation": operation,
            "slack_error_code": slack_error,
        }
        if organization:
            support_info["organization"] = organization
        if team_id:
            support_info["team_id"] = team_id

        # Customize message based on common Slack errors
        if slack_error == "domain_taken":
            message = "The domain generated from your organization name is already in use by another Slack workspace."
            suggested_actions = [
                "Go back and choose a different organization name",
                "Try adding your company name or a unique identifier",
                "Contact support if you believe this is your existing workspace",
            ]
        elif slack_error == "invalid_auth":
            message = (
                "Bot authentication failed - the Compass bot apps need approval for your workspace."
            )
            suggested_actions = [
                "Your workspace was created successfully",
                "Contact support to approve bot apps and complete setup",
                "Keep your workspace information handy for support",
            ]
        else:
            message = f"A Slack API error occurred during {operation}."
            suggested_actions = [
                "Contact support with the error details",
                "Try the operation again",
                "Check Slack service status if the error persists",
            ]

        return cls(
            title="Slack Integration Error",
            message=message,
            details=f"Slack API returned error '{slack_error}' during {operation}",
            context=context,
            error_type="slack_api",
            suggested_actions=suggested_actions,
            support_info=support_info,
        )

    @classmethod
    def from_generic_exception(
        cls,
        *,
        exception: Exception,
        additional_context: dict[str, Any] | None = None,
    ) -> "UserFacingError":
        """Create a UserFacingError from any generic exception with sensible defaults."""
        exception_name = type(exception).__name__
        exception_message = str(exception)

        context = {
            "original_exception_type": exception_name,
            "original_exception_message": exception_message,
        }
        if additional_context:
            context.update(additional_context)

        support_info = {
            "error_category": "system_error",
            "exception_type": exception_name,
            "exception_message": exception_message,
        }

        return cls(
            title="System Error",
            message="An unexpected error occurred while processing your request.",
            details=f"{exception_name}: {exception_message}",
            context=context,
            error_type="system",
            suggested_actions=[
                "Try refreshing the page and attempting the operation again",
                "Contact support if the error persists",
                "Include the error details below when contacting support",
            ],
            support_info=support_info,
        )
