---
title: Session ID Availability
read_when:
  - "using ${CLAUDE_SESSION_ID} in commands"
  - "debugging session ID errors"
  - "implementing session tracking"
  - "writing slash commands that need session context"
---

# Session ID Availability

The `${CLAUDE_SESSION_ID}` environment variable is available in **some** but not all execution contexts. Understanding when it's available prevents confusing failures.

## Availability by Context

| Context                      | ${CLAUDE_SESSION_ID} Available | Notes                                            |
| ---------------------------- | ------------------------------ | ------------------------------------------------ |
| Slash commands               | ✅ Yes                         | String substitution by Claude Code               |
| Skills                       | ✅ Yes                         | String substitution by Claude Code               |
| Direct agent invocation      | ✅ Yes                         | If agent was spawned by Claude Code              |
| Exec scripts called directly | ❌ No                          | Running `erk exec foo` from shell has no session |
| Background processes         | ❌ No                          | Detached from Claude context                     |
| CI/CD workflows              | ❌ No                          | No interactive Claude session                    |

## String Substitution vs Environment Variable

**Critical distinction:** `${CLAUDE_SESSION_ID}` is **not** a shell environment variable. It's a Claude Code string substitution that happens **before** the command executes.

### In Slash Commands and Skills

```bash
# This works - Claude Code substitutes before execution
erk exec impl-signal started --session-id="${CLAUDE_SESSION_ID}"

# Claude Code transforms this to:
erk exec impl-signal started --session-id="abc-123-def"
```

### In Hook Scripts

Hooks receive session ID via **stdin JSON**, not environment:

```python
# Hook receives:
{"session_id": "abc-123-def", "tool_name": "Read", ...}

# Hook interpolates for Claude:
print(f"erk exec marker create --session-id {data['session_id']}")
```

The hook outputs a command string that Claude then executes with substitution applied.

## Expected Failures

Some erk exec commands **require** session ID but may fail gracefully:

```bash
erk exec impl-signal started --session-id="${CLAUDE_SESSION_ID}"
# Error: Session ID required for impl-signal started.
```

This is **expected** when:

- Testing commands directly from shell
- Running in CI without session context
- Command is called from non-Claude context

**Design pattern:** Commands that need session ID should accept it as required argument and fail clearly when missing.

## Graceful Degradation Pattern

Commands should handle missing session ID appropriately:

```python
def my_command(session_id: str | None) -> None:
    if session_id is None:
        # Graceful: Skip session-dependent features
        console.info("Session ID not available, skipping tracking")
        return

    # Use session ID for tracking
    save_marker(session_id=session_id)
```

**When to use:**

- Features that enhance but aren't required
- Telemetry and tracking
- Debug information

**When to fail hard:**

- Core functionality depends on session
- Data corruption risk without session context
- User explicitly requested session-dependent operation

## Alternative: Session File Discovery

When session ID isn't available but session file is needed, use file discovery:

```bash
# Find current session file
CURRENT_SESSION=$(ls -t ~/.claude/projects/*/session.jsonl | head -1)
```

**Limitations:**

- May find wrong session in parallel execution
- Requires filesystem access
- Race conditions possible

## Testing Without Session ID

In tests, always provide explicit session ID:

```python
def test_session_dependent_command():
    result = run_command(
        ["erk", "exec", "impl-signal", "started", "--session-id=test-123"]
    )
    assert result.success
```

Don't rely on `${CLAUDE_SESSION_ID}` substitution in tests.

## Related Documentation

- [Plan-Implement Workflow](plan-implement.md) - Session upload for async learn
- [Session Preprocessing](../sessions/preprocessing.md) - Processing session files
- [Hooks](../hooks/) - Hook stdin protocol
