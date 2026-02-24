# Plan: Document Force-Delete Branch Patterns in Land Cleanup

> **Replans:** #8051

## Context

PR #8049 added `force=True` to all four branch cleanup functions in `erk land`. The code is fully merged. This erk-learn plan captures two documentation updates to preserve the design rationale for future agents.

## What Changed Since Original Plan

- PR #8049 is merged (commit `a429b202a`) — all code changes complete
- All four cleanup functions in `land_cmd.py` confirmed using `force=True`
- No corrections to the original plan's technical analysis

## Remaining Gaps

Two documentation sections still need to be written:

1. New section in `docs/learned/erk/branch-cleanup.md`
2. New section in `docs/learned/architecture/branch-manager-abstraction.md`

## Implementation Steps

### Step 1: Add "Force Deletion During Automated Land Cleanup" section to `branch-cleanup.md`

**File:** `docs/learned/erk/branch-cleanup.md`
**Insert after:** "Worktree State After Landing PRs" section (after line 162, before "Common Errors" at line 164)

Content should document:
- Why `force=True` is safe during land cleanup (PR already merged, user confirmed via `cleanup_confirmed`)
- The four cleanup functions by name: `_cleanup_no_worktree()`, `_cleanup_slot_with_assignment()`, `_cleanup_slot_without_assignment()`, `_cleanup_non_slot_worktree()`
- All four use `force=True` at lines 758, 779, 804, 835 of `land_cmd.py`
- Protection gates: `cleanup_confirmed` flag gates 3 of 4 functions; `_ensure_branch_not_checked_out()` called before all deletions
- Contrast with manual `wt delete` which respects user's force flag

### Step 2: Add "Force Parameter Usage Patterns" section to `branch-manager-abstraction.md`

**File:** `docs/learned/architecture/branch-manager-abstraction.md`
**Insert after:** "Error Handling: Mixed Patterns" section (after line 102, before "Sub-Gateway Architecture" at line 104)

Content should document:
- When to use `force=True` vs `force=False`
- Pattern: post-merge automated cleanup = `force=True` (land cleanup, session upload, submit reuse)
- Pattern: user-initiated deletion = respect user's `force` flag (`wt delete`)
- The `-D` vs `-d` git flag mapping in `real.py:59`
- Tripwire reinforcement: always flow `force=force` through all BranchManager layers

### Step 3: Update frontmatter `last_audited` on both files

Update `last_audited` timestamps on both modified docs.

## Verification

- Read both files after editing to confirm sections are well-placed
- Run `make fast-ci` to ensure no formatting/lint issues
