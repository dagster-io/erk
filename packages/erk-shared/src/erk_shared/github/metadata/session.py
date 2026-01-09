"""Session content metadata block operations.

These support storing session content in GitHub issue comments, with:
- Chunking for large sessions (GitHub comment size limit is 65536 bytes)
- Numbered chunks for navigation
- Extraction hints about potential documentation patterns
- Metadata-derived naming (branch name, first message)
"""

import re

from erk_shared.github.metadata.constants import (
    CHUNK_SAFETY_BUFFER,
    GITHUB_COMMENT_SIZE_LIMIT,
)
from erk_shared.github.metadata.core import extract_raw_metadata_blocks


def chunk_session_content(
    content: str,
    max_chunk_size: int | None = None,
) -> list[str]:
    """Split content into chunks that fit within GitHub comment limits.

    Uses line-aware splitting to avoid breaking content mid-line.
    Each chunk will be at most max_chunk_size bytes.

    Args:
        content: The full session content to chunk
        max_chunk_size: Maximum size per chunk in bytes. If None, uses
            GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER.

    Returns:
        List of content chunks, each fitting within the size limit
    """
    if max_chunk_size is None:
        max_chunk_size = GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER

    if len(content.encode("utf-8")) <= max_chunk_size:
        return [content]

    chunks: list[str] = []
    lines = content.split("\n")
    current_chunk_lines: list[str] = []
    current_chunk_size = 0

    for line in lines:
        line_with_newline = line + "\n"
        line_size = len(line_with_newline.encode("utf-8"))

        # If a single line exceeds the limit, we need to split it
        if line_size > max_chunk_size:
            # Flush current chunk first
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = []
                current_chunk_size = 0

            # Split the long line by bytes
            encoded = line.encode("utf-8")
            start = 0
            while start < len(encoded):
                end = min(start + max_chunk_size - 1, len(encoded))  # Leave room for newline
                # Ensure we don't split in the middle of a UTF-8 character
                while end > start and end < len(encoded) and (encoded[end] & 0xC0) == 0x80:
                    end -= 1
                chunk_bytes = encoded[start:end]
                chunks.append(chunk_bytes.decode("utf-8", errors="replace"))
                start = end
            continue

        # Check if adding this line would exceed the limit
        if current_chunk_size + line_size > max_chunk_size:
            # Flush current chunk
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
            current_chunk_lines = [line]
            current_chunk_size = line_size
        else:
            current_chunk_lines.append(line)
            current_chunk_size += line_size

    # Don't forget the last chunk
    if current_chunk_lines:
        chunks.append("\n".join(current_chunk_lines))

    return chunks


def render_session_content_block(
    content: str,
    *,
    chunk_number: int | None = None,
    total_chunks: int | None = None,
    session_label: str | None = None,
    extraction_hints: list[str] | None = None,
) -> str:
    """Render session content in a code fence within metadata block structure.

    Creates a collapsible metadata block containing session XML wrapped in
    a code fence for proper display on GitHub.

    Args:
        content: The session XML content to wrap
        chunk_number: Current chunk number (1-indexed), if chunked
        total_chunks: Total number of chunks, if chunked
        session_label: Label for the session (e.g., branch name, "fix-auth-bug")
        extraction_hints: List of hints about potential extractions

    Returns:
        Rendered metadata block markdown string

    Example output:
        <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
        <!-- erk:metadata-block:session-content -->
        <details>
        <summary><strong>Session Data (1/3): fix-auth-bug</strong></summary>

        **Extraction Hints:**
        - Error handling patterns
        - Test fixture setup

        ```xml
        <session>
        ...
        </session>
        ```

        </details>
        <!-- /erk:metadata-block:session-content -->
    """
    # Build the summary line
    summary_parts = ["Session Data"]

    # Add chunk indicator if provided
    if chunk_number is not None and total_chunks is not None:
        summary_parts.append(f" ({chunk_number}/{total_chunks})")

    # Add session label if provided
    if session_label:
        summary_parts.append(f": {session_label}")

    summary_text = "".join(summary_parts)

    # Build extraction hints section if provided
    hints_section = ""
    if extraction_hints:
        hints_lines = ["**Extraction Hints:**"]
        for hint in extraction_hints:
            hints_lines.append(f"- {hint}")
        hints_section = "\n".join(hints_lines) + "\n\n"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>{summary_text}</strong></summary>

