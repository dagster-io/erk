# Change Learn Plan Labeling: `erk-learn` Only (no `erk-plan`)

## Context

Currently, learn plans get BOTH `erk-plan` AND `erk-learn` labels. This means the Plans tab query (`labels=["erk-plan"]`) returns learn plans too, requiring either client-side filtering or a new `exclude_labels` mechanism to separate them. Changing learn plans to use ONLY `erk-learn` makes the Plans/Learn tab split work naturally via GitHub's label API — no exclusion logic needed.

The user has confirmed that backfilling existing issues is acceptable.

## Summary of Changes

**Label scheme change**: Learn plans → ONLY `erk-learn` (drop `erk-plan`)
**Result**: Plans tab queries `erk-plan`, Learn tab queries `erk-learn` — mutually exclusive, no client-side split needed.

---

## 1. Label Assignment — Stop adding `erk-plan` to learn plans

### `packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py`
- **Lines 140-148**: Change `create_plan_issue` so when `erk-learn` is in `extra_labels`, the base label is `erk-learn` instead of `erk-plan`:
  ```python
  # Current: always starts with erk-plan
  labels = [_LABEL_ERK_PLAN]

  # New: use erk-learn as base if it's a learn plan
  is_learn_plan = extra_labels is not None and _LABEL_ERK_LEARN in extra_labels
  if is_learn_plan:
      labels = [_LABEL_ERK_LEARN]
  else:
      labels = [_LABEL_ERK_PLAN]
  # Then add remaining extra_labels (excluding erk-learn since it's already base)
  ```
- **Line 151**: `is_learn_plan` detection already works (checks for `erk-learn` in labels)

### `src/erk/cli/commands/exec/scripts/plan_save.py`
- **Lines 239-241**: Same pattern — learn plans get ONLY `erk-learn`:
  ```python
  # Current
  labels = ["erk-plan"]
  if plan_type == "learn":
      labels.append("erk-learn")

  # New
  if plan_type == "learn":
      labels = ["erk-learn"]
  else:
      labels = ["erk-plan"]
  ```

## 2. ViewConfig — Learn tab queries `erk-learn`

### `src/erk/tui/views/types.py`
- **Line 44**: Change LEARN_VIEW labels from `("erk-plan",)` to `("erk-learn",)`

## 3. Routing Logic — Handle `erk-learn` in fetch path

### `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`
- **Line 130**: Update routing condition from `if "erk-plan" in filters.labels:` to:
  ```python
  if "erk-plan" in filters.labels or "erk-learn" in filters.labels:
  ```

### `src/erk/tui/app.py`
- **Lines 326-329**: `_filter_rows_for_view` — simplify to a pass-through since server-side filtering now handles the split. Keep the method but make it a no-op (return `rows` for all modes) with a comment that server-side labels handle the split.

### `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`
- **Lines 441-451**: `fetch_plans_for_objective` — currently queries `labels=("erk-plan",)`. This is correct: objective plans screens show implementation plans, not learn plans. No change needed.

## 4. Remove `exclude_labels` (revert in-progress work)

If there are any uncommitted changes adding `exclude_labels`, revert them. The new labeling scheme eliminates the need entirely:
- No `exclude_labels` field on `ViewConfig`
- No `exclude_labels` field on `PlanFilters`
- No `exclude_labels` parameter on service methods or gateway ABCs

## 5. Backfill Script

Create a one-time backfill script (or inline `gh` commands) to fix existing learn plan issues:
1. Find all open issues with BOTH `erk-plan` AND `erk-learn` labels
2. Remove the `erk-plan` label from each

```bash
# Find issues with both labels
gh issue list -l "erk-plan" -l "erk-learn" --state all --json number,title -L 500

# For each: remove erk-plan label
gh issue edit <number> --remove-label "erk-plan"
```

This can be run manually after the code changes land.

## 6. Test Updates

All tests that assert learn plans have `["erk-plan", "erk-learn"]` need updating to `["erk-learn"]` only:

| File | Line(s) | Change |
|------|---------|--------|
| `packages/erk-shared/tests/unit/github/test_plan_issues.py` | 81-88, 478-499, 916 | Assert only `erk-learn` label |
| `packages/erk-shared/tests/unit/integrations/gt/operations/test_finalize.py` | 97 | `["erk-learn"]` |
| `tests/integration/plan_store/test_github_plan_store.py` | 747, 754 | `{"erk-learn"}` / `("erk-learn",)` |
| `tests/commands/dispatch/test_learn_plans.py` | 17, 71, 95, 114 | `["erk-learn"]` |
| `tests/core/test_impl_folder.py` | 525, 534 | `("erk-learn",)` |
| `tests/unit/plan_store/test_planned_pr_backend.py` | 146 | `("erk-learn",)` |
| `tests/unit/cli/commands/init/test_create_plans_repo_labels.py` | 70 | Keep — this tests all labels exist in repo, not on a single issue |
| `tests/unit/cli/commands/land/test_update_parent_learn_status.py` | 98, 143 | `["erk-learn"]` |
| `tests/unit/cli/commands/land/test_learn_status.py` | 247 | `["erk-learn"]` |
| `tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py` | 258 | `["erk-learn"]` |

## 7. Documentation Updates

### `docs/learned/planning/learn-vs-implementation-plans.md`
- **Line 30**: Change table from `erk-plan` + `erk-learn` to just `erk-learn`
- **Line 19**: Update the preamble about shared `erk-plan` label

### `packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py`
- **Line 108**: Update docstring for `extra_labels` parameter

## Code That Already Works (no changes needed)

These all check `"erk-learn" in labels` which continues to work:
- `land_cmd.py:314` — learn plan detection
- `dispatch_cmd.py:56` — `is_learn_plan()` helper
- `complete_cmd.py:50` — learn plan validation
- `finalize.py:39` — learn plan detection in gt operations
- `plan_utils.py:190` — title tag selection
- `real.py:730` — `is_learn_plan` detection in row builder
- `duplicate_check_cmd.py:119` — filtering out learn plans
- `.claude/commands/local/replan-learn-plans.md` — queries `-f labels=erk-learn`

## Verification

1. Run `make fast-ci` to confirm all tests pass
2. Run `erk dash -i` and verify:
   - Plans tab shows only implementation plans
   - Learn tab shows only learn plans
   - Switching tabs triggers separate API calls with correct labels
3. Run the backfill commands against the real repo to migrate existing issues
