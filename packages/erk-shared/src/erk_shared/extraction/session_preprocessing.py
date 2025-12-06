"""Session preprocessing for extraction workflow.

This module provides functions to preprocess Claude Code session logs,
converting JSONL format to compressed XML suitable for extraction.
"""

import hashlib
import json
from pathlib import Path


def escape_xml(text: str) -> str:
    """Minimal XML escaping for special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_empty_session(entries: list[dict]) -> bool:
    """Check if session contains only metadata with no meaningful content.

    Empty sessions are characterized by:
    - Fewer than 3 entries (too small to be meaningful)
    - Only metadata/system entries without substantive interaction

    Args:
        entries: List of session entries to check

    Returns:
        True if session is empty/meaningless, False otherwise
    """
    if len(entries) < 3:
        return True

    # Check if there's any meaningful content
    has_user_message = False
    has_assistant_response = False

    for entry in entries:
        entry_type = entry.get("type")
        if entry_type == "user":
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = " ".join(text_parts)
            if content and len(str(content).strip()) > 0:
                has_user_message = True

        elif entry_type == "assistant":
            content_blocks = entry.get("message", {}).get("content", [])
            for block in content_blocks:
                if block.get("type") == "text" and block.get("text", "").strip():
                    has_assistant_response = True
                    break

    # Session is empty if it lacks meaningful interaction
    return not (has_user_message and has_assistant_response)


def is_warmup_session(entries: list[dict]) -> bool:
    """Check if session is a warmup containing only boilerplate acknowledgment.

    Warmup sessions contain predictable patterns like:
    - "I've reviewed"
    - "I'm ready"
    - "loaded the instructions"

    Args:
        entries: List of session entries to check

    Returns:
        True if session is a warmup, False otherwise
    """
    if not entries:
        return False

    # Look for warmup keyword in first user message
    for entry in entries:
        if entry.get("type") == "user":
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = " ".join(text_parts)

            content_lower = str(content).lower()
            if "warmup" in content_lower:
                return True
            break

    return False


def deduplicate_documentation_blocks(entries: list[dict]) -> list[dict]:
    """Replace duplicate command documentation blocks with marker text.

    Command documentation can appear verbatim multiple times, consuming
    significant tokens. This function detects duplicate blocks by content hash
    and replaces them with a reference marker.

    Args:
        entries: List of session entries

    Returns:
        Modified entries with duplicate documentation replaced by markers
    """
    seen_docs: dict[str, int] = {}  # hash -> first occurrence count
    occurrence_counter: dict[str, int] = {}  # hash -> current occurrence
    deduplicated = []

    for entry in entries:
        if entry.get("type") == "user":
            content = entry.get("message", {}).get("content", "")
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = " ".join(text_parts)

            content_str = str(content)

            # Detect command documentation by markers
            is_doc = any(
                marker in content_str
                for marker in [
                    "/erk:plan-save-issue",
                    "/erk:plan-implement",
                    "/gt:submit-branch",
                    "/gt:pr-update",
                    "command-message>",
                    "command-name>",
                ]
            )

            if is_doc and len(content_str) > 500:
                # Hash the content
                content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]

                if content_hash not in seen_docs:
                    # First occurrence - keep it
                    seen_docs[content_hash] = 1
                    occurrence_counter[content_hash] = 1
                    deduplicated.append(entry)
                else:
                    # Duplicate - replace with marker
                    occurrence_counter[content_hash] += 1
                    occurrence_num = occurrence_counter[content_hash]

                    # Create marker entry
                    marker_entry = entry.copy()
                    marker_content = (
                        f"[Duplicate command documentation block omitted - "
                        f"hash {content_hash}, occurrence #{occurrence_num}]"
                    )

                    # Preserve structure
                    if isinstance(entry.get("message", {}).get("content"), list):
                        marker_entry["message"] = {
                            "content": [{"type": "text", "text": marker_content}]
                        }
                    else:
                        marker_entry["message"] = {"content": marker_content}

                    deduplicated.append(marker_entry)
            else:
                deduplicated.append(entry)
        else:
            deduplicated.append(entry)

    return deduplicated


def truncate_parameter_value(value: str, max_length: int = 200) -> str:
    """Truncate long parameter values while preserving identifiability.

    Special handling for file paths to preserve structure.

    Args:
        value: Parameter value to truncate
        max_length: Maximum length (default 200)

    Returns:
        Truncated value with context markers
    """
    if len(value) <= max_length:
        return value

    # Detect file paths - check for path separators and no spaces
    has_slash = "/" in value
    has_no_spaces_early = " " not in value[: min(100, len(value))]

    if has_slash and has_no_spaces_early:
        # Likely a file path - preserve start and end structure
        parts = value.split("/")
        if len(parts) > 3:
            # Build path keeping first 2 parts and last 2 parts
            first_parts = "/".join(parts[:2])
            last_parts = "/".join(parts[-2:])
            return f"{first_parts}/.../{last_parts}"

    # General text - keep beginning and end with marker
    keep_chars = (max_length - 20) // 2
    truncated_count = len(value) - max_length
    return f"{value[:keep_chars]}...[truncated {truncated_count} chars]...{value[-keep_chars:]}"


def truncate_tool_parameters(entries: list[dict]) -> list[dict]:
    """Truncate verbose tool parameters to reduce token usage.

    Tool parameters can be extremely long (20+ lines), especially prompts.
    This function truncates them while preserving identifiability.

    Args:
        entries: List of session entries

    Returns:
        Modified entries with truncated parameters
    """
    truncated = []

    for entry in entries:
        if entry.get("type") == "assistant":
            message = entry.get("message", {})
            content_blocks = message.get("content", [])

            modified_blocks = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    # Truncate input parameters
                    input_params = block.get("input", {})
                    truncated_params = {}
                    for key, value in input_params.items():
                        value_str = str(value)
                        if len(value_str) > 200:
                            truncated_params[key] = truncate_parameter_value(value_str)
                        else:
                            truncated_params[key] = value

                    # Create modified block
                    modified_block = block.copy()
                    modified_block["input"] = truncated_params
                    modified_blocks.append(modified_block)
                else:
                    modified_blocks.append(block)

            # Update entry
            modified_entry = entry.copy()
            modified_entry["message"] = message.copy()
            modified_entry["message"]["content"] = modified_blocks
            truncated.append(modified_entry)
        else:
            truncated.append(entry)

    return truncated


def prune_tool_result_content(result_text: str) -> str:
    """Prune verbose tool results to first 30 lines, preserving errors.

    Tool results can be extremely long. This function keeps the first 30 lines
    (which usually contain the most relevant context) and preserves any lines
    containing error keywords.

    Args:
        result_text: Tool result text to prune

    Returns:
        Pruned result text with error preservation
    """
    lines = result_text.split("\n")

    if len(lines) <= 30:
        return result_text

    # Keep first 30 lines
    kept_lines = lines[:30]

    # Scan remaining lines for errors
    error_keywords = ["error", "exception", "failed", "failure", "fatal", "warning"]
    error_lines = []

    for line in lines[30:]:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in error_keywords):
            error_lines.append(line)

    # Combine
    if error_lines:
        result_lines = kept_lines + [f"\n... [{len(lines) - 30} lines omitted] ...\n"] + error_lines
    else:
        result_lines = kept_lines + [f"\n... [{len(lines) - 30} lines omitted] ..."]

    return "\n".join(result_lines)


def is_log_discovery_operation(entry: dict) -> bool:
    """Check if entry is a log discovery bash command (pwd, ls, etc.).

    These are implementation mechanics that don't provide semantic value
    for plan enhancement.

    Args:
        entry: Session entry to check

    Returns:
        True if entry is a log discovery operation, False otherwise
    """
    if entry.get("type") != "assistant":
        return False

    content_blocks = entry.get("message", {}).get("content", [])

    for block in content_blocks:
        if block.get("type") == "tool_use":
            tool_name = block.get("name", "")
            if tool_name != "Bash":
                continue

            # Check command parameter
            input_params = block.get("input", {})
            command = input_params.get("command", "")

            # Log discovery patterns
            log_discovery_patterns = [
                "pwd",
                "ls ~/.claude/projects/",
                "ls ~/.claude",
                "find ~/.claude",
                "echo $SESSION_ID",
            ]

            for pattern in log_discovery_patterns:
                if pattern in command:
                    return True

    return False


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


def generate_compressed_xml(
    entries: list[dict], source_label: str | None = None, enable_pruning: bool = True
) -> str:
    """Generate coarse-grained XML from filtered entries.

    Args:
        entries: List of session entries to convert to XML
        source_label: Optional label for agent logs
        enable_pruning: Whether to prune tool results (default: True)

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
            xml_lines.append(f"  <user>{escape_xml(content)}</user>")

        elif entry_type == "assistant":
            # Extract text and tool uses
            content_blocks = message.get("content", [])
            for content in content_blocks:
                if content.get("type") == "text":
                    text = content.get("text", "")
                    if text.strip():  # Only include non-empty text
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
            # Handle tool results - apply pruning if enabled
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

            # Apply pruning if enabled
            if enable_pruning:
                result_text = prune_tool_result_content(result_text)

            xml_lines.append(f'  <tool_result tool="{escape_xml(tool_use_id)}">')
            xml_lines.append(escape_xml(result_text))
            xml_lines.append("  </tool_result>")

    xml_lines.append("</session>")
    return "\n".join(xml_lines)


