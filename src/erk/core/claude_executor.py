"""Claude CLI execution abstraction.

This module provides the RealClaudeExecutor implementation and re-exports
ABC and types from erk_shared.core for backward compatibility.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

# Re-export ABC and types from erk_shared.core for backward compatibility
from erk_shared.core.claude_executor import ClaudeEvent as ClaudeEvent
from erk_shared.core.claude_executor import ClaudeExecutor as ClaudeExecutor
from erk_shared.core.claude_executor import CommandResult as CommandResult
from erk_shared.core.claude_executor import ErrorEvent as ErrorEvent
from erk_shared.core.claude_executor import IssueNumberEvent as IssueNumberEvent
from erk_shared.core.claude_executor import NoOutputEvent as NoOutputEvent
from erk_shared.core.claude_executor import NoTurnsEvent as NoTurnsEvent
from erk_shared.core.claude_executor import PrNumberEvent as PrNumberEvent
from erk_shared.core.claude_executor import ProcessErrorEvent as ProcessErrorEvent
from erk_shared.core.claude_executor import PromptResult as PromptResult
from erk_shared.core.claude_executor import PrTitleEvent as PrTitleEvent
from erk_shared.core.claude_executor import PrUrlEvent as PrUrlEvent
from erk_shared.core.claude_executor import SpinnerUpdateEvent as SpinnerUpdateEvent
from erk_shared.core.claude_executor import TextEvent as TextEvent
from erk_shared.core.claude_executor import ToolEvent as ToolEvent

# Constants for process execution
PROCESS_TIMEOUT_SECONDS = 600  # 10 minutes
STDERR_JOIN_TIMEOUT = 5.0  # 5 seconds (increased from 1.0)

logger = logging.getLogger(__name__)


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
        model: str | None = None,
    ) -> Iterator[ClaudeEvent]:
        """Execute Claude CLI command and yield typed events in real-time.

        Implementation details:
        - Uses subprocess.Popen() for streaming stdout line-by-line
        - Passes --permission-mode acceptEdits, --output-format stream-json
        - Optionally passes --dangerously-skip-permissions when dangerous=True
        - Optionally passes --model when model is specified
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
        if model is not None:
            cmd_args.extend(["--model", model])
        cmd_args.append(command)

        if verbose:
            # Verbose mode - stream to terminal, no parsing, no events
            result = subprocess.run(cmd_args, cwd=worktree_path, check=False)

            if result.returncode != 0:
                error_msg = f"Claude command {command} failed with exit code {result.returncode}"
                yield ErrorEvent(message=error_msg)
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
            yield ProcessErrorEvent(
                message=f"Failed to start Claude CLI: {e}\nCommand: {' '.join(cmd_args)}"
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
                    yield TextEvent(content=text_content)

                    # Also try to extract PR metadata from text (simpler than nested JSON)
                    from erk.core.output_filter import extract_pr_metadata_from_text

                    text_metadata = extract_pr_metadata_from_text(text_content)
                    text_pr_url = text_metadata.get("pr_url")
                    if text_pr_url is not None:
                        yield PrUrlEvent(url=str(text_pr_url))
                    text_pr_number = text_metadata.get("pr_number")
                    if text_pr_number is not None:
                        yield PrNumberEvent(number=int(text_pr_number))
                    text_pr_title = text_metadata.get("pr_title")
                    if text_pr_title is not None:
                        yield PrTitleEvent(title=str(text_pr_title))
                    text_issue_number = text_metadata.get("issue_number")
                    if text_issue_number is not None:
                        yield IssueNumberEvent(number=int(text_issue_number))

                # Yield tool summaries
                tool_summary = parsed.get("tool_summary")
                if tool_summary is not None and isinstance(tool_summary, str):
                    yield ToolEvent(summary=tool_summary)

                # Yield spinner updates
                spinner_text = parsed.get("spinner_update")
                if spinner_text is not None and isinstance(spinner_text, str):
                    yield SpinnerUpdateEvent(status=spinner_text)

                # Yield PR URL
                pr_url_value = parsed.get("pr_url")
                if pr_url_value is not None:
                    yield PrUrlEvent(url=str(pr_url_value))

                # Yield PR number
                pr_number_value = parsed.get("pr_number")
                if pr_number_value is not None:
                    yield PrNumberEvent(number=int(pr_number_value))

                # Yield PR title
                pr_title_value = parsed.get("pr_title")
                if pr_title_value is not None:
                    yield PrTitleEvent(title=str(pr_title_value))

                # Yield issue number
                issue_number_value = parsed.get("issue_number")
                if issue_number_value is not None:
                    yield IssueNumberEvent(number=int(issue_number_value))

                # Detect zero-turn completions (hook blocking)
                num_turns = parsed.get("num_turns")
                if num_turns is not None and num_turns == 0:
                    diag = f"Claude command {command} completed without processing"
                    diag += "\n  This usually means a hook blocked the command"
                    diag += "\n  Run 'claude' directly to see hook error messages"
                    diag += f"\n  Working directory: {worktree_path}"
                    yield NoTurnsEvent(diagnostic=diag)

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
            timeout_minutes = PROCESS_TIMEOUT_SECONDS // 60
            yield ProcessErrorEvent(
                message=f"Claude command {command} timed out after {timeout_minutes} minutes"
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
            yield NoOutputEvent(diagnostic=diag)

            if returncode != 0:
                yield ErrorEvent(message=f"Exit code {returncode}")
            return

        # Enhanced error messages for non-zero exit codes
        if returncode != 0:
            error_msg = f"Claude command {command} failed"
            error_msg += f"\n  Exit code: {returncode}"
            error_msg += f"\n  Lines processed: {line_count}"
            if stderr_output:
                error_msg += "\n  Stderr:\n" + "".join(stderr_output).strip()
            yield ErrorEvent(message=error_msg)

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

    def execute_interactive(
        self,
        worktree_path: Path,
        dangerous: bool,
        command: str,
        target_subpath: Path | None,
        model: str | None = None,
    ) -> None:
        """Execute Claude CLI in interactive mode by replacing current process.

        Implementation details:
        - Verifies Claude CLI is available
        - Changes to worktree directory (and to subpath if provided)
        - Builds command arguments with the specified command
        - Replaces current process using os.execvp

        Note:
            This function never returns - the process is replaced by Claude CLI.

            The target_subpath is trusted to exist because it was computed from
            the source worktree's directory structure. Since the new worktree
            shares git history with the source, the path should exist.
        """
        # Verify Claude is available
        if not self.is_claude_available():
            raise RuntimeError("Claude CLI not found\nInstall from: https://claude.com/download")

        # Change to worktree directory (optionally to subpath)
        # Trust the computed subpath exists - it was derived from the source worktree
        # which has the same git history. If it doesn't exist, os.chdir will raise
        # FileNotFoundError which is the appropriate error.
        if target_subpath is not None:
            target_dir = worktree_path / target_subpath
            os.chdir(target_dir)
        else:
            os.chdir(worktree_path)

        # Build command arguments
        cmd_args = ["claude", "--permission-mode", "acceptEdits"]
        if dangerous:
            cmd_args.append("--dangerously-skip-permissions")
        if model is not None:
            cmd_args.extend(["--model", model])
        # Only append command if non-empty (allows launching Claude for planning)
        if command:
            cmd_args.append(command)

        # Redirect stdin/stdout/stderr to /dev/tty only if they are not already TTYs.
        # This ensures Claude gets terminal access when running as subprocess with
        # captured stdout (e.g., shell integration), while avoiding unnecessary
        # redirection when already running in a terminal (which can break tools
        # like Bun that expect specific TTY capabilities).
        if not (os.isatty(1) and os.isatty(2)):
            try:
                tty_fd = os.open("/dev/tty", os.O_RDWR)
                os.dup2(tty_fd, 0)  # stdin
                os.dup2(tty_fd, 1)  # stdout
                os.dup2(tty_fd, 2)  # stderr
                os.close(tty_fd)
            except OSError:
                logger.debug(
                    "Unable to redirect stdin/stdout/stderr to /dev/tty; "
                    "falling back to inherited descriptors"
                )

        # Replace current process with Claude
        os.execvp("claude", cmd_args)
        # Never returns - process is replaced

    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str = "haiku",
        tools: list[str] | None = None,
        cwd: Path | None = None,
    ) -> PromptResult:
        """Execute a single prompt and return the result.

        Implementation details:
        - Uses subprocess.run with --print and --output-format text
        - Returns PromptResult with success status and output
        """
        cmd = [
            "claude",
            "--print",
            "--output-format",
            "text",
            "--model",
            model,
        ]
        if tools is not None:
            cmd.extend(["--allowedTools", ",".join(tools)])
        cmd.append(prompt)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )

        if result.returncode != 0:
            return PromptResult(
                success=False,
                output="",
                error=result.stderr.strip() if result.stderr else f"Exit code {result.returncode}",
            )

        return PromptResult(
            success=True,
            output=result.stdout.strip(),
            error=None,
        )
