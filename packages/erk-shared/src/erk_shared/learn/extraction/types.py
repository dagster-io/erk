"""Types for session learn workflow."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SessionInfo:
    """Metadata for a session log file."""

    session_id: str
    path: Path
    size_bytes: int
    mtime_unix: float
    is_current: bool


@dataclass(frozen=True)
class BranchContext:
    """Git branch context for session selection behavior."""

    current_branch: str
    trunk_branch: str
    is_on_trunk: bool
