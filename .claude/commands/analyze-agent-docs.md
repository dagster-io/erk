---
description: Analyze session logs to show which agent docs were read and why
---

# /analyze-agent-docs

Analyzes the current session(s) to identify which agent documentation files (`docs/agent/`) were read and the context/reason for reading them.

## Instructions

### Step 1: Discover Sessions

Run:

```bash
dot-agent run erk list-sessions --min-size 1024
```

Parse the JSON to get:

- `project_dir` - Base path for session files
- `sessions` - List of session metadata
- `branch_context.is_on_trunk` - Whether on trunk branch
- `current_session_id` - From SESSION_CONTEXT

### Step 2: Select Sessions

Apply auto-selection:

- If `is_on_trunk`: Use current session only
- Else if current session < 1024 bytes AND substantial sessions exist: Use substantial sessions
- Else: Use current session

### Step 3: Parse Session Logs

For each selected session:

1. Read `<project_dir>/<session_id>.jsonl`
2. Parse each JSON line
3. Find entries where:
   - `type` is `"assistant"`
   - `message.content` contains objects with `type: "tool_use"` and `name: "Read"`
   - The `input.file_path` contains `docs/agent/`

### Step 4: Extract Context

For each agent doc read found:

1. Note the entry index
2. Look backwards to find the most recent:
   - `type: "user"` entry → extract `message.content` text (user request)
   - `type: "assistant"` text block (not tool_use) → extract reasoning
3. Summarize the context in one sentence

### Step 5: Output Markdown Table

Output a markdown table:

```markdown
## Agent Documentation Reads

**Session(s) analyzed:** <session-ids>
**Total docs read:** <count>

| File | Context/Reason |
|------|----------------|
| `<file-path>` | <context-summary> |
...
```

If no agent docs were read, output:

```markdown
## Agent Documentation Reads

No `docs/agent/` files were read in the analyzed session(s).
```

### Notes

- Deduplicate files if read multiple times (list once, aggregate contexts)
- Sort by order of first read
- Truncate long context summaries to ~80 characters
