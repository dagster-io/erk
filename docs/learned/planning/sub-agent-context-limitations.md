---
title: Sub-Agent Context Limitations
read_when:
  - delegating session-dependent commands to Task tool sub-agents
  - debugging impl-signal or plan-save-to-issue failures with empty session IDs
  - designing workflows that split work between root agent and sub-agents
tripwires:
  - action: "including impl-signal or plan-save-to-issue in a Task tool sub-agent prompt"
    warning: "Sub-agents cannot access ${CLAUDE_SESSION_ID}. Session-dependent commands must run in the root agent context. See sub-agent-context-limitations.md."
  - action: "passing ${CLAUDE_SESSION_ID} to a sub-agent via the prompt string"
    warning: "String substitution of ${CLAUDE_SESSION_ID} happens at the root agent level. By the time the sub-agent runs the bash command, the variable is not in its environment. The root agent must resolve the value and pass it as a literal."
---

# Sub-Agent Context Limitations

`${CLAUDE_SESSION_ID}` is a Claude Code runtime variable available only to the **root agent**. Task tool sub-agents run in isolated contexts that do not inherit Claude Code environment variables. This creates a cross-cutting constraint: any `erk exec` command requiring `--session-id` will silently fail when delegated to a sub-agent, because the variable expands to an empty string.

## Why Sub-Agents Can't Access Session ID

Claude Code injects `${CLAUDE_SESSION_ID}` as a string substitution at the root agent level — it is not a shell environment variable that propagates to child processes. When a root agent launches a sub-agent via the Task tool, the sub-agent gets a fresh, isolated execution context. There is no mechanism for Claude Code runtime variables to flow across this boundary.

This is a platform-level constraint, not something erk can work around in its own code. The erk commands validate the session ID and return structured errors rather than failing silently, but the fundamental limitation is in how the Task tool isolates sub-agent environments.

## Commands Affected

Any `erk exec` command accepting `--session-id` degrades when run from a sub-agent:

| Command               | Session ID Role                                         | Impact When Missing                                                         |
| --------------------- | ------------------------------------------------------- | --------------------------------------------------------------------------- |
| `impl-signal started` | Links GitHub comment to session, deletes plan file      | No GitHub comment, plan file persists                                       |
| `impl-signal ended`   | Links ended event to session                            | No GitHub metadata update                                                   |
| `plan-save-to-issue`  | Session-scoped plan lookup, deduplication, snapshotting | Falls back to latest-by-mtime (may pick wrong plan), no deduplication guard |

<!-- Source: src/erk/cli/commands/exec/scripts/impl_signal.py, _signal_started -->

The `impl-signal` command validates session ID upfront and returns a structured error (see diagnostic output below) rather than proceeding with empty state — this is intentional graceful degradation so the `|| true` pattern in `/erk:plan-implement` doesn't mask the failure entirely.

## The Root-Agent-First Pattern

The solution is architectural: **session-dependent commands must always run in the root agent**, not be delegated. The `/erk:plan-implement` command already follows this pattern — it runs `impl-signal started` and `impl-signal ended` directly (Steps 6 and 10) rather than including them in any sub-agent prompt.

This creates a sandwich pattern: root agent handles session-bound bookkeeping (signal start, signal end, upload session), while the actual implementation work in between can safely be delegated.

### Anti-Pattern: Delegating Signaling to Sub-Agents

```
WRONG — sub-agent cannot resolve ${CLAUDE_SESSION_ID}:

Task(prompt="Implement the plan. When done, run:
  erk exec impl-signal ended --session-id=${CLAUDE_SESSION_ID}")
```

The string `${CLAUDE_SESSION_ID}` appears literally in the sub-agent's prompt but is not substituted — the sub-agent's bash execution expands it to empty.

## Diagnostic Output

When `impl-signal` receives an empty or missing session ID, it outputs:

```json
{
  "success": false,
  "event": "started",
  "error_type": "session-id-required",
  "message": "Session ID required for impl-signal started. Ensure ${CLAUDE_SESSION_ID} is available in the command context."
}
```

If you see `session-id-required` errors, the command was executed outside the root agent context.

## Design Rules for New Workflows

When adding new `erk exec` commands or slash commands that involve sub-agent delegation:

1. **Classify each command** as session-dependent or session-independent before designing the workflow
2. **Keep session-dependent commands in the root agent** — run them before or after sub-agent delegation, never during
3. **Pass resolved values, not variable references** — if a sub-agent needs a session ID for any reason, the root agent must resolve it to a literal string first

<!-- Source: .claude/commands/erk/plan-implement.md:182-219 -->

The `/erk:plan-implement` command is the canonical example of this pattern — see Steps 6 and 10 for how signaling brackets the implementation work.
