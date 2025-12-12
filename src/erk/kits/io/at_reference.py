"""Parse Claude Code @ memory references from markdown content.

This module extracts @ file references used by Claude Code's memory system.
The @ syntax allows CLAUDE.md and AGENTS.md files to include content from
other markdown files.

Specification
-------------
The @ reference syntax is a Claude Code-specific feature (not a general
markdown standard). There is no formal grammar specification published by
Anthropic, so parsing rules are derived from official documentation and
observed behavior.

Authoritative Sources
---------------------
1. Claude Code Memory Documentation
   https://code.claude.com/docs/en/memory

   Key documented behaviors:
   - "CLAUDE.md files can import additional files using @path/to/import syntax"
   - "Both relative and absolute paths are allowed"
   - "imports are not evaluated inside markdown code spans and code blocks"
   - Maximum recursion depth: 5 hops
   - Home directory expansion supported: @~/.claude/...

2. GitHub Issue #1041 (anthropics/claude-code)
   https://github.com/anthropics/claude-code/issues/1041

   Clarifies path resolution and configuration requirements.

Parsing Rules (Derived)
-----------------------
Based on the above sources, we implement these rules:

1. STANDALONE LINES ONLY: A @ reference must be on its own line, not inline.
   This matches "import" semantics (whole-file inclusion) vs inline references.

2. CODE BLOCK EXCLUSION: References inside fenced code blocks (```) are
   not processed. This is explicitly documented.

3. PATH FORMAT: @<path>[#fragment]
   - Path starts immediately after @
   - Path continues until whitespace or # (fragment delimiter)
   - Optional #fragment for anchor links

4. NO INLINE CODE: References inside backtick spans (`@example`) are excluded.
   This follows from "code spans" exclusion in documentation.

Limitations
-----------
- Home directory expansion (~/) is recognized but not resolved by this parser
  (resolution is the caller's responsibility)
- MCP resource syntax (@server:protocol://path) is NOT handled by this module
- Recursion/transitive imports are NOT followed by this parser

Implementation Note
-------------------
No reference implementation exists in public Claude Code source. The official
npm package is obfuscated. This implementation is based solely on documented
behavior and empirical testing.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AtReference:
    """A parsed @ file reference.

    Attributes:
        raw_text: Original text including @ and fragment
        file_path: Path portion without @ or fragment
        fragment: Optional #fragment anchor (without #)
        line_number: 1-indexed line number in source
    """

    raw_text: str
    file_path: str
    fragment: str | None
    line_number: int


# Regex pattern for @ references: @<path> or @<path>#<fragment>
# Matches lines that are exactly @filepath or @filepath#fragment (with optional whitespace)
_AT_REFERENCE_PATTERN = re.compile(r"^\s*@([^\s#]+)(?:#([^\s]+))?\s*$")


def parse_at_references(content: str) -> list[AtReference]:
    """Extract standalone @ file references from markdown content.

    Parses markdown content and extracts @ file references that:
    - Appear on their own line (not inline with other text)
    - Are NOT inside fenced code blocks (``` ... ```)
    - Are NOT inside inline code spans (`...`)

    Args:
        content: Markdown content to parse

    Returns:
        List of AtReference objects for each valid @ reference found
    """
    references: list[AtReference] = []
    in_code_block = False
    lines = content.split("\n")

    for line_number, line in enumerate(lines, start=1):
        # Track fenced code blocks
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        # Skip content inside code blocks
        if in_code_block:
            continue

        # Skip if the line contains inline code around @
        # Check if @ appears inside backticks
        if _is_at_in_inline_code(line):
            continue

        # Try to match standalone @ reference
        match = _AT_REFERENCE_PATTERN.match(line)
        if match:
            file_path = match.group(1)
            fragment = match.group(2)
            raw_text = line.strip()

            references.append(
                AtReference(
                    raw_text=raw_text,
                    file_path=file_path,
                    fragment=fragment,
                    line_number=line_number,
                )
            )

    return references


def _is_at_in_inline_code(line: str) -> bool:
    """Check if @ reference appears inside inline code spans.

    Handles cases like: `@click.command()` or ``@property``

    Args:
        line: A single line of text to check

    Returns:
        True if @ appears inside backtick-delimited code spans
    """
    # Find all backtick-delimited regions and check if @ is inside any of them
    # This handles both single backticks and double backticks

    at_positions: list[int] = []

    # Find all @ positions
    for pos, char in enumerate(line):
        if char == "@":
            at_positions.append(pos)

    if not at_positions:
        return False

    # Track code span regions
    code_regions: list[tuple[int, int]] = []
    i = 0
    while i < len(line):
        if line[i] == "`":
            # Count consecutive backticks
            start = i
            backtick_count = 0
            while i < len(line) and line[i] == "`":
                backtick_count += 1
                i += 1

            # Find matching closing backticks
            search_pattern = "`" * backtick_count
            close_pos = line.find(search_pattern, i)
            if close_pos != -1:
                code_regions.append((start, close_pos + backtick_count))
                i = close_pos + backtick_count
        else:
            i += 1

    # Check if any @ is inside a code region
    for at_pos in at_positions:
        for start, end in code_regions:
            if start < at_pos < end:
                return True

    return False
