"""Claude CLI execution abstraction - ABC and types.

This module provides the abstract interface and typed events for Claude CLI execution.
The real implementation (RealClaudeExecutor) remains in erk.core.claude_executor.
"""

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# Typed Claude CLI Events
# =============================================================================


@dataclass(frozen=True)
class TextEvent:
    """Text content from Claude."""

    content: str


@dataclass(frozen=True)
class ToolEvent:
    """Tool usage summary."""

    summary: str


@dataclass(frozen=True)
class SpinnerUpdateEvent:
    """Status update for spinner display."""

    status: str


@dataclass(frozen=True)
class PrUrlEvent:
    """Pull request URL."""

    url: str


@dataclass(frozen=True)
class PrNumberEvent:
    """Pull request number."""

    number: int


@dataclass(frozen=True)
class PrTitleEvent:
    """Pull request title."""

    title: str


@dataclass(frozen=True)
class IssueNumberEvent:
    """GitHub issue number."""

    number: int


@dataclass(frozen=True)
class ErrorEvent:
    """Error with non-zero exit code."""

    message: str


@dataclass(frozen=True)
class NoOutputEvent:
    """Claude CLI produced no output."""

    diagnostic: str


@dataclass(frozen=True)
class NoTurnsEvent:
    """Claude completed with num_turns=0 (hook blocking)."""

    diagnostic: str


@dataclass(frozen=True)
class ProcessErrorEvent:
    """Failed to start or timeout."""

    message: str


# Union type for all Claude events
ClaudeEvent = (
    TextEvent
    | ToolEvent
    | SpinnerUpdateEvent
    | PrUrlEvent
    | PrNumberEvent
    | PrTitleEvent
    | IssueNumberEvent
    | ErrorEvent
    | NoOutputEvent
    | NoTurnsEvent
    | ProcessErrorEvent
)


@dataclass(frozen=True)
class PromptResult:
    """Result of executing a single prompt.

    Attributes:
        success: Whether the prompt completed successfully
        output: The output text from Claude
        error: Error message if command failed, None otherwise
    """

    success: bool
    output: str
    error: str | None


@dataclass(frozen=True)
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


