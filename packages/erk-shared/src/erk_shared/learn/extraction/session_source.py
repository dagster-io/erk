"""Session source abstraction for learn workflow.

This module provides an abstraction layer over session source metadata,
enabling the learn workflow to handle both local sessions (from ~/.claude)
and remote sessions (from GitHub Actions artifacts) uniformly.

The key insight is that session *files* are always local during processing
(remote sessions get downloaded first), but we need to track *where* they
came from for proper attribution and filtering.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, TypedDict


class SessionSourceDict(TypedDict):
    """TypedDict for serialized SessionSource data."""

    source_type: str
    session_id: str
    run_id: str | None
    path: str | None


class SessionSource(ABC):
    """Abstract base class describing where a session came from.

    All implementations must provide:
    - source_type: Identifier for the source (e.g., "local", "remote")
    - session_id: The Claude Code session ID
    - run_id: Optional GitHub Actions run ID (for remote sessions)
    - path: Optional file path where the session is located

    Design note: Sessions are always processed locally (files on disk).
    This abstraction tracks the *origin* of those files, not where they
    currently reside. Remote sessions are downloaded before processing.
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier.

        Returns:
            "local" for local sessions, "remote" for downloaded sessions
        """

    @property
    @abstractmethod
    def session_id(self) -> str:
        """Return the Claude Code session ID.

        Returns:
            Session ID string (e.g., "abc-123-def-456")
        """

    @property
    @abstractmethod
    def run_id(self) -> str | None:
        """Return the GitHub Actions run ID if applicable.

        Returns:
            Run ID string for remote sessions, None for local sessions
        """

    @property
    @abstractmethod
    def path(self) -> str | None:
        """Return the file path where the session is located.

        Returns:
            File path string for sessions with known locations, None otherwise.
            For local sessions, this is populated when the session is discovered.
            For remote sessions, this is None until the session is downloaded.
        """

    def to_dict(self) -> SessionSourceDict:
        """Serialize to a dictionary for JSON output.

        Returns:
            Dictionary with source_type, session_id, run_id, and path.
        """
        return SessionSourceDict(
            source_type=self.source_type,
            session_id=self.session_id,
            run_id=self.run_id,
            path=self.path,
        )


SessionSourceType = Literal["local", "remote"]


@dataclass(frozen=True)
class LocalSessionSource(SessionSource):
    """Session source for locally-available sessions.

    Local sessions are those found in ~/.claude/projects/ on the machine
    where learn is running. They have no associated GitHub Actions run.

    Attributes:
        _session_id: The Claude Code session ID
        _path: Optional file path where the session is located
    """

    _session_id: str
    _path: str | None = None

    @property
    def source_type(self) -> Literal["local"]:
        """Return 'local' for local sessions."""
        return "local"

    @property
    def session_id(self) -> str:
        """Return the session ID."""
        return self._session_id

    @property
    def run_id(self) -> None:
        """Return None - local sessions have no run ID."""
        return None

    @property
    def path(self) -> str | None:
        """Return the file path where the session is located."""
        return self._path


@dataclass(frozen=True)
class RemoteSessionSource(SessionSource):
    """Session source for sessions downloaded from GitHub Actions artifacts.

    Remote sessions are those that originated from a GitHub Actions workflow
    run. They have an associated run ID that can be used to fetch additional
    details or link back to the original run.

    Attributes:
        _session_id: The Claude Code session ID
        _run_id: The GitHub Actions run ID that produced this session
        _path: Optional file path, populated after the session artifact is downloaded.
               None when remote session is discovered but not yet downloaded.
    """

    _session_id: str
    _run_id: str
    _path: str | None = None

    @property
    def source_type(self) -> Literal["remote"]:
        """Return 'remote' for remote sessions."""
        return "remote"

    @property
    def session_id(self) -> str:
        """Return the session ID."""
        return self._session_id

    @property
    def run_id(self) -> str:
        """Return the GitHub Actions run ID."""
        return self._run_id

    @property
    def path(self) -> str | None:
        """Return the file path where the session is located.

        Returns:
            File path string after the session artifact is downloaded,
            None if the session has not been downloaded yet.
        """
        return self._path
