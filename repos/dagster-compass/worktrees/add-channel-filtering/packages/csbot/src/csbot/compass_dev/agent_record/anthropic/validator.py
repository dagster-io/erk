#!/usr/bin/env python3
"""Validate AnthropicAgent event mapping against recorded real API responses.

Usage:
    python validator.py --recording recordings/text_responses/simple_text.json
    python validator.py --validate-all --generate-report
    python validator.py --recording recordings/tool_calling/weather_call.json --verbose
"""

import json
from pathlib import Path
from typing import Any


class ValidationResult:
    """Result of validating a recorded response."""

    def __init__(self, recording_path: Path):
        self.recording_path = recording_path
        self.success = False
        self.events_generated: list[Any] = []
        self.expected_events: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duration_ms: float = 0
        self.event_count = 0

    def add_error(self, message: str):
        """Add an error to the validation result."""
        self.errors.append(message)
        self.success = False

    def add_warning(self, message: str):
        """Add a warning to the validation result."""
        self.warnings.append(message)


def find_recording_by_scenario(
    scenario_name: str, recordings_dir: Path | None = None
) -> Path | None:
    """Find recording file by scenario name."""
    if not recordings_dir:
        recordings_dir = Path(__file__).parent / "recordings"

    # Common patterns for recording files
    patterns = [
        f"{scenario_name}.json",
        f"*{scenario_name}*.json",
    ]

    # Search in subdirectories
    for subdir in ["text_responses", "tool_calling", "error_cases", "edge_cases"]:
        subdir_path = recordings_dir / subdir
        if subdir_path.exists():
            for pattern in patterns:
                matches = list(subdir_path.glob(pattern))
                if matches:
                    return matches[0]  # Return first match

    return None


def format_recording_header(recording_data: dict[str, Any], verbose: bool = False) -> str:
    """Format recording metadata and context information."""
    lines = []

    # Basic metadata
    metadata = recording_data.get("metadata", {})
    scenario = metadata.get("scenario", "Unknown")
    recorded_at = metadata.get("recorded_at", "Unknown")
    duration = metadata.get("duration_seconds", 0)
    raw_count = metadata.get("raw_event_count", 0)
    agent_count = metadata.get("agent_block_event_count", 0)
    model = metadata.get("model", "Unknown")

    lines.append(f"🎬 Recording: {scenario}")
    lines.append(f"📅 Recorded: {recorded_at}")
    lines.append(f"⏱️  Duration: {duration:.2f}s ({raw_count} raw, {agent_count} agent events)")
    lines.append(f"🤖 Model: {model}")

    if verbose:
        # Request parameters
        req_params = recording_data.get("request_params", {})
        max_tokens = req_params.get("max_tokens", "N/A")
        temperature = req_params.get("temperature", "N/A")

        lines.append(f"⚙️  Config: max_tokens={max_tokens}, temperature={temperature}")

        # Available tools
        tools = req_params.get("tools", [])
        if tools:
            if isinstance(tools, list) and tools and isinstance(tools[0], str):
                # New format: just tool names
                lines.append(f"🔧 Available Tools ({len(tools)}): {', '.join(tools)}")
            elif isinstance(tools, list):
                # Old format: tool specs
                lines.append(f"🔧 Available Tools ({len(tools)}):")
                for tool in tools:
                    tool_name = tool.get("name", "Unknown")
                    description = tool.get("description", "No description")
                    lines.append(f"   • {tool_name}: {description}")

        # Request messages
        messages = req_params.get("messages", [])
        if messages:
            lines.append(f"💬 Input Messages ({len(messages)}):")
            for i, msg in enumerate(messages):
                role = msg.get("role", "Unknown")
                content = msg.get("content", "")
                if len(content) > 100:
                    content = content[:100] + "..."
                lines.append(f"   {i + 1}. {role}: {content}")

    return "\n".join(lines)


