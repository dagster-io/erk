# Update plan-save output: hierarchical Implement/Checkout format

## Context

The plan-save command's "next steps" output currently uses flat labels ("Checkout:", "Implement:") under "Same slot" / "New slot" section headers. The user wants a hierarchical format grouped by action (Implement first, then Checkout), with "Here" vs "In new wt" as sub-labels, and non-dangerous implement as the default with `(dangerously)` as a nested sub-option.

## Target format

```
Implement plan #8651:
  Here:             source "$(erk br co --for-plan 8651 --script)" && erk implement
    (dangerously):  source "$(erk br co --for-plan 8651 --script)" && erk implement -d
  In new wt:        source "$(erk br co --new-slot --for-plan 8651 --script)" && erk implement
    (dangerously):  source "$(erk br co --new-slot --for-plan 8651 --script)" && erk implement -d

Checkout plan #8651:
  Here:       erk br co --for-plan 8651
  In new wt:  erk br co --new-slot --for-plan 8651

Dispatch to queue: erk pr dispatch 8651
```

This replaces the old "Same slot" / "New slot" section headers and "Local:" / "Implement:" labels. Trunk detection for ordering is removed — the format is the same regardless of branch context.

## Changes

### 1. Update `PlannedPRNextSteps` dataclass
**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py` (lines 44-84)

Add non-dangerous implement properties:
- `implement_here` → `source "$(erk br co --for-plan {N} --script)" && erk implement`
- `implement_here_dangerous` → same but with `-d`
- `implement_new_wt` → `source "$(erk br co --new-slot --for-plan {N} --script)" && erk implement`
- `implement_new_wt_dangerous` → same but with `-d`

Existing properties (`checkout_and_implement`, `checkout_new_slot_and_implement`, `checkout_branch_and_implement`) are only used within next_steps.py, tests, and docs — safe to replace.

### 2. Update `format_planned_pr_next_steps_plain()`
**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py` (lines 108-121)

Rewrite to produce the hierarchical format. Drop trunk-detection parameter (not currently used anyway). The "In Claude Code" / "Dispatch to queue" slash command section stays as-is at the top.

### 3. Update `IssueNextSteps` and `format_next_steps_plain()`
**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py` (lines 7-31, 92-105)

Apply same hierarchical format for consistency. Add same non-dangerous implement properties.

### 4. Update plan-save.md command spec
**File:** `.claude/commands/erk/plan-save.md` (lines 171-220)

Replace the "Slot options block" (lines 171-205) and "Next steps block" (lines 207-220) with the new hierarchical format. Remove trunk detection logic from the spec.

### 5. Update tests
**File:** `packages/erk-shared/tests/unit/output/test_next_steps.py`

- Update existing tests that assert on output format
- Add tests for non-dangerous implement commands
- Add tests for the hierarchical structure (Implement section before Checkout section)

### 6. Update docs/learned references
**Files:**
- `docs/learned/planning/next-steps-output.md` — update property table and format examples
- `docs/learned/conventions.md` (line ~203) — update property name references
- `tests/unit/shared/test_next_steps.py` — update/remove old property tests

## Verification

1. Run tests: `pytest packages/erk-shared/tests/unit/output/test_next_steps.py`
2. Run tests: `pytest tests/unit/shared/test_next_steps.py`
3. Check formatting visually by inspecting the formatted string output in tests
