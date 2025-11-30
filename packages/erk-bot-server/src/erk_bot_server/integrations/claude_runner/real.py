"""Real Claude CLI runner using subprocess."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from erk_bot_server.integrations.claude_runner.abc import ClaudeRunner
from erk_bot_server.models.session import StreamEvent


class RealClaudeRunner(ClaudeRunner):
    """Production implementation using subprocess to run Claude CLI."""

    async def execute_message(
        self,
        session_id: str,
        message: str,
        working_directory: str,
        timeout_seconds: int,
    ) -> AsyncIterator[StreamEvent]:
        """Execute Claude CLI and stream the response.

        Runs: claude --resume <session_id> --print --output-format stream-json \
                     --permission-mode acceptEdits "<message>"
        """
        cmd = [
            "claude",
            "--resume",
            session_id,
            "--print",
            "--output-format",
            "stream-json",
            "--permission-mode",
            "acceptEdits",
            message,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=working_directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if process.stdout is None:
            yield StreamEvent("error", {"message": "Failed to start process"})
            return

        try:
            async for line in process.stdout:
                decoded = line.decode().strip()
                if not decoded:
                    continue

                event = self._parse_stream_line(decoded)
                if event is not None:
                    yield event

            await asyncio.wait_for(process.wait(), timeout=timeout_seconds)

            # Final done event
            yield StreamEvent(
                "done",
                {"success": process.returncode == 0},
            )

        except TimeoutError:
            process.kill()
            yield StreamEvent(
                "error",
                {"message": f"Process timed out after {timeout_seconds} seconds"},
            )

    def _parse_stream_line(self, line: str) -> StreamEvent | None:
        """Parse a line from Claude CLI stream-json output.

        The stream-json format produces JSON objects, one per line.
        Each object has a "type" field indicating the event type.

        Returns:
            StreamEvent if line is valid, None if parsing fails
        """
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None

        event_type = data.get("type", "")

        # Map Claude CLI event types to our StreamEvent types
        if event_type == "assistant":
            # Assistant text output
            message_data = data.get("message") or {}
            content_list = message_data.get("content") if isinstance(message_data, dict) else []
            if isinstance(content_list, list) and content_list:
                # Extract text from content blocks
                text_parts: list[str] = []
                for item in content_list:
                    item_dict = dict(item) if isinstance(item, dict) else {}
                    if item_dict.get("type") == "text":
                        text_parts.append(str(item_dict.get("text", "")))
                if text_parts:
                    return StreamEvent("text", {"content": "".join(text_parts)})

        elif event_type == "tool_use":
            # Tool being used
            tool_name = data.get("name", "")
            tool_input = data.get("input", {})
            summary = self._summarize_tool(tool_name, tool_input)
            return StreamEvent("tool", {"name": tool_name, "summary": summary})

        elif event_type == "error":
            # Error from Claude
            message = data.get("error", {}).get("message", "Unknown error")
            return StreamEvent("error", {"message": message})

        elif event_type == "result":
            # Final result
            success = data.get("subtype") != "error"
            result_data: dict[str, str | int | bool] = {"success": success}
            if "duration_ms" in data:
                result_data["duration_seconds"] = data["duration_ms"] / 1000
            return StreamEvent("done", result_data)

        # Ignore other event types (system, user, etc.)
        return None

    def _summarize_tool(self, name: str, input_data: Any) -> str:
        """Create a human-readable summary of a tool invocation."""
        if name == "Edit":
            file_path = input_data.get("file_path", "unknown file")
            return f"Editing {file_path}"
        elif name == "Write":
            file_path = input_data.get("file_path", "unknown file")
            return f"Writing {file_path}"
        elif name == "Read":
            file_path = input_data.get("file_path", "unknown file")
            return f"Reading {file_path}"
        elif name == "Bash":
            command = str(input_data.get("command", ""))[:50]
            return f"Running: {command}..."
        elif name == "Glob":
            pattern = input_data.get("pattern", "")
            return f"Searching for {pattern}"
        elif name == "Grep":
            pattern = input_data.get("pattern", "")
            return f"Searching for '{pattern}'"
        else:
            return f"Using {name}"
