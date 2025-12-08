"""Claude Code session store abstraction layer.

This package provides a domain-driven interface for Claude Code session operations.
All filesystem details are hidden behind the ClaudeCodeSessionStore ABC.
"""

from erk_shared.extraction.claude_code_session_store.abc import (
    ClaudeCodeSessionStore,
    Session,
    SessionContent,
)
from erk_shared.extraction.claude_code_session_store.fake import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)
from erk_shared.extraction.claude_code_session_store.real import (
    RealClaudeCodeSessionStore,
)

__all__ = [
    "ClaudeCodeSessionStore",
    "Session",
    "SessionContent",
    "RealClaudeCodeSessionStore",
    "FakeClaudeCodeSessionStore",
    "FakeProject",
    "FakeSessionData",
]
