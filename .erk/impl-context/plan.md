# Clean up impl-context at end of plan-implement

## Context

Currently `.erk/impl-context/` only gets cleaned up during `erk pr submit` (via `cleanup_impl_for_submit` in the submit pipeline). If a user implements via `/erk:plan-implement` but then submits with `gt` or `gh` directly instead of `erk pr submit`, the impl-context directory survives in the repo. Adding cleanup at the end of plan-implement ensures it always gets removed, while the existing submit pipeline cleanup remains idempotent.

## Changes

### 1. Update `.claude/commands/erk/plan-implement.md`

Add a new step between current Step 10 (upload session) and Step 11 (CI) that calls the exec script:

```bash
erk exec cleanup-impl-context
```

This removes `.erk/impl-context/`, stages the deletion, commits, and pushes — all idempotent.

Remove the "CRITICAL: Never delete the impl directory" line from the current Step 11 (renumbered to Step 12), since we now explicitly clean it up.

Renumber Steps 11-13 → 12-14.

### 2. No changes needed elsewhere

- **`cleanup_impl_for_submit`** (`src/erk/cli/commands/pr/submit_pipeline.py:194-211`): Already idempotent — early-returns if directory doesn't exist or isn't tracked. No changes needed.
- **`cleanup_impl_context` exec script** (`src/erk/cli/commands/exec/scripts/cleanup_impl_context.py`): Keep as-is — this is what plan-implement will call.
- **CI workflows**: No changes — they have their own cleanup paths.

## Verification

1. Run `erk implement` on a test plan, confirm `.erk/impl-context/` is removed after implementation completes
2. Run `erk pr submit` after — confirm it succeeds (idempotent, no-ops on missing directory)
3. Run unit tests for `cleanup_impl_context` exec script
