"""Session preprocessing for extraction workflow.

Two-stage preprocessing architecture:
1. Stage 1: Deterministic mechanical reduction (this module) - fast, local, predictable
2. Stage 2: Haiku distillation (llm_distillation module) - semantic judgment calls

This module provides Stage 1: simple, deterministic operations that are always correct.
All semantic judgment calls (noise detection, deduplication, truncation) are delegated
to Haiku in Stage 2.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


def escape_xml(text: str) -> str:
    """Minimal XML escaping for special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def compact_whitespace(text: str) -> str:
    """Compact multiple consecutive newlines to a single newline.

    Args:
        text: Text to compact

    Returns:
        Text with multiple newlines collapsed to single newlines
    """
    return re.sub(r"\n{3,}", "\n\n", text)


def remove_empty_text_blocks(content_blocks: list[dict]) -> list[dict]:
    """Remove text blocks that are empty or contain only whitespace.

    Args:
        content_blocks: List of content blocks from a message

    Returns:
        Filtered list without empty text blocks
    """
    result = []
    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if text.strip():
                result.append(block)
        else:
            result.append(block)
    return result


def deduplicate_assistant_messages(entries: list[dict]) -> list[dict]:
    """Remove duplicate assistant text when tool_use present."""
    deduplicated = []
    prev_assistant_text = None

    for entry in entries:
        if entry["type"] == "assistant":
            message_content = entry["message"].get("content", [])

            # Extract text and tool uses separately
            text_blocks = [c for c in message_content if c.get("type") == "text"]
            tool_uses = [c for c in message_content if c.get("type") == "tool_use"]

            current_text = text_blocks[0]["text"] if text_blocks else None

            # If text same as previous AND there's a tool_use, drop the duplicate text
            if current_text == prev_assistant_text and tool_uses:
                # Keep only tool_use content
                entry["message"]["content"] = tool_uses

            prev_assistant_text = current_text

        deduplicated.append(entry)

    return deduplicated


@dataclass
class SessionXmlWriter:
    """Streaming XML writer that outputs elements as they're added."""

    _lines: list[str] = field(default_factory=lambda: ["<session>"])

    def _escape(self, text: str) -> str:
        """Escape XML special characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _format_attrs(self, **attrs: str | int | bool | None) -> str:
        """Format attributes for XML element, skipping None values."""
        parts = []
        for k, v in attrs.items():
            if v is not None:
                parts.append(f'{k}="{self._escape(str(v))}"')
        return " ".join(parts)

    def meta(self, **attrs: str) -> None:
        """Write a meta element."""
        attr_str = " ".join(f'{k}="{self._escape(v)}"' for k, v in attrs.items())
        self._lines.append(f"  <meta {attr_str} />")

    def user(self, content: str, timestamp: str | None = None) -> None:
        """Write a user element with optional timestamp."""
        if timestamp:
            ts_attr = f'timestamp="{self._escape(timestamp)}"'
            self._lines.append(f"  <user {ts_attr}>{self._escape(content)}</user>")
        else:
            self._lines.append(f"  <user>{self._escape(content)}</user>")

    def assistant(self, text: str, timestamp: str | None = None) -> None:
        """Write an assistant text element with optional timestamp."""
        if timestamp:
            ts_attr = f'timestamp="{self._escape(timestamp)}"'
            self._lines.append(f"  <assistant {ts_attr}>{self._escape(text)}</assistant>")
        else:
            self._lines.append(f"  <assistant>{self._escape(text)}</assistant>")

    def thinking(self, text: str) -> None:
        """Write a thinking element containing assistant's reasoning."""
        self._lines.append(f"  <thinking>{self._escape(text)}</thinking>")

    def unknown_block(self, block: dict) -> None:
        """Write an unknown content block with its raw JSON.

        Ensures new block types are preserved rather than silently dropped.
        """
        block_type = block.get("type", "unknown")
        # Output as JSON to preserve all data
        block_json = json.dumps(block, ensure_ascii=False)
        self._lines.append(f'  <content_block type="{self._escape(block_type)}">')
        self._lines.append(f"    {self._escape(block_json)}")
        self._lines.append("  </content_block>")

    def usage(self, usage_data: dict) -> None:
        """Write a usage metadata element with all fields from the usage dict.

        Uses blacklist approach - passes through all fields except known nested objects.
        """
        if not usage_data:
            return
        # Exclude nested objects that don't serialize well to attributes
        excluded = {"cache_creation"}  # Nested object with ephemeral token breakdowns
        attrs = self._format_attrs(
            **{k: v for k, v in usage_data.items() if k not in excluded and v is not None}
        )
        if attrs:
            self._lines.append(f"  <usage {attrs} />")

    def tool_use(self, block: dict) -> None:
        """Write a tool_use element with all fields from the block.

        Uses blacklist approach - passes through all fields.
        """
        name = block.get("name", "")
        tool_id = block.get("id", "")
        params = block.get("input", {})

        # Core attributes
        attrs = [f'name="{self._escape(name)}"', f'id="{self._escape(tool_id)}"']

        # Pass through any additional fields (blacklist approach)
        excluded = {"type", "name", "id", "input"}  # Already handled
        for key, value in block.items():
            if key not in excluded and value is not None:
                attrs.append(f'{key}="{self._escape(str(value))}"')

        attr_str = " ".join(attrs)
        self._lines.append(f"  <tool_use {attr_str}>")
        for key, value in params.items():
            self._lines.append(
                f'    <param name="{self._escape(key)}">{self._escape(str(value))}</param>'
            )
        self._lines.append("  </tool_use>")

    def tool_result(
        self,
        tool_id: str,
        content: str,
        is_error: bool = False,
        tool_use_result: dict | None = None,
    ) -> None:
        """Write a tool_result element with all metadata from toolUseResult.

        Uses blacklist approach - passes through all fields from toolUseResult.
        """
        attrs = [f'tool="{self._escape(tool_id)}"']
        if is_error:
            attrs.append('is_error="true"')

        # Pass through all toolUseResult metadata
        if tool_use_result:
            for key, value in tool_use_result.items():
                if value is not None:
                    # Convert camelCase to snake_case for XML consistency
                    xml_key = "".join(f"_{c.lower()}" if c.isupper() else c for c in key).lstrip(
                        "_"
                    )
                    attrs.append(f'{xml_key}="{self._escape(str(value))}"')

        attr_str = " ".join(attrs)
        self._lines.append(f"  <tool_result {attr_str}>")
        self._lines.append(self._escape(content))
        self._lines.append("  </tool_result>")

    def finish(self) -> str:
        """Close session and return complete XML."""
        self._lines.append("</session>")
        return "\n".join(self._lines)