{hints_section}```xml
{content}
```

</details>
<!-- /erk:metadata-block:session-content -->"""


def extract_session_content_from_block(block_body: str) -> str | None:
    """Extract session XML content from a session-content metadata block body.

    Parses the <details> structure to find the XML code fence content.

    Args:
        block_body: Raw body content from a session-content metadata block

    Returns:
        The session XML content, or None if not found
    """
    # The session-content block has format:
    # <details>
    # <summary><strong>Session Data...</strong></summary>
    #
    # [Optional: **Extraction Hints:**...]
    #
    # ```xml
    # <session content here>
    # ```
    #
    # </details>

    # Extract content from the xml code fence
    pattern = r"```xml\s*(.*?)\s*```"
    match = re.search(pattern, block_body, re.DOTALL)

    if match is None:
        return None

    return match.group(1).strip()


def extract_session_content_from_comments(
    comments: list[str],
) -> tuple[str | None, list[str]]:
    """Extract session XML content from GitHub issue comments.

    Parses all comments looking for session-content metadata blocks,
    handles chunked content by combining in order, and returns the
    combined session XML.

    Args:
        comments: List of comment body strings

    Returns:
        Tuple of (combined_session_xml, list_of_session_ids)
        Returns (None, []) if no session content found
    """
    # Collect all session-content blocks with their chunk info
    chunks: list[tuple[int | None, int | None, str]] = []

    for body in comments:
        if not body:
            continue

        # Extract raw metadata blocks
        raw_blocks = extract_raw_metadata_blocks(body)

        for raw_block in raw_blocks:
            if raw_block.key != "session-content":
                continue

            # Extract the session XML from this block
            session_xml = extract_session_content_from_block(raw_block.body)
            if session_xml is None:
                continue

            # Try to determine chunk number from the summary
            # Format: <summary><strong>Session Data (1/3): label</strong></summary>
            chunk_pattern = r"Session Data\s*\((\d+)/(\d+)\)"
            chunk_match = re.search(chunk_pattern, raw_block.body)

            if chunk_match:
                chunk_num = int(chunk_match.group(1))
                total_chunks = int(chunk_match.group(2))
                chunks.append((chunk_num, total_chunks, session_xml))
            else:
                # Non-chunked content
                chunks.append((None, None, session_xml))

    if not chunks:
        return (None, [])

    # Sort chunks by chunk number (None values first for non-chunked)
    def sort_key(
        item: tuple[int | None, int | None, str],
    ) -> tuple[int, int]:
        chunk_num, total, _ = item
        if chunk_num is None:
            return (0, 0)
        return (1, chunk_num)

    chunks.sort(key=sort_key)

    # Combine all session XML content
    combined_xml = "\n".join(xml for _, _, xml in chunks)

    # Extract session IDs from the XML content
    # Session IDs appear in the session header like: session_id="abc123"
    session_id_pattern = r'session_id="([^"]+)"'
    session_ids = re.findall(session_id_pattern, combined_xml)

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_session_ids: list[str] = []
    for sid in session_ids:
        if sid not in seen:
            seen.add(sid)
            unique_session_ids.append(sid)

    return (combined_xml, unique_session_ids)


def render_session_content_blocks(
    content: str,
    *,
    session_label: str | None = None,
    extraction_hints: list[str] | None = None,
    max_chunk_size: int | None = None,
) -> list[str]:
    """Render session content as one or more metadata blocks.

    Automatically chunks content if it exceeds the maximum chunk size,
    adding chunk numbers to each block for navigation.

    Args:
        content: The full session XML content
        session_label: Label for the session (e.g., branch name)
        extraction_hints: List of hints about potential extractions
            (only included in first chunk)
        max_chunk_size: Maximum size per chunk in bytes. If None, uses
            GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER.

    Returns:
        List of rendered metadata block strings, one per chunk
    """
    if max_chunk_size is None:
        max_chunk_size = GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER
    # Calculate overhead for the block wrapper (without hints, conservative estimate)
    # The wrapper includes HTML comments, details tags, code fence, etc.
    wrapper_overhead = 300  # Conservative estimate

    # Hints overhead is only in first chunk
    hints_overhead = 0
    if extraction_hints:
        hints_overhead = sum(len(f"- {hint}\n".encode()) for hint in extraction_hints)
        hints_overhead += len(b"**Extraction Hints:**\n\n")

    # Adjust chunk size for wrapper overhead
    content_max_size = max_chunk_size - wrapper_overhead

    chunks = chunk_session_content(content, content_max_size)
    total_chunks = len(chunks)

    blocks: list[str] = []
    for i, chunk_content in enumerate(chunks, start=1):
        # Only include hints in the first chunk
        chunk_hints = extraction_hints if i == 1 else None

        # Only include chunk numbers if there are multiple chunks
        chunk_num = i if total_chunks > 1 else None
        total = total_chunks if total_chunks > 1 else None

        block = render_session_content_block(
            chunk_content,
            chunk_number=chunk_num,
            total_chunks=total,
            session_label=session_label,
            extraction_hints=chunk_hints,
        )
        blocks.append(block)

    return blocks


def get_default_max_chunk_size() -> int:
    """Get the default maximum chunk size for session content.

    Returns:
        Default max chunk size (GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER)
    """
    return GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER


def render_session_prompts_block(
    prompts: list[str],
    *,
    max_prompt_display_length: int,
) -> str:
    """Render session prompts as a metadata block with numbered markdown blocks.

    Creates a collapsible metadata block containing user prompts from
    the planning session, formatted as numbered code blocks for readability.

    Args:
        prompts: List of user prompt strings to include.
        max_prompt_display_length: Maximum characters to show per prompt.
            Prompts longer than this are truncated with "..." suffix.

    Returns:
        Rendered metadata block markdown string.

    Example output:
        <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
        <!-- erk:metadata-block:planning-session-prompts -->
        <details>
        <summary><code>planning-session-prompts</code> (3 prompts)</summary>

        **Prompt 1:**

        ```
        Add a dark mode toggle
        ```

        **Prompt 2:**

        ```
        Make sure tests pass
        ```

        </details>
        <!-- /erk:metadata-block:planning-session-prompts -->
    """
    # Build the numbered prompt blocks
    prompt_blocks: list[str] = []
    for i, prompt in enumerate(prompts, start=1):
        # Truncate long prompts for display
        display_text = prompt
        if len(prompt) > max_prompt_display_length:
            display_text = prompt[: max_prompt_display_length - 3] + "..."

        block = f"""**Prompt {i}:**

