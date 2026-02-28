# Plan: Fix consolidated learn plans missing `erk-plan` label and add replan validation

## Context

When `/local:replan-learn-plans` consolidates learn plans via `/erk:replan`, the resulting plan is saved with `--plan-type=learn`, which sets labels to `["erk-pr", "erk-learn"]`. The `erk-consolidated` label is then added. But `erk pr dispatch` requires the `erk-plan` label, so dispatch fails. The user had to manually add `erk-plan` after the fact.

Additionally, there's no validation step at the end of the replan process to catch issues like this before the user tries to dispatch.

## Changes

### 1. Add `erk-plan` label for consolidated plans in `/erk:replan`

**File:** `.claude/commands/erk/replan.md`

In Step 7.4, where `erk-consolidated` is already added for consolidation mode, also add `erk-plan`:

```markdown
4. **If CONSOLIDATION_MODE** (multiple plans consolidated), add labels:
   ```bash
   erk exec add-plan-label <new_plan_number> --label "erk-consolidated"
   erk exec add-plan-label <new_plan_number> --label "erk-plan"
   ```
   The `erk-consolidated` label prevents re-consolidation. The `erk-plan` label makes the plan dispatchable.
```

This ensures consolidated learn plans get three type labels: `erk-learn` (from plan-save), `erk-plan` (for dispatch), and `erk-consolidated` (prevents re-consolidation). The defense-in-depth filtering in the Plans TUI view already handles plans with both `erk-plan` and `erk-learn` — they appear in the Learn tab only, which is correct.

### 2. Add validation step (Step 8) to `/erk:replan`

**File:** `.claude/commands/erk/replan.md`

Add a new Step 8 after Step 7 that validates the new plan is in a healthy state:

```markdown
### Step 8: Validate New Plan

After saving and closing, verify the new plan:

```bash
erk exec get-plan-info <new_plan_number>
```

Check:
- Plan exists and is OPEN
- Has `erk-plan` label (required for dispatch)
- If CONSOLIDATION_MODE: has `erk-consolidated` label
- If IS_LEARN_PLAN: has `erk-learn` label

If any check fails, report the issue and attempt to fix (e.g., add missing label).

Display validation result:
```
✓ Plan #<number> validated: OPEN, labels: [erk-pr, erk-plan, erk-learn, erk-consolidated]
```
```

### 3. Update consolidation-labels doc

**File:** `docs/learned/planning/consolidation-labels.md`

Add a note that consolidated plans also receive `erk-plan` for dispatchability.

## Files to modify

1. `.claude/commands/erk/replan.md` — Add `erk-plan` label in Step 7.4, add Step 8 validation
2. `docs/learned/planning/consolidation-labels.md` — Document that consolidated plans get `erk-plan`

## Verification

1. Read the updated `replan.md` and confirm Step 7.4 adds both `erk-consolidated` and `erk-plan`
2. Read the updated `replan.md` and confirm Step 8 validates the plan state
3. Mentally trace the flow: `/local:replan-learn-plans` → `/erk:replan` with `IS_LEARN_PLAN=true, CONSOLIDATION_MODE=true` → plan-save adds `erk-pr, erk-learn` → Step 7.4 adds `erk-consolidated, erk-plan` → Step 8 validates all four labels present → dispatch succeeds
