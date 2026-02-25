# Fix: Learn PRs appearing in Planned PRs tab

## Context

The `erk dash` "Planned PRs" tab shows PRs with the `erk-learn` label alongside `erk-plan` PRs. These should be separate — `erk-learn` PRs should only appear in the "Learn" tab (tab 2), not the "Plans" tab (tab 1).

**Root cause:** `PlannedPRBackend.create_plan()` unconditionally adds the `erk-plan` label to every PR it creates (line 367), then adds the caller's labels on top. This means learn plans end up with **three** labels: `erk-planned-pr` + `erk-plan` + `erk-learn`. Since the Plans tab queries for `erk-plan`, learn PRs show up.

**Secondary bug:** `RealPlanDataProvider.fetch_plans()` doesn't pass `exclude_labels` from `PlanFilters` to the plan list service, so the backup client-side filter never fires either.

## Changes

### 1. Fix `PlannedPRBackend.create_plan()` — stop unconditionally adding `erk-plan`

**File:** `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py:366-372`

Replace the hardcoded `erk-plan` label addition with simply applying the labels passed by the caller:

```python
# Before (broken):
# Add erk-plan label
self._github.add_label_to_pr(repo_root, pr_number, _PLAN_LABEL)
# Add any extra labels
for label in labels:
    if label != _PLAN_LABEL:
        self._github.add_label_to_pr(repo_root, pr_number, label)

# After (fixed):
# Add all labels provided by caller
for label in labels:
    self._github.add_label_to_pr(repo_root, pr_number, label)
```

The callers (`plan_save.py:242-247`, `plan_issues.py:146-151`) already correctly build the label list:
- Standard plans: `["erk-planned-pr", "erk-plan"]`
- Learn plans: `["erk-planned-pr", "erk-learn"]`

### 2. Fix `RealPlanDataProvider.fetch_plans()` — pass `exclude_labels` through

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py:143-151`

Add `exclude_labels` to the `get_plan_list_data()` call (defense-in-depth):

```python
plan_data = self._ctx.plan_list_service.get_plan_list_data(
    location=self._location,
    labels=list(filters.labels),
    state=filters.state,
    limit=filters.limit,
    skip_workflow_runs=not needs_workflow_runs,
    creator=filters.creator,
    exclude_labels=list(filters.exclude_labels) if filters.exclude_labels else None,
)
```

### 3. Fix existing PRs — remove `erk-plan` label from learn PRs

Existing learn PRs in the repo currently have both `erk-plan` and `erk-learn` labels. After fixing the code, run a one-time cleanup via `gh` CLI to remove `erk-plan` from any PR that has `erk-learn`:

```bash
gh issue list -l erk-learn,erk-plan --state open --json number -q '.[].number' | \
  xargs -I{} gh issue edit {} --remove-label erk-plan
```

## Verification

1. Run existing tests for `PlannedPRBackend.create_plan`
2. Run existing tests for `RealPlanDataProvider.fetch_plans`
3. After deploying: `erk dash` Plans tab should no longer show learn PRs
4. `erk dash` Learn tab should still show learn PRs
