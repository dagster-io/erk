"""Ops interface for Claude CLI execution."""

import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from erk.kits.cli.progress import command_status
from erk_kits.data.kits.command.scripts.command.formatting import (
    format_complex_parameter,
    format_string_parameter,
    format_string_result,
    format_structured_result,
)
from erk_kits.data.kits.command.scripts.command.message_parsing import (
    ToolResult,
    ToolUse,
    build_result_status_string,
    extract_text_from_assistant_message,
    extract_tool_results_from_user_message,
    extract_tool_uses_from_assistant_message,
)


@dataclass(frozen=True)
class CommandExecutionResult:
    """Result of command execution."""

    returncode: int


class ClaudeCliOps(ABC):
    """Abstract interface for executing Claude CLI commands."""

    @abstractmethod
    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        """Execute a Claude Code slash command.

        Args:
            command_name: Name of the command (e.g., "ensure-ci" or "gt:submit-branch")
            cwd: Working directory for execution
            json_output: Whether to use JSON output format

        Returns:
            CommandExecutionResult with exit code

        Raises:
            FileNotFoundError: If claude CLI binary not found
        """
        pass


class RealClaudeCliOps(ClaudeCliOps):
    """Real implementation using subprocess to invoke Claude CLI."""

    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        """Execute Claude CLI via subprocess with streaming output."""
        # Build claude CLI command - always use stream-json for real-time output
        cmd = [
            "claude",
            "--print",
            "--verbose",  # Required for stream-json with --print
            "--permission-mode",
            "bypassPermissions",
            "--setting-sources",
            "project",
            "--output-format",
            "stream-json",  # Always use streaming JSON for real-time output
            f"/{command_name}",
        ]

        # Execute with animated status spinner
        with command_status(command_name):
            # Execute Claude Code CLI with streaming output
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
            )

            # Stream output line by line, parsing JSONL format
            if process.stdout is not None:
                self._stream_jsonl_output(process.stdout)

            # Wait for process to complete
            returncode = process.wait()

        return CommandExecutionResult(returncode=returncode)

    def _stream_jsonl_output(self, stdout) -> None:
        """Stream and parse JSONL output from Claude CLI."""
        for line in stdout:
            try:
                msg = json.loads(line)
                msg_type = msg.get("type")

                if msg_type == "assistant":
                    self._handle_assistant_message(msg)
                elif msg_type == "user":
                    self._handle_user_message(msg)
                elif msg_type == "result":
                    self._handle_result_message(msg)
                # Skip system messages (internal metadata)

            except json.JSONDecodeError:
                # If JSON parsing fails, print raw line
                print(f"\n[Warning: Invalid JSON]: {line}", end="", flush=True)

    def _handle_assistant_message(self, msg: dict) -> None:
        """Handle assistant message with text and tool use."""
        # Extract and print text items
        for text in extract_text_from_assistant_message(msg):
            print(text, end="", flush=True)

        # Extract and display tool uses
        for tool_use in extract_tool_uses_from_assistant_message(msg):
            self._display_tool_use_info(tool_use)

    def _display_tool_use_info(self, tool_use: ToolUse) -> None:
        """Display tool invocation with parameters."""
        print(f"\n⚙️  Using {tool_use.name}", flush=True)

        if not tool_use.input_params:
            return

        for param_name, param_value in tool_use.input_params.items():
            self._display_parameter(param_name, param_value)

    def _display_parameter(self, param_name: str, param_value) -> None:
        """Display a single tool parameter with appropriate formatting."""
        if isinstance(param_value, str):
            self._display_string_parameter(param_name, param_value)
        elif isinstance(param_value, (list, dict)):
            self._display_complex_parameter(param_name, param_value)
        else:
            # For other types (int, bool, etc), show inline
            print(f"   {param_name}: {param_value}", flush=True)

    def _display_string_parameter(self, param_name: str, param_value: str) -> None:
        """Display string parameter (inline or multiline)."""
        for line in format_string_parameter(param_name, param_value):
            print(line, flush=True)

    def _display_complex_parameter(self, param_name: str, param_value) -> None:
        """Display complex parameter (list/dict) as formatted JSON."""
        for line in format_complex_parameter(param_name, param_value):
            print(line, flush=True)

    def _handle_user_message(self, msg: dict) -> None:
        """Handle user message with tool results."""
        for result in extract_tool_results_from_user_message(msg):
            self._display_tool_result_data(result)

    def _display_tool_result_data(self, result: ToolResult) -> None:
        """Display tool result data."""
        print("\n📤 Result:", flush=True)

        if isinstance(result.content, str):
            self._display_string_result(result.content)
        elif isinstance(result.content, list):
            self._display_structured_result(result.content)

        if result.is_error:
            print("   [Error result]", flush=True)

    def _display_string_result(self, result_content: str) -> None:
        """Display string result with indentation."""
        for line in format_string_result(result_content):
            print(line, flush=True)

    def _display_structured_result(self, result_content: list) -> None:
        """Display structured result content."""
        for line in format_structured_result(result_content):
            print(line, flush=True)

    def _handle_result_message(self, msg: dict) -> None:
        """Handle completion result message."""
        status_string = build_result_status_string(msg)
        print(status_string, flush=True)


class FakeClaudeCliOps(ClaudeCliOps):
    """Fake implementation for testing."""

    def __init__(self) -> None:
        """Initialize fake with tracking."""
        self._executions: list[tuple[str, Path, bool]] = []
        self._next_returncode: int = 0
        self._should_raise_file_not_found: bool = False

    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        """Record execution and return configured result."""
        self._executions.append((command_name, cwd, json_output))

        if self._should_raise_file_not_found:
            raise FileNotFoundError("claude CLI not found")

        return CommandExecutionResult(returncode=self._next_returncode)

    # Mutation tracking (read-only access for tests)

    @property
    def executions(self) -> list[tuple[str, Path, bool]]:
        """Return list of (command_name, cwd, json_output) tuples."""
        return list(self._executions)

    def get_execution_count(self) -> int:
        """Return number of executions."""
        return len(self._executions)

    def get_last_execution(self) -> tuple[str, Path, bool] | None:
        """Return last execution or None."""
        if not self._executions:
            return None
        return self._executions[-1]

    # Configuration methods for tests

    def set_next_returncode(self, returncode: int) -> None:
        """Configure the return code for next execution."""
        self._next_returncode = returncode

    def set_file_not_found_error(self, should_raise: bool) -> None:
        """Configure whether to raise FileNotFoundError."""
        self._should_raise_file_not_found = should_raise