def format_anthropic_event(event_data: dict[str, Any], index: int) -> str:
    """Format a single Anthropic event for display."""
    event_type = event_data.get("type", "unknown")

    lines = [f"{index + 1}. {event_type}"]

    if event_type == "message_start":
        message = event_data.get("message", {})
        lines.append(f"   ├─ Message ID: {message.get('id', 'N/A')}")
        lines.append(f"   ├─ Model: {message.get('model', 'N/A')}")
        usage = message.get("usage", {})
        if usage:
            lines.append(
                f"   └─ Usage: input_tokens={usage.get('input_tokens', 0)}, output_tokens={usage.get('output_tokens', 0)}"
            )

    elif event_type == "content_block_start":
        lines.append(f"   ├─ Index: {event_data.get('index', 'N/A')}")
        content_block = event_data.get("content_block", {})
        block_type = content_block.get("type", "N/A")
        lines.append(f"   ├─ Type: {block_type}")

        # Enhanced tool use details
        if block_type == "tool_use":
            tool_id = content_block.get("id", "N/A")
            tool_name = content_block.get("name", "N/A")
            lines.append(f"   ├─ Tool ID: {tool_id}")
            lines.append(f"   └─ Tool Name: {tool_name}")
        else:
            lines[-1] = f"   └─ Type: {block_type}"

    elif event_type == "content_block_delta":
        lines.append(f"   ├─ Index: {event_data.get('index', 'N/A')}")
        delta = event_data.get("delta", {})

        # Handle text deltas
        text = delta.get("text", "")
        if text:
            if len(text) > 50:
                text = text[:50] + "..."
            lines.append(f'   └─ Text: "{text}"')

        # Handle tool use JSON deltas
        partial_json = delta.get("partial_json", "")
        if partial_json:
            if len(partial_json) > 100:
                partial_json = partial_json[:100] + "..."
            lines.append(f"   └─ Tool JSON: {partial_json}")

        # If neither text nor partial_json, show delta type
        if not text and not partial_json:
            delta_type = delta.get("type", "unknown")
            lines.append(f"   └─ Delta Type: {delta_type}")

    elif event_type == "content_block_stop":
        lines.append(f"   └─ Index: {event_data.get('index', 'N/A')}")

    elif event_type == "message_delta":
        delta = event_data.get("delta", {})
        lines.append(f"   ├─ Stop reason: {delta.get('stop_reason', 'N/A')}")
        usage = event_data.get("usage", {})
        if usage:
            lines.append(f"   └─ Output tokens: {usage.get('output_tokens', 0)}")

    elif event_type == "message_stop":
        lines.append("   └─ Stream completed")

    return "\n".join(lines)


def format_agent_event_from_dict(event_dict: dict[str, Any], index: int) -> str:
    """Format an Agent event from dictionary for display."""
    event_type = event_dict.get("event", {}).get("type", "unknown")
    lines = [f"{index + 1}. Agent{event_type.title()}Event"]

    event_data = event_dict.get("event", {})

    if event_type == "start":
        lines.append(f"   ├─ Index: {event_data.get('index', 'N/A')}")
        content_block = event_data.get("content_block", {})
        block_type = content_block.get("type", "N/A")
        lines.append(f"   └─ Content Block: {block_type}")

        if block_type == "call_tool":
            tool_name = content_block.get("name", "N/A")
            tool_id = content_block.get("id", "N/A")
            lines[-1] = f"   ├─ Content Block: {block_type}"
            lines.append(f"   ├─ Tool: {tool_name}")
            lines.append(f"   └─ Tool ID: {tool_id}")

    elif event_type == "delta":
        lines.append(f"   ├─ Index: {event_data.get('index', 'N/A')}")
        delta = event_data.get("delta", {})
        delta_type = delta.get("type", "unknown")
        lines.append(f"   ├─ Delta Type: {delta_type}")

        if delta_type == "text_delta":
            text = delta.get("text", "")
            if len(text) > 50:
                text = text[:50] + "..."
            lines.append(f'   └─ Text: "{text}"')
        elif delta_type == "input_json_delta":
            partial_json = delta.get("partial_json", "")
            if len(partial_json) > 50:
                partial_json = partial_json[:50] + "..."
            lines.append(f"   └─ JSON: {partial_json}")
        else:
            lines[-1] = f"   └─ Delta Type: {delta_type}"

    elif event_type == "stop":
        lines.append(f"   └─ Index: {event_data.get('index', 'N/A')}")

    return "\n".join(lines)


