"""HTTP client abstraction for dependency injection.

This module provides an ABC for HTTP client operations to enable
testing without actual network calls and to improve TUI responsiveness
by avoiding subprocess overhead.
"""

from abc import ABC, abstractmethod
from typing import Any


class HttpClient(ABC):
    """Abstract HTTP client for dependency injection.

    This is a minimal interface designed for TUI operations that need
    fast HTTP calls without subprocess overhead. It focuses on JSON APIs.
    """

    @abstractmethod
    def patch(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a PATCH request to the API.

        Args:
            endpoint: API endpoint path (e.g., "repos/owner/repo/issues/123")
            data: JSON body to send

        Returns:
            Response JSON as a dictionary

        Raises:
            HttpError: If the request fails
        """
        ...

    @abstractmethod
    def post(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a POST request to the API.

        Args:
            endpoint: API endpoint path (e.g., "repos/owner/repo/issues")
            data: JSON body to send

        Returns:
            Response JSON as a dictionary

        Raises:
            HttpError: If the request fails
        """
        ...

    @abstractmethod
    def get(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """Send a GET request to the API.

        Args:
            endpoint: API endpoint path (e.g., "repos/owner/repo/issues/123")

        Returns:
            Response JSON as a dictionary

        Raises:
            HttpError: If the request fails
        """
        ...


class HttpError(Exception):
    """Exception raised when an HTTP request fails."""

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        endpoint: str,
    ) -> None:
        """Create an HttpError.

        Args:
            status_code: HTTP status code
            message: Error message
            endpoint: The endpoint that was called
        """
        self.status_code = status_code
        self.endpoint = endpoint
        super().__init__(f"HTTP {status_code} for {endpoint}: {message}")
