# Plan: Add erk-consolidated Label to Prevent Re-consolidation

## Problem

When `/local:replan-learn-plans` runs:
1. It queries all open issues with the `erk-learn` label
2. `/erk:replan` creates a consolidated plan that **also receives the `erk-learn` label**
3. Running `/local:replan-learn-plans` again picks up the consolidated plan, causing it to be re-consolidated

## Solution

Add a new `erk-consolidated` label to mark plans that are themselves consolidations. This label:
- Gets added by `/erk:replan` when creating a consolidated plan
- Is excluded by `/local:replan-learn-plans` when querying

### Why a Label?

- GitHub's API supports native label filtering
- Labels are visible in the GitHub UI for easy identification
- More robust than parsing issue body content
- Works for any future consolidation workflows (not just learn plans)

## Implementation

### Files to Modify

1. **`.claude/commands/erk/replan.md`** - Add `erk-consolidated` label when creating consolidated plans
2. **`.claude/commands/local/replan-learn-plans.md`** - Exclude issues with `erk-consolidated` label

### Changes to `/erk:replan`

In **Step 7** (Save and Close), after calling `/erk:plan-save`:

**For CONSOLIDATION_MODE only** (multiple plans being consolidated):
```bash
gh issue edit <new_issue_number> --add-label "erk-consolidated"
```

This adds the `erk-consolidated` label to the newly created consolidated plan.

**For single plan replan**: Do NOT add the label (single plan replans are not consolidations).

### Changes to `/local:replan-learn-plans`

In **Step 1**, modify the query to exclude consolidated plans:

**Option A - Two-label exclusion (if GitHub API supports negative filtering):**
Query issues with `erk-learn` but without `erk-consolidated`.

**Option B - Post-filter approach (more reliable):**
1. Fetch issues with `erk-learn` label AND their full label list:
```bash
gh api repos/dagster-io/erk/issues \
  -X GET \
  --paginate \
  -f labels=erk-learn \
  -f state=open \
  -f per_page=100 \
  --jq '.[] | {number, title, created_at, labels: [.labels[].name]}'
```

2. Filter out issues where labels array contains `erk-consolidated`

3. Report to user if any were filtered:
```
Filtered out N already-consolidated plan(s): #X, #Y, ...
```

### Edge Case

If ALL open erk-learn issues have the `erk-consolidated` label:
```
All N open erk-learn plans are already consolidated. Nothing new to consolidate.
```

## Verification

1. Run `/local:replan-learn-plans` with 2+ erk-learn issues
2. Verify the consolidated plan has both `erk-learn` AND `erk-consolidated` labels
3. Run `/local:replan-learn-plans` again
4. Verify the consolidated plan is filtered out and not re-consolidated