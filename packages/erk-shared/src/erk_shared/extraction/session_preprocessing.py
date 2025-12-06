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


def generate_compressed_xml(entries: list[dict], source_label: str | None = None) -> str:
    """Generate coarse-grained XML from mechanically reduced entries.

    This is Stage 1 output - deterministic structure conversion.
    No semantic judgment is applied here.

    Args:
        entries: List of session entries to convert to XML
        source_label: Optional label for agent logs

    Returns:
        XML string representation of the session
    """
    xml_lines = ["<session>"]

    # Add source label if provided (for agent logs)
    if source_label:
        xml_lines.append(f'  <meta source="{escape_xml(source_label)}" />')

    # Extract session metadata once (from first entry with gitBranch)
    for entry in entries:
        # Check in the original entry structure (before filtering)
        if "gitBranch" in entry:
            branch = entry["gitBranch"]
            xml_lines.append(f'  <meta branch="{escape_xml(branch)}" />')
            break

    for entry in entries:
        entry_type = entry["type"]
        message = entry.get("message", {})

        if entry_type == "user":
            # Extract user content
            content = message.get("content", "")
            if isinstance(content, list):
                # Handle list of content blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)
            # Apply whitespace compaction
            content = compact_whitespace(str(content))
            xml_lines.append(f"  <user>{escape_xml(content)}</user>")

        elif entry_type == "assistant":
            # Extract text and tool uses
            content_blocks = message.get("content", [])
            for content in content_blocks:
                if content.get("type") == "text":
                    text = content.get("text", "")
                    if text.strip():  # Only include non-empty text
                        # Apply whitespace compaction
                        text = compact_whitespace(text)
                        xml_lines.append(f"  <assistant>{escape_xml(text)}</assistant>")
                elif content.get("type") == "tool_use":
                    tool_name = content.get("name", "")
                    tool_id = content.get("id", "")
                    escaped_name = escape_xml(tool_name)
                    escaped_id = escape_xml(tool_id)
                    xml_lines.append(f'  <tool_use name="{escaped_name}" id="{escaped_id}">')
                    input_params = content.get("input", {})
                    for key, value in input_params.items():
                        escaped_key = escape_xml(key)
                        escaped_value = escape_xml(str(value))
                        xml_lines.append(f'    <param name="{escaped_key}">{escaped_value}</param>')
                    xml_lines.append("  </tool_use>")

        elif entry_type == "tool_result":
            # Handle tool results - no pruning in Stage 1 (Haiku handles that)
            content_blocks = message.get("content", [])
            tool_use_id = message.get("tool_use_id", "")

            # Extract result content
            result_parts = []
            for block in content_blocks:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        result_parts.append(block.get("text", ""))
                    elif "text" in block:
                        result_parts.append(block["text"])
                elif isinstance(block, str):
                    result_parts.append(block)

            result_text = "\n".join(result_parts)
            # Apply whitespace compaction
            result_text = compact_whitespace(result_text)

            xml_lines.append(f'  <tool_result tool="{escape_xml(tool_use_id)}">')
            xml_lines.append(escape_xml(result_text))
            xml_lines.append("  </tool_result>")

    xml_lines.append("</session>")
    return "\n".join(xml_lines)


def reduce_session_mechanically(entries: list[dict]) -> list[dict]:
    """Stage 1: Deterministic token reduction.

    Simple, predictable operations that are always correct:
    - Drop file-history-snapshot entries
    - Strip usage metadata
    - Remove empty text blocks
    - Drop sessionId field
    - Compact whitespace (handled in XML generation)

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

        # Build reduced entry with minimal fields
        reduced_entry = {
            "type": entry["type"],
            "message": entry.get("message", {}).copy(),
        }

        # Preserve gitBranch for metadata (will be extracted in XML generation)
        if "gitBranch" in entry:
            reduced_entry["gitBranch"] = entry["gitBranch"]

        # Drop usage metadata from assistant messages
        if "usage" in reduced_entry["message"]:
            del reduced_entry["message"]["usage"]

        # Remove empty text blocks from content
        message_content = reduced_entry["message"].get("content", [])
        if isinstance(message_content, list):
            reduced_entry["message"]["content"] = remove_empty_text_blocks(message_content)

        reduced.append(reduced_entry)

    return reduced


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
    raw_entries = []
    total_entries = 0
    skipped_entries = 0

    for line in log_path.read_text(encoding="utf-8").splitlines():
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


def preprocess_session(
    session_path: Path,
    session_id: str | None = None,
    include_agents: bool = True,
) -> str:
    """Stage 1: Preprocess a session log file to compressed XML format.

    This performs deterministic mechanical reduction only:
    - Drops file-history-snapshot entries
    - Strips usage metadata
    - Removes empty text blocks
    - Compacts whitespace
    - Deduplicates repeated assistant text

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
