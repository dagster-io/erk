"""Error handling utilities for web applications."""

import aiohttp_jinja2
from aiohttp import web

from csbot.slackbot.exceptions import UserFacingError


def handle_user_facing_error(
    logger,
    error: UserFacingError,
    request: web.Request,
) -> web.Response:
    """Handle a UserFacingError by rendering a rich error page.

    Args:
        logger: Logger instance to use for error logging
        error: UserFacingError exception with rich context
        request: The web request for additional context

    Returns:
        web.Response with appropriate status and rich HTML error page
    """
    # Log the error for debugging
    logger.error(f"UserFacingError: {error.title} - {error.message}", exc_info=True)

    [icon_bg_color, icon_fg_color, icon] = {
        "configuration": ["bg-orange-100", "text-orange-600", "⚙️"],
        "onboarding": ["bg-red-100", "text-red-600", "❌"],
        "slack_api": ["bg-blue-100", "text-blue-600", "🔗"],
        "system": ["bg-purple-100", "text-purple-600", "💥"],
    }.get(error.error_type, ["bg-gray-100", "text-gray-600", "⚠️"])

    header_icon_html = f"""
    <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full mb-4 {icon_bg_color}">
        <span class="text-2xl {icon_fg_color}">
        {icon}
        </span>
    </div>"""

    # Get error context and add request info
    context = error.get_error_context()
    context.update(
        {
            "header_icon_html": header_icon_html,
            "header_text": error.title,
            "subheader_text": error.message,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
            "remote_addr": request.remote,
            "timestamp": "compass-bot",
            "get_support_details": lambda: error.get_support_details(),
            "get_support_email_body": lambda: f"Error Details:\n\n{error.get_support_details()}\n\nUser Agent: {request.headers.get('User-Agent', 'Unknown')}\nRemote Address: {request.remote}",
        }
    )

    status_code = 400 if error.error_type in ["configuration", "slack_api"] else 500

    return aiohttp_jinja2.render_template(
        "errors/user_error.html", request, context, status=status_code
    )


def handle_generic_exception(
    logger,
    exception: Exception,
    request: web.Request,
    context: dict | None = None,
) -> web.Response:
    """Handle any generic exception by converting it to a UserFacingError and rendering.

    Args:
        logger: Logger instance to use for error logging
        exception: The exception that occurred
        request: The web request for additional context
        context: Additional context to include in the error

    Returns:
        web.Response with appropriate status and rich HTML error page
    """
    # Convert generic exception to UserFacingError
    error_context = context or {}
    error_context.update(
        {
            "request_method": request.method,
            "request_path": request.path,
        }
    )

    user_facing_error = UserFacingError.from_generic_exception(
        exception=exception,
        additional_context=error_context,
    )

    return handle_user_facing_error(logger, user_facing_error, request)
