# Fix: lifecycle_stage never transitions to "implemented" after successful remote implementation

## Context

When a remote implementation completes successfully with code changes, the `lifecycle_stage` in the plan metadata stays at `"planned"` instead of transitioning to `"implemented"`. This causes `erk dash` to show stale status.

**Root cause:** The `plan-implement.yml` workflow has two outcome paths after implementation, but only the no-changes path updates the lifecycle stage:

- **No changes** (line 325-341): Calls `erk exec handle-no-changes` → correctly sets `lifecycle_stage: "implemented"`
- **Has changes** (line 344-451): Goes through submit → mark ready → cleanup → update PR body → trigger CI → **never updates lifecycle_stage**

The `erk exec update-lifecycle-stage` command already exists and handles both issue-based and draft-PR plans. It just isn't being called.

## Fix

**File:** `.github/workflows/plan-implement.yml`

Add a new step after "Trigger CI workflows" (after line 451):

```yaml
- name: Update lifecycle stage to implemented
  if: steps.implement.outputs.implementation_success == 'true' && steps.handle_outcome.outputs.has_changes == 'true' && (steps.submit.outcome == 'success' || steps.handle_conflicts.outcome == 'success')
  env:
    PLAN_ID: ${{ inputs.plan_id }}
  run: |
    erk exec update-lifecycle-stage --plan-id "$PLAN_ID" --stage implemented
```

This uses the same condition as the other success-path steps (Mark PR ready, Clean up staging dirs, Update PR body, Trigger CI).

## Also fix #7717 manually

After the workflow fix, manually update PR #7717:

```bash
erk exec update-lifecycle-stage --plan-id 7717 --stage implemented
```

## Verification

1. Read the workflow YAML to confirm the new step is present with the correct condition
2. Verify by examining a future remote implementation run — the lifecycle stage should transition to "implemented" after successful completion
