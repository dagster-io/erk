"""Claude CLI execution abstraction.

This module provides abstraction over Claude CLI execution, enabling
dependency injection for testing without mock.patch.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# Constants for process execution
PROCESS_TIMEOUT_SECONDS = 600  # 10 minutes
STDERR_JOIN_TIMEOUT = 5.0  # 5 seconds (increased from 1.0)


@dataclass
class StreamEvent:
    """Event emitted during streaming execution.

    Attributes:
        event_type: Type of event:
            - "text": Text content from Claude
            - "tool": Tool usage summary
            - "spinner_update": Status update for spinner display
            - "pr_url": Pull request URL
            - "pr_number": Pull request number
            - "pr_title": Pull request title
            - "issue_number": GitHub issue number
            - "error": Error with non-zero exit code
            - "no_output": Claude CLI produced no output (diagnostic info)
            - "no_turns": Claude completed with num_turns=0 (likely hook blocking)
            - "process_error": Failed to start or timeout (Popen failure, timeout)
        content: The content of the event (text message, tool summary, spinner text,
            PR URL, PR number, PR title, issue number, or error/diagnostic details)
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

        Example:
            >>> executor = RealClaudeExecutor()
            >>> for event in executor.execute_command_streaming(
            ...     "/erk:plan-implement",
            ...     Path("/repos/my-project"),
            ...     dangerous=False
            ... ):
            ...     if event.event_type == "tool":
            ...         print(f"Tool: {event.content}")
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

        Example:
            >>> executor = RealClaudeExecutor()
            >>> result = executor.execute_command(
            ...     "/erk:plan-implement",
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
            elif event.event_type == "no_output":
                error_message = event.content
                success = False
            elif event.event_type == "no_turns":
                error_message = event.content
                success = False
            elif event.event_type == "process_error":
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
    def execute_interactive_command(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool = False,
    ) -> int:
        """Execute Claude CLI interactively with a command, returning exit code.

        Unlike execute_interactive(), this method runs Claude in a subprocess
        and returns control to the caller after completion. The user can
        interact with Claude during execution.

        Args:
            command: The slash command to execute (e.g., "/erk:create-extraction-plan")
            worktree_path: Path to worktree directory to run in
            dangerous: Whether to skip permission prompts

        Returns:
            Exit code from the Claude CLI process (0 = success)

        Raises:
            RuntimeError: If Claude CLI is not available

        Example:
            >>> executor = RealClaudeExecutor()
            >>> exit_code = executor.execute_interactive_command(
            ...     "/erk:create-extraction-plan",
            ...     Path("/repos/my-project"),
            ...     dangerous=True,
            ... )
            >>> if exit_code == 0:
            ...     print("Extraction plan created successfully")
        """
        ...


class RealClaudeExecutor(ClaudeExecutor):
    """Production implementation using subprocess and Claude CLI."""

    def is_claude_available(self) -> bool:
        """Check if Claude CLI is in PATH using shutil.which."""
        return shutil.which("claude") is not None

    def execute_command_streaming(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
    ) -> Iterator[StreamEvent]:
        """Execute Claude CLI command and yield StreamEvents in real-time.

        Implementation details:
        - Uses subprocess.Popen() for streaming stdout line-by-line
        - Passes --permission-mode acceptEdits, --output-format stream-json
        - Optionally passes --dangerously-skip-permissions when dangerous=True
        - In verbose mode: streams output to terminal (no parsing, no events yielded)
        - In filtered mode: parses stream-json and yields events in real-time
        - In debug mode: emits additional debug information to stderr
        """
        cmd_args = [
            "claude",
            "--print",
            "--verbose",
            "--permission-mode",
            "acceptEdits",
            "--output-format",
            "stream-json",
        ]
        if dangerous:
            cmd_args.append("--dangerously-skip-permissions")
        cmd_args.append(command)

        if verbose:
            # Verbose mode - stream to terminal, no parsing, no events
            result = subprocess.run(cmd_args, cwd=worktree_path, check=False)

            if result.returncode != 0:
                error_msg = f"Claude command {command} failed with exit code {result.returncode}"
                yield StreamEvent("error", error_msg)
            return

        # Filtered mode - streaming with real-time parsing
        if debug:
            print(f"[DEBUG executor] Starting Popen with args: {cmd_args}", file=sys.stderr)
            print(f"[DEBUG executor] cwd: {worktree_path}", file=sys.stderr)
            sys.stderr.flush()

        # Handle Popen errors (e.g., claude not found, permission denied)
        try:
            process = subprocess.Popen(
                cmd_args,
                cwd=worktree_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )
        except OSError as e:
            yield StreamEvent(
                "process_error",
                f"Failed to start Claude CLI: {e}\nCommand: {' '.join(cmd_args)}",
            )
            return

        if debug:
            print(f"[DEBUG executor] Popen started, pid={process.pid}", file=sys.stderr)
            sys.stderr.flush()

        stderr_output: list[str] = []

        # Capture stderr in background thread
        def capture_stderr() -> None:
            if process.stderr:
                for line in process.stderr:
                    stderr_output.append(line)

        stderr_thread = threading.Thread(target=capture_stderr, daemon=True)
        stderr_thread.start()

        # Process stdout line by line in real-time
        line_count = 0
        if debug:
            print("[DEBUG executor] Starting to read stdout...", file=sys.stderr)
            sys.stderr.flush()
        if process.stdout:
            for line in process.stdout:
                line_count += 1
                if debug:
                    print(
                        f"[DEBUG executor] Line #{line_count}: {line[:100]!r}...", file=sys.stderr
                    )
                    sys.stderr.flush()
                if not line.strip():
                    continue

                # Try to parse as JSON
                parsed = self._parse_stream_json_line(line, worktree_path, command)
                if parsed is None:
                    if debug:
                        print(
                            f"[DEBUG executor] Line #{line_count} parsed to None", file=sys.stderr
                        )
                        sys.stderr.flush()
                    continue

                if debug:
                    print(f"[DEBUG executor] Line #{line_count} parsed: {parsed}", file=sys.stderr)
                    sys.stderr.flush()

                # Yield text content and extract metadata from it
                text_content = parsed.get("text_content")
                if text_content is not None and isinstance(text_content, str):
                    yield StreamEvent("text", text_content)

                    # Also try to extract PR metadata from text (simpler than nested JSON)
                    from erk.core.output_filter import extract_pr_metadata_from_text

                    text_metadata = extract_pr_metadata_from_text(text_content)
                    if text_metadata.get("pr_url"):
                        yield StreamEvent("pr_url", str(text_metadata["pr_url"]))
                    if text_metadata.get("pr_number"):
                        yield StreamEvent("pr_number", str(text_metadata["pr_number"]))
                    if text_metadata.get("pr_title"):
                        yield StreamEvent("pr_title", str(text_metadata["pr_title"]))
                    if text_metadata.get("issue_number"):
                        yield StreamEvent("issue_number", str(text_metadata["issue_number"]))

                # Yield tool summaries
                tool_summary = parsed.get("tool_summary")
                if tool_summary is not None and isinstance(tool_summary, str):
                    yield StreamEvent("tool", tool_summary)

                # Yield spinner updates
                spinner_text = parsed.get("spinner_update")
                if spinner_text is not None and isinstance(spinner_text, str):
                    yield StreamEvent("spinner_update", spinner_text)

                # Yield PR URL
                pr_url_value = parsed.get("pr_url")
                if pr_url_value is not None:
                    yield StreamEvent("pr_url", str(pr_url_value))

                # Yield PR number
                pr_number_value = parsed.get("pr_number")
                if pr_number_value is not None:
                    yield StreamEvent("pr_number", str(pr_number_value))

                # Yield PR title
                pr_title_value = parsed.get("pr_title")
                if pr_title_value is not None:
                    yield StreamEvent("pr_title", str(pr_title_value))

                # Yield issue number
                issue_number_value = parsed.get("issue_number")
                if issue_number_value is not None:
                    yield StreamEvent("issue_number", str(issue_number_value))

                # Detect zero-turn completions (hook blocking)
                num_turns = parsed.get("num_turns")
                if num_turns is not None and num_turns == 0:
                    diag = f"Claude command {command} completed without processing"
                    diag += "\n  This usually means a hook blocked the command"
                    diag += "\n  Run 'claude' directly to see hook error messages"
                    diag += f"\n  Working directory: {worktree_path}"
                    yield StreamEvent("no_turns", diag)

        if debug:
            print(
                f"[DEBUG executor] stdout reading complete, total lines: {line_count}",
                file=sys.stderr,
            )
            sys.stderr.flush()

        # Wait for process to complete with timeout
        try:
            returncode = process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            yield StreamEvent(
                "process_error",
                f"Claude command {command} timed out after {PROCESS_TIMEOUT_SECONDS // 60} minutes",
            )
            return

        # Wait for stderr thread to finish with increased timeout
        stderr_thread.join(timeout=STDERR_JOIN_TIMEOUT)

        # Detect no output condition - yield before checking exit code
        if line_count == 0:
            diag = f"Claude command {command} completed but produced no output"
            diag += f"\n  Exit code: {returncode}"
            diag += f"\n  Working directory: {worktree_path}"
            if stderr_output:
                diag += "\n  Stderr:\n" + "".join(stderr_output)
            yield StreamEvent("no_output", diag)

            if returncode != 0:
                yield StreamEvent("error", f"Exit code {returncode}")
            return

        # Enhanced error messages for non-zero exit codes
        if returncode != 0:
            error_msg = f"Claude command {command} failed"
            error_msg += f"\n  Exit code: {returncode}"
            error_msg += f"\n  Lines processed: {line_count}"
            if stderr_output:
                error_msg += "\n  Stderr:\n" + "".join(stderr_output).strip()
            yield StreamEvent("error", error_msg)

        # Debug summary
        if debug:
            print("[DEBUG executor] === Summary ===", file=sys.stderr)
            print(f"[DEBUG executor] Exit code: {returncode}", file=sys.stderr)
            print(f"[DEBUG executor] Lines: {line_count}", file=sys.stderr)
            if stderr_output:
                print(f"[DEBUG executor] Stderr: {''.join(stderr_output)}", file=sys.stderr)
            sys.stderr.flush()

    def _parse_stream_json_line(
        self, line: str, worktree_path: Path, command: str
    ) -> dict[str, str | int | bool | None] | None:
        """Parse a single stream-json line and extract relevant information.

        Args:
            line: JSON line from stream-json output
            worktree_path: Path to worktree for relativizing paths
            command: The slash command being executed

        Returns:
            Dict with text_content, tool_summary, spinner_update, pr_url, pr_number,
            pr_title, and issue_number keys, or None if not JSON
        """
        # Import here to avoid circular dependency
        from erk.core.output_filter import (
            determine_spinner_status,
            extract_pr_metadata,
            extract_text_content,
            summarize_tool_use,
        )

        if not line.strip():
            return None

        # Parse JSON safely - JSON parsing requires exception handling
        data: dict | None = None
        if line.strip():
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    data = parsed
            except json.JSONDecodeError:
                return None

        if data is None:
            return None

        result: dict[str, str | int | bool | None] = {
            "text_content": None,
            "tool_summary": None,
            "spinner_update": None,
            "pr_url": None,
            "pr_number": None,
            "pr_title": None,
            "issue_number": None,
            "num_turns": None,
            "is_error": None,
            "result_text": None,
        }

        # stream-json format uses "type": "assistant" with nested "message" object
        # (not "type": "assistant_message" with content at top level)
        msg_type = data.get("type")
        message = data.get("message", {})
        if not isinstance(message, dict):
            message = {}

        # Extract text from assistant messages
        if msg_type == "assistant":
            text = extract_text_content(message)
            if text:
                result["text_content"] = text

            # Extract tool summaries and spinner updates
            content = message.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        summary = summarize_tool_use(item, worktree_path)
                        if summary:
                            result["tool_summary"] = summary

                        # Generate spinner update for all tools (even suppressible ones)
                        spinner_text = determine_spinner_status(item, command, worktree_path)
                        result["spinner_update"] = spinner_text
                        break

        # Extract PR metadata from tool results
        if msg_type == "user":
            content = message.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        tool_content = item.get("content")
                        # Handle both string and list formats
                        # String format: raw JSON string
                        # List format: [{"type": "text", "text": "..."}]
                        content_str: str | None = None
                        if isinstance(tool_content, str):
                            content_str = tool_content
                        elif isinstance(tool_content, list):
                            # Extract text from list of content items
                            for content_item in tool_content:
                                is_text_item = (
                                    isinstance(content_item, dict)
                                    and content_item.get("type") == "text"
                                )
                                if is_text_item:
                                    text = content_item.get("text")
                                    if isinstance(text, str):
                                        content_str = text
                                        break
                        if content_str is not None:
                            pr_metadata = extract_pr_metadata(content_str)
                            if pr_metadata.get("pr_url"):
                                result["pr_url"] = pr_metadata["pr_url"]
                                result["pr_number"] = pr_metadata["pr_number"]
                                result["pr_title"] = pr_metadata["pr_title"]
                                result["issue_number"] = pr_metadata.get("issue_number")
                                break

        # Parse type: result messages for num_turns (hook blocking detection)
        if msg_type == "result":
            num_turns = data.get("num_turns")
            if num_turns is not None:
                result["num_turns"] = num_turns
            result["is_error"] = data.get("is_error", False)
            result_text = data.get("result")
            if result_text is not None:
                result["result_text"] = result_text

        return result

    def execute_interactive(self, worktree_path: Path, dangerous: bool) -> None:
        """Execute Claude CLI in interactive mode by replacing current process.

        Implementation details:
        - Verifies Claude CLI is available
        - Changes to worktree directory
        - Builds command arguments with /erk:plan-implement
        - Replaces current process using os.execvp

        Note:
            This function never returns - the process is replaced by Claude CLI.
        """
        # Verify Claude is available
        if not self.is_claude_available():
            raise RuntimeError("Claude CLI not found\nInstall from: https://claude.com/download")

        # Change to worktree directory
        os.chdir(worktree_path)

        # Build command arguments
        cmd_args = ["claude", "--permission-mode", "acceptEdits"]
        if dangerous:
            cmd_args.append("--dangerously-skip-permissions")
        cmd_args.append("/erk:plan-implement")

        # Replace current process with Claude
        os.execvp("claude", cmd_args)
        # Never returns - process is replaced

    def execute_interactive_command(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool = False,
    ) -> int:
        """Execute Claude CLI interactively with a command, returning exit code.

        Implementation details:
        - Verifies Claude CLI is available
        - Uses subprocess.run() so control returns after Claude exits
        - No output capture - user sees and interacts with Claude directly
        """
        # Verify Claude is available
        if not self.is_claude_available():
            raise RuntimeError("Claude CLI not found\nInstall from: https://claude.com/download")

        # Build command arguments
        cmd_args = ["claude", "--permission-mode", "acceptEdits"]
        if dangerous:
            cmd_args.append("--dangerously-skip-permissions")
        cmd_args.append(command)

        # Run Claude interactively (no output capture)
        result = subprocess.run(cmd_args, cwd=worktree_path, check=False)
        return result.returncode