def _extract_user_content(message: dict) -> str:
    """Extract text content from user message."""
    content = message.get("content", "")
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(text_parts)
    return str(content)


def _extract_tool_result_content(message: dict) -> str:
    """Extract text content from tool result message."""
    content_blocks = message.get("content", [])
    result_parts = []
    for block in content_blocks:
        if isinstance(block, dict):
            if block.get("type") == "text":
                result_parts.append(block.get("text", ""))
            elif "text" in block:
                result_parts.append(block["text"])
        elif isinstance(block, str):
            result_parts.append(block)
    return "\n".join(result_parts)


def _extract_is_error_from_tool_result(message: dict) -> bool:
    """Check if tool result has is_error flag set."""
    content_blocks = message.get("content", [])
    if isinstance(content_blocks, list):
        for block in content_blocks:
            if isinstance(block, dict) and block.get("is_error"):
                return True
    return False


def generate_compressed_xml(entries: list[dict], source_label: str | None = None) -> str:
    """Generate coarse-grained XML from mechanically reduced entries.

    This is Stage 1 output - deterministic structure conversion.
    No semantic judgment is applied here.

    Preserves important metadata:
    - thinking blocks (assistant reasoning)
    - usage metadata (token counts)
    - timestamps (chronological context)
    - is_error flags and duration_ms (execution details)

    Args:
        entries: List of session entries to convert to XML
        source_label: Optional label for agent logs

    Returns:
        XML string representation of the session
    """
    writer = SessionXmlWriter()

    # Write metadata
    if source_label:
        writer.meta(source=source_label)

    # Pass through session-level metadata from first entry (blacklist approach)
    # These are fields that describe the session context, not individual entries
    _meta_fields_to_skip = {"type", "message", "timestamp", "toolUseResult"}
    if entries:
        first_entry = entries[0]
        meta_attrs = {}
        for key, value in first_entry.items():
            if key not in _meta_fields_to_skip and value is not None:
                # Convert camelCase to snake_case for consistency
                xml_key = "".join(f"_{c.lower()}" if c.isupper() else c for c in key).lstrip("_")
                meta_attrs[xml_key] = str(value)
        if meta_attrs:
            writer.meta(**meta_attrs)

    # Stream entries
    for entry in entries:
        entry_type = entry["type"]
        message = entry.get("message", {})
        timestamp = entry.get("timestamp")

        if entry_type == "user":
            content = _extract_user_content(message)
            writer.user(compact_whitespace(content), timestamp=timestamp)

        elif entry_type == "assistant":
            # Known content block types
            known_block_types = {"thinking", "text", "tool_use"}

            # First output thinking blocks (assistant's reasoning)
            for block in message.get("content", []):
                if block.get("type") == "thinking":
                    thinking_text = block.get("thinking", "")
                    if thinking_text.strip():
                        writer.thinking(compact_whitespace(thinking_text))

            # Then output text, tool_use, and unknown blocks
            first_text = True
            for block in message.get("content", []):
                block_type = block.get("type")
                if block_type == "text":
                    text = block.get("text", "")
                    if text.strip():
                        # Only include timestamp on first text block
                        writer.assistant(
                            compact_whitespace(text),
                            timestamp=timestamp if first_text else None,
                        )
                        first_text = False
                elif block_type == "tool_use":
                    writer.tool_use(block)
                elif block_type not in known_block_types:
                    # Pass through unknown block types (blacklist approach)
                    writer.unknown_block(block)

            # Output usage metadata if present (blacklist approach - pass all fields)
            usage = message.get("usage", {})
            if usage:
                writer.usage(usage)

        elif entry_type == "tool_result":
            content = _extract_tool_result_content(message)
            is_error = _extract_is_error_from_tool_result(message)

            # Pass through entire toolUseResult (blacklist approach)
            tool_use_result = entry.get("toolUseResult")

            writer.tool_result(
                tool_id=message.get("tool_use_id", ""),
                content=compact_whitespace(content),
                is_error=is_error,
                tool_use_result=tool_use_result,
            )

    return writer.finish()


