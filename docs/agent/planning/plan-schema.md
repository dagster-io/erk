---
title: Plan Schema Reference
read_when:
  - "understanding plan issue structure"
  - "debugging plan validation errors"
  - "working with plan-header or plan-body blocks"
  - "creating extraction plans with session content"
  - "embedding session XML in GitHub issues"
---

# Plan Schema Reference

Complete reference for the erk plan issue structure.

## Overview

Plan issues use a multi-part structure:

| Location            | Block Key         | Purpose                                     |
| ------------------- | ----------------- | ------------------------------------------- |
| Issue body          | `plan-header`     | Compact metadata for fast querying          |
| First comment       | `plan-body`       | Full plan content in collapsible details    |
| Additional comments | `session-content` | Session XML for extraction plans (optional) |

The plan-header/plan-body separation optimizes GitHub API performance - metadata can be queried without fetching comments. Session-content blocks are used only in extraction plans to provide session context for pattern extraction.

## Issue Body: plan-header Block

The issue body contains only the `plan-header` metadata block wrapped in HTML comments and a collapsible details element. The structure uses:

- Opening marker: `<!-- erk:metadata-block:plan-header -->`
- A `<details>` element with `<summary><code>plan-header</code></summary>`
- YAML content inside a fenced code block
- Closing marker: `<!-- /erk:metadata-block:plan-header -->`

Example YAML content:

```yaml
schema_version: "2"
created_at: 2025-01-15T10:30:00Z
created_by: username
last_dispatched_run_id: null
last_dispatched_node_id: null
last_dispatched_at: null
last_local_impl_at: null
last_local_impl_event: null
last_local_impl_session: null
last_local_impl_user: null
last_remote_impl_at: null
```

### plan-header Fields

**Required fields:**

| Field        | Type   | Description                    |
| ------------ | ------ | ------------------------------ |
| `created_at` | string | ISO 8601 timestamp of creation |
| `created_by` | string | GitHub username of creator     |

**Optional fields:**

| Field                     | Type         | Description                             |
| ------------------------- | ------------ | --------------------------------------- |
| `worktree_name`           | string\|null | Set when worktree is created            |
| `last_dispatched_run_id`  | string\|null | Workflow run ID (set by workflow)       |
| `last_dispatched_node_id` | string\|null | GraphQL node ID (for batch queries)     |
| `last_dispatched_at`      | string\|null | Dispatch timestamp                      |
| `last_local_impl_at`      | string\|null | Local implementation timestamp          |
| `last_local_impl_event`   | string\|null | "started" or "ended"                    |
| `last_local_impl_session` | string\|null | Claude Code session ID                  |
| `last_local_impl_user`    | string\|null | User who ran implementation             |
| `last_remote_impl_at`     | string\|null | GitHub Actions implementation timestamp |

**Extraction plan fields (when `plan_type: extraction`):**

| Field                    | Type         | Description                    |
| ------------------------ | ------------ | ------------------------------ |
| `plan_type`              | string       | "standard" or "extraction"     |
| `source_plan_issues`     | list[int]    | Issue numbers of source plans  |
| `extraction_session_ids` | list[string] | Session IDs that were analyzed |

## First Comment: plan-body Block

The first comment contains the full plan content in a collapsible block. The structure uses:

- Opening marker: `<!-- erk:metadata-block:plan-body -->`
- A `<details>` element with `<summary><strong>📋 Implementation Plan</strong></summary>`
- The full plan markdown content
- Closing marker: `<!-- /erk:metadata-block:plan-body -->`

## Additional Comments: session-content Blocks

Extraction plans may include one or more `session-content` metadata blocks containing preprocessed session XML. These blocks enable agents to analyze session context when implementing extraction plans.

### Structure

Each session-content block uses:

- Opening marker: `<!-- erk:metadata-block:session-content -->`
- A `<details>` element with summary showing chunk number and optional label
- Optional extraction hints section
- XML content wrapped in fenced code block (see [github-xml-rendering.md](../architecture/github-xml-rendering.md))
- Closing marker: `<!-- /erk:metadata-block:session-content -->`

### Example

````markdown
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>Session Data (1/3): fix-auth-bug</strong></summary>

**Extraction Hints:**

- Error handling patterns with subprocess
- Test fixture setup for CLI commands

```xml
<session>
  <user>Can you fix the authentication bug?</user>
  <assistant>Let me investigate the auth flow...</assistant>
  <tool_result name="Read">
    <file_path>src/auth.py</file_path>
    ...
  </tool_result>
</session>
```

</details>
<!-- /erk:metadata-block:session-content -->
````

### Key Features

- **Chunking**: Large sessions can be split across multiple numbered blocks (e.g., "1/3", "2/3", "3/3")
- **Optional labels**: Session labels help identify the context (e.g., "fix-auth-bug")
- **Extraction hints**: Bulleted list highlighting key patterns or insights to extract
- **XML code fences**: Required to prevent GitHub from interpreting XML tags as HTML (see [XML rendering docs](../architecture/github-xml-rendering.md))

### When to Use

Session-content blocks are used in extraction plans (plans created by `/erk:create-extraction-plan` or `/erk:create-raw-extraction-plan`) to provide session context that implementing agents should analyze and extract patterns from.

## HTML Comment Markers

All metadata blocks use consistent markers:

```html
<!-- erk:metadata-block:{key} -->
...content...
<!-- /erk:metadata-block:{key} -->
```

The closing tag may also omit the key: `<!-- /erk:metadata-block -->`

## Validation

Use `erk plan check` to validate plan issues:

```bash
erk plan check 123
```

This validates:

- [PASS/FAIL] plan-header metadata block present
- [PASS/FAIL] plan-header has required fields
- [PASS/FAIL] First comment exists
- [PASS/FAIL] plan-body content extractable

## Python API

Key functions in `erk_shared.github.metadata`:

```python
# Create plan-header for issue body
from erk_shared.github.metadata import format_plan_header_body

body = format_plan_header_body(
    created_at=timestamp,
    created_by=username,
    plan_type="extraction",  # Optional
    source_plan_issues=[123],  # For extraction plans
    extraction_session_ids=["abc123"],  # For extraction plans
)

# Create plan-body for first comment
from erk_shared.github.metadata import format_plan_content_comment

comment = format_plan_content_comment(plan_content)

# Extract plan from comment
from erk_shared.github.metadata import extract_plan_from_comment

plan = extract_plan_from_comment(comment_body)

# Find metadata block
from erk_shared.github.metadata import find_metadata_block

block = find_metadata_block(issue_body, "plan-header")
if block:
    created_by = block.data.get("created_by")
```

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Full plan lifecycle from creation to merge
- [Kit CLI Commands](../kits/cli-commands.md) - Commands that create/update plans
