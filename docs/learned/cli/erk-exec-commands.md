---
title: erk exec Commands
read_when:
  - "running erk exec subcommands"
  - "looking up erk exec syntax"
tripwires:
  - action: "running any erk exec subcommand"
    warning: "Check syntax with `erk exec <command> -h` first, or load erk-exec skill for workflow guidance."
---

# erk exec Commands

The `erk exec` command group contains utility scripts for automation and agent workflows.

## Usage Pattern

All erk exec commands use named options (not positional arguments for most parameters):

```bash
# Correct
erk exec get-pr-review-comments --pr 123

# Wrong - positional arguments don't work
erk exec get-pr-review-comments 123
```

## Key Commands by Category

See the `erk-exec` skill for complete workflow guidance and the full command reference.

### PR Operations

- `get-pr-review-comments` - Fetch PR review threads
- `resolve-review-thread` - Resolve a review thread
- `reply-to-discussion-comment` - Reply to PR discussion
- `handle-no-changes` - Handle zero-change implementation outcomes (called by erk-impl workflow)

### Plan Operations

- `plan-save-to-issue` - Save plan to GitHub
- `get-plan-metadata` - Read plan issue metadata
- `setup-impl-from-issue` - Prepare .impl/ folder

### Session Operations

- `list-sessions` - List Claude Code sessions
- `preprocess-session` - Compress session for analysis
- `impl-signal` - Signal implementation workflow state changes

## Command Reference: impl-signal

Signals implementation workflow state changes (started, completed, etc.) for plan tracking and cleanup.

**Required Parameters:**

- `--session-id`: Claude session ID for workflow tracking. Must be non-empty and non-whitespace.

**Validation Pattern:**

The command validates session IDs using a triple-check pattern:

1. Not None (parameter was provided)
2. Not empty string (`""`)
3. Not whitespace-only (e.g., `"   "`)

This defensive validation is necessary because `${CLAUDE_SESSION_ID}` substitution from workflow commands may fail silently, resulting in empty or whitespace values.

**Error Response:**

On validation failure, returns exit code 0 with JSON:

```json
{
  "success": false,
  "event": "started",
  "error_type": "session-id-required",
  "message": "Session ID required for impl-signal started..."
}
```

**Cross-reference:** See [Session ID Access](../architecture/erk-architecture.md) for why erk code never reads `CLAUDE_CODE_SESSION_ID` from environment.
