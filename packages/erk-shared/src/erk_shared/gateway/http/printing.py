"""Printing HTTP client wrapper for verbose output.

This module provides an HTTP client wrapper that prints styled output
for operations before delegating to the wrapped implementation.
"""

from typing import Any

from erk_shared.gateway.http.abc import HttpClient
from erk_shared.printing.base import PrintingBase


class PrintingHttpClient(PrintingBase, HttpClient):
    """Wrapper that prints HTTP operations before delegating.

    This wrapper prints styled output for HTTP operations, then delegates
    to the wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production with printing
        printing_client = PrintingHttpClient(real_client, script_mode=False, dry_run=False)

        # For dry-run with printing
        dry_run_inner = DryRunHttpClient(real_client)
        printing_client = PrintingHttpClient(dry_run_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    def patch(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """PATCH request with printed output."""
        self._emit(self._format_command(f"HTTP PATCH {endpoint}"))
        return self._wrapped.patch(endpoint, data=data)

    def post(
        self,
        endpoint: str,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """POST request with printed output."""
        self._emit(self._format_command(f"HTTP POST {endpoint}"))
        return self._wrapped.post(endpoint, data=data)

    def get(
        self,
        endpoint: str,
    ) -> dict[str, Any]:
        """GET request with printed output."""
        self._emit(self._format_command(f"HTTP GET {endpoint}"))
        return self._wrapped.get(endpoint)