# Fields to exclude from entries during mechanical reduction.
# Using a blacklist ensures new fields are preserved by default.
_ENTRY_FIELDS_TO_EXCLUDE = frozenset(
    {
        "parentUuid",  # Internal graph structure
        "isSidechain",  # Internal routing (handled via agent log discovery)
        "userType",  # Typically always "external"
        "cwd",  # Redundant with gitBranch
        "version",  # Claude Code version, not relevant for analysis
        "sessionId",  # Already used for filtering
        "agentId",  # Already captured in source label
        "uuid",  # Internal identifier
        "requestId",  # Internal identifier
        "slug",  # Internal identifier
    }
)


def reduce_session_mechanically(entries: list[dict]) -> list[dict]:
    """Stage 1: Deterministic token reduction.

    Simple, predictable operations that are always correct:
    - Drop file-history-snapshot entries
    - Remove empty text blocks
    - Compact whitespace (handled in XML generation)

    Uses a blacklist approach to preserve unknown fields by default,
    ensuring resilience against future session log format changes.

    Args:
        entries: Raw session entries from JSONL

    Returns:
        Mechanically reduced entries
    """
    reduced = []

    for entry in entries:
        # Drop file-history-snapshot entries entirely
        if entry.get("type") == "file-history-snapshot":
            continue

        # Copy entry, excluding blacklisted fields
        reduced_entry = {k: v for k, v in entry.items() if k not in _ENTRY_FIELDS_TO_EXCLUDE}

        # Deep copy message and remove empty text blocks
        if "message" in reduced_entry:
            reduced_entry["message"] = reduced_entry["message"].copy()
            message_content = reduced_entry["message"].get("content", [])
            if isinstance(message_content, list):
                reduced_entry["message"]["content"] = remove_empty_text_blocks(message_content)

        reduced.append(reduced_entry)

    return reduced


def process_log_content(
    content: str,
    session_id: str | None = None,
) -> tuple[list[dict], int, int]:
    """Process JSONL content string and return mechanically reduced entries.

    This is Stage 1 processing: deterministic mechanical reduction only.
    No semantic judgment calls (those are delegated to Haiku in Stage 2).

    Args:
        content: Raw JSONL content string
        session_id: Optional session ID to filter entries by

    Returns:
        Tuple of (reduced entries, total entries count, skipped entries count)
    """
    raw_entries = []
    total_entries = 0
    skipped_entries = 0

    for line in content.splitlines():
        if not line.strip():
            continue

        entry = json.loads(line)
        total_entries += 1

        # Filter by session ID if provided
        if session_id is not None:
            entry_session = entry.get("sessionId")
            # Include if sessionId matches OR if sessionId field missing (backward compat)
            if entry_session is not None and entry_session != session_id:
                skipped_entries += 1
                continue

        raw_entries.append(entry)

    # Apply Stage 1 mechanical reduction
    reduced_entries = reduce_session_mechanically(raw_entries)

    return reduced_entries, total_entries, skipped_entries


