---
title: Session ID Substitution
read_when:
  - "writing slash commands that need session context"
  - "developing hooks that interact with Claude sessions"
  - "debugging session ID unavailable errors"
  - "passing session metadata to erk exec scripts"
---

# Session ID Substitution

Claude session IDs can be accessed in commands and hooks, but the mechanism differs between contexts. Understanding these differences prevents "session ID unavailable" errors.

## Context-Specific Mechanisms

### In Skills and Commands

**Method**: String substitution via `${CLAUDE_SESSION_ID}`

**Support**: Available since Claude Code 2.1.9

**Usage**:

```bash
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" --type plan
```

**How it works**:

- Claude Code intercepts the string `${CLAUDE_SESSION_ID}` before execution
- Substitutes the actual session ID value
- Passes the resolved command to the shell

**Availability**: Always available in skill and command contexts

### In Hooks

**Method**: Session ID passed via **stdin JSON**, not environment variables

**Usage** (in Python hook):

```python
import json
import sys

# Read hook input from stdin
hook_input = json.loads(sys.stdin.read())
session_id = hook_input.get("session_id")

# Generate command for Claude with interpolated value
command = f"erk exec marker create --session-id {session_id}"
print(command)  # stdout becomes system reminder for Claude
```

**Key difference**: Hooks receive session metadata as structured input, then **generate commands for Claude** that include the session ID value directly.

**Why not `${CLAUDE_SESSION_ID}` in hooks?**

- Hooks execute in Python, not in Claude's command interpolation context
- Hook output (stdout) becomes system reminders for Claude
- By the time Claude sees the output, it's already a plain string

### When Generating Commands for Claude from Hooks

If a hook needs to tell Claude to run a command with session ID:

```python
# Hook code (Python)
session_id = hook_input["session_id"]

# Generate command with actual value interpolated
output = f"erk exec marker create --session-id {session_id}"
print(output)
```

**Result**: Claude sees a system reminder containing:

```
erk exec marker create --session-id abc123-def456-...
```

Claude can then execute this exact command without needing substitution.

## Best-Effort Pattern

For commands where session ID may be unavailable (e.g., running outside Claude Code):

```bash
erk exec impl-signal started --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

**Components**:

- `2>/dev/null`: Suppress error output if command fails
- `|| true`: Ensure non-zero exit code doesn't halt execution

**When to use**:

- Session markers that are nice-to-have but not critical
- Commands that should work both inside and outside Claude Code
- Non-blocking telemetry or logging

## Error Handling

### Session ID Required but Unavailable

If a command absolutely requires session ID:

```bash
if [ -z "${CLAUDE_SESSION_ID}" ]; then
  echo "Error: Session ID required but not available"
  exit 1
fi

erk exec marker create --session-id "${CLAUDE_SESSION_ID}"
```

### Session ID Optional

If a command can work without session ID:

```bash
# Use session ID if available, skip if not
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || \
  erk exec marker create --no-session
```

## Documentation in AGENTS.md

From `AGENTS.md` Section "Claude Environment Manipulation":

> **In skills/commands**: Use `${CLAUDE_SESSION_ID}` string substitution (supported since Claude Code 2.1.9)
>
> **In hooks**: Hooks receive session ID via **stdin JSON**, not environment variables. When generating commands for Claude from hooks, interpolate the actual value.

This is the canonical reference for session ID access patterns.

## Common Mistakes

### 1. Using ${CLAUDE_SESSION_ID} in Hook Output

**Wrong**:

```python
# In hook code
print(f"erk exec marker --session-id ${CLAUDE_SESSION_ID}")
```

**Right**:

```python
# In hook code
session_id = hook_input["session_id"]
print(f"erk exec marker --session-id {session_id}")
```

### 2. Expecting Environment Variable in Hooks

**Wrong**:

```python
# In hook code
session_id = os.environ["CLAUDE_SESSION_ID"]  # Doesn't exist!
```

**Right**:

```python
# In hook code
hook_input = json.loads(sys.stdin.read())
session_id = hook_input["session_id"]
```

### 3. Not Handling Unavailable Session ID

**Wrong**:

```bash
# In command - will error outside Claude Code
erk exec marker --session-id "${CLAUDE_SESSION_ID}"
```

**Right**:

```bash
# In command - gracefully handles unavailability
erk exec marker --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

## Related Documentation

- [Hook Development](../hooks/hook-development.md) - Hook stdin/stdout contracts
- [Command Development](command-development.md) - Writing robust commands
- [AGENTS.md](../../AGENTS.md) - Canonical session ID documentation
