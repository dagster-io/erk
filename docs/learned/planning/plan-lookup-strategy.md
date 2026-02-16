---
title: Plan Lookup Strategy
read_when:
  - "debugging plan lookup issues"
  - "understanding plan file discovery"
  - "troubleshooting wrong plan saved"
last_audited: "2026-02-16 08:00 PT"
audit_result: clean
---

# Plan Lookup Strategy

This document describes the 4-tier priority system for finding plan files when saving or implementing plans.

## Priority Order

When `plan_save_to_issue` needs to locate a plan file, it checks these sources in order (see `plan_save_to_issue.py` lines 199-213):

| Priority | Source                                  | Condition                                        |
| -------- | --------------------------------------- | ------------------------------------------------ |
| 1        | `--plan-file` CLI argument              | Always checked first                             |
| 2        | Scratch storage `plan.md`               | Only with `--session-id`                         |
| 3        | Slug-based lookup in `~/.claude/plans/` | Only with `--session-id` (via `get_latest_plan`) |
| 4        | `~/.claude/plans/` (mtime-based)        | Fallback when no session or no slug found        |

## Session-Scoped Lookup (Priority 2)

When a `--session-id` is provided, erk first checks for a plan stored directly in scratch storage:

```
{repo_root}/.erk/scratch/sessions/{session-id}/plan.md
```

This ensures the correct plan is used even when multiple sessions run in parallel.

## Slug-Based Lookup (Priority 3)

If no plan exists in scratch storage, `ClaudeInstallation.get_latest_plan()` delegates to `find_plan_for_session()`, which extracts slug entries from the session's JSONL logs and looks for a matching file in `~/.claude/plans/{slug}.md`. This uses session identity rather than modification time.

## Mtime-Based Fallback (Priority 4)

Without a session ID (or when slug-based lookup fails), erk falls back to `~/.claude/plans/` and selects the most recently modified `*.md` file. This is acceptable for single-session workflows but can cause issues with parallel sessions.

## Decision Tree

```
Plan file requested
    │
    ├─ --plan-file provided?
    │   └─ YES → Use specified file
    │
    ├─ --session-id provided?
    │   └─ YES → Check scratch storage (.erk/scratch/sessions/{id}/plan.md)
    │       ├─ Found? → Use session plan
    │       └─ Not found? → Slug-based lookup (extract slug from session logs)
    │           ├─ Slug found in ~/.claude/plans/{slug}.md? → Use it
    │           └─ Not found? → Continue to mtime fallback
    │
    └─ Check ~/.claude/plans/
        └─ Use most recent *.md by mtime
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
2. Session ID doesn't match any scratch storage or session log slugs
3. Plan file was already consumed (deleted after save)

**Diagnosis**:

```bash
# Check scratch storage
ls .erk/scratch/sessions/*/

# Check Claude plans directory
ls -la ~/.claude/plans/
```

## Implementation Reference

The lookup logic lives in two places:

- **`plan_save_to_issue.py`** (`src/erk/cli/commands/exec/scripts/`) orchestrates the 4-tier priority cascade (priorities 1-2, then delegates to `get_latest_plan` for 3-4).
- **`ClaudeInstallation.find_plan_for_session()`** (`packages/erk-shared/src/erk_shared/gateway/claude_installation/`) implements slug-based plan lookup via session log parsing.
- **`ClaudeInstallation.get_latest_plan()`** (same package) combines slug-based lookup with mtime fallback.

## Related Documentation

- [Scratch Storage](scratch-storage.md) - Session-scoped file storage
- [Parallel Session Awareness](../sessions/parallel-session-awareness.md) - Why session scoping matters
