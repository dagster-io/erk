---
title: Session-Based Plan Deduplication
read_when:
  - "understanding duplicate plan prevention"
  - "working with exit-plan-mode hook"
  - "debugging duplicate issue creation"
tripwires:
  - action: "modifying marker deletion behavior in exit-plan-mode hook"
    warning: "Reusable markers (plan-saved) must persist; one-time markers (implement-now, objective-context) are consumed. Deleting reusable markers breaks state machines and enables retry loops that create duplicates."
---

# Session-Based Plan Deduplication

This document explains how erk prevents duplicate plan issues from being created during retry loops or hook edge cases.

## Problem

When Claude retries a blocked ExitPlanMode call, the same plan could be saved multiple times, creating duplicate GitHub issues. This can happen when:

1. Hook blocks with prompt → user chooses "save" → save succeeds → hook fires again
2. Network failures during save → retry creates second issue
3. Session interruption → user resumes → re-runs save command

## Two-Layer Defense

Erk uses two complementary mechanisms:

### Layer 1: Hook Blocking

The `exit-plan-mode-hook` uses markers to track state:

| Marker                              | Created By                         | Effect                       | Lifecycle |
| ----------------------------------- | ---------------------------------- | ---------------------------- | --------- |
| `exit-plan-mode-hook.plan-saved`    | `plan-save-to-issue`               | Block exit, msg shown        | Reusable  |
| `exit-plan-mode-hook.implement-now` | Agent via `erk exec marker create` | Allow exit                   | One-time  |
| `objective-context`                 | `/erk:objective-next-plan`         | Suggests `--objective-issue` | One-time  |

**Reusable markers** persist across hook invocations (not deleted when read).
**One-time markers** are consumed (deleted) after being processed.

### Layer 2: Command-Level Deduplication

Even if hooks fail, `plan-save-to-issue` checks for existing saved issues:

1. Before creating an issue, check if this session already saved a plan
2. Use `_get_existing_saved_issue()` helper to query GitHub
3. If found, return existing issue instead of creating duplicate

## Marker Lifecycle

### One-Time Markers

```
Created → Read by hook → Deleted immediately
```

Used for: `implement-now`, `objective-context`, `incremental-plan`

These represent decisions that should only be acted upon once.

### Reusable Markers

```
Created → Read by hook → Persists → Can be read again
```

Used for: `plan-saved`

The `plan-saved` marker persists because it represents a state ("plan has been saved") not an action. If the session continues after saving, subsequent ExitPlanMode calls should still know the plan was saved.

## Critical Persistence Behavior

**NEVER delete `plan-saved` marker when blocking exit.** This marker must persist because:

1. User may continue working in plan mode after saving
2. Subsequent ExitPlanMode calls need to know plan is already saved
3. Deleting it would allow the same plan to be saved again

The `plan-saved` marker is only relevant for the hook's decision-making. It doesn't prevent the user from creating a new plan in a new session.

## \_get_existing_saved_issue() Pattern

The command-level deduplication uses this pattern:

```
1. Extract session ID from request
2. Query GitHub for issues created in this session
3. Check plan-header metadata for session_id match
4. Return existing issue number if found, None otherwise
```

This provides a safety net even if marker state becomes corrupted.

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Overall plan creation flow
- [Erk Hooks](../hooks/erk.md) - Hook implementation details
- [Scratch Storage](scratch-storage.md) - Where markers are stored
