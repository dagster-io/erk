"""Claude CLI executor integration.

Provides abstraction over Claude CLI execution for both general command
execution (streaming, interactive) and specific AI generation tasks.
"""

from erk_shared.integrations.claude.abc import (
    ClaudeExecutor,
    CommandResult,
    CommitMessageResult,
    StreamEvent,
)
from erk_shared.integrations.claude.fake import (
    ExecuteCommandCall,
    ExecuteInteractiveCall,
    FakeClaudeExecutor,
    GenerateCommitMessageCall,
)
from erk_shared.integrations.claude.real import RealClaudeExecutor

__all__ = [
    # ABC and types
    "ClaudeExecutor",
    "CommandResult",
    "CommitMessageResult",
    "StreamEvent",
    # Real implementation
    "RealClaudeExecutor",
    # Fake for testing
    "FakeClaudeExecutor",
    "GenerateCommitMessageCall",
    "ExecuteCommandCall",
    "ExecuteInteractiveCall",
]
