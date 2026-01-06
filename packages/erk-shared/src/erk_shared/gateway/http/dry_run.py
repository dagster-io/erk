"""No-op HTTP client wrapper for dry-run mode.

This module provides an HTTP client wrapper that prevents actual HTTP
requests while logging what would have been done.
"""

from typing import Any

from erk_shared.gateway.http.abc import HttpClient
from erk_shared.output.output import user_output


class DryRunHttpClient(HttpClient):
    """No-op wrapper that prevents HTTP requests in dry-run mode.

    All HTTP operations are mutations (they send data to external APIs),
    so all methods are no-ops that print what would happen.

    Usage:
        real_client = RealHttpClient(token=token, base_url=url)
        dry_run_client = DryRunHttpClient(real_client)

        # Prints message instead of making request
        dry_run_client.patch("repos/owner/repo/issues/123", data={"state": "closed"})
    """

    def __init__(self, wrapped: HttpClient) -> None:
        """Create a dry-run wrapper around an HttpClient implementation.

        Args:
            wrapped: The HttpClient implementation to wrap
        """
        self._wrapped = wrapped

    def patch(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """No-op for PATCH request in dry-run mode."""
        user_output(f"[DRY RUN] Would PATCH {endpoint}")
        return {}

    def post(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """No-op for POST request in dry-run mode."""
        user_output(f"[DRY RUN] Would POST {endpoint}")
        return {}

    def get(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """No-op for GET request in dry-run mode.

        Note: GET is typically read-only, but we still no-op because
        it makes network requests which we want to avoid in dry-run.
        """
        user_output(f"[DRY RUN] Would GET {endpoint}")
        return {}
