# Fix: run_id shows "-" for implemented plans in erk dash

## Context

`erk dash` shows `-` for `run-id` on plans that were successfully implemented via CI (e.g., PR #8232), even though those PRs have a `**Remotely executed:** [Run #...]` note in the PR body. Meanwhile, plans whose CI run **failed** correctly show the run_id.

This is caused by a string literal mismatch introduced during a backend rename. The Python dispatch code sends `plan_backend = "planned_pr"` when triggering the workflow, but `plan-implement.yml` checks for `"draft_pr"` in two places. This means:

1. `ci-update-pr-body` is always called **without** `--planned-pr` for planned-PR-backed plans
2. Without `--planned-pr`, `ci-update-pr-body` rebuilds the PR body from scratch, **destroying the `plan-header` metadata block**
3. The destroyed plan-header had `last_dispatched_node_id` — the value the TUI uses to batch-query GitHub Actions for run status
4. After body rebuild, `extract_plan_header_dispatch_info()` returns `(None, None, None)` → TUI shows `-`

**Why failed runs show correctly:** The `ci-update-pr-body` step has `continue-on-error: true`. When CI implementation fails, the step's condition `steps.implement.outputs.implementation_success == 'true'` is false, so `ci-update-pr-body` never runs. The plan-header is untouched, so the run_id shows.

## Root Cause: Where the Mismatch Occurs

**What dispatch code sends** (`dispatch_cmd.py:327`, `one_shot_dispatch.py:312`):
```python
"plan_backend": "planned_pr"
```

**What the workflow checks** (`.github/workflows/plan-implement.yml`):
```bash
# Line 152 — error message routing (comment on PR vs issue):
if [ "$ERK_PLAN_BACKEND" = "draft_pr" ]; then

# Line 428 — --planned-pr flag selection (THE CRITICAL ONE):
if [ "${{ inputs.plan_backend }}" = "draft_pr" ]; then
    PLANNED_PR_FLAG="--planned-pr"
fi
```

Both checks fail → `--planned-pr` is never set → `ci-update-pr-body` destroys the plan-header on every successful implementation.

## Fix

Mechanical change: replace `"draft_pr"` with `"planned_pr"` in the two condition checks in `plan-implement.yml`, plus update stale descriptions in `plan-implement.yml`, `one-shot.yml`, and `learn.yml`.

### File: `.github/workflows/plan-implement.yml`

**Change 1 — `workflow_dispatch` input description** (line 41):
```yaml
# Before:
description: "Plan backend type (github or draft_pr)"
# After:
description: "Plan backend type (github or planned_pr)"
```

**Change 2 — `workflow_call` input description** (line 82):
```yaml
# Before:
description: "Plan backend type (github or draft_pr)"
# After:
description: "Plan backend type (github or planned_pr)"
```

**Change 3 — error message routing condition** (line 152):
```bash
# Before:
if [ "$ERK_PLAN_BACKEND" = "draft_pr" ]; then
# After:
if [ "$ERK_PLAN_BACKEND" = "planned_pr" ]; then
```

**Change 4 — `--planned-pr` flag selection** (line 428, the critical fix):
```bash
# Before:
if [ "${{ inputs.plan_backend }}" = "draft_pr" ]; then
# After:
if [ "${{ inputs.plan_backend }}" = "planned_pr" ]; then
```

### File: `.github/workflows/one-shot.yml`

**Change 5 — `plan_backend` input description** (line 48):
```yaml
# Before:
description: "Plan backend type (github or draft_pr)"
# After:
description: "Plan backend type (github or planned_pr)"
```

**Change 6 — `plan_issue_number` description** (line 43):
```yaml
# Before:
description: "Plan entity number: issue number (github backend) or PR number (draft_pr backend)"
# After:
description: "Plan entity number: issue number (github backend) or PR number (planned_pr backend)"
```

### File: `.github/workflows/learn.yml`

**Change 7 — `plan_backend` input description** (line 29):
```yaml
# Before:
description: "Plan backend type (github or draft_pr)"
# After:
description: "Plan backend type (github or planned_pr)"
```

## No Test Changes Required

This is a YAML-only fix. The affected `plan-implement.yml` step logic is tested by CI execution, not by unit tests. There are no tests asserting the string `"draft_pr"` in workflow YAML files.

## Codebase Analysis: Bug Scope

**Scope is LIMITED to workflow YAML files** — Python code is correct throughout:
- ✅ Python code uses `provider="github-draft-pr"` (immutable provider string, correctly preserved per [backend-naming-conventions.md](docs/learned/planning/backend-naming-conventions.md))
- ✅ `dispatch_cmd.py` and `one_shot_dispatch.py` correctly send `plan_backend="planned_pr"`
- ❌ **Only** `.github/workflows/*.yml` files check for the OLD value `"draft_pr"` (4 condition checks, 5 stale descriptions)

This is a renaming artifact: The backend was renamed from the workflow parameter `"draft_pr"` to `"planned_pr"` in Python, but the corresponding workflow YAML checks were not updated.

## Verification

After the fix, the next time a plan is dispatched and successfully implemented via CI:

1. `ci-update-pr-body --planned-pr` will be called (instead of without `--planned-pr`)
2. `extract_plan_header_block(pr_result.body)` will extract the existing plan-header
3. The rebuilt PR body will include the plan-header block at the end
4. `extract_plan_header_dispatch_info()` will return the `last_dispatched_node_id`
5. The TUI batch query will find the workflow run
6. `erk dash` will show the run_id and run status for successfully implemented plans

**Quick verification** after a new plan implementation:
- Check the PR body includes a `<!-- erk:metadata-block:plan-header -->` block
- Check `erk dash` shows run_id for that PR (instead of `-`)
- Confirm "Closes #N" is absent from the footer (since `--planned-pr` suppresses it)