async def list_input_events(recording_path: Path, verbose: bool = False):
    """List raw Anthropic events from a recording."""
    try:
        with open(recording_path, encoding="utf-8") as f:
            recording_data = json.load(f)

        # Display rich header
        print(format_recording_header(recording_data, verbose))
        print()
        print("─" * 80)
        print()

        events = recording_data.get("raw_anthropic_events", [])
        for i, event_data in enumerate(events):
            print(format_anthropic_event(event_data, i))
            print()

    except Exception as e:
        print(f"❌ Error reading recording: {e}")
        return 1

    return 0


async def list_agent_events(recording_path: Path, verbose: bool = False):
    """List AgentEvents generated from a recording."""
    try:
        with open(recording_path, encoding="utf-8") as f:
            recording_data = json.load(f)

        # Check if recording has captured Agent events (new format)
        if recording_data.get("agent_block_events"):
            # Use the captured Agent events directly
            print(format_recording_header(recording_data, verbose))
            print("\n" + "─" * 80 + "\n")

            agent_events_data = recording_data["agent_block_events"]
            for i, event_dict in enumerate(agent_events_data):
                print(format_agent_event_from_dict(event_dict, i))
                print()

            # Also show agent messages if available
            if recording_data.get("agent_messages") and verbose:
                print("\n" + "─" * 40 + " Agent Messages " + "─" * 40 + "\n")
                agent_messages = recording_data["agent_messages"]
                for i, msg_dict in enumerate(agent_messages):
                    role = msg_dict.get("role", "unknown")
                    content = msg_dict.get("content", "")
                    content_preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"{i + 1}. {role}: {content_preview}")
                    print()

            return 0

        else:
            print("❌ No agent events found in recording")
            return 1

    except Exception as e:
        print(f"❌ Error reading agent events: {e}")
        return 1


async def validate_json_files(recordings_dir: Path, verbose: bool = False) -> int:
    """Validate that all JSON files are parseable and have correct schema.

    Args:
        recordings_dir: Directory containing recording JSON files
        verbose: Whether to show verbose output

    Returns:
        Exit code: 0 if all files are valid, 1 if any issues found
    """
    if not recordings_dir.exists():
        print(f"❌ Recordings directory not found: {recordings_dir}")
        return 1

    # Find all JSON files
    json_files = [f for f in recordings_dir.rglob("*.json") if not f.name.startswith("_")]

    if not json_files:
        print(f"❌ No JSON files found in {recordings_dir}")
        return 1

    print(f"🔍 Checking {len(json_files)} JSON files...")

    errors = []

    for json_file in json_files:
        if verbose:
            print(f"  📋 Checking {json_file.name}...")

        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

            # Check required fields for recording schema
            required_fields = ["raw_anthropic_events", "request_params", "metadata"]
            for field in required_fields:
                if field not in data:
                    errors.append(f"{json_file.name}: Missing required field '{field}'")

            # Check that raw_anthropic_events is a list
            if "raw_anthropic_events" in data and not isinstance(
                data["raw_anthropic_events"], list
            ):
                errors.append(f"{json_file.name}: 'raw_anthropic_events' must be a list")

            # Check that request_params has required fields
            if "request_params" in data:
                req_params = data["request_params"]
                required_req_fields = ["model", "messages", "max_tokens"]
                for field in required_req_fields:
                    if field not in req_params:
                        errors.append(
                            f"{json_file.name}: Missing required request_params field '{field}'"
                        )

            if verbose:
                print(f"    ✅ {json_file.name}")

        except json.JSONDecodeError as e:
            errors.append(f"{json_file.name}: Invalid JSON - {e}")
            if verbose:
                print(f"    ❌ {json_file.name}: JSON decode error")
        except Exception as e:
            errors.append(f"{json_file.name}: Error reading file - {e}")
            if verbose:
                print(f"    ❌ {json_file.name}: Read error")

    # Summary
    if errors:
        print(f"\n❌ Found {len(errors)} issues:")
        for error in errors:
            print(f"  • {error}")
        return 1
    else:
        print(f"\n✅ All {len(json_files)} JSON files are valid")
        return 0
