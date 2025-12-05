"""Claude session detection abstraction for safety checks.

This module provides an ABC for detecting active Claude Code sessions
in directories to prevent deleting worktrees with active sessions.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class ClaudeSessionDetector(ABC):
    """Abstract Claude session detection for dependency injection.

    Used to check if a directory has an active Claude Code session before
    performing destructive operations like worktree deletion.
    """

    @abstractmethod
    def has_active_session(self, directory: Path) -> bool:
        """Check if the given directory has an active Claude Code session.

        This detects whether any Claude Code process has files open in the
        specified directory tree.

        Args:
            directory: Path to check for active Claude sessions

        Returns:
            True if an active Claude session is detected, False otherwise
        """
        ...
