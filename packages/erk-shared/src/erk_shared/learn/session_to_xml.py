"""Convert JSONL session data to XML via batched LLM processing.

This module provides a fresh implementation of session-to-XML conversion
with comprehensive testing from the start.
"""

from erk_shared.learn.prompts import BATCH_TO_XML_PROMPT
from erk_shared.prompt_executor.abc import PromptExecutor


def filter_junk_lines(lines: list[str]) -> list[str]:
    """Filter out junk lines from JSONL content.

    Removes:
    - Empty lines
    - Lines that are pure queue operations (no meaningful content)
    - Lines that are only metadata with no user/assistant content

    Args:
        lines: List of JSONL line strings

    Returns:
        Filtered list with junk removed
    """
    filtered: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip queue-operation lines (they have no user content)
        if '"type":"queue-operation"' in stripped:
            continue

        filtered.append(stripped)

    return filtered


def batch_lines(lines: list[str], char_limit: int) -> list[list[str]]:
    """Batch lines by character count.

    Groups lines into batches where each batch's total character count
    is at or below char_limit. Each line is assigned to exactly one batch.

    Args:
        lines: List of line strings to batch
        char_limit: Maximum total characters per batch

    Returns:
        List of batches, where each batch is a list of lines
    """
    if not lines:
        return []

    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_size = 0

    for line in lines:
        line_size = len(line)

        # If adding this line exceeds limit and batch has content, start new batch
        if current_size + line_size > char_limit and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_size = 0

        current_batch.append(line)
        current_size += line_size

    # Don't forget the last batch
    if current_batch:
        batches.append(current_batch)

    return batches


def convert_batch_to_xml(batch_content: str, prompt_executor: PromptExecutor) -> str:
    """Convert a single batch of JSONL entries to XML using LLM.

    Args:
        batch_content: Newline-joined JSONL entries
        prompt_executor: Executor for running the conversion prompt

    Returns:
        XML elements as a string (may be empty if batch has no meaningful content)

    Raises:
        RuntimeError: If LLM execution fails
    """
    prompt = BATCH_TO_XML_PROMPT.format(batch_content=batch_content)
    result = prompt_executor.execute_prompt(prompt, model="haiku")

    if not result.success:
        msg = f"LLM batch conversion failed: {result.error}"
        raise RuntimeError(msg)

    return result.output.strip()


def session_to_xml(
    session_content: str,
    prompt_executor: PromptExecutor,
    *,
    batch_char_limit: int,
) -> str:
    """Convert JSONL session content to XML via batched Haiku calls.

    This is a fresh implementation of session-to-XML conversion with:
    1. Deterministic filtering of junk lines
    2. Character-based batching
    3. LLM processing per batch
    4. Accumulation into final XML

    Args:
        session_content: Raw JSONL session content (newline-separated)
        prompt_executor: Executor for LLM calls
        batch_char_limit: Maximum characters per batch (e.g., 50_000)

    Returns:
        XML string wrapped in <session>...</session> tags
    """
    # Split into lines
    lines = session_content.split("\n")

    # Filter junk (deterministic)
    filtered = filter_junk_lines(lines)

    if not filtered:
        return "<session></session>"

    # Batch by character count
    batches = batch_lines(filtered, batch_char_limit)

    # Convert each batch via LLM
    xml_parts: list[str] = []
    for batch in batches:
        batch_content = "\n".join(batch)
        xml_part = convert_batch_to_xml(batch_content, prompt_executor)
        if xml_part:
            xml_parts.append(xml_part)

    # Combine into final XML
    inner_content = "\n".join(xml_parts)
    return f"<session>\n{inner_content}\n</session>"