def process_log_file(
    log_path: Path,
    session_id: str | None = None,
) -> tuple[list[dict], int, int]:
    """Process a single JSONL log file and return mechanically reduced entries.

    This is Stage 1 processing: deterministic mechanical reduction only.
    No semantic judgment calls (those are delegated to Haiku in Stage 2).

    Args:
        log_path: Path to the JSONL log file
        session_id: Optional session ID to filter entries by

    Returns:
        Tuple of (reduced entries, total entries count, skipped entries count)
    """
    content = log_path.read_text(encoding="utf-8")
    return process_log_content(content, session_id)


def preprocess_session_content(
    main_content: str,
    agent_logs: list[tuple[str, str]],
    session_id: str | None = None,
) -> str:
    """Stage 1: Preprocess session content to compressed XML format.

    This is the content-based version of preprocess_session, working with
    raw strings instead of file paths. Used by SessionStore-based workflows.

    This performs deterministic mechanical reduction only:
    - Drops file-history-snapshot entries
    - Removes empty text blocks
    - Compacts whitespace
    - Deduplicates repeated assistant text

    Preserves for analysis:
    - thinking blocks (assistant reasoning)
    - usage metadata (token counts)
    - timestamps (chronological context)
    - is_error flags and duration_ms (execution details)

    Args:
        main_content: Raw JSONL content string for main session
        agent_logs: List of (agent_id, raw JSONL content) tuples
        session_id: Optional session ID to filter entries by

    Returns:
        Compressed XML string (mechanically reduced, not semantically filtered)
    """
    # Process main session content
    entries, _, _ = process_log_content(main_content, session_id=session_id)

    # Apply standard deduplication (deterministic - always enabled)
    entries = deduplicate_assistant_messages(entries)

    # Generate main session XML
    xml_sections = [generate_compressed_xml(entries)]

    # Process agent logs
    for agent_id, agent_content in agent_logs:
        agent_entries, _, _ = process_log_content(agent_content, session_id=session_id)

        # Apply standard deduplication
        agent_entries = deduplicate_assistant_messages(agent_entries)

        # Generate XML with source label
        source_label = f"agent-{agent_id}"
        agent_xml = generate_compressed_xml(agent_entries, source_label=source_label)
        xml_sections.append(agent_xml)

    # Combine all XML sections
    return "\n\n".join(xml_sections)


def preprocess_session(
    session_path: Path,
    session_id: str | None = None,
    include_agents: bool = True,
) -> str:
    """Stage 1: Preprocess a session log file to compressed XML format.

    This performs deterministic mechanical reduction only:
    - Drops file-history-snapshot entries
    - Removes empty text blocks
    - Compacts whitespace
    - Deduplicates repeated assistant text

    Preserves for analysis:
    - thinking blocks (assistant reasoning)
    - usage metadata (token counts)
    - timestamps (chronological context)
    - is_error flags and duration_ms (execution details)

    All semantic judgment calls (noise detection, deduplication, truncation)
    are delegated to Stage 2 Haiku distillation.

    Args:
        session_path: Path to the session JSONL file
        session_id: Optional session ID to filter entries by
        include_agents: Whether to include agent logs

    Returns:
        Compressed XML string (mechanically reduced, not semantically filtered)
    """
    # Process main session log (Stage 1 reduction)
    entries, _, _ = process_log_file(session_path, session_id=session_id)

    # Apply standard deduplication (deterministic - always enabled)
    entries = deduplicate_assistant_messages(entries)

    # Generate main session XML
    xml_sections = [generate_compressed_xml(entries)]

    # Discover and process agent logs if requested
    if include_agents:
        agent_logs = _discover_agent_logs(session_path)
        for agent_log in agent_logs:
            agent_entries, _, _ = process_log_file(agent_log, session_id=session_id)

            # Apply standard deduplication
            agent_entries = deduplicate_assistant_messages(agent_entries)

            # Generate XML with source label
            source_label = f"agent-{agent_log.stem.replace('agent-', '')}"
            agent_xml = generate_compressed_xml(agent_entries, source_label=source_label)
            xml_sections.append(agent_xml)

    # Combine all XML sections
    return "\n\n".join(xml_sections)


def _discover_agent_logs(session_log_path: Path) -> list[Path]:
    """Discover agent logs in the same directory as the session log."""
    log_dir = session_log_path.parent
    agent_logs = sorted(log_dir.glob("agent-*.jsonl"))
    return agent_logs
