"""Session source abstraction for learn workflow.

This module provides an abstraction layer over session source metadata,
enabling the learn workflow to handle both local sessions (from ~/.claude)
and remote sessions (from GitHub Actions artifacts) uniformly.

The key insight is that session *files* are always local during processing
(remote sessions get downloaded first), but we need to track *where* they
came from for proper attribution and filtering.
"""

from abc import ABC, abstractmethod
from typing import Literal, TypedDict


class SessionSourceDict(TypedDict):
    """TypedDict for serialized SessionSource data."""

    source_type: str
    session_id: str
    run_id: str | None
    path: str | None
    gist_url: str | None


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

    @property
    @abstractmethod
    def gist_url(self) -> str | None:
        """Return the gist URL where the session JSONL is stored.

        Returns:
            Gist raw URL for remote sessions uploaded via gist, None otherwise.
        """

    def to_dict(self) -> SessionSourceDict:
        """Serialize to a dictionary for JSON output.

        Returns:
            Dictionary with source_type, session_id, run_id, path, and gist_url.
        """
        return SessionSourceDict(
            source_type=self.source_type,
            session_id=self.session_id,
            run_id=self.run_id,
            path=self.path,
            gist_url=self.gist_url,
        )


SessionSourceType = Literal["local", "remote"]


class LocalSessionSource(SessionSource):
    """Session source for locally-available sessions.

    Local sessions are those found in ~/.claude/projects/ on the machine
    where learn is running. They have no associated GitHub Actions run.

    Attributes:
        session_id: The Claude Code session ID
        path: Optional file path where the session is located
    """

    __slots__ = ("_session_id", "_path")

    _session_id: str
    _path: str | None

    def __init__(self, *, session_id: str, path: str | None) -> None:
        self._session_id = session_id
        self._path = path

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

    @property
    def gist_url(self) -> None:
        """Return None - local sessions have no gist URL."""
        return None


class RemoteSessionSource(SessionSource):
    """Session source for sessions from remote implementations.

    Remote sessions are those that originated from a GitHub Actions workflow
    run or other remote execution environment. They can be retrieved via:
    - Gist URL (preferred): Direct download from gist raw URL
    - Artifact (legacy): Download from GitHub Actions artifact using run_id

    Attributes:
        session_id: The Claude Code session ID
        run_id: The GitHub Actions run ID (optional for gist-based sessions)
        path: Optional file path, populated after the session is downloaded.
              None when remote session is discovered but not yet downloaded.
        gist_url: Optional gist raw URL for direct download (preferred method)
    """

    __slots__ = ("_session_id", "_run_id", "_path", "_gist_url")

    _session_id: str
    _run_id: str | None
    _path: str | None
    _gist_url: str | None

    def __init__(
        self,
        *,
        session_id: str,
        run_id: str | None,
        path: str | None,
        gist_url: str | None,
    ) -> None:
        self._session_id = session_id
        self._run_id = run_id
        self._path = path
        self._gist_url = gist_url

    @property
    def source_type(self) -> Literal["remote"]:
        """Return 'remote' for remote sessions."""
        return "remote"

    @property
    def session_id(self) -> str:
        """Return the session ID."""
        return self._session_id

    @property
    def run_id(self) -> str | None:
        """Return the GitHub Actions run ID if available."""
        return self._run_id

    @property
    def path(self) -> str | None:
        """Return the file path where the session is located.

        Returns:
            File path string after the session is downloaded,
            None if the session has not been downloaded yet.
        """
        return self._path

    @property
    def gist_url(self) -> str | None:
        """Return the gist raw URL for direct download.

        Returns:
            Gist raw URL if the session was uploaded to gist, None otherwise.
        """
        return self._gist_url
