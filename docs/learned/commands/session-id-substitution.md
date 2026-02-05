---
title: Session ID Substitution
read_when:
  - "writing slash commands that need session context"
  - "developing hooks that interact with Claude sessions"
  - "debugging session ID unavailable errors"
  - "passing session metadata to erk exec scripts"
last_audited: "2026-02-05"
audit_result: edited
---

# Session ID Substitution

Claude session IDs are accessed differently in commands vs hooks. Understanding the difference prevents "session ID unavailable" errors.

## Two Mechanisms

| Context         | Mechanism                                                            | Example                                                                       |
| --------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Skills/Commands | `${CLAUDE_SESSION_ID}` string substitution (since Claude Code 2.1.9) | `erk exec marker create --session-id "${CLAUDE_SESSION_ID}"`                  |
| Hooks           | Session ID via **stdin JSON** (`hook_input["session_id"]`)           | See `src/erk/hooks/decorators.py` — `@hook_command` extracts it automatically |

See AGENTS.md "Claude Environment Manipulation" section for the canonical reference.

## Best-Effort Pattern

For non-critical session markers in commands:

```bash
erk exec impl-signal started --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

Use this when session ID is nice-to-have but not critical (markers, telemetry, logging).

## Common Mistakes

### Using ${CLAUDE_SESSION_ID} in Hook Output

```python
# WRONG: Python doesn't expand Claude substitutions
print(f"erk exec marker --session-id ${{CLAUDE_SESSION_ID}}")

# CORRECT: Interpolate the actual value from stdin JSON
session_id = hook_input["session_id"]
print(f"erk exec marker --session-id {session_id}")
```

### Expecting Environment Variable in Hooks

```python
# WRONG: No CLAUDE_SESSION_ID env var exists
session_id = os.environ["CLAUDE_SESSION_ID"]

# CORRECT: Read from stdin JSON (or use @hook_command decorator)
hook_input = json.loads(sys.stdin.read())
session_id = hook_input["session_id"]
```

### Not Handling Unavailable Session ID

```bash
# WRONG: Will error outside Claude Code
erk exec marker --session-id "${CLAUDE_SESSION_ID}"

# CORRECT: Gracefully handles unavailability
erk exec marker --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

## Related Documentation

- [AGENTS.md](../../AGENTS.md) — Canonical session ID documentation
- `src/erk/hooks/decorators.py` — Hook decorator that extracts session ID from stdin
