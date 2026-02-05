---
title: Devrun Agent - Read-Only Design
read_when:
  - "using the devrun agent"
  - "running CI checks via Task tool"
  - "debugging devrun agent failures"
  - "writing prompts for devrun"
tripwires:
  - action: "asking devrun agent to fix errors or make tests pass"
    warning: "Devrun is READ-ONLY. It runs commands and reports results. The parent agent must handle all fixes."
last_audited: "2026-02-05"
audit_result: edited
---

# Devrun Agent - Read-Only Design

The `devrun` agent is a specialized Task subagent for running development CLI tools (pytest, ty, ruff, prettier, make, gt). Its critical constraint: **it never modifies files**.

For the complete operational contract (tool access, command normalization, reporting format), see `.claude/agents/devrun.md`.

## Why This Design?

**Separation of concerns:** Devrun handles command execution and output parsing (stateless). The parent agent handles code changes and iteration logic (stateful).

**Clear failure attribution:** When devrun reports failures, it's unambiguous that the parent must act. No confusion about whether the agent "tried to fix" something.

**Iteration loop:** The parent drives the fix cycle:

1. Parent sends: "Run pytest and report results"
2. Devrun reports failures
3. Parent fixes code using Edit/Write tools
4. Parent sends: "Run pytest again and report results"
5. Repeat until passing

## Common Mistakes

### Delegating fix responsibility

```
# WRONG
"Run make fast-ci and fix any issues"

# CORRECT
"Run make fast-ci and report results"
```

### Asking for iterative fixing

```
# WRONG
"Keep running pytest until all tests pass"

# CORRECT
"Run pytest and report results"
# [Parent fixes, then re-invokes devrun]
```

### Expecting devrun to track state

```
# WRONG
"Continue fixing the remaining test failures"
# [Devrun is stateless - doesn't know "remaining"]

# CORRECT
# [Parent maintains state, fixes specific issues, re-invokes devrun]
"Run pytest and report results"
```

## Related Documentation

- `.claude/agents/devrun.md` — Agent definition with complete operational contract
- [AGENTS.md](../../../AGENTS.md) — Devrun agent routing rules
