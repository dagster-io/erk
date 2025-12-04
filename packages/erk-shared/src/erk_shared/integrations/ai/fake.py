"""Fake implementation of AI executor for testing.

Provides a test double that returns configurable responses and tracks
calls for assertion in tests. Follows the constructor injection pattern.
"""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.integrations.ai.abc import ClaudeCLIExecutor, CommitMessageResult


@dataclass
class GenerateCommitMessageCall:
    """Record of a call to generate_commit_message.

    Captures all arguments for test assertions.
    """

    diff_file: Path
    repo_root: Path
    current_branch: str
    parent_branch: str


class FakeClaudeCLIExecutor(ClaudeCLIExecutor):
    """Test double for AI generation.

    Configured via constructor with fixed responses. Tracks all calls
    for test assertions via read-only properties.
    """

    def __init__(
        self,
        *,
        title: str = "Test PR title",
        body: str = "Test PR body",
        should_raise: Exception | None = None,
    ) -> None:
        """Initialize with configured response.

        Args:
            title: Title to return from generate_commit_message
            body: Body to return from generate_commit_message
            should_raise: If set, raise this exception instead of returning
        """
        self._title = title
        self._body = body
        self._should_raise = should_raise
        self._calls: list[GenerateCommitMessageCall] = []

    def generate_commit_message(
        self,
        diff_file: Path,
        repo_root: Path,
        current_branch: str,
        parent_branch: str,
    ) -> CommitMessageResult:
        """Return configured response and record call."""
        self._calls.append(
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

    @property
    def generate_commit_message_calls(self) -> list[GenerateCommitMessageCall]:
        """Read-only access to recorded calls for test assertions."""
        return list(self._calls)

    @property
    def call_count(self) -> int:
        """Number of calls made to generate_commit_message."""
        return len(self._calls)
