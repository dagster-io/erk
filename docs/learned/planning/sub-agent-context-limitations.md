---
title: Sub-Agent Context Limitations
read_when:
  - debugging impl-signal failures, working with CLAUDE_SESSION_ID, delegating to Task tool sub-agents, implementing plan-save workflow
---

# Sub-Agent Context Limitations

When the root Claude agent launches sub-agents via the Task tool, certain environment context is **not propagated** to the sub-agent. This creates silent failure modes where commands requiring session-specific context fail without clear errors.

## The Problem: CLAUDE_SESSION_ID Not Propagated

`${CLAUDE_SESSION_ID}` is an environment variable available to the **root agent** but **not to Task tool sub-agents**.

### Example Failure Pattern

Root agent delegates plan implementation to a sub-agent:

```python
# Root agent launches sub-agent
task_tool(
    subagent_type="Plan",
    prompt="Implement the plan in .impl/plan.md"
)
```

Sub-agent tries to signal GitHub:

```bash
# Inside sub-agent, this fails silently
erk exec impl-signal started --session-id="${CLAUDE_SESSION_ID}"
```

**Result**: Command outputs error JSON with `"error_type": "session-id-required"`, but the sub-agent may not surface this clearly.

## Why This Happens

**Root agent environment:**

- Has access to `${CLAUDE_SESSION_ID}` via Claude Code runtime
- Can substitute this variable when running bash commands

**Sub-agent environment:**

- Runs in isolated context via Task tool
- Does not inherit Claude Code environment variables
- `${CLAUDE_SESSION_ID}` expands to empty string

## Commands Affected

Any `erk exec` command that requires `--session-id` will fail in sub-agent context:

| Command                | Requires Session ID | Impact if Missing                                 |
| ---------------------- | ------------------- | ------------------------------------------------- |
| `impl-signal started`  | Yes                 | No GitHub comment posted for implementation start |
| `impl-signal ended`    | Yes                 | No GitHub comment posted for implementation end   |
| `plan-save-to-issue`   | Yes                 | Plan saved but not associated with session marker |
| `capture-session-info` | No (reads from env) | Returns empty values                              |

## Workaround: Root Agent Handles All Signaling

**Solution**: The root agent must execute all `impl-signal` commands before delegating to sub-agents.

### Correct Pattern

```python
# Root agent signals BEFORE delegating
bash("erk exec impl-signal started --session-id=\"${CLAUDE_SESSION_ID}\"")

# Then delegate implementation to sub-agent
task_tool(
    subagent_type="Plan",
    prompt="Implement the plan in .impl/plan.md"
)

# Root agent signals AFTER sub-agent completes
bash("erk exec impl-signal ended --session-id=\"${CLAUDE_SESSION_ID}\"")
```

### Wrong Pattern

```python
# Root agent delegates immediately
task_tool(
    subagent_type="Plan",
    prompt="""
    Implement the plan in .impl/plan.md

    Remember to run:
    - erk exec impl-signal started --session-id="${CLAUDE_SESSION_ID}"
    - erk exec impl-signal ended --session-id="${CLAUDE_SESSION_ID}"
    """
)
# Sub-agent will fail to signal (no session ID available)
```

## Detecting This Issue

**Symptom**: Command returns JSON with `"success": false` and `"error_type": "session-id-required"`:

```json
{
  "success": false,
  "event": "started",
  "error_type": "session-id-required",
  "message": "Session ID required for impl-signal started. Ensure ${CLAUDE_SESSION_ID} is available in the command context."
}
```

**Root Cause**: The command was executed in a context without `CLAUDE_SESSION_ID` (likely a sub-agent).

## Design Implication

When designing workflows that involve sub-agents:

1. **Identify session-dependent commands** — Any command using `${CLAUDE_SESSION_ID}`
2. **Execute them in root agent** — Before or after sub-agent delegation
3. **Document the limitation** — Make it clear which commands cannot be delegated

## Related Documentation

- [Plan Implementation Workflow](plan-implementation.md) — How root agent orchestrates signaling around sub-agent work
- [Session ID Access Patterns](../sessions/session-id-access.md) — When and where session ID is available
- [Impl Signal Commands](../cli/commands/impl-signal.md) — Commands requiring session context
