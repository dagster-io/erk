---
title: Plan Lookup Strategy
read_when:
  - "debugging plan lookup issues"
  - "understanding plan file discovery"
  - "troubleshooting wrong plan saved"
---

# Plan Lookup Strategy

This document describes the 3-tier priority system for finding plan files when saving or implementing plans.

## Priority Order

When erk needs to locate a plan file, it checks these locations in order:

| Priority | Source                           | Condition                |
| -------- | -------------------------------- | ------------------------ |
| 1        | `--plan-file` CLI argument       | Always checked first     |
| 2        | Scratch storage (session-scoped) | Only with `--session-id` |
| 3        | `~/.claude/plans/` (mtime-based) | Fallback                 |

## Session-Scoped Lookup

When a `--session-id` is provided, erk looks for plans in scratch storage first:

```
{repo_root}/.erk/scratch/sessions/{session-id}/plan-*.md
```

This ensures the correct plan is used even when multiple sessions run in parallel.

## Mtime-Based Fallback

Without a session ID, erk falls back to `~/.claude/plans/` and selects the most recently modified plan file. This is acceptable for single-session workflows but can cause issues with parallel sessions.

## Decision Tree

```
Plan file requested
    │
    ├─ --plan-file provided?
    │   └─ YES → Use specified file
    │
    ├─ --session-id provided?
    │   └─ YES → Check scratch storage
    │       ├─ Found? → Use session plan
    │       └─ Not found? → Continue to fallback
    │
    └─ Check ~/.claude/plans/
        └─ Use most recent by mtime
```

## Troubleshooting

### Wrong Plan Saved

**Symptom**: Issue created contains a different plan than expected.

**Cause**: Multiple sessions running in parallel, mtime-based lookup selected another session's plan.

**Solution**: Always pass `--session-id` to `erk exec plan-save-to-issue`:

```bash
erk exec plan-save-to-issue --session-id "${CLAUDE_SESSION_ID}" --format json
```

### Plan Not Found

**Symptom**: "No plan file found" error.

**Causes**:

1. Plan was never saved (Claude Code didn't write to `~/.claude/plans/`)
2. Session ID doesn't match any scratch storage
3. Plan file was already consumed (deleted after save)

**Diagnosis**:

```bash
# Check scratch storage
ls .erk/scratch/sessions/*/

# Check Claude plans directory
ls -la ~/.claude/plans/
```

## Implementation Reference

See `find_plan_for_session()` in `src/erk/cli/commands/exec/scripts/` for the canonical implementation.

## Related Documentation

- [Scratch Storage](scratch-storage.md) - Session-scoped file storage
- [Parallel Session Awareness](../sessions/parallel-session-awareness.md) - Why session scoping matters
