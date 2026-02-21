# Fix: `erk one-shot` fails to write dispatch metadata with draft_pr backend

## Context

When running `erk one-shot` with `ERK_PLAN_BACKEND=draft_pr`, the command produces:

```
Warning: Failed to update dispatch metadata: Plan #7713 not found
```

**Root cause:** `one_shot_dispatch.py` creates a skeleton GitHub **issue** (#7713) for branch naming, then creates a draft **PR** (#7714). When it calls `write_dispatch_metadata()`, it passes `issue_number=7713` to `plan_backend.get_plan("7713")`. With the draft_pr backend, `DraftPRPlanBackend.get_plan("7713")` calls `github.get_pr(7713)` — looking for a **PR** #7713. But #7713 is an issue, not a PR, so it returns `PRNotFound` → `PlanNotFound`.

In github backend mode, the skeleton issue IS the plan. In draft_pr mode, the plan is the draft PR, but the one-shot flow doesn't account for this.

## Fix

**File:** `src/erk/cli/commands/one_shot_dispatch.py`

In the dispatch metadata section (lines 295-314), skip the `write_dispatch_metadata()` call when the plan backend is draft_pr. The skeleton issue in draft_pr mode is only used for branch naming — it's not a plan-backend-managed entity, so writing plan dispatch metadata to it is incorrect.

The draft PR (#7714) created by one-shot is a plain draft PR (no plan-header metadata block), so we can't write dispatch metadata to it either. The CI workflow's `register_one_shot_plan.py` handles plan registration as a fallback.

```python
# Lines 295-314: wrap the write_dispatch_metadata call with a backend check
from erk_shared.plan_store import get_plan_backend

if plan_issue_number is not None and get_plan_backend() != "draft_pr":
    # Write dispatch metadata to plan issue (github backend only)
    # In draft_pr mode, the skeleton issue is only for branch naming
    # and has no plan-header metadata block
    try:
        write_dispatch_metadata(...)
    ...
```

The queued event comment (lines 316-339) should still be posted — it uses `ctx.issues.add_comment()` directly (not the plan backend) and works correctly for both backends.

## Verification

1. Run `erk one-shot --dry-run "test prompt"` to verify no regression in dry-run mode
2. Run `erk one-shot "test prompt"` with `ERK_PLAN_BACKEND=draft_pr` — should no longer show the warning
3. Run existing tests: `pytest tests/ -k one_shot`
