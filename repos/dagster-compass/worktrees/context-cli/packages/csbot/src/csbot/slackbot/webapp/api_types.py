"""API response helpers for webapp JSON endpoints.

REST-ful approach:
- Success responses (2xx): Return data directly, no wrapper
- Error responses (4xx/5xx): Return {"error": "message"} with appropriate status code
"""

from typing import TypedDict


class APIErrorResponse(TypedDict):
    """Standard error response with human-readable message."""

    error: str


def error_response(error: str) -> APIErrorResponse:
    """Create a standardized error response.

    Args:
        error: Human-readable error message

    Returns:
        A dictionary with the error message

    Example:
        return web.json_response(error_response("Organization not found"), status=404)
    """
    return {"error": error}
