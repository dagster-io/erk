#!/usr/bin/env python3
"""Extract session IDs from free-form text.

This command parses text containing potential session IDs and separates them
from remaining context. It recognizes multiple session ID patterns.

Usage:
    echo "session abc123 focus on testing" | dot-agent run erk parse-session-context
    dot-agent run erk parse-session-context --text "session abc123 focus on testing"

Output:
    JSON object with success status, extracted session IDs, and remaining context

Exit Codes:
    0: Success
    1: Error (parsing failed)

Examples:
    $ echo "session abc123 and def456" | dot-agent run erk parse-session-context
    {
      "success": true,
      "session_ids": ["abc123", "def456"],
      "remaining_context": "and"
    }
"""

import json
import re
import sys

import click


def extract_session_ids_from_text(text: str) -> tuple[list[str], str]:
    """Extract session IDs from free-form text.

    Recognizes multiple patterns:
    - `session <id>` - explicit prefix
    - UUID patterns (8+ hex chars with hyphens)
    - Short IDs (8 hex chars)

    Args:
        text: Text potentially containing session IDs

    Returns:
        Tuple of (session_ids list, remaining_context string)
    """
    session_ids: list[str] = []
    remaining_parts: list[str] = []

    # Patterns in order of specificity
    # 1. Full UUID pattern: 8-4-4-4-12 hex chars
    uuid_pattern = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

    # 2. Explicit session prefix: "session <id>" or "session:<id>"
    session_prefix_pattern = re.compile(r"session[:\s]+([0-9a-fA-F-]{8,36})", re.IGNORECASE)

    # 3. Short hex ID (8 chars, commonly used as session ID shorthand)
    re.compile(r"\b([0-9a-fA-F]{8})\b")

    # Track which parts of text were consumed as session IDs
    consumed_ranges: list[tuple[int, int]] = []

    # Extract full UUIDs first
    for match in uuid_pattern.finditer(text):
        session_id = match.group(0)
        if session_id not in session_ids:
            session_ids.append(session_id)
        consumed_ranges.append((match.start(), match.end()))

    # Extract explicit session prefix patterns
    for match in session_prefix_pattern.finditer(text):
        session_id = match.group(1)
        # Check if this ID wasn't already captured as a UUID
        if session_id not in session_ids:
            session_ids.append(session_id)
        consumed_ranges.append((match.start(), match.end()))

    # Build remaining context by excluding consumed ranges
    consumed_ranges.sort()
    merged_ranges: list[tuple[int, int]] = []
    for start, end in consumed_ranges:
        if merged_ranges and start <= merged_ranges[-1][1]:
            merged_ranges[-1] = (merged_ranges[-1][0], max(merged_ranges[-1][1], end))
        else:
            merged_ranges.append((start, end))

    # Extract remaining text
    last_end = 0
    for start, end in merged_ranges:
        if start > last_end:
            remaining_parts.append(text[last_end:start])
        last_end = end
    if last_end < len(text):
        remaining_parts.append(text[last_end:])

    remaining_context = " ".join(remaining_parts).strip()
    # Clean up extra whitespace
    remaining_context = re.sub(r"\s+", " ", remaining_context)

    return session_ids, remaining_context


@click.command(name="parse-session-context")
@click.option(
    "--text",
    default=None,
    type=str,
    help="Text containing potential session IDs (alternative to stdin)",
)
def parse_session_context(text: str | None) -> None:
    """Extract session IDs from free-form text.

    Recognizes multiple session ID patterns:
    - `session <id>` - explicit prefix
    - UUID patterns (8+ hex chars with hyphens)
    - Short IDs (8 hex chars)
    """
    # Get input from --text option or stdin
    if text is not None:
        input_text = text
    else:
        # Read from stdin
        if sys.stdin.isatty():
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": "No input provided",
                        "help": "Provide text via --text option or stdin",
                    }
                )
            )
            raise SystemExit(1)
        input_text = sys.stdin.read()

    session_ids, remaining_context = extract_session_ids_from_text(input_text)

    result = {
        "success": True,
        "session_ids": session_ids,
        "remaining_context": remaining_context,
    }

    click.echo(json.dumps(result, indent=2))
