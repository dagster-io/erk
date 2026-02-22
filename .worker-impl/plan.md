# Plan: Display Learn Workflow Run URL for All Statuses

## Problem

In `erk plan view`, the Learn section only shows the workflow run URL when `learn_status == "pending"`. When the learn workflow completes (e.g., `completed_no_plan` showing "no insights"), the workflow URL is not displayed even though `learn_run_id` exists in the metadata.

**Current output:**
```
─── Learn ───
Status:      no insights
Plan session: a4e2e616-ded9-4353-8ecd-e54eb6ec17d1
```

**Desired output:**
```
─── Learn ───
Status:      no insights
Workflow:    https://github.com/dagster-io/erk/actions/runs/21287685117
Plan session: a4e2e616-ded9-4353-8ecd-e54eb6ec17d1
```

## Implementation

**File:** `src/erk/cli/commands/plan/view.py`

**Change:** Modify the condition at lines 219-228 to show the workflow URL whenever `learn_run_id` exists, not just when status is "pending".

Current code (lines 219-228):
```python
# Show workflow URL when learn is in progress
if learn_status_val == "pending":
    learn_run_id_raw = header_info.get(LEARN_RUN_ID)
    if learn_run_id_raw is not None and plan_url is not None:
        ...
```

New code:
```python
# Show workflow URL when learn run ID is available
learn_run_id_raw = header_info.get(LEARN_RUN_ID)
if learn_run_id_raw is not None and plan_url is not None:
    owner_repo = extract_owner_repo_from_github_url(plan_url)
    if owner_repo is not None:
        workflow_url = construct_workflow_run_url(
            owner_repo[0], owner_repo[1], str(learn_run_id_raw)
        )
        lines.append(_format_field("Workflow", workflow_url))
```

## Verification

1. Run `erk plan view 5650` and verify the workflow URL appears in the Learn section
2. Test with a plan that has `learn_status == "pending"` to ensure it still displays correctly
3. Test with a plan that has no `learn_run_id` to ensure no errors occur