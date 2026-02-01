---
read-when: using session ID in commands, writing hooks that need session context, accessing ${CLAUDE_SESSION_ID}, debugging session ID unavailability
tripwires: 0
---

# Session ID Availability in Claude Code

## Context Availability

Session ID is available in different ways depending on the execution context.

## In Skills and Slash Commands

Skills and slash commands can use **string substitution** with the `${CLAUDE_SESSION_ID}` variable:

```bash
# Skills can use this substitution directly
erk exec plan-save-to-issue --session-id "${CLAUDE_SESSION_ID}"
```

Claude Code performs the substitution before executing the command, replacing `${CLAUDE_SESSION_ID}` with the actual session ID.

**Supported since**: Claude Code 2.1.9

## In Hooks

Hooks receive session context via **stdin JSON**, NOT environment variables.

**WRONG (won't work)**:

```python
# This won't work - session ID is not in environment
session_id = os.environ.get("CLAUDE_SESSION_ID")
```

**CORRECT**:

```python
import sys
import json

# Read session context from stdin
hook_input = json.loads(sys.stdin.read())
session_id = hook_input["session_id"]

# Generate command for Claude with interpolated session ID
command = f"erk exec plan-save-to-issue --session-id {session_id}"
print(command)
```

When hooks output commands for Claude to execute, they must interpolate the actual session ID value (not use `${CLAUDE_SESSION_ID}` substitution).

## Why the Difference?

- **Skills/Commands**: Executed in Claude's shell context where substitution works
- **Hooks**: Executed as separate processes receiving JSON input, generating commands for Claude

## Common Pattern: Plan Workflows

In erk plan mode:

**Slash command** (uses substitution):

```bash
erk exec plan-save-to-issue --session-id "${CLAUDE_SESSION_ID}"
```

**Hook** (uses stdin JSON):

```python
hook_data = json.loads(sys.stdin.read())
session_id = hook_data["session_id"]
output = f"erk exec plan-save-to-issue --session-id {session_id} ..."
print(output)
```

Both achieve the same result: passing the session ID to the command.

## Debugging Session ID Issues

If commands fail with "session ID required":

1. **Check context**: Are you in a hook or a skill/command?
2. **Hook context**: Verify stdin JSON parsing and field access
3. **Skill context**: Verify using `${CLAUDE_SESSION_ID}` substitution syntax
4. **Version**: Ensure Claude Code >= 2.1.9 for substitution support

## Related Documentation

- [Plan Persistence](../planning/plan-persistence.md) - Session ID in plan-save-to-issue
- [Hook Decision Flow](../planning/hook-decision-flow.md) - Exit-plan-mode hook options
- [Session-Based Plan Deduplication](../planning/session-deduplication.md) - Why session ID matters
