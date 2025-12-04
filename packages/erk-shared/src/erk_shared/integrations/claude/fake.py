"""Fake implementation of Claude executor for testing.

Provides a test double that returns configurable responses and tracks
calls for assertion in tests. Follows the constructor injection pattern.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from erk_shared.integrations.claude.abc import (
    ClaudeExecutor,
    CommitMessageResult,
    StreamEvent,
)


@dataclass
class GenerateCommitMessageCall:
    """Record of a call to generate_commit_message.

    Captures all arguments for test assertions.
    """

    diff_file: Path
    repo_root: Path
    current_branch: str
    parent_branch: str


@dataclass
class ExecuteCommandCall:
    """Record of a call to execute_command or execute_command_streaming.

    Captures all arguments for test assertions.
    """

    command: str
    worktree_path: Path
    dangerous: bool
    verbose: bool = False


@dataclass
class ExecuteInteractiveCall:
    """Record of a call to execute_interactive.

    Captures all arguments for test assertions.
    """

    worktree_path: Path
    dangerous: bool


class FakeClaudeExecutor(ClaudeExecutor):
    """Test double for Claude CLI execution.

    Configured via constructor with fixed responses. Tracks all calls
    for test assertions via read-only properties.
    """

    def __init__(
        self,
        *,
        # generate_commit_message responses
        title: str = "Test PR title",
        body: str = "Test PR body",
        should_raise: Exception | None = None,
        # execute_command responses
        command_events: list[StreamEvent] | None = None,
        # is_claude_available response
        claude_available: bool = True,
    ) -> None:
        """Initialize with configured responses.

        Args:
            title: Title to return from generate_commit_message
            body: Body to return from generate_commit_message
            should_raise: If set, raise this exception from generate_commit_message
            command_events: Events to yield from execute_command_streaming
            claude_available: Value to return from is_claude_available
        """
        self._title = title
        self._body = body
        self._should_raise = should_raise
        self._command_events = command_events or []
        self._claude_available = claude_available
        self._commit_message_calls: list[GenerateCommitMessageCall] = []
        self._execute_command_calls: list[ExecuteCommandCall] = []
        self._execute_interactive_calls: list[ExecuteInteractiveCall] = []

    def is_claude_available(self) -> bool:
        """Return configured availability."""
        return self._claude_available

    def execute_command_streaming(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
    ) -> Iterator[StreamEvent]:
        """Return configured events and record call."""
        self._execute_command_calls.append(
            ExecuteCommandCall(
                command=command,
                worktree_path=worktree_path,
                dangerous=dangerous,
                verbose=verbose,
            )
        )
        yield from self._command_events

    def execute_interactive(self, worktree_path: Path, dangerous: bool) -> None:
        """Record call (does not actually replace process in tests)."""
        self._execute_interactive_calls.append(
            ExecuteInteractiveCall(
                worktree_path=worktree_path,
                dangerous=dangerous,
            )
        )

    def generate_commit_message(
        self,
        diff_file: Path,
        repo_root: Path,
        current_branch: str,
        parent_branch: str,
    ) -> CommitMessageResult:
        """Return configured response and record call."""
        self._commit_message_calls.append(
            GenerateCommitMessageCall(
                diff_file=diff_file,
                repo_root=repo_root,
                current_branch=current_branch,
                parent_branch=parent_branch,
            )
        )

        if self._should_raise is not None:
            raise self._should_raise

        return CommitMessageResult(title=self._title, body=self._body)

    # Read-only properties for test assertions

    @property
    def generate_commit_message_calls(self) -> list[GenerateCommitMessageCall]:
        """Read-only access to recorded generate_commit_message calls."""
        return list(self._commit_message_calls)

    @property
    def execute_command_calls(self) -> list[ExecuteCommandCall]:
        """Read-only access to recorded execute_command calls."""
        return list(self._execute_command_calls)

    @property
    def execute_interactive_calls(self) -> list[ExecuteInteractiveCall]:
        """Read-only access to recorded execute_interactive calls."""
        return list(self._execute_interactive_calls)

    @property
    def call_count(self) -> int:
        """Number of calls made to generate_commit_message."""
        return len(self._commit_message_calls)
