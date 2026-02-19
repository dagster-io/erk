# Fix: Thread `learned_from_issue` and `created_from_workflow_run_url` through draft PR backend

## Context

When `ERK_PLAN_BACKEND=draft_pr`, the plan-save dispatch in `plan_save.py` drops two parameters that are only passed to the issues backend:
- `learned_from_issue` — links learn plans to their parent plan (used for branch auto-detection and parent status updates on land)
- `created_from_workflow_run_url` — backlinks to the CI workflow run that created the plan

This means learn plans saved as draft PRs lose their parent link, breaking:
1. Auto-detection of parent branch for stacking (`submit.py:get_learn_plan_parent_branch`)
2. Parent plan status updates when a learn plan lands (`land_pipeline.py:update_learn_plan`)
3. CI workflow backlinks

The metadata infrastructure already supports both fields — `format_plan_header_body()` accepts them and serializes them correctly. The gap is purely in the draft PR dispatch path not passing them through.

## Changes

### 1. `src/erk/cli/commands/exec/scripts/plan_save.py`

**`_save_plan_via_draft_pr()`** (line 257): Add two parameters to signature:
- `learned_from_issue: int | None`
- `created_from_workflow_run_url: str | None`

**`_save_as_draft_pr()`** (line 104): Add same two parameters to signature.

**Metadata dict** (line 184): Add entries:
```python
if learned_from_issue is not None:
    metadata["learned_from_issue"] = learned_from_issue

if created_from_workflow_run_url is not None:
    metadata["created_from_workflow_run_url"] = created_from_workflow_run_url
```

**Dispatch call** (line 422): Pass the two missing params:
```python
_save_plan_via_draft_pr(
    ctx,
    output_format=output_format,
    plan_file=plan_file,
    session_id=session_id,
    objective_issue=objective_issue,
    plan_type=plan_type,
    learned_from_issue=learned_from_issue,
    created_from_workflow_run_url=created_from_workflow_run_url,
)
```

### 2. `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py`

**`create_plan()`** (line 246): Extract new fields from metadata dict and pass to `format_plan_header_body()`:

```python
# After the existing created_from_session extraction (line 295-298):
learned_from_issue_raw = metadata.get(LEARNED_FROM_ISSUE)
learned_from_issue_val: int | None = (
    int(learned_from_issue_raw)
    if learned_from_issue_raw is not None and isinstance(learned_from_issue_raw, (int, str))
    else None
)

created_from_workflow_run_url_raw = metadata.get(CREATED_FROM_WORKFLOW_RUN_URL)
created_from_workflow_run_url_val: str | None = (
    str(created_from_workflow_run_url_raw)
    if created_from_workflow_run_url_raw is not None
    else None
)
```

Then replace the two hardcoded `None` values in the `format_plan_header_body()` call:
- `created_from_workflow_run_url=None` → `created_from_workflow_run_url=created_from_workflow_run_url_val`
- `learned_from_issue=None` → `learned_from_issue=learned_from_issue_val`

**Imports**: Add `LEARNED_FROM_ISSUE` and `CREATED_FROM_WORKFLOW_RUN_URL` to the schemas import.

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/plan_save.py` | Thread params through dispatch + both inner functions + metadata dict |
| `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py` | Extract fields from metadata, pass to `format_plan_header_body()`, add imports |

## Verification

1. Run existing plan_save tests via devrun
2. Run existing draft_pr plan store tests via devrun
3. Run ty type check to confirm signatures align
