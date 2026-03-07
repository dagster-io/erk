"""Real HTTP client implementation using httpx.

RealHttpClient provides fast, in-process HTTP requests to APIs
without subprocess overhead. Designed for TUI responsiveness.
"""

from typing import Any

import httpx

from erk_shared.gateway.http.abc import HttpClient, HttpError


class RealHttpClient(HttpClient):
    """Production HTTP client using httpx for fast API calls."""

    def __init__(
        self,
        *,
        token: str,
        base_url: str,
    ) -> None:
        """Create RealHttpClient with authentication.

        Args:
            token: Bearer token for authentication
            base_url: Base URL for API (e.g., "https://api.github.com")
        """
        self._token = token
        self._base_url = base_url.rstrip("/")

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with authentication."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: dict[str, Any] | None,
    ) -> httpx.Response:
        """Send an HTTP request and raise on error.

        Args:
            method: HTTP method (GET, POST, PATCH)
            endpoint: API endpoint path
            json_data: Optional JSON body to send

        Returns:
            httpx Response object

        Raises:
            HttpError: If the response status code is >= 400
        """
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        response = httpx.request(
            method, url, json=json_data, headers=self._build_headers(), timeout=30.0
        )

        if response.status_code >= 400:
            raise HttpError(
                status_code=response.status_code,
                message=response.text,
                endpoint=endpoint,
            )

        return response

    def patch(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a PATCH request to the API."""
        response = self._make_request("PATCH", endpoint, json_data=data)
        return response.json() if response.content else {}

    def post(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a POST request to the API."""
        response = self._make_request("POST", endpoint, json_data=data)
        return response.json() if response.content else {}

    def put(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a PUT request to the API."""
        response = self._make_request("PUT", endpoint, json_data=data)
        return response.json() if response.content else {}

    def get(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """Send a GET request to the API."""
        return self._make_request("GET", endpoint, json_data=None).json()

    def get_list(
        self,
        endpoint: str,
    ) -> list[dict[str, Any]]:
        """Send a GET request expecting a JSON array response."""
        return self._make_request("GET", endpoint, json_data=None).json()

    def graphql(
        self,
        *,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a GraphQL query via POST /graphql."""
        payload = {"query": query, "variables": variables}
        return self._make_request("POST", "graphql", json_data=payload).json()

    @property
    def supports_direct_api(self) -> bool:
        """RealHttpClient can make real API calls."""
        return True
