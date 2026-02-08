---
title: Session ID Substitution
read_when:
  - writing slash commands or skills that need session context
  - developing hooks that interact with Claude sessions
  - debugging session ID unavailable or empty string errors
  - deciding where to place session-dependent logic (root agent vs sub-agent)
tripwires:
  - action: "treating CLAUDE_SESSION_ID as an environment variable in hooks or Python code"
    warning: "CLAUDE_SESSION_ID is NOT an environment variable — it is a string substitution performed by Claude Code's skill/command loader. Treating it as an env var in hooks or Python code will silently produce an empty string."
last_audited: "2026-02-08"
audit_result: clean
---

# Session ID Substitution

## Why Two Mechanisms Exist

Claude Code provides session IDs through two completely different channels depending on execution context. This matters because using the wrong mechanism produces silent failures — an empty string where the session ID should be, with no error.

**Skills and commands** run inside Claude Code's markdown expansion layer, which performs `${CLAUDE_SESSION_ID}` string substitution before the shell ever sees the text. This is a Claude Code feature, not a shell variable — it only works in `.claude/commands/` and `.claude/skills/` markdown content.

**Hooks** run as external processes invoked by Claude Code. They receive session context as JSON on **stdin**, not through environment variables or string substitution. The `@hook_command` decorator in erk abstracts this, injecting a `HookContext` with the session ID already extracted.

## Decision Table

| Context           | Mechanism                          | Why It Works This Way                                                   |
| ----------------- | ---------------------------------- | ----------------------------------------------------------------------- |
| Skills / Commands | `${CLAUDE_SESSION_ID}` in markdown | Claude Code expands this before shell execution                         |
| Hooks             | stdin JSON → `HookContext`         | Hooks are external processes; Claude Code passes context via stdin pipe |
| Sub-agents        | **Neither** — not propagated       | Task tool sub-agents don't inherit Claude Code's string substitution    |

## The Sub-Agent Boundary

`${CLAUDE_SESSION_ID}` only works in the **root agent**. Task tool sub-agents run in isolated context and the substitution produces an empty string. This means any command requiring a session ID must be executed by the root agent before or after sub-agent delegation, never inside the sub-agent.

See [Sub-Agent Context Limitations](../planning/sub-agent-context-limitations.md) for the full pattern.

## Best-Effort Pattern

When session ID is useful but not critical (markers, telemetry, logging), suppress failures:

```bash
erk exec impl-signal started --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

This prevents errors when running outside Claude Code or in contexts where the substitution isn't available.

## Anti-Patterns

### Treating the substitution as an environment variable in hooks

```python
# WRONG: No such env var exists — this raises KeyError
session_id = os.environ["CLAUDE_SESSION_ID"]
```

Hooks receive session ID via stdin JSON. Use the `@hook_command` decorator which provides `hook_ctx.session_id`.

<!-- Source: src/erk/hooks/decorators.py, HookContext -->

See `HookContext` and `_extract_session_id()` in `src/erk/hooks/decorators.py` for the extraction implementation.

### Emitting `${CLAUDE_SESSION_ID}` in hook stdout for Claude to execute

```python
# WRONG: Python f-string won't expand Claude's substitution syntax
print(f"erk exec marker --session-id ${{CLAUDE_SESSION_ID}}")
```

Hook stdout becomes system reminders in Claude's context, but string substitution doesn't apply to system reminders — only to command/skill markdown. Interpolate the actual value read from stdin JSON instead.

### Omitting error suppression in commands

```bash
# WRONG: Hard failure outside Claude Code
erk exec marker --session-id "${CLAUDE_SESSION_ID}"
```

If the command is non-critical, always append `2>/dev/null || true`. If the command is critical, validate the session ID before proceeding and surface a clear error.

## Related Documentation

- **AGENTS.md** "Claude Environment Manipulation" section — canonical reference for both mechanisms
- [Sub-Agent Context Limitations](../planning/sub-agent-context-limitations.md) — propagation boundary details
- [Scratch Storage](../planning/scratch-storage.md) — session-scoped storage that depends on session ID availability
