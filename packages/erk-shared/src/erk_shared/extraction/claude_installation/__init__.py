"""Claude installation abstraction layer.

This package provides a domain-driven interface for Claude installation operations.
All filesystem details are hidden behind the ClaudeInstallation ABC.
"""

from erk_shared.extraction.claude_installation.abc import (
    ClaudeInstallation,
    Session,
    SessionContent,
)
from erk_shared.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.extraction.claude_installation.real import (
    RealClaudeInstallation,
)

__all__ = [
    "ClaudeInstallation",
    "Session",
    "SessionContent",
    "RealClaudeInstallation",
    "FakeClaudeInstallation",
    "FakeProject",
    "FakeSessionData",
]
