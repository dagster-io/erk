"""Printing wrapper for git configuration operations."""

from pathlib import Path

from erk_shared.gateway.git.config_ops.abc import GitConfigOps
from erk_shared.printing.base import PrintingBase


class PrintingGitConfigOps(PrintingBase, GitConfigOps):
    """Wrapper that prints operations before delegating.

    Mutation operations print styled output before delegating.
    Query operations delegate without printing.
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Mutation Operations (print before delegating)
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Config set with printed output."""
        self._emit(self._format_command(f"git config --{scope} {key} {value}"))
        self._wrapped.config_set(cwd, key, value, scope=scope)

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_git_user_name(cwd)
