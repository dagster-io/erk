"""Fake implementation of ClaudeExecutor for testing.

This fake enables testing Claude command execution without
requiring the actual Claude CLI or using subprocess mocks.
"""

from collections.abc import Iterator
from pathlib import Path

from erk.core.claude_executor import ClaudeExecutor, CommandResult, StreamEvent


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
        >>> executor.execute_command("/erk:plan-implement", Path("/repo"), False)
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
        interactive_command_exit_code: int = 0,
        simulated_pr_url: str | None = None,
        simulated_pr_number: int | None = None,
        simulated_pr_title: str | None = None,
        simulated_issue_number: int | None = None,
        simulated_tool_events: list[str] | None = None,
        simulated_no_output: bool = False,
        simulated_zero_turns: bool = False,
        simulated_process_error: str | None = None,
    ) -> None:
        """Initialize fake with predetermined behavior.

        Args:
            claude_available: Whether Claude CLI should appear available
            command_should_fail: Whether execute_command should raise RuntimeError
            interactive_command_exit_code: Exit code to return from execute_interactive_command
            simulated_pr_url: PR URL to return in CommandResult (simulates successful PR creation)
            simulated_pr_number: PR number to return (simulates PR metadata)
            simulated_pr_title: PR title to return (simulates PR metadata)
            simulated_issue_number: Issue number to return (simulates linked issue)
            simulated_tool_events: Tool event contents to emit (e.g., "Using...")
            simulated_no_output: Whether to simulate Claude CLI producing no output
            simulated_zero_turns: Whether to simulate Claude completing with num_turns=0
                (hook blocking scenario)
            simulated_process_error: Error message to simulate process startup failure
        """
        self._claude_available = claude_available
        self._command_should_fail = command_should_fail
        self._interactive_command_exit_code = interactive_command_exit_code
        self._simulated_pr_url = simulated_pr_url
        self._simulated_pr_number = simulated_pr_number
        self._simulated_pr_title = simulated_pr_title
        self._simulated_issue_number = simulated_issue_number
        self._simulated_tool_events = simulated_tool_events or []
        self._simulated_no_output = simulated_no_output
        self._simulated_zero_turns = simulated_zero_turns
        self._simulated_process_error = simulated_process_error
        self._executed_commands: list[tuple[str, Path, bool, bool]] = []
        self._interactive_calls: list[tuple[Path, bool]] = []
        self._interactive_command_calls: list[tuple[str, Path, bool]] = []

    def is_claude_available(self) -> bool:
        """Return the availability configured at construction time."""
        return self._claude_available

    def execute_command_streaming(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
    ) -> Iterator[StreamEvent]:
        """Track command execution and yield simulated streaming events.

        This method records the call parameters for test assertions.
        It does not execute any actual subprocess operations.

        Args:
            command: The slash command to execute
            worktree_path: Path to worktree directory
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output or filtered output
            debug: Whether to emit debug output for stream parsing

        Yields:
            StreamEvent objects simulating command execution

        Raises:
            RuntimeError: If command_should_fail was set to True
        """
        self._executed_commands.append((command, worktree_path, dangerous, verbose))

        # Process error takes precedence (simulates Popen failure)
        if self._simulated_process_error is not None:
            yield StreamEvent("process_error", self._simulated_process_error)
            return

        # No output simulation (simulates Claude CLI producing no output)
        if self._simulated_no_output:
            yield StreamEvent(
                "no_output",
                f"Claude command {command} completed but produced no output",
            )
            return

        # Zero turns simulation (simulates hook blocking)
        if self._simulated_zero_turns:
            diag = f"Claude command {command} completed without processing"
            diag += "\n  This usually means a hook blocked the command"
            diag += "\n  Run 'claude' directly to see hook error messages"
            diag += f"\n  Working directory: {worktree_path}"
            yield StreamEvent("no_turns", diag)
            return

        if self._command_should_fail:
            yield StreamEvent("error", f"Claude command {command} failed (simulated failure)")
            return

        # Simulate some basic streaming events
        yield StreamEvent("text", "Starting execution...")
        yield StreamEvent("spinner_update", f"Running {command}...")

        # Yield any configured tool events
        for tool_event in self._simulated_tool_events:
            yield StreamEvent("tool", tool_event)

        yield StreamEvent("text", "Execution complete")

        # Yield PR metadata if configured
        if self._simulated_pr_url is not None:
            yield StreamEvent("pr_url", self._simulated_pr_url)
        if self._simulated_pr_number is not None:
            yield StreamEvent("pr_number", str(self._simulated_pr_number))
        if self._simulated_pr_title is not None:
            yield StreamEvent("pr_title", self._simulated_pr_title)
        if self._simulated_issue_number is not None:
            yield StreamEvent("issue_number", str(self._simulated_issue_number))

    def execute_command(
        self, command: str, worktree_path: Path, dangerous: bool, verbose: bool = False
    ) -> CommandResult:
        """Track command execution without running subprocess.

        This method records the call parameters for test assertions.
        It does not execute any actual subprocess operations.

        Args:
            command: The slash command to execute
            worktree_path: Path to worktree directory
            dangerous: Whether to skip permission prompts
            verbose: Whether to show raw output or filtered output

        Returns:
            CommandResult with success status

        Raises:
            RuntimeError: If command_should_fail was set to True
        """
        self._executed_commands.append((command, worktree_path, dangerous, verbose))

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

    def execute_interactive(self, worktree_path: Path, dangerous: bool) -> None:
        """Track interactive execution without replacing process.

        This method records the call parameters for test assertions.
        Unlike RealClaudeExecutor, this does not use os.execvp and returns
        normally to allow tests to continue.

        Raises:
            RuntimeError: If Claude CLI is not available
        """
        if not self._claude_available:
            raise RuntimeError("Claude CLI not found\nInstall from: https://claude.com/download")

        self._interactive_calls.append((worktree_path, dangerous))

    def execute_interactive_command(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool = False,
    ) -> int:
        """Track interactive command execution and return configured exit code.

        This method records the call parameters for test assertions.
        Unlike RealClaudeExecutor, this does not run an actual subprocess.

        Returns:
            The exit code configured via interactive_command_exit_code parameter

        Raises:
            RuntimeError: If Claude CLI is not available
        """
        if not self._claude_available:
            raise RuntimeError("Claude CLI not found\nInstall from: https://claude.com/download")

        self._interactive_command_calls.append((command, worktree_path, dangerous))
        return self._interactive_command_exit_code

    @property
    def executed_commands(self) -> list[tuple[str, Path, bool, bool]]:
        """Get the list of execute_command() calls that were made.

        Returns list of (command, worktree_path, dangerous, verbose) tuples.

        This property is for test assertions only.
        """
        return self._executed_commands.copy()

    @property
    def interactive_calls(self) -> list[tuple[Path, bool]]:
        """Get the list of execute_interactive() calls that were made.

        Returns list of (worktree_path, dangerous) tuples.

        This property is for test assertions only.
        """
        return self._interactive_calls.copy()

    @property
    def interactive_command_calls(self) -> list[tuple[str, Path, bool]]:
        """Get the list of execute_interactive_command() calls that were made.

        Returns list of (command, worktree_path, dangerous) tuples.

        This property is for test assertions only.
        """
        return self._interactive_command_calls.copy()
