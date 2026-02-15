---
title: Claude CLI Execution Modes
read_when:
  - "writing commands that run in both interactive and CI contexts"
  - "debugging commands that work locally but fail in GitHub Actions"
  - "understanding --print mode behavioral differences"
---

# Claude CLI Execution Modes

## Overview

Claude CLI has two primary execution modes with different behavioral characteristics.

## Mode Comparison

| Feature                   | Interactive Mode       | `--print` Mode (CI)         |
| ------------------------- | ---------------------- | --------------------------- |
| Invocation                | `/command` or `claude` | `claude --print "/command"` |
| Used by                   | Local development      | GitHub Actions workflows    |
| Stdin interaction         | Yes                    | No                          |
| `context: fork` isolation | Yes                    | **No** (loads inline)       |
| Task tool isolation       | Yes                    | Yes                         |
| Multi-turn tool use       | Yes                    | Yes                         |

## The Critical Difference: Subagent Isolation

The most significant behavioral difference affects subagent creation:

**context: fork**:

- Interactive: Creates separate agent context with own session ID
- `--print`: Loads skill content inline, contaminating parent context

**Task tool**:

- Interactive: Creates separate agent context
- `--print`: Creates separate agent context (works identically)

## Testing Commands for Both Modes

Commands destined for CI workflows should be tested in both modes:

```bash
# Interactive test
/your-command args

# CI simulation
claude --print "/your-command args"
```

Verify:

1. All phases execute (not just first phase)
2. Expected artifacts are produced
3. Session logs show separate session IDs for subagent work

## When to Use Task Tool

Use explicit Task tool delegation (not `context: fork`) when:

- Command will run via `--print` in CI
- Skill has terminal output instructions
- Multi-phase workflow where isolation failure would be catastrophic
- You need guaranteed isolation regardless of execution mode

See `.claude/commands/erk/pr-address.md` for an implementation example (grep for "Task tool").

## Related Documentation

- [Context Fork Feature](../claude-code/context-fork-feature.md) — Execution mode limitations
- [Task Context Isolation Pattern](task-context-isolation.md) — CI context constraints and Task delegation
- [Multi-Phase Command Patterns](../commands/multi-phase-command-patterns.md) — Premature termination vulnerability
