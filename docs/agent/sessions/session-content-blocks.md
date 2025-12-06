---
title: Session Content Metadata Blocks
read_when:
  - "storing session data in github issues"
  - "understanding session chunking"
  - "working with render_session_content_block"
  - "extracting session xml from comments"
---

# Session Content Metadata Blocks

Technical reference for storing and extracting Claude Code session content in GitHub issue comments.

## Overview

Session content blocks enable storing session XML data in GitHub issue comments with:

- **Chunking**: Automatic splitting for large sessions (GitHub's 64KB comment limit)
- **Collapsible display**: Clean GitHub rendering with expandable details
- **Extraction support**: Programmatic extraction and recombination
- **Metadata embedding**: Labels and hints for context

## Block Structure

### Single-Chunk Format

````markdown
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>Session Data: feature-name</strong></summary>

```xml
<session session_id="abc123-def456" branch="feature-name">
  <entry type="user">...</entry>
  <entry type="assistant">...</entry>
</session>
```
````

</details>
<!-- /erk:metadata-block:session-content -->
```

### Multi-Chunk Format

When content exceeds the chunk size limit, chunks are numbered:

````markdown
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>Session Data (1/3): feature-name</strong></summary>

**Extraction Hints:**

- Error handling patterns
- Test fixture setup

```xml
<session session_id="abc123">
  <!-- First portion of session -->
</session>
```
````

</details>
<!-- /erk:metadata-block:session-content -->
```

Subsequent chunks:

````markdown
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>Session Data (2/3): feature-name</strong></summary>

```xml
  <!-- Middle portion of session -->
```
````

</details>
<!-- /erk:metadata-block:session-content -->
```

## Size Limits and Chunking

### GitHub Limits

| Limit                | Value        | Notes                             |
| -------------------- | ------------ | --------------------------------- |
| Comment size         | 65,536 bytes | Hard limit enforced by GitHub API |
| Safety buffer        | 1,000 bytes  | Reserved for metadata overhead    |
| Effective chunk size | 64,536 bytes | Maximum content per chunk         |

### Chunking Algorithm

The `chunk_session_content()` function implements line-aware chunking:

```python
def chunk_session_content(
    content: str,
    max_chunk_size: int = GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER,
) -> list[str]:
    """Split content into chunks that fit within GitHub comment limits.

    Uses line-aware splitting to avoid breaking content mid-line.
    """
```

**Algorithm:**

1. Check if content fits in single chunk (return as-is if so)
2. Split content into lines
3. Accumulate lines until adding another would exceed limit
4. Start new chunk when limit reached
5. Handle oversized single lines by byte-level splitting

**Key behaviors:**

- Never splits mid-line (unless single line exceeds limit)
- UTF-8 aware (doesn't split mid-character)
- Preserves line breaks in output

## Render Functions

### `render_session_content_block()`

Renders a single session content block:

```python
def render_session_content_block(
    content: str,
    *,
    chunk_number: int | None = None,
    total_chunks: int | None = None,
    session_label: str | None = None,
    extraction_hints: list[str] | None = None,
) -> str:
```

**Parameters:**

| Parameter          | Type                | Description                           |
| ------------------ | ------------------- | ------------------------------------- |
| `content`          | `str`               | The session XML content               |
| `chunk_number`     | `int \| None`       | Current chunk (1-indexed), if chunked |
| `total_chunks`     | `int \| None`       | Total number of chunks                |
| `session_label`    | `str \| None`       | Label like branch name                |
| `extraction_hints` | `list[str] \| None` | Hints for extraction analysis         |

**Example:**

```python
from erk_shared.github.metadata import render_session_content_block

block = render_session_content_block(
    "<session>...</session>",
    chunk_number=1,
    total_chunks=3,
    session_label="fix-auth-bug",
    extraction_hints=["Error handling patterns", "Test setup"],
)
```

### `render_session_content_blocks()`

Automatically handles chunking and returns multiple blocks:

```python
def render_session_content_blocks(
    content: str,
    *,
    session_label: str | None = None,
    extraction_hints: list[str] | None = None,
    max_chunk_size: int = GITHUB_COMMENT_SIZE_LIMIT - CHUNK_SAFETY_BUFFER,
) -> list[str]:
```

**Behavior:**

- Returns single-element list if content fits in one chunk
- Splits and numbers chunks if content exceeds limit
- Only includes extraction hints in first chunk
- Accounts for wrapper overhead when calculating chunk sizes

**Example:**

```python
from erk_shared.github.metadata import render_session_content_blocks

blocks = render_session_content_blocks(
    large_session_xml,
    session_label="feature-implementation",
    extraction_hints=["Authentication flow", "Rate limiting"],
)

# Post each block as a separate comment
for block in blocks:
    github.post_comment(issue_number, block)
```

## Extract Functions

### `extract_session_content_from_block()`

Extracts XML content from a single block's body:

```python
def extract_session_content_from_block(block_body: str) -> str | None:
    """Extract session XML content from a session-content metadata block body."""
```

**Algorithm:**

1. Search for XML code fence pattern: ` ```xml ... ``` `
2. Extract content between fences
3. Return stripped content or None if not found

### `extract_session_content_from_comments()`

Extracts and combines session content from multiple comments:

```python
def extract_session_content_from_comments(
    comments: list[str],
) -> tuple[str | None, list[str]]:
    """Extract session XML from GitHub issue comments.

    Returns:
        Tuple of (combined_session_xml, list_of_session_ids)
    """
```

**Algorithm:**

1. Iterate through all comment bodies
2. Extract raw metadata blocks using HTML comment markers
3. Filter for `session-content` blocks only
4. Parse chunk numbers from summary text
5. Sort chunks by chunk number
6. Combine XML content in order
7. Extract session IDs from combined XML

**Chunk ordering:**

```python
# Sorting key: (is_chunked, chunk_number)
# Non-chunked content comes first, then chunks in order
def sort_key(item):
    chunk_num, total, _ = item
    if chunk_num is None:
        return (0, 0)
    return (1, chunk_num)
```

## Session ID Extraction

Session IDs are extracted from the XML content using regex:

```python
# Pattern matches: session_id="abc123-def456"
session_id_pattern = r'session_id="([^"]+)"'
session_ids = re.findall(session_id_pattern, combined_xml)

# Deduplicate while preserving order
unique_session_ids = list(dict.fromkeys(session_ids))
```

This enables:

- Correlating extracted content back to original sessions
- Linking to session logs for debugging
- Tracking which sessions were analyzed

## CLI Commands

### Rendering: `render-session-content`

```bash
dot-agent run erk render-session-content \
  --session-file /path/to/session.xml \
  --session-label "feature-name" \
  --extraction-hints "Pattern 1,Pattern 2"
```

**Output (JSON):**

```json
{
  "success": true,
  "blocks": ["<!-- erk:metadata-block:session-content -->..."],
  "chunk_count": 3
}
```

### Extraction: `extract-session-from-issue`

```bash
dot-agent run erk extract-session-from-issue 123
```

**Output (JSON):**

```json
{
  "success": true,
  "issue_number": 123,
  "session_file": "/path/to/.erk/scratch/abc123/session-from-issue-xyz.xml",
  "session_ids": ["abc123-def456", "ghi789-jkl012"],
  "chunk_count": 2
}
```

## Integration with GitHub Issues

### Posting Session Content

```python
from erk_shared.github.metadata import render_session_content_blocks

# Read session XML
session_xml = Path("session.xml").read_text()

# Render as blocks
blocks = render_session_content_blocks(
    session_xml,
    session_label="my-feature",
)

# Post each block as a comment
for block in blocks:
    github.create_issue_comment(
        repo=repo,
        issue_number=issue_number,
        body=block,
    )
```

### Extracting Session Content

```python
from erk_shared.github.metadata import extract_session_content_from_comments

# Fetch all comments from issue
comments = github.get_issue_comments(repo, issue_number)

# Extract and combine session XML
session_xml, session_ids = extract_session_content_from_comments(
    [comment.body for comment in comments]
)

if session_xml:
    # Process the combined session
    analyze_session(session_xml)
```

## Block Detection Pattern

The extraction uses HTML comment markers for reliable parsing:

```python
# Opening marker pattern
pattern = r"<!-- erk:metadata-block:session-content -->"

# Closing marker patterns (both supported)
# - <!-- /erk:metadata-block:session-content -->
# - <!-- /erk:metadata-block -->
closing = r"<!-- /erk:metadata-block(?::session-content)? -->"
```

This design:

- Survives GitHub's markdown rendering
- Is invisible to users viewing the issue
- Provides reliable extraction boundaries

## Handling Edge Cases

### Empty Content

```python
session_xml, session_ids = extract_session_content_from_comments([])
# Returns: (None, [])
```

### Malformed Blocks

Blocks with invalid structure are silently skipped:

- Missing XML code fence
- Invalid chunk numbers
- Corrupted metadata markers

### Duplicate Session IDs

Multiple occurrences of the same session ID are deduplicated:

```python
session_ids = ["abc", "def", "abc", "ghi", "abc"]
unique_ids = list(dict.fromkeys(session_ids))
# Result: ["abc", "def", "ghi"]
```

## Code Reference

### Module Location

```
packages/erk-shared/src/erk_shared/github/metadata.py
```

### Key Constants

```python
GITHUB_COMMENT_SIZE_LIMIT = 65536
CHUNK_SAFETY_BUFFER = 1000
```

### Function Summary

| Function                                  | Purpose                                |
| ----------------------------------------- | -------------------------------------- |
| `chunk_session_content()`                 | Split content into size-limited chunks |
| `render_session_content_block()`          | Render single metadata block           |
| `render_session_content_blocks()`         | Render with automatic chunking         |
| `extract_session_content_from_block()`    | Extract XML from single block          |
| `extract_session_content_from_comments()` | Extract and combine from comments      |

## Related

- [Session Layout](./layout.md) - JSONL session log format
- [Raw Extraction Workflow](../planning/raw-extraction-workflow.md) - End-to-end extraction automation
- [GitHub Metadata Blocks](../architecture/markers.md) - General metadata block patterns
