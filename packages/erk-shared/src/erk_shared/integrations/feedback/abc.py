"""User-facing diagnostic output with mode awareness."""

from abc import ABC, abstractmethod


class UserFeedback(ABC):
    """Provides user-facing diagnostic output that's mode-aware.

    This abstraction eliminates the need to thread 'script' booleans through
    function signatures. Instead, functions call ctx.feedback methods which
    automatically handle output suppression based on the current mode.

    Two modes:
    - Interactive: Show all diagnostics (info, success, errors)
    - Script: Suppress diagnostics, only show errors

    Usage:
        # In command code
        ctx.feedback.info("Starting operation...")
        result = perform_operation()
        ctx.feedback.success("Operation complete")

        # Errors always appear
        if not valid:
            ctx.feedback.error("Error: Invalid configuration")
            raise SystemExit(1)

    Mode behavior:
        Interactive mode (script=False):
            - info() -> outputs to stderr
            - success() -> outputs to stderr with green styling
            - error() -> outputs to stderr with red styling

        Script mode (script=True):
            - info() -> suppressed
            - success() -> suppressed
            - error() -> still outputs to stderr with red styling
    """

    @abstractmethod
    def info(self, message: str) -> None:
        """Show informational message (suppressed in script mode)."""

    @abstractmethod
    def success(self, message: str) -> None:
        """Show success message (suppressed in script mode)."""

    @abstractmethod
    def error(self, message: str) -> None:
        """Show error message (always shown, even in script mode)."""
