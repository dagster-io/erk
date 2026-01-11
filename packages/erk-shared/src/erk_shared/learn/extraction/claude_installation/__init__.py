"""Claude installation abstraction layer.

This package provides a domain-driven interface for Claude installation operations.
All filesystem details are hidden behind the ClaudeInstallation ABC.

Import directly from submodules:
- abc: ClaudeInstallation, Session, SessionContent, FoundSession
- real: RealClaudeInstallation
- fake: FakeClaudeInstallation, FakeProject, FakeSessionData
"""

from erk_shared.learn.extraction.claude_installation.abc import (
    ClaudeInstallation,
    FoundSession,
    Session,
    SessionContent,
)
from erk_shared.learn.extraction.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)
from erk_shared.learn.extraction.claude_installation.real import (
    RealClaudeInstallation,
)

__all__ = [
    "ClaudeInstallation",
    "FoundSession",
    "Session",
    "SessionContent",
    "RealClaudeInstallation",
    "FakeClaudeInstallation",
    "FakeProject",
    "FakeSessionData",
]
