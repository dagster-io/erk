"""Fake implementation of ClaudeExecutor for testing.

This fake enables testing Claude command execution without
requiring the actual Claude CLI or using subprocess mocks.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk_shared.context.types import ClaudePermissionMode

from erk.core.claude_executor import (
    ClaudeEvent,
    ClaudeExecutor,
    CommandResult,
    ErrorEvent,
    IssueNumberEvent,
    NoOutputEvent,
    NoTurnsEvent,
    PrNumberEvent,
    ProcessErrorEvent,
    PromptResult,
    PrTitleEvent,
    PrUrlEvent,
    SpinnerUpdateEvent,
    TextEvent,
    ToolEvent,
)


class FakeClaudeExecutor(ClaudeExecutor):
    """In-memory fake implementation of Claude CLI execution.

    Constructor Injection:
    - All state is provided via constructor parameters
    - Mutations are tracked in read-only properties

    When to Use:
    - Testing commands that execute Claude CLI (e.g., erk implement --no-interactive)
    - Simulating Claude CLI availability
    - Verifying command execution without actual subprocess calls

    Examples:
        # Test with Claude available and successful execution
        >>> executor = FakeClaudeExecutor(claude_available=True)
        >>> executor.execute_command("/erk:system:impl-execute", Path("/repo"), False)
        >>> assert len(executor.executed_commands) == 1

        # Test with Claude not available
        >>> executor = FakeClaudeExecutor(claude_available=False)
        >>> assert not executor.is_claude_available()

        # Test command failure
        >>> executor = FakeClaudeExecutor(command_should_fail=True)
        >>> try:
        ...     executor.execute_command("/bad-command", Path("/repo"), False)
        ... except RuntimeError:
        ...     print("Command failed as expected")

        # Test interactive execution
        >>> executor = FakeClaudeExecutor(claude_available=True)
        >>> executor.execute_interactive(Path("/repo"), dangerous=False)
        >>> assert len(executor.interactive_calls) == 1
    """

    def __init__(
        self,
        *,
        claude_available: bool = True,
        command_should_fail: bool = False,
        simulated_pr_url: str | None = None,
        simulated_pr_number: int | None = None,
        simulated_pr_title: str | None = None,
        simulated_issue_number: int | None = None,
        simulated_tool_events: list[str] | None = None,
        simulated_no_output: bool = False,
        simulated_zero_turns: bool = False,
        simulated_process_error: str | None = None,
        simulated_prompt_output: str | None = None,
        simulated_prompt_error: str | None = None,
        simulated_no_work_events: bool = False,
    ) -> None:
        """Initialize fake with predetermined behavior.

        Args:
            claude_available: Whether Claude CLI should appear available
            command_should_fail: Whether execute_command should raise RuntimeError
            simulated_pr_url: PR URL to return in CommandResult (simulates successful PR creation)
            simulated_pr_number: PR number to return (simulates PR metadata)
            simulated_pr_title: PR title to return (simulates PR metadata)
            simulated_issue_number: Issue number to return (simulates linked issue)
            simulated_tool_events: Tool event contents to emit (e.g., "Using...")
            simulated_no_output: Whether to simulate Claude CLI producing no output
            simulated_zero_turns: Whether to simulate Claude completing with num_turns=0
                (hook blocking scenario)
            simulated_process_error: Error message to simulate process startup failure
            simulated_prompt_output: Output to return from execute_prompt() on success.
                If None, defaults to "Test Title\n\nTest body"
            simulated_prompt_error: Error message to return from execute_prompt() on failure.
                If set, execute_prompt() will return a failure result.
            simulated_no_work_events: Whether to simulate Claude completing successfully
                but without emitting any work events (TextEvent or ToolEvent). This
                tests the "empty response" failure mode where Claude produces JSON
                but no actual work output.
        """
        self._claude_available = claude_available
        self._command_should_fail = command_should_fail
        self._simulated_pr_url = simulated_pr_url
        self._simulated_pr_number = simulated_pr_number
        self._simulated_pr_title = simulated_pr_title
        self._simulated_issue_number = simulated_issue_number
        self._simulated_tool_events = simulated_tool_events or []
        self._simulated_no_output = simulated_no_output
        self._simulated_zero_turns = simulated_zero_turns
        self._simulated_process_error = simulated_process_error
        self._simulated_prompt_output = simulated_prompt_output
        self._simulated_prompt_error = simulated_prompt_error
        self._simulated_no_work_events = simulated_no_work_events
        self._executed_commands: list[tuple[str, Path, bool, bool, str | None]] = []
        self._interactive_calls: list[tuple[Path, bool, str, Path | None, str | None, str]] = []
        self._prompt_calls: list[tuple[str, str | None]] = []

    def is_claude_available(self) -> bool:
        """Return the availability configured at construction time."""
        return self._claude_available

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
        """Track command execution and yield simulated typed events.

        This method records the call parameters for test assertions.
        It does not execute any actual subprocess operations.

        Args:
            command: The slash command to execute
            worktree_path: Path to worktree directory
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output or filtered output
            debug: Whether to emit debug output for stream parsing
            model: Optional model name (haiku, sonnet, opus) - recorded but not used

        Yields:
            ClaudeEvent objects simulating command execution

        Raises:
            RuntimeError: If command_should_fail was set to True
        """
        self._executed_commands.append((command, worktree_path, dangerous, verbose, model))

        # Process error takes precedence (simulates Popen failure)
        if self._simulated_process_error is not None:
            yield ProcessErrorEvent(message=self._simulated_process_error)
            return

        # No output simulation (simulates Claude CLI producing no output)
        if self._simulated_no_output:
            yield NoOutputEvent(
                diagnostic=f"Claude command {command} completed but produced no output"
            )
            return

        # Zero turns simulation (simulates hook blocking)
        if self._simulated_zero_turns:
            diag = f"Claude command {command} completed without processing"
            diag += "\n  This usually means a hook blocked the command"
            diag += "\n  Run 'claude' directly to see hook error messages"
            diag += f"\n  Working directory: {worktree_path}"
            yield NoTurnsEvent(diagnostic=diag)
            return

        if self._command_should_fail:
            yield ErrorEvent(message=f"Claude command {command} failed (simulated failure)")
            return

        # No work events simulation: emits only non-work events (spinner, metadata)
        # This tests the scenario where Claude completes but produces no output
        if self._simulated_no_work_events:
            yield SpinnerUpdateEvent(status=f"Running {command}...")
            yield SpinnerUpdateEvent(status="Completed")
            # Note: no TextEvent or ToolEvent emitted
            return

        # Simulate some basic streaming events
        yield TextEvent(content="Starting execution...")
        yield SpinnerUpdateEvent(status=f"Running {command}...")

        # Yield any configured tool events
        for tool_event in self._simulated_tool_events:
            yield ToolEvent(summary=tool_event)

        yield TextEvent(content="Execution complete")

        # Yield PR metadata if configured
        if self._simulated_pr_url is not None:
            yield PrUrlEvent(url=self._simulated_pr_url)
        if self._simulated_pr_number is not None:
            yield PrNumberEvent(number=self._simulated_pr_number)
        if self._simulated_pr_title is not None:
            yield PrTitleEvent(title=self._simulated_pr_title)
        if self._simulated_issue_number is not None:
            yield IssueNumberEvent(number=self._simulated_issue_number)

    def execute_command(
        self,
        *,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        model: str | None = None,
    ) -> CommandResult:
        """Track command execution without running subprocess.

        This method records the call parameters for test assertions.
        It does not execute any actual subprocess operations.

        Args:
            command: The slash command to execute
            worktree_path: Path to worktree directory
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output or filtered output
            model: Optional model name (ignored in fake)

        Returns:
            CommandResult with success status

        Raises:
            RuntimeError: If command_should_fail was set to True
        """
        self._executed_commands.append((command, worktree_path, dangerous, verbose, model))

        if self._command_should_fail:
            return CommandResult(
                success=False,
                pr_url=None,
                pr_number=None,
                pr_title=None,
                issue_number=None,
                duration_seconds=0.0,
                error_message=f"Claude command {command} failed (simulated failure)",
                filtered_messages=[],
            )

        return CommandResult(
            success=True,
            pr_url=self._simulated_pr_url,
            pr_number=self._simulated_pr_number,
            pr_title=self._simulated_pr_title,
            issue_number=self._simulated_issue_number,
            duration_seconds=0.0,
            error_message=None,
            filtered_messages=[],
        )

    def execute_interactive(
        self,
        *,
        worktree_path: Path,
        dangerous: bool,
        command: str,
        target_subpath: Path | None,
        model: str | None = None,
        permission_mode: ClaudePermissionMode = "acceptEdits",
    ) -> None:
        """Track interactive execution without replacing process.

        This method records the call parameters for test assertions.
        Unlike RealClaudeExecutor, this does not use os.execvp and returns
        normally to allow tests to continue.

        Raises:
            RuntimeError: If Claude CLI is not available
        """
        if not self._claude_available:
            raise RuntimeError("Claude CLI not found\nInstall from: https://claude.com/download")

        self._interactive_calls.append(
            (worktree_path, dangerous, command, target_subpath, model, permission_mode)
        )

    @property
    def executed_commands(self) -> list[tuple[str, Path, bool, bool, str | None]]:
        """Get the list of execute_command() calls that were made.

        Returns list of (command, worktree_path, dangerous, verbose, model) tuples.

        This property is for test assertions only.
        """
        return self._executed_commands.copy()

    @property
    def interactive_calls(
        self,
    ) -> list[tuple[Path, bool, str, Path | None, str | None, str]]:
        """Get the list of execute_interactive() calls that were made.

        Returns list of tuples:
        (worktree_path, dangerous, command, target_subpath, model, permission_mode)

        This property is for test assertions only.
        """
        return self._interactive_calls.copy()

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str,
        tools: list[str] | None,
        cwd: Path | None,
        system_prompt: str | None,
    ) -> PromptResult:
        """Track prompt execution and return simulated result.

        This method records the prompt and system_prompt for test assertions.
        It does not execute any actual subprocess operations.

        Args:
            prompt: The prompt text to send
            model: Model to use (ignored in fake)
            tools: Optional list of allowed tools (ignored in fake)
            cwd: Optional working directory (ignored in fake)
            system_prompt: Optional system prompt (tracked for test assertions)

        Returns:
            PromptResult with simulated output or error
        """
        self._prompt_calls.append((prompt, system_prompt))

        if self._simulated_prompt_error is not None:
            return PromptResult(
                success=False,
                output="",
                error=self._simulated_prompt_error,
            )

        # Default output if none specified
        output = self._simulated_prompt_output
        if output is None:
            output = "Test Title\n\nTest body"

        return PromptResult(
            success=True,
            output=output,
            error=None,
        )

    @property
    def prompt_calls(self) -> list[tuple[str, str | None]]:
        """Get the list of execute_prompt() calls that were made.

        Returns list of (prompt, system_prompt) tuples.

        This property is for test assertions only.
        """
        return self._prompt_calls.copy()
