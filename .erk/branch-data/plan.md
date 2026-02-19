# Fix Remaining Missing Data in Draft PR Plans

## Context

After the previous fix (`f28358b5f`) corrected `created_at`, `author`, and `pr_linkages` for draft-PR-backed plans, two issues remain visible in `erk dash -i`:

1. **"(No plan content found)"** in the plan detail modal for draft PR plans — the body is already extracted but `fetch_plan_content()` doesn't recognize it
2. **`run-id` and `run-state` always "-"** — `DraftPRPlanListService` returns `workflow_runs={}` without looking up workflow runs from plan header metadata

The `local-wt` column showing "-" is expected behavior: draft PR plan branches (`plan-fix-...`) don't match the `P{N}-...` branch pattern used for worktree detection, and no local impl has been run.

---

## Fix 1: Plan Content "(No plan content found)"

**Root cause:** `PlanBodyScreen` calls `fetch_plan_content(plan_id, plan_body)` where `plan_body` is `plan.body`. For draft PR plans, `plan.body` is the _extracted_ plan content (set by `DraftPRPlanListService` via `extract_plan_content(pr.body)`), not the raw PR body with the metadata block. So `extract_plan_header_comment_id(plan_body)` finds no metadata → returns `None` → content shows as not found.

**Fix in:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`, `fetch_plan_content()` (line 388)

When `comment_id is None`, check whether the body contains a `plan-header` metadata block:

- **No metadata block** → `plan_body` IS the plan content (draft PR case) → return it directly (or `None` if empty)
- **Has metadata block but no comment_id** → malformed/old issue → return `None` (existing behavior)

```python
def fetch_plan_content(self, plan_id: int, plan_body: str) -> str | None:
    comment_id = extract_plan_header_comment_id(plan_body)
    if comment_id is None:
        # Draft PR plans: plan_body IS the content (no metadata block present)
        block = find_metadata_block(plan_body, "plan-header")
        if block is None:
            return plan_body if plan_body.strip() else None
        return None
    # Issue-based plans: fetch content from the referenced comment
    ...existing fetch logic...
```

**New import needed** in `real.py`: add `find_metadata_block` to the existing import from `erk_shared.gateway.github.metadata.core` (line 23).

---

## Fix 2: `run-id` / `run-state` Always "-"

**Root cause:** `DraftPRPlanListService.get_plan_list_data()` (line 107 of `src/erk/core/services/plan_list_service.py`) returns `workflow_runs={}` unconditionally. But draft PR plans DO store `last_dispatched_node_id` in their `plan-header` metadata when a workflow run is dispatched.

**Fix:** After the PR loop, extract `last_dispatched_node_id` from `pr_details.body` (the raw PR body, available in the loop) using the already-imported `extract_plan_header_dispatch_info`. Then batch-fetch workflow runs the same way `RealPlanListService` does. Also respect `skip_workflow_runs`.

```python
# In DraftPRPlanListService.get_plan_list_data():
plans = []
pr_linkages: dict[int, list[PullRequestInfo]] = {}
node_id_to_plan: dict[str, int] = {}

for _branch, pr_info in prs.items():
    pr_details = self._github.get_pr(location.root, pr_info.number)
    if isinstance(pr_details, PRNotFound):
        continue
    plan_body = extract_plan_content(pr_details.body)
    plan = pr_details_to_plan(pr_details, plan_body=plan_body)
    plans.append(plan)
    pr_linkages[pr_info.number] = [pr_info]

    # Capture dispatch node_id for workflow run batch fetch
    _, node_id, _ = extract_plan_header_dispatch_info(pr_details.body)
    if node_id is not None:
        node_id_to_plan[node_id] = pr_info.number

    if limit is not None and len(plans) >= limit:
        break

workflow_runs: dict[int, WorkflowRun | None] = {}
if not skip_workflow_runs and node_id_to_plan:
    try:
        runs_by_node_id = self._github.get_workflow_runs_by_node_ids(
            location.root, list(node_id_to_plan.keys())
        )
        for node_id, run in runs_by_node_id.items():
            workflow_runs[node_id_to_plan[node_id]] = run
    except Exception as e:
        logging.warning("Failed to fetch workflow runs: %s", e)

return PlanListData(plans=plans, pr_linkages=pr_linkages, workflow_runs=workflow_runs)
```

**Import needed:** add `import logging` (already present in the file? check — if not, add it).

---

## Files to Modify

1. **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`**
   - Add `find_metadata_block` to import from `erk_shared.gateway.github.metadata.core` (line 23–26)
   - Update `fetch_plan_content()` (line 388–415)

2. **`src/erk/core/services/plan_list_service.py`**
   - Update `DraftPRPlanListService.get_plan_list_data()` (lines 47–108)
   - Add `import logging` if not present
   - The `extract_plan_header_dispatch_info` import is already there (line 17)
   - The `WorkflowRun` import is already there (line 23)

## Tests to Add/Update

**New file: `tests/tui/data/test_fetch_plan_content.py`**
(modeled after `tests/tui/data/test_fetch_objective_content.py`)

- `test_fetch_plan_content_returns_content_from_comment()` — issue-based plan with comment_id, HTTP returns comment → returns content
- `test_fetch_plan_content_draft_pr_body_returned_directly()` — plan_body has no metadata block (draft PR case) → returns body directly without HTTP call
- `test_fetch_plan_content_draft_pr_empty_body_returns_none()` — plan_body is empty/whitespace → returns `None`
- `test_fetch_plan_content_issue_body_missing_comment_id_returns_none()` — body has plan-header block but no comment_id → returns `None`

**Updated file: `tests/unit/services/test_plan_list_service.py`** — add to `TestDraftPRPlanListService`:

- `test_fetches_workflow_runs_from_dispatch_node_id()` — PR body has `last_dispatched_node_id`, workflow run returned
- `test_skip_workflow_runs_flag_respected()` — `skip_workflow_runs=True` skips fetch
- `test_workflow_run_api_failure_returns_empty_runs()` — API failure → still returns plans, empty runs

**Existing test to verify still passes:** `test_populates_pr_linkages_from_plan_pr` asserts `workflow_runs == {}` for PRs without node_id — still correct after fix.

---

## Verification

```bash
# Run targeted tests
uv run pytest tests/tui/data/ tests/unit/services/test_plan_list_service.py -v

# Manual check
erk dash -i  # open plan detail (Enter) → should show plan content
             # run-id/run-state columns should show data for plans with dispatched workflow runs
```
