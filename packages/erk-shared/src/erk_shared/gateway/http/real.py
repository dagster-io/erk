"""Real HTTP client implementation using httpx.

RealHttpClient provides fast, in-process HTTP requests to APIs
without subprocess overhead. Designed for TUI responsiveness.
"""

from typing import Any

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

    def patch(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a PATCH request to the API.

        Args:
            endpoint: API endpoint path
            data: JSON body to send

        Returns:
            Response JSON as a dictionary

        Raises:
            HttpError: If the request fails
        """
        # Inline import: httpx is only needed at runtime and keeps module import fast
        import httpx

        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        response = httpx.patch(url, json=data, headers=self._build_headers(), timeout=30.0)

        if response.status_code >= 400:
            raise HttpError(
                status_code=response.status_code,
                message=response.text,
                endpoint=endpoint,
            )

        return response.json()

    def post(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a POST request to the API.

        Args:
            endpoint: API endpoint path
            data: JSON body to send

        Returns:
            Response JSON as a dictionary

        Raises:
            HttpError: If the request fails
        """
        import httpx

        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        response = httpx.post(url, json=data, headers=self._build_headers(), timeout=30.0)

        if response.status_code >= 400:
            raise HttpError(
                status_code=response.status_code,
                message=response.text,
                endpoint=endpoint,
            )

        return response.json()

    def get(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """Send a GET request to the API.

        Args:
            endpoint: API endpoint path

        Returns:
            Response JSON as a dictionary

        Raises:
            HttpError: If the request fails
        """
        import httpx

        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        response = httpx.get(url, headers=self._build_headers(), timeout=30.0)

        if response.status_code >= 400:
            raise HttpError(
                status_code=response.status_code,
                message=response.text,
                endpoint=endpoint,
            )

        return response.json()
