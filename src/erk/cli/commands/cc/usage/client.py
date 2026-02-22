"""Anthropic Admin API client for Claude Code usage analytics."""

import json
import urllib.error
import urllib.request
from typing import Any


class AnthropicAdminError(Exception):
    """Error from the Anthropic Admin API."""

    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(f"Anthropic API error ({status_code}): {message}")
        self.status_code = status_code


class AnthropicAdminClient:
    """Client for querying the Anthropic Admin API.

    Supports fetching Claude Code usage reports with automatic pagination.
    """

    BASE_URL = "https://api.anthropic.com/v1/organizations"

    def __init__(self, *, token: str) -> None:
        self._token = token

    def get_claude_code_usage(
        self,
        *,
        starting_at: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch Claude Code usage records with automatic pagination.

        Args:
            starting_at: Start date in YYYY-MM-DD format.
            limit: Maximum results per page (up to 1000).

        Returns:
            List of usage records from the API.

        Raises:
            AnthropicAdminError: If the API returns an error response.
        """
        all_records: list[dict[str, Any]] = []
        page: str | None = None

        while True:
            data = self._fetch_page(
                starting_at=starting_at,
                limit=limit,
                page=page,
            )
            results = data.get("data", [])
            all_records.extend(results)

            if not data.get("has_more", False):
                break

            page = data.get("next_page")
            if page is None:
                break

        return all_records

    def _fetch_page(
        self,
        *,
        starting_at: str,
        limit: int,
        page: str | None,
    ) -> dict[str, Any]:
        """Fetch a single page of usage data from the API."""
        params = f"starting_at={starting_at}&limit={limit}"
        if page is not None:
            params += f"&page={page}"

        url = f"{self.BASE_URL}/usage_report/claude_code?{params}"

        request = urllib.request.Request(
            url,
            headers={
                "x-api-key": self._token,
                "anthropic-version": "2023-06-01",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            message = body if body else e.reason
            raise AnthropicAdminError(
                status_code=e.code,
                message=message,
            ) from e
