---
description: List recent sessions for the current worktree
---

# /erk:sessions-list

Lists the 10 most recent Claude Code sessions associated with the current worktree.

## Usage

```bash
/erk:sessions-list
```

## Output

Displays a table with:

- Session ID (first 8 chars)
- Date/time of last activity
- Summary (first user message, truncated)
- Size indicator (correlates with message count)

---

## Agent Instructions

### Step 1: Get Project Directory

```bash
dot-agent run erk find-project-dir
```

Parse the JSON output to get:

- `project_dir`: Path to session logs
- `session_logs`: List of session filenames

### Step 2: Filter and Sort Sessions

From `session_logs`, filter out agent logs (starting with `agent-`) and sort by modification time (most recent first). Take the first 10.

### Step 3: Extract Summary for Each Session

For each session file, read the first 50 lines and extract:

1. **Session ID**: From filename (stem without `.jsonl`)
2. **Modification time**: From file stat
3. **First user message**: Find first entry with `type: "user"`, extract first 60 chars of text content

### Step 4: Display Results

Output a formatted table:

```
Session ID   Date                 Summary
─────────────────────────────────────────────────────────────────────
4f852cdc     Dec 3, 11:38 AM      how many session ids does this corres...
d8f6bb38     Dec 3, 11:35 AM      no rexporting due to backwards compat...
d82e9306     Dec 3, 11:28 AM      /gt:pr-submit
b5a65c0a     Dec 3, 11:26 AM      /erk:merge-conflicts-fix
c02881d4     Dec 3, 11:20 AM      /gt:pr-submit
bf38066f     Dec 3, 11:20 AM      /erk:plan-implement
```

If no sessions found, display:

```
No sessions found for this worktree.
```