def process_log_file(
    log_path: Path,
    session_id: str | None = None,
    enable_filtering: bool = True,
) -> tuple[list[dict], int, int]:
    """Process a single JSONL log file and return filtered entries.

    Args:
        log_path: Path to the JSONL log file
        session_id: Optional session ID to filter entries by
        enable_filtering: Whether to apply optimization filters (default: True)

    Returns:
        Tuple of (filtered entries, total entries count, skipped entries count)
    """
    entries = []
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

        # Filter out noise entries
        if entry.get("type") == "file-history-snapshot":
            continue

        # Filter log discovery operations if filtering enabled
        if enable_filtering and is_log_discovery_operation(entry):
            continue

        # Keep minimal fields but preserve gitBranch for metadata extraction
        filtered = {
            "type": entry["type"],
            "message": entry.get("message", {}),
        }

        # Preserve gitBranch for metadata (will be extracted in XML generation)
        if "gitBranch" in entry:
            filtered["gitBranch"] = entry["gitBranch"]

        # Drop usage metadata from assistant messages
        if "usage" in filtered["message"]:
            del filtered["message"]["usage"]

        entries.append(filtered)

    return entries, total_entries, skipped_entries


def preprocess_session(
    session_path: Path,
    session_id: str | None = None,
    include_agents: bool = True,
    enable_filtering: bool = True,
) -> str:
    """Preprocess a session log file to compressed XML format.

    This is the main entry point for session preprocessing.

    Args:
        session_path: Path to the session JSONL file
        session_id: Optional session ID to filter entries by
        include_agents: Whether to include agent logs
        enable_filtering: Whether to apply all filtering optimizations

    Returns:
        Compressed XML string, or empty string if session is empty/warmup
    """
    # Process main session log
    entries, _, _ = process_log_file(
        session_path, session_id=session_id, enable_filtering=enable_filtering
    )

    # Apply filtering operations if enabled
    if enable_filtering:
        # Check for empty/warmup sessions
        if is_empty_session(entries):
            return ""

        if is_warmup_session(entries):
            return ""

        # Apply documentation deduplication
        entries = deduplicate_documentation_blocks(entries)

        # Apply parameter truncation
        entries = truncate_tool_parameters(entries)

    # Apply standard deduplication (always enabled)
    entries = deduplicate_assistant_messages(entries)

    # Generate main session XML
    xml_sections = [generate_compressed_xml(entries, enable_pruning=enable_filtering)]

    # Discover and process agent logs if requested
    if include_agents:
        agent_logs = _discover_agent_logs(session_path)
        for agent_log in agent_logs:
            agent_entries, _, _ = process_log_file(
                agent_log, session_id=session_id, enable_filtering=enable_filtering
            )

            # Apply filtering for agent logs
            if enable_filtering:
                if is_empty_session(agent_entries):
                    continue
                if is_warmup_session(agent_entries):
                    continue
                agent_entries = deduplicate_documentation_blocks(agent_entries)
                agent_entries = truncate_tool_parameters(agent_entries)

            agent_entries = deduplicate_assistant_messages(agent_entries)

            # Generate XML with source label
            source_label = f"agent-{agent_log.stem.replace('agent-', '')}"
            agent_xml = generate_compressed_xml(
                agent_entries, source_label=source_label, enable_pruning=enable_filtering
            )
            xml_sections.append(agent_xml)

    # Combine all XML sections
    return "\n\n".join(xml_sections)


def _discover_agent_logs(session_log_path: Path) -> list[Path]:
    """Discover agent logs in the same directory as the session log."""
    log_dir = session_log_path.parent
    agent_logs = sorted(log_dir.glob("agent-*.jsonl"))
    return agent_logs
