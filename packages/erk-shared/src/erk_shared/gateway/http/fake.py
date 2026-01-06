"""Fake HTTP client implementation for testing.

FakeHttpClient is an in-memory implementation that tracks requests
without actual network calls, enabling fast and deterministic tests.
"""

from dataclasses import dataclass
from typing import Any

from erk_shared.gateway.http.abc import HttpClient, HttpError


@dataclass(frozen=True)
class RecordedRequest:
    """A recorded HTTP request for test assertions."""

    method: str
    endpoint: str
    data: dict[str, Any] | None


class FakeHttpClient(HttpClient):
    """In-memory fake implementation that tracks HTTP requests.

    This class has NO public setup methods except via constructor.
    All state is configured at construction or captured during execution.
    """

    def __init__(self) -> None:
        """Create FakeHttpClient with empty state."""
        self._requests: list[RecordedRequest] = []
        self._responses: dict[str, dict[str, Any]] = {}
        self._errors: dict[str, HttpError] = {}

    @property
    def requests(self) -> list[RecordedRequest]:
        """Get the list of recorded requests.

        Returns a copy of the list to prevent external mutation.

        This property is for test assertions only.
        """
        return list(self._requests)

    def set_response(
        self,
        endpoint: str,
        *,
        response: dict[str, Any],
    ) -> None:
        """Configure a response for an endpoint.

        Args:
            endpoint: The endpoint pattern to match
            response: The JSON response to return
        """
        self._responses[endpoint] = response

    def set_error(
        self,
        endpoint: str,
        *,
        status_code: int,
        message: str,
    ) -> None:
        """Configure an error for an endpoint.

        Args:
            endpoint: The endpoint pattern to match
            status_code: HTTP status code for the error
            message: Error message
        """
        self._errors[endpoint] = HttpError(
            status_code=status_code,
            message=message,
            endpoint=endpoint,
        )

    def _get_response(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Get the configured response or raise configured error.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data (for recording)

        Returns:
            Configured response

        Raises:
            HttpError: If configured to fail
        """
        self._requests.append(RecordedRequest(method, endpoint, data))

        if endpoint in self._errors:
            raise self._errors[endpoint]

        return self._responses.get(endpoint, {})

    def patch(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Record PATCH request and return configured response.

        Args:
            endpoint: API endpoint path
            data: JSON body sent

        Returns:
            Configured response dictionary
        """
        return self._get_response("PATCH", endpoint, data)

    def post(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Record POST request and return configured response.

        Args:
            endpoint: API endpoint path
            data: JSON body sent

        Returns:
            Configured response dictionary
        """
        return self._get_response("POST", endpoint, data)

    def get(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """Record GET request and return configured response.

        Args:
            endpoint: API endpoint path

        Returns:
            Configured response dictionary
        """
        return self._get_response("GET", endpoint, None)
