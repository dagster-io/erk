"""Fake Claude session detection for testing.

FakeClaudeSessionDetector is an in-memory implementation that returns
configured responses based on constructor injection, enabling deterministic
tests without needing lsof or real Claude processes.
"""

from pathlib import Path

from erk_shared.integrations.claude.abc import ClaudeSessionDetector


class FakeClaudeSessionDetector(ClaudeSessionDetector):
    """In-memory fake implementation for testing.

    This class has NO public setup methods. All state is provided via constructor.
    Test scenarios configure which directories have active sessions at construction time.
    """

    def __init__(self, active_sessions: set[Path] | None = None) -> None:
        """Create FakeClaudeSessionDetector with configured active session paths.

        Args:
            active_sessions: Set of paths that should be reported as having
                active Claude sessions. Defaults to empty set (no active sessions).
        """
        self._active_sessions: set[Path] = active_sessions if active_sessions is not None else set()
        self._check_calls: list[Path] = []

    @property
    def check_calls(self) -> list[Path]:
        """Get the list of directories that were checked.

        Returns list of paths passed to has_active_session().

        This property is for test assertions only.
        """
        return self._check_calls

    def has_active_session(self, directory: Path) -> bool:
        """Check if the given directory has an active Claude Code session.

        Returns True if the directory was configured as having an active session
        at construction time. Uses simple path comparison without filesystem access
        to work correctly with sentinel paths in tests.

        Args:
            directory: Path to check for active Claude sessions

        Returns:
            True if configured as having an active session, False otherwise
        """
        self._check_calls.append(directory)

        # Simple path comparison - no filesystem access (LBYL for sentinel paths)
        for session_path in self._active_sessions:
            # Check if directory is the same or a subdirectory of an active session
            if directory == session_path:
                return True
            # Also check if it's a prefix match (for sentinel paths in tests)
            if str(directory).startswith(str(session_path)):
                return True
        return False
