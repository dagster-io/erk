---
description: Create extraction plan with raw session context (no analysis)
---

# /erk:create-raw-extraction-plan

Creates a GitHub issue containing raw preprocessed session data. Used by `erk pr land --extract` for capturing session context without analysis.

## Agent Instructions

### Step 1: Discover Sessions

Run session discovery:

```bash
dot-agent run erk list-sessions --min-size 1024
```

Parse the JSON output to get:

- `current_session_id` from SESSION_CONTEXT
- `sessions` list with metadata
- `project_dir` for session log paths
- `branch_context.is_on_trunk` for selection logic

### Step 2: Auto-Select Sessions

Use the same auto-selection logic as `/erk:create-extraction-plan`:

- If on trunk: use current session only
- If current session is trivial (<1KB) AND 1+ substantial sessions exist: auto-select substantial sessions
- If current session is substantial: use it

**No user prompts** - this command always auto-selects.

### Step 3: Preprocess Sessions

For each selected session, run preprocessing:

```bash
dot-agent run erk preprocess-session <project_dir>/<session_id>.jsonl --stdout
```

Capture the output XML. If multiple sessions, concatenate them with session ID headers.

### Step 4: Create Issue with Raw Context

Get session ID from SESSION_CONTEXT reminder. Create GitHub issue:

```bash
dot-agent run erk create-extraction-plan \
    --plan-content="<content>" \
    --session-id="<current-session-id>" \
    --extraction-session-ids="<comma-separated-session-ids>"
```

Where `<content>` should be:

```markdown
# Raw Session Context

This issue contains raw preprocessed session data from the landed PR.

## Session XML

<the preprocessed XML content>
```

**Size limit handling (65,536 char max for issue comments):**

1. If the CLI returns an error related to content size, warn the user
2. Truncate content to 65,000 characters (leaving buffer)
3. Add truncation notice at the end of content
4. Retry with truncated content

### Step 5: Output Result

Output JSON to stdout for the caller to parse:

```json
{ "issue_url": "<the-created-issue-url>" }
```

If content was truncated, also display a warning to stderr:

```
Warning: Session content truncated to 65,000 characters (original: X chars)
```

If no sessions were found or preprocessing failed, output:

```json
{ "issue_url": null, "error": "<error-message>" }
```
