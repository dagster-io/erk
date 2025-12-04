"""Abstract base class for Claude CLI execution.

Provides an abstraction over Claude CLI execution, enabling dependency
injection for testing without mock.patch. Combines general execution
(streaming, interactive) with specific AI generation tasks.
"""

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StreamEvent:
    """Event emitted during streaming execution.

    Attributes:
        event_type: Type of event ("text", "tool", "spinner_update", "pr_url",
            "pr_number", "pr_title", "issue_number", "error")
        content: The content of the event
    """

    event_type: str
    content: str


@dataclass
class CommandResult:
    """Result of executing a Claude CLI command.

    Attributes:
        success: Whether the command completed successfully
        pr_url: Pull request URL if one was created, None otherwise
        pr_number: Pull request number if one was created, None otherwise
        pr_title: Pull request title if one was created, None otherwise
        issue_number: GitHub issue number if one was linked, None otherwise
        duration_seconds: Execution time in seconds
        error_message: Error description if command failed, None otherwise
        filtered_messages: List of text messages and tool summaries for display
    """

    success: bool
    pr_url: str | None
    pr_number: int | None
    pr_title: str | None
    issue_number: int | None
    duration_seconds: float
    error_message: str | None
    filtered_messages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CommitMessageResult:
    """Result from generating a commit message.

    Attributes:
        title: The PR title (first line of commit message)
        body: The PR body (remaining lines of commit message)
    """

    title: str
    body: str


class ClaudeExecutor(ABC):
    """Abstract interface for Claude CLI execution.

    This abstraction enables testing without mock.patch by making Claude
    execution an injectable dependency. Combines general execution methods
    with specific AI generation tasks.
    """

    @abstractmethod
    def is_claude_available(self) -> bool:
        """Check if Claude CLI is installed and available in PATH.

        Returns:
            True if Claude CLI is available, False otherwise.
        """
        ...

    @abstractmethod
    def execute_command_streaming(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
    ) -> Iterator[StreamEvent]:
        """Execute Claude CLI command and yield StreamEvents in real-time.

        Args:
            command: The slash command to execute (e.g., "/erk:plan-implement")
            worktree_path: Path to worktree directory to run command in
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output (True) or filtered output (False)
            debug: Whether to emit debug output for stream parsing

        Yields:
            StreamEvent objects as they occur during execution
        """
        ...

    def execute_command(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
    ) -> CommandResult:
        """Execute Claude CLI command and return final result (non-streaming).

        This is a convenience method that collects all streaming events
        and returns a final CommandResult. Use execute_command_streaming()
        for real-time updates.

        Args:
            command: The slash command to execute (e.g., "/erk:plan-implement")
            worktree_path: Path to worktree directory to run command in
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output (True) or filtered output (False)

        Returns:
            CommandResult containing success status, PR URL, duration, and messages
        """
        start_time = time.time()
        filtered_messages: list[str] = []
        pr_url: str | None = None
        pr_number: int | None = None
        pr_title: str | None = None
        issue_number: int | None = None
        error_message: str | None = None
        success = True

        for event in self.execute_command_streaming(command, worktree_path, dangerous, verbose):
            if event.event_type == "text":
                filtered_messages.append(event.content)
            elif event.event_type == "tool":
                filtered_messages.append(event.content)
            elif event.event_type == "pr_url":
                pr_url = event.content
            elif event.event_type == "pr_number":
                # Convert string back to int - safe because we control the source
                if event.content.isdigit():
                    pr_number = int(event.content)
            elif event.event_type == "pr_title":
                pr_title = event.content
            elif event.event_type == "issue_number":
                # Convert string back to int - safe because we control the source
                if event.content.isdigit():
                    issue_number = int(event.content)
            elif event.event_type == "error":
                error_message = event.content
                success = False

        duration = time.time() - start_time
        return CommandResult(
            success=success,
            pr_url=pr_url,
            pr_number=pr_number,
            pr_title=pr_title,
            issue_number=issue_number,
            duration_seconds=duration,
            error_message=error_message,
            filtered_messages=filtered_messages,
        )

    @abstractmethod
    def execute_interactive(self, worktree_path: Path, dangerous: bool) -> None:
        """Execute Claude CLI in interactive mode by replacing current process.

        Args:
            worktree_path: Path to worktree directory to run in
            dangerous: Whether to skip permission prompts

        Raises:
            RuntimeError: If Claude CLI is not available

        Note:
            In production (RealClaudeExecutor), this function never returns - the
            process is replaced by Claude CLI via os.execvp. In testing
            (FakeClaudeExecutor), this simulates the behavior without actually
            replacing the process.
        """
        ...

    @abstractmethod
    def generate_commit_message(
        self,
        diff_file: Path,
        repo_root: Path,
        current_branch: str,
        parent_branch: str,
    ) -> CommitMessageResult:
        """Generate commit message from a diff file.

        Invokes an AI model to analyze the diff and produce a structured
        commit message suitable for a pull request.

        Args:
            diff_file: Path to the diff file to analyze
            repo_root: Repository root directory
            current_branch: Name of the current branch
            parent_branch: Name of the parent branch

        Returns:
            CommitMessageResult with title and body

        Raises:
            RuntimeError: If AI generation fails
        """
        ...