class ClaudeExecutor(ABC):
    """Abstract interface for Claude CLI execution.

    This abstraction enables testing without mock.patch by making Claude
    execution an injectable dependency.
    """

    @abstractmethod
    def is_claude_available(self) -> bool:
        """Check if Claude CLI is installed and available in PATH.

        Returns:
            True if Claude CLI is available, False otherwise.

        Example:
            >>> executor = RealClaudeExecutor()
            >>> if executor.is_claude_available():
            ...     print("Claude CLI is installed")
        """
        ...

    @abstractmethod
    def execute_command_streaming(
        self,
        *,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
        model: str | None = None,
    ) -> Iterator[ClaudeEvent]:
        """Execute Claude CLI command and yield typed events in real-time.

        Args:
            command: The slash command to execute (e.g., "/erk:system:impl-execute")
            worktree_path: Path to worktree directory to run command in
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output (True) or filtered output (False)
            debug: Whether to emit debug output for stream parsing
            model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI

        Yields:
            ClaudeEvent objects as they occur during execution

        Example:
            >>> executor = RealClaudeExecutor()
            >>> for event in executor.execute_command_streaming(
            ...     "/erk:system:impl-execute",
            ...     Path("/repos/my-project"),
            ...     dangerous=False
            ... ):
            ...     match event:
            ...         case ToolEvent(summary=s):
            ...             print(f"Tool: {s}")
        """
        ...

    def execute_command(
        self,
        *,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        model: str | None = None,
    ) -> CommandResult:
        """Execute Claude CLI command and return final result (non-streaming).

        This is a convenience method that collects all streaming events
        and returns a final CommandResult. Use execute_command_streaming()
        for real-time updates.

        Args:
            command: The slash command to execute (e.g., "/erk:system:impl-execute")
            worktree_path: Path to worktree directory to run command in
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output (True) or filtered output (False)
            model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI

        Returns:
            CommandResult containing success status, PR URL, duration, and messages

        Example:
            >>> executor = RealClaudeExecutor()
            >>> result = executor.execute_command(
            ...     "/erk:system:impl-execute",
            ...     Path("/repos/my-project"),
            ...     dangerous=False
            ... )
            >>> if result.success:
            ...     print(f"PR created: {result.pr_url}")
        """
        start_time = time.time()
        filtered_messages: list[str] = []
        pr_url: str | None = None
        pr_number: int | None = None
        pr_title: str | None = None
        issue_number: int | None = None
        error_message: str | None = None
        success = True

        for event in self.execute_command_streaming(
            command=command,
            worktree_path=worktree_path,
            dangerous=dangerous,
            verbose=verbose,
            model=model,
        ):
            match event:
                case TextEvent(content=text):
                    filtered_messages.append(text)
                case ToolEvent(summary=summary):
                    filtered_messages.append(summary)
                case PrUrlEvent(url=url):
                    pr_url = url
                case PrNumberEvent(number=num):
                    pr_number = num
                case PrTitleEvent(title=title):
                    pr_title = title
                case IssueNumberEvent(number=num):
                    issue_number = num
                case ErrorEvent(message=msg):
                    error_message = msg
                    success = False
                case NoOutputEvent(diagnostic=diag):
                    error_message = diag
                    success = False
                case NoTurnsEvent(diagnostic=diag):
                    error_message = diag
                    success = False
                case ProcessErrorEvent(message=msg):
                    error_message = msg
                    success = False
                case SpinnerUpdateEvent():
                    pass  # Spinner updates not captured in CommandResult

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
    def execute_interactive(
        self,
        *,
        worktree_path: Path,
        dangerous: bool,
        command: str,
        target_subpath: Path | None,
        model: str | None = None,
    ) -> None:
        """Execute Claude CLI in interactive mode by replacing current process.

        Args:
            worktree_path: Path to worktree directory to run in
            dangerous: Whether to skip permission prompts
            command: The slash command to execute (default: /erk:system:impl-execute)
            target_subpath: Optional subdirectory within worktree to start in.
                If provided and exists, Claude will start in that subdirectory
                instead of the worktree root. This preserves the user's relative
                directory position when switching worktrees.
            model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI

        Raises:
            RuntimeError: If Claude CLI is not available

        Note:
            In production (RealClaudeExecutor), this function never returns - the
            process is replaced by Claude CLI via os.execvp. In testing
            (FakeClaudeExecutor), this simulates the behavior without actually
            replacing the process.

        Example:
            >>> executor = RealClaudeExecutor()
            >>> executor.execute_interactive(
            ...     Path("/repos/my-project"),
            ...     dangerous=False
            ... )
            # Never returns in production - process is replaced
        """
        ...

    @abstractmethod
    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path | None,
        system_prompt: str | None,
    ) -> PromptResult:
        """Execute a single prompt and return the result.

        This is a simpler interface for single-shot prompts that don't need
        streaming. The prompt is sent to Claude CLI with --print flag and
        the result is returned synchronously.

        Args:
            prompt: The prompt text to send to Claude
            model: Model to use (e.g., "haiku" for speed/cost)
            tools: List of allowed tools (e.g., ["Read", "Bash"]) or None
            cwd: Working directory for the command or None
            system_prompt: System prompt to replace Claude Code's default, or None.
                When provided, uses --system-prompt flag to completely replace
                the default system prompt, enabling more deterministic behavior
                for narrow, single-shot tasks.

        Returns:
            PromptResult with success status and output text

        Example:
            >>> executor = RealClaudeExecutor()
            >>> result = executor.execute_prompt(
            ...     "Generate a commit message for this diff",
            ...     model="haiku",
            ... )
            >>> if result.success:
            ...     print(result.output)
        """
        ...