```
{display_text}
```"""
        prompt_blocks.append(block)

    # Join blocks with blank lines
    content = "\n\n".join(prompt_blocks)

    # Summary shows count
    count_suffix = f" ({len(prompts)} prompt{'s' if len(prompts) != 1 else ''})"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:planning-session-prompts -->
<details>
<summary><code>planning-session-prompts</code>{count_suffix}</summary>

{content}

</details>
<!-- /erk:metadata-block:planning-session-prompts -->"""


def extract_prompts_from_session_prompts_block(block_body: str) -> list[str] | None:
    """Extract prompts list from a planning-session-prompts metadata block.

    Parses the <details> structure to find numbered prompt blocks and extract
    the prompt text from each code fence.

    Args:
        block_body: Raw body content from a planning-session-prompts metadata block.

    Returns:
        List of prompt strings, or None if parsing fails.
    """
    # The planning-session-prompts block has format:
    # <details>
    # <summary><code>planning-session-prompts</code> (N prompts)</summary>
    #
    # **Prompt 1:**
    #
    # ```
    # First prompt text
    # ```
    #
    # **Prompt 2:**
    #
    # ```
    # Second prompt text
    # ```
    #
    # </details>

    # Find all prompt blocks: **Prompt N:** followed by a code fence
    # Pattern: **Prompt \d+:** followed by ``` ... ```
    pattern = r"\*\*Prompt \d+:\*\*\s*\n\n```\n(.*?)\n```"
    matches = re.findall(pattern, block_body, re.DOTALL)

    if not matches:
        return None

    return [match.strip() for match in matches]
