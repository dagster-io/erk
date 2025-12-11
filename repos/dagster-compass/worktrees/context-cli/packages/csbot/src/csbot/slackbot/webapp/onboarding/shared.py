"""Shared utilities and handlers for onboarding flows."""

import re
from typing import TYPE_CHECKING

from aiohttp import web

from csbot.slackbot.exceptions import UserFacingError

if TYPE_CHECKING:
    from csbot.slackbot.bot_server.bot_server import CompassBotServer

# RFC 5322 compliant email regex pattern
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9._%+-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$"
)


def is_valid_email(email: str) -> bool:
    """Validate email format using RFC 5322 compliant regex."""
    return EMAIL_PATTERN.match(email) is not None


async def send_onboarding_notification(
    bot_server: "CompassBotServer",
    step_name: str,
    organization: str,
    email: str,
    additional_info: dict[str, str] | None = None,
) -> None:
    """Send a notification about onboarding step completion to internal Slack channel.

    This is a fire-and-forget function optimized for performance - it doesn't block
    the calling code and has minimal impact on app performance.

    Args:
        bot_server: Bot server instance containing configuration
        step_name: Name of the onboarding step (e.g., "Organization Created", "Joined Channel")
        organization: Organization name
        email: User email
        additional_info: Optional dictionary of additional information to include
    """
    # Old webhook notification function - deprecated in favor of Segment analytics
    return  # Early return to disable webhook notifications


def send_onboarding_notification_background(
    bot_server: "CompassBotServer",
    step_name: str,
    organization: str,
    email: str,
    additional_info: dict[str, str] | None = None,
) -> None:
    """Synchronous wrapper that schedules the notification to run in the background.

    This is the recommended way to send notifications - it's completely non-blocking
    and has zero impact on request response time.
    """
    # Old webhook notification function - deprecated in favor of Segment analytics
    return  # Early return to disable webhook notifications


def log_and_return_error(
    logger,
    user_facing_error: str,
    log: str,
) -> web.Response:
    """Log an error message and return a 500 HTTP response.

    Args:
        logger: Logger instance to use for error logging
        user_facing_error: User-friendly error message to return in response
        log: Detailed error message to log

    Returns:
        web.Response with 500 status and user-facing error text
    """
    logger.error(log)
    return web.Response(
        status=500,
        text=user_facing_error,
        content_type="text/plain",
    )


def log_and_return_validation_error(
    logger,
    user_facing_error: str,
    log: str,
) -> web.Response:
    """Log a validation error and return a 400 HTTP response.

    Args:
        logger: Logger instance to use for warning logging
        user_facing_error: User-friendly error message to return in response
        log: Detailed error message to log

    Returns:
        web.Response with 400 status and user-facing error text
    """
    logger.warning(log)
    return web.Response(
        status=400,
        text=user_facing_error,
        content_type="text/plain",
    )


def validate_email_input(email: str | None) -> None:
    """Validate email input and raise UserFacingError if invalid."""
    if not email or not isinstance(email, str):
        raise UserFacingError(
            title="Missing Email",
            message="Please provide a valid email address.",
            details="Missing or invalid email",
            error_type="onboarding",
            suggested_actions=[
                "Go back and enter your email address",
                "Make sure the email field is properly filled out",
            ],
        )

    if not is_valid_email(email):
        raise UserFacingError(
            title="Invalid Email Format",
            message="Please provide a valid email address format.",
            details="Invalid email format",
            error_type="onboarding",
            suggested_actions=[
                "Go back and check your email address",
                "Make sure it includes @ and a valid domain",
            ],
        )


def validate_organization_input(organization: str | None) -> None:
    """Validate organization input and raise UserFacingError if invalid."""
    if not organization or not isinstance(organization, str):
        raise UserFacingError(
            title="Missing Organization",
            message="Please provide your organization name.",
            details="Missing or invalid organization",
            error_type="onboarding",
            suggested_actions=[
                "Go back and enter your organization name",
                "Make sure the organization field is properly filled out",
            ],
        )
