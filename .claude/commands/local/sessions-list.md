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
- Relative time (e.g., "2h ago")
- Summary (first user message, truncated)

---

## Agent Instructions

### Step 1: Get Sessions List

```bash
erk exec list-sessions
```

Parse the JSON output which contains:

- `success`: Whether the operation succeeded
- `branch_context`: Git branch information (current_branch, trunk_branch, is_on_trunk)
- `current_session_id`: The session ID from SESSION_CONTEXT env (if available)
- `sessions`: List of session objects with:
  - `session_id`: Full session ID
  - `mtime_display`: Formatted date (e.g., "Dec 3, 11:38 AM")
  - `mtime_relative`: Relative time (e.g., "2h ago")
  - `summary`: First user message (truncated)
  - `is_current`: True if this is the current session
- `project_dir`: Path to the project directory

### Step 2: Display Results

Format the JSON output as a table:

```
Session ID   Date                 Relative   Summary
─────────────────────────────────────────────────────────────────────────────
4f852cdc     Dec 3, 11:38 AM      2h ago     how many session ids does this... (current)
d8f6bb38     Dec 3, 11:35 AM      2h ago     no rexporting due to backwards...
d82e9306     Dec 3, 11:28 AM      3h ago     /gt:pr-submit
b5a65c0a     Dec 3, 11:26 AM      3h ago     /erk:merge-conflicts-fix
c02881d4     Dec 3, 11:20 AM      3h ago     /gt:pr-submit
bf38066f     Dec 3, 11:20 AM      3h ago     /erk:system:impl-execute
```

Notes:

- Show "(current)" suffix for the session marked `is_current: true`
- Truncate session_id to first 8 characters for display
- Use the first 40 characters of summary for display

If no sessions found, display:

```
No sessions found for this worktree.
```

If error occurred, display the error message from the JSON.
