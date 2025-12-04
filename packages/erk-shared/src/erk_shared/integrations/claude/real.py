"""Real implementation of Claude CLI executor.

Uses subprocess to invoke Claude CLI for both streaming command execution
and AI generation tasks. This implementation should only be used at runtime;
tests should use FakeClaudeExecutor.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

from erk_shared.integrations.claude.abc import (
    ClaudeExecutor,
    CommitMessageResult,
    StreamEvent,
)
from erk_shared.output.output_filter import (
    determine_spinner_status,
    extract_pr_metadata,
    extract_pr_metadata_from_text,
    extract_text_content,
    summarize_tool_use,
)


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

        process = subprocess.Popen(
            cmd_args,
            cwd=worktree_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
        )

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

        if debug:
            print(
                f"[DEBUG executor] stdout reading complete, total lines: {line_count}",
                file=sys.stderr,
            )
            sys.stderr.flush()

        # Wait for process to complete
        returncode = process.wait()

        # Wait for stderr thread to finish
        stderr_thread.join(timeout=1.0)

        if returncode != 0:
            error_msg = f"Claude command {command} failed with exit code {returncode}"
            if stderr_output:
                error_msg += "\n" + "".join(stderr_output)
            yield StreamEvent("error", error_msg)

    def _parse_stream_json_line(
        self, line: str, worktree_path: Path, command: str
    ) -> dict[str, str | int | None] | None:
        """Parse a single stream-json line and extract relevant information.

        Args:
            line: JSON line from stream-json output
            worktree_path: Path to worktree for relativizing paths
            command: The slash command being executed

        Returns:
            Dict with text_content, tool_summary, spinner_update, pr_url, pr_number,
            pr_title, and issue_number keys, or None if not JSON
        """
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

        result: dict[str, str | int | None] = {
            "text_content": None,
            "tool_summary": None,
            "spinner_update": None,
            "pr_url": None,
            "pr_number": None,
            "pr_title": None,
            "issue_number": None,
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

    def generate_commit_message(
        self,
        diff_file: Path,
        repo_root: Path,
        current_branch: str,
        parent_branch: str,
    ) -> CommitMessageResult:
        """Generate commit message by invoking Claude CLI.

        Uses the commit-message-generator subagent to analyze the diff
        and produce a structured commit message.
        """
        # Construct prompt for commit-message-generator subagent
        prompt = f"""Use the Task tool to delegate to the commit-message-generator subagent:

Task(
    subagent_type="commit-message-generator",
    description="Generate commit message from diff",
    prompt="Analyze the git diff and generate a commit message.

Diff file: {diff_file}
Repository root: {repo_root}
Current branch: {current_branch}
Parent branch: {parent_branch}

Use the Read tool to load the diff file."
)

Return ONLY the raw output from the subagent (the commit message text).
Do NOT add any commentary, headers, or formatting around it."""

        result = subprocess.run(
            ["claude", "--print", "--output-format", "text", prompt],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )

        output = result.stdout.strip()
        if not output:
            raise RuntimeError("AI generation returned empty output")

        # Parse: first line is title, rest is body
        lines = output.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        return CommitMessageResult(title=title, body=body)
