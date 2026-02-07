---
title: Metadata Blocks Reference
read_when:
  - "working with erk metadata in GitHub issues"
  - "parsing or extracting data from issue comments"
  - "creating new event types for issue tracking"
---

# Metadata Blocks Reference

Erk uses structured metadata blocks embedded in GitHub issues and comments to track state and events. This document describes the format and how to work with them.

## Block Structure

Metadata blocks are wrapped in HTML comments with a collapsible details element containing YAML:

- Opening marker: `<!-- erk:metadata-block:{key} -->`
- A `<details>` element with `<summary><code>{key}</code></summary>`
- YAML content inside a fenced code block
- Closing marker: `<!-- /erk:metadata-block:{key} -->`

## Parsing Blocks

Use functions from `erk_shared.github.metadata.core`:

```python
from erk_shared.github.metadata.core import (
    find_metadata_block,      # Find specific block by key
    extract_metadata_value,   # Get single field from block
    parse_metadata_blocks,    # Parse all blocks in text
)

# Find a specific block
block = find_metadata_block(issue_body, "plan-header")
if block:
    session_id = block.data.get("session_id")

# Extract single value directly
session_id = extract_metadata_value(comment, "impl-started", "session_id")
```

## Creating Blocks

Use `create_metadata_block()` and `render_metadata_block()`:

```python
from erk_shared.github.metadata.core import (
    create_metadata_block,
    render_metadata_block,
)

# Create block with data
block = create_metadata_block(
    key="learn-invoked",
    data={
        "session_id": "abc123",
        "timestamp": "2025-01-15T10:00:00Z",
    },
    schema=None,  # Optional schema validation
)

# Render to markdown
markdown = render_metadata_block(block)
```

## Standard Block Types

### Plan Blocks

| Key           | Location      | Purpose                         |
| ------------- | ------------- | ------------------------------- |
| `plan-header` | Issue body    | Plan metadata for fast querying |
| `plan-body`   | First comment | Full plan content (collapsible) |

See [Plan Schema Reference](../planning/plan-schema.md) for field details.

### Event Blocks (Comments)

| Key                | Purpose                         |
| ------------------ | ------------------------------- |
| `impl-started`     | Implementation started event    |
| `impl-ended`       | Implementation ended event      |
| `learn-invoked`    | Learn command was run           |
| `workflow-started` | GitHub Actions workflow started |

### Event Block Fields

Common fields for event blocks:

```yaml
session_id: "abc123-def456" # Claude Code session ID
timestamp: "2025-01-15T10:00:00Z" # ISO 8601
user: "username" # Who triggered the event
```

## Extracting Events from Comments

For bulk extraction of sessions from comments, use the helpers in `erk_shared.learn.impl_events`:

```python
from erk_shared.learn.impl_events import (
    extract_implementation_sessions,
    extract_learn_sessions,
)

# Get all implementation session IDs
impl_sessions = extract_implementation_sessions(comments)

# Get all learn session IDs
learn_sessions = extract_learn_sessions(comments)
```

## Best Practices

1. **Always use the parsing functions** - Don't write custom regex for metadata blocks
2. **Use schemas for validation** - Define schemas for new block types
3. **Keep blocks self-contained** - Each block should have all needed context
4. **Prefer YAML fields over nested structures** - Flat is better than nested

## Related Documentation

- [Plan Schema Reference](../planning/plan-schema.md) - plan-header and plan-body fields
- [Plan Lifecycle](../planning/lifecycle.md) - How events flow through plan lifecycle
