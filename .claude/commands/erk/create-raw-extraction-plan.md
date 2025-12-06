---
description: Create extraction plan with raw session context (no analysis)
---

# /erk:create-raw-extraction-plan

Creates a GitHub issue containing raw preprocessed session data. Used by `erk pr land --extract` for capturing session context without analysis.

## Agent Instructions

Run the raw extraction CLI command:

```bash
erk plan create-raw
```

This command handles the complete workflow:

- Discovers and auto-selects sessions from the project directory
- Preprocesses session content into XML format
- Creates a GitHub issue with comprehensive issue body
- Posts chunked session XML as comments (handles >64K content)
- Deletes pending extraction marker on success

**Output:** JSON with `issue_url`, `issue_number`, `chunks` count, and `sessions_processed`, or `error` if failed.

**Dynamic values** (handled automatically by Python orchestrator):

- `branch_name` - from current branch context
- `session_ids` - comma-separated list of processed session IDs
- `comment_count` - number of chunked content blocks

If extraction fails, output the error message and inform the user. The pending extraction marker is NOT deleted on failure, ensuring the user is reminded to extract insights before cleanup.
