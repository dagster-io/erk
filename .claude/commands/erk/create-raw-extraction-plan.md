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
- `branch_context.branch_name` for session labeling

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

Get session ID from SESSION_CONTEXT reminder and branch name from discovery output.

**Session Content Formatting:**

Write the preprocessed session XML to a scratch file, then use the `render-session-content` CLI command:

```bash
# Write preprocessed session XML to scratch directory
# Agent writes output to .erk/scratch/<session-id>/session-content.xml

# Render session content blocks
dot-agent run erk render-session-content \
    --session-file=.erk/scratch/<session-id>/session-content.xml \
    --session-label="<branch-name>" \
    --extraction-hints="Session data for future documentation extraction"
```

Parse the JSON output to get the `blocks` array:

```json
{
  "success": true,
  "blocks": ["<rendered-block-1>", "<rendered-block-2>"],
  "chunk_count": 2
}
```

This produces properly formatted metadata blocks:

- XML wrapped in code fences (prevents markdown rendering issues)
- Collapsible `<details>` sections
- Numbered chunks if content exceeds 64K limit (e.g., "Session Data (1/3)")
- Session label in summary (branch name)

**Note:** Using scratch directory (`.erk/scratch/<session-id>/`) instead of `/tmp/` follows the project's AI workflow file conventions per `docs/agent/planning/scratch-storage.md`.

**Create the issue:**

```bash
dot-agent run erk create-extraction-plan \
    --plan-content="<issue-body-content>" \
    --session-id="<current-session-id>" \
    --extraction-session-ids="<comma-separated-session-ids>"
```

Where `<issue-body-content>` should be a brief description (the session content goes in comments):

```markdown
# Raw Session Context

This issue contains raw preprocessed session data from the landed PR.

See comments below for session XML content.
```

**If multiple comment bodies are returned (chunked content):**

Post each as a separate comment to the created issue:

```bash
gh issue comment <issue-number> --body "<comment-body>"
```

### Step 5: Delete Pending Extraction Marker

After successfully creating the extraction issue, delete the pending extraction marker:

```bash
dot-agent run erk marker-delete pending-extraction
```

This allows the user to delete the worktree without needing `--force`.

### Step 6: Output Result

Output JSON to stdout for the caller to parse:

```json
{ "issue_url": "<the-created-issue-url>", "chunks": <number-of-comments> }
```

If no sessions were found or preprocessing failed, output:

```json
{ "issue_url": null, "error": "<error-message>" }
```

**Note:** The pending extraction marker is NOT deleted if extraction fails. This ensures the user is reminded to extract insights before cleanup.
