#!/usr/bin/env python3
"""
Session Log Preprocessor

Compresses JSONL session logs to XML format by removing metadata and deduplicating messages.
This command is invoked via erk exec preprocess-session <log-path>.
"""

import json
import tempfile
from pathlib import Path

import click


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
    import hashlib

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
                    "/erk:system:impl-execute",
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
            # Extract user content - may contain both text and tool_result blocks
            content = message.get("content", "")
            if isinstance(content, list):
                # Handle list of content blocks - separate text from tool_results
                text_parts = []
                tool_results = []
                for block in content:
                    if isinstance(block, dict):
                        block_type = block.get("type")
                        if block_type == "text":
                            text_parts.append(block.get("text", ""))
                        elif block_type == "tool_result":
                            tool_results.append(block)
                    elif isinstance(block, str):
                        text_parts.append(block)

                # Output text content if present
                if text_parts:
                    text_content = "\n".join(text_parts)
                    xml_lines.append(f"  <user>{escape_xml(text_content)}</user>")

                # Output tool_results as separate elements
                for tool_result in tool_results:
                    tool_use_id = tool_result.get("tool_use_id", "")
                    result_content = tool_result.get("content", "")

                    # Handle content that may be a string or list of blocks
                    if isinstance(result_content, list):
                        result_parts = []
                        for item in result_content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    result_parts.append(item.get("text", ""))
                                elif "text" in item:
                                    result_parts.append(item["text"])
                            elif isinstance(item, str):
                                result_parts.append(item)
                        result_content = "\n".join(result_parts)

                    # Apply pruning if enabled
                    if enable_pruning:
                        result_content = prune_tool_result_content(result_content)

                    xml_lines.append(f'  <tool_result tool="{escape_xml(tool_use_id)}">')
                    xml_lines.append(escape_xml(result_content))
                    xml_lines.append("  </tool_result>")
            else:
                # String content
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
    source_label: str | None = None,
    enable_filtering: bool = True,
) -> tuple[list[dict], int, int]:
    """Process a single JSONL log file and return filtered entries.

    Args:
        log_path: Path to the JSONL log file
        session_id: Optional session ID to filter entries by
        source_label: Optional label for agent logs
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


def discover_agent_logs(session_log_path: Path, session_id: str) -> list[Path]:
    """Discover agent logs in the same directory belonging to the session.

    Args:
        session_log_path: Path to the main session log file
        session_id: Session ID to filter by

    Returns:
        List of agent log paths matching the session ID
    """
    log_dir = session_log_path.parent
    all_agent_logs = sorted(log_dir.glob("agent-*.jsonl"))

    # Filter by session ID - check first entry of each file
    matching_logs = []
    for agent_log in all_agent_logs:
        first_line = agent_log.read_text(encoding="utf-8").split("\n", 1)[0]
        if not first_line.strip():
            continue
        first_entry = json.loads(first_line)
        if first_entry.get("sessionId") == session_id:
            matching_logs.append(agent_log)

    return matching_logs


def discover_planning_agent_logs(session_log_path: Path, parent_session_id: str) -> list[Path]:
    """
    Discover agent logs from Plan subagents only.

    Algorithm:
    1. Parse parent session JSONL to find Task tool invocations
    2. Filter for entries where input.subagent_type == "Plan"
    3. Extract agent IDs via temporal correlation with agent logs
    4. Return only agent logs matching Plan subagents

    Args:
        session_log_path: Path to the main session log file
        parent_session_id: Session ID of the parent session

    Returns:
        List of agent log paths from Plan subagents only.
        Empty list if no Plan subagents found.
    """
    log_dir = session_log_path.parent

    # Step 1: Find all Task tool invocations with subagent_type="Plan"
    plan_task_timestamps: list[float] = []

    for line in session_log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        entry = json.loads(line)

        # Look for assistant messages with tool_use content
        if entry.get("type") == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])

            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        # Check if this is a Task tool with subagent_type="Plan"
                        if block.get("name") == "Task":
                            tool_input = block.get("input", {})
                            if tool_input.get("subagent_type") == "Plan":
                                # Record timestamp for correlation
                                timestamp = message.get("timestamp")
                                if timestamp is not None:
                                    plan_task_timestamps.append(timestamp)

    # If no Plan tasks found, return empty list (fallback to main session only)
    if not plan_task_timestamps:
        return []

    # Step 2: Discover all agent logs
    all_agent_logs = sorted(log_dir.glob("agent-*.jsonl"))

    # Step 3: Filter agent logs by temporal correlation
    planning_agent_logs: list[Path] = []

    for agent_log in all_agent_logs:
        # Read first entry to check sessionId and timestamp
        if not agent_log.exists():
            continue
        first_line = agent_log.read_text(encoding="utf-8").splitlines()[0]
        if not first_line.strip():
            continue

        first_entry = json.loads(first_line)

        # Check if this agent log belongs to our parent session
        if first_entry.get("sessionId") != parent_session_id:
            continue

        # Check if this agent log's timestamp correlates with a Plan Task
        agent_timestamp = first_entry.get("message", {}).get("timestamp")
        if agent_timestamp is None:
            continue

        # Match if within 1 second of any Plan Task timestamp
        for plan_timestamp in plan_task_timestamps:
            if abs(agent_timestamp - plan_timestamp) <= 1.0:
                planning_agent_logs.append(agent_log)
                break

    return planning_agent_logs


def estimate_tokens(content: str) -> int:
    """Estimate token count from string content.

    Uses the rough heuristic of 4 characters per token.

    Args:
        content: String content to estimate tokens for

    Returns:
        Estimated token count
    """
    return len(content) // 4


def split_entries_to_chunks(
    entries: list[dict],
    *,
    max_tokens: int,
    source_label: str | None,
    enable_pruning: bool,
) -> list[str]:
    """Split entries into XML chunks that fit within token budget.

    Each chunk is a valid XML document with <session>...</session> wrapper.
    Splitting happens at entry boundaries, never mid-entry.

    Args:
        entries: List of session entries to split
        max_tokens: Maximum tokens per chunk
        source_label: Optional label for agent logs (included in each chunk)
        enable_pruning: Whether to prune tool results

    Returns:
        List of XML strings, each under the token budget
    """
    if not entries:
        empty_xml = generate_compressed_xml(
            [], source_label=source_label, enable_pruning=enable_pruning
        )
        return [empty_xml]

    chunks: list[str] = []
    current_entries: list[dict] = []
    current_tokens = 0

    # Estimate overhead for XML wrapper
    wrapper_overhead = estimate_tokens("<session>\n</session>")
    if source_label:
        wrapper_overhead += estimate_tokens(f'  <meta source="{source_label}" />\n')

    for entry in entries:
        # Generate XML for this single entry to estimate size
        single_xml = generate_compressed_xml(
            [entry], source_label=None, enable_pruning=enable_pruning
        )
        # Extract just the entry content (without session wrapper)
        entry_xml = single_xml.replace("<session>\n", "").replace("\n</session>", "")
        entry_tokens = estimate_tokens(entry_xml)

        # Check if adding this entry would exceed budget
        if current_tokens + entry_tokens + wrapper_overhead > max_tokens and current_entries:
            # Finalize current chunk
            chunk_xml = generate_compressed_xml(
                current_entries, source_label=source_label, enable_pruning=enable_pruning
            )
            chunks.append(chunk_xml)
            current_entries = []
            current_tokens = 0

        current_entries.append(entry)
        current_tokens += entry_tokens

    # Finalize last chunk
    if current_entries:
        chunk_xml = generate_compressed_xml(
            current_entries, source_label=source_label, enable_pruning=enable_pruning
        )
        chunks.append(chunk_xml)

    return chunks


@click.command(name="preprocess-session")
@click.argument("log_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--session-id",
    type=str,
    default=None,
    help="Filter JSONL entries by session ID before preprocessing",
)
@click.option(
    "--include-agents/--no-include-agents",
    default=True,
    help="Include agent logs from same directory (default: True)",
)
@click.option(
    "--no-filtering",
    is_flag=True,
    help="Disable all filtering optimizations (raw output)",
)
@click.option(
    "--stdout",
    is_flag=True,
    help="Output XML to stdout instead of temp file",
)
@click.option(
    "--max-tokens",
    type=int,
    default=None,
    help="Split output into multiple files of ~max-tokens each",
)
def preprocess_session(
    *,
    log_path: Path,
    session_id: str | None,
    include_agents: bool,
    no_filtering: bool,
    stdout: bool,
    max_tokens: int | None,
) -> None:
    """Preprocess session log JSONL to compressed XML format.

    By default, automatically discovers and includes agent logs (agent-*.jsonl)
    from the same directory as the main session log.

    All optimization filters are enabled by default for maximum token reduction:
    - Empty session filtering
    - Warmup session filtering
    - Documentation deduplication
    - Parameter truncation
    - Tool result pruning
    - Log discovery operation filtering

    Use --no-filtering to disable all optimizations and get raw output.
    Use --max-tokens to split output into multiple files.

    Args:
        log_path: Path to the main session JSONL file
        session_id: Optional session ID to filter entries by
        include_agents: Whether to include agent logs
        no_filtering: Disable all filtering optimizations
        max_tokens: Optional maximum tokens per output file (splits if exceeded)
    """
    # Track whether user explicitly provided session ID (for diagnostic output)
    user_provided_session_id = session_id is not None

    # Auto-extract session ID from filename if not provided
    if session_id is None:
        session_id = log_path.stem  # filename without extension is the session ID

    enable_filtering = not no_filtering

    # Process main session log
    entries, total_entries, skipped_entries = process_log_file(
        log_path, session_id=session_id, enable_filtering=enable_filtering
    )

    # Apply filtering operations if enabled
    if enable_filtering:
        # Check for empty/warmup sessions
        if is_empty_session(entries):
            click.echo("⚠️  Empty session detected - skipping output", err=True)
            return

        if is_warmup_session(entries):
            click.echo("⚠️  Warmup session detected - skipping output", err=True)
            return

        # Apply documentation deduplication
        entries = deduplicate_documentation_blocks(entries)

        # Apply parameter truncation
        entries = truncate_tool_parameters(entries)

    # Apply standard deduplication (always enabled)
    entries = deduplicate_assistant_messages(entries)

    # Show diagnostic output only if user explicitly provided session ID
    if user_provided_session_id:
        click.echo(f"✅ Filtered JSONL by session ID: {session_id[:8]}...", err=True)
        click.echo(
            f"📊 Included {total_entries - skipped_entries} entries, "
            f"skipped {skipped_entries} entries",
            err=True,
        )

    # Track original bytes for compression metrics (main session + included agent logs)
    original_bytes = len(log_path.read_text(encoding="utf-8"))

    # Collect all entries with their source labels for splitting
    all_entries_with_labels: list[tuple[list[dict], str | None]] = [(entries, None)]

    # Discover and process agent logs if requested
    if include_agents:
        agent_logs = discover_agent_logs(log_path, session_id)
        for agent_log in agent_logs:
            agent_entries, _agent_total, _agent_skipped = process_log_file(
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

            # Add agent log size to original bytes (only for included logs)
            original_bytes += len(agent_log.read_text(encoding="utf-8"))

            # Collect with source label
            source_label = f"agent-{agent_log.stem.replace('agent-', '')}"
            all_entries_with_labels.append((agent_entries, source_label))

    # Generate XML sections (with or without splitting)
    if max_tokens is not None:
        # Split each session's entries into chunks
        xml_sections: list[str] = []
        for session_entries, source_label in all_entries_with_labels:
            chunks = split_entries_to_chunks(
                session_entries,
                max_tokens=max_tokens,
                source_label=source_label,
                enable_pruning=enable_filtering,
            )
            xml_sections.extend(chunks)
    else:
        # Generate single XML for each session (no splitting)
        xml_sections = []
        for session_entries, source_label in all_entries_with_labels:
            xml = generate_compressed_xml(
                session_entries, source_label=source_label, enable_pruning=enable_filtering
            )
            xml_sections.append(xml)

    # Calculate compression metrics (only when filtering is enabled)
    if enable_filtering:
        original_size = original_bytes
        compressed_size = sum(len(section) for section in xml_sections)
        if original_size > 0:
            reduction_pct = ((original_size - compressed_size) / original_size) * 100
            stats_msg = (
                f"📉 Token reduction: {reduction_pct:.1f}% "
                f"({original_size:,} → {compressed_size:,} chars)"
            )
            # Route stats to stderr when stdout contains XML
            click.echo(stats_msg, err=True)

    filename_session_id = log_path.stem  # Extract session ID from filename

    if stdout:
        # Output XML directly to stdout
        if max_tokens is not None and len(xml_sections) > 1:
            # Output multiple chunks with delimiter
            click.echo("\n---CHUNK---\n".join(xml_sections))
        else:
            click.echo("\n\n".join(xml_sections))
    else:
        # Write to file(s) and print path(s)
        if max_tokens is not None and len(xml_sections) > 1:
            # Write multiple numbered files
            output_paths: list[Path] = []
            for i, section in enumerate(xml_sections, start=1):
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    prefix=f"session-{filename_session_id}-part{i}-",
                    suffix=".xml",
                    delete=False,
                    dir=tempfile.gettempdir(),
                ) as f:
                    f.write(section)
                    output_paths.append(Path(f.name))

            # Print all paths to stdout
            for path in output_paths:
                click.echo(str(path))
        else:
            # Write single file (backward compatible)
            xml_content = "\n\n".join(xml_sections)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=f"session-{filename_session_id}-",
                suffix="-compressed.xml",
                delete=False,
                dir=tempfile.gettempdir(),
            ) as f:
                f.write(xml_content)
                temp_file = Path(f.name)

            # Print path to stdout for command capture
            click.echo(str(temp_file))


if __name__ == "__main__":
    preprocess_session()
