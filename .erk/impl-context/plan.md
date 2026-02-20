# Plan: Planned PRs view — rename, lifecycle column, fetch all PR states

## Context

In `draft_pr` mode (`ERK_PLAN_BACKEND=draft_pr`), plans are stored as GitHub draft PRs. Three problems:

1. **Naming**: TUI shows "Plans" everywhere, but they're PRs in this mode
2. **Draft-only filter**: `_parse_plan_prs_with_details()` filters out non-draft PRs, so published/merged PRs disappear from the list
3. **No lifecycle indicator**: No way to see where a planned PR is in the planning → implementation → review → merged lifecycle

## Part 1: Rename "Plans" → "Planned PRs" in draft_pr mode

Thread `plan_backend` from `list_cmd.py` → `ErkDashApp` → child widgets.

### 1a. `src/erk/cli/commands/plan/list_cmd.py` (~line 681)

- Import `get_plan_backend` from `erk_shared.plan_store`
- Pass `plan_backend=get_plan_backend()` to `ErkDashApp`

### 1b. `src/erk/tui/app.py`

- Add `plan_backend: PlanBackendType` param to `__init__` (default `"github"`)
- Store as `self._plan_backend`
- Add `_display_name_for_view(self, mode: ViewMode) -> str`:
  - If `mode == ViewMode.PLANS` and `self._plan_backend == "draft_pr"` → `"Planned PRs"`
  - Otherwise → `get_view_config(mode).display_name`
- Pass resolved `plans_display_name` to `ViewBar` (line 141)
- Loading message (line 143): use `_display_name_for_view(ViewMode.PLANS).lower()`
- Replace all 4 uses of `view_config.display_name.lower()` for status bar noun (lines 252, 395, 660, 678) with `self._display_name_for_view(self._view_mode).lower()`
- Pass `plan_backend` to `PlanDataTable` constructor (line 144)

### 1c. `src/erk/tui/widgets/view_bar.py`

- Add `plans_display_name: str = "Plans"` param to `__init__`
- Store as `self._plans_display_name`
- In `_refresh_display()`: for `ViewMode.PLANS`, use `self._plans_display_name` instead of `config.display_name`

### 1d. `src/erk/tui/widgets/plan_table.py`

- Add `plan_backend: PlanBackendType = "github"` to `__init__`
- In `_setup_columns()` line 143: column header `"pr"` when `draft_pr`, else `"plan"`
- Thread `plan_backend` through `reconfigure()`

## Part 2: Remove draft-only filter (fetch all erk-plan PRs)

### 2a. `packages/erk-shared/src/erk_shared/gateway/github/real.py` (~line 1659)

Remove the client-side draft filter in `_parse_plan_prs_with_details()`:

```python
# REMOVE these lines:
# Client-side draft filter: only include drafts
if not node.get("isDraft", False):
    continue
```

Read actual `isDraft` value from node instead of hardcoding `True`:

- Line 1688: `is_draft=node.get("isDraft", False)` (was `is_draft=True`)
- Line 1712: `is_draft=node.get("isDraft", False)` (was `is_draft=True`)

## Part 3: Lifecycle stage — schema + writes + reads

### 3a. Add `LIFECYCLE_STAGE` to plan-header schema

In `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`:

- Add `"lifecycle_stage"` to `PlanHeaderFieldName` literal type
- Add `LIFECYCLE_STAGE` constant: `"lifecycle_stage"`
- Add to `PLAN_HEADER_OPTIONAL_FIELDS`
- Add validation: must be one of `"pre-plan"`, `"planning"`, `"planned"`, `"implementing"`, `"review"` or null
- Terminal states (`merged`, `closed`) derived from PR state — not stored in header

Valid values and transitions:

```
pre-plan → planning → planned → implementing → review
                                     ↓
                              (merged/closed from PR state)
```

### 3b. Write `lifecycle_stage` at transition points

| Transition            | Where                                                                                             | Value            |
| --------------------- | ------------------------------------------------------------------------------------------------- | ---------------- |
| Plan saved (regular)  | `DraftPRPlanBackend.create_plan()` in `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py` | `"planned"`      |
| One-shot PR created   | `dispatch_one_shot()` in `src/erk/cli/commands/one_shot_dispatch.py`                              | `"pre-plan"`     |
| Planning job starts   | One-shot workflow (write plan-header to PR body)                                                  | `"planning"`     |
| Planning completes    | `register-one-shot-plan` in `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py`         | `"planned"`      |
| Implementation starts | Where `LAST_LOCAL_IMPL_AT` or `LAST_REMOTE_IMPL_AT` is written                                    | `"implementing"` |
| PR marked ready       | Where `mark_pr_ready()` is called                                                                 | `"review"`       |

**Scope note**: For this PR, implement the writes for `plan-save` → `"planned"` and TUI reads with inference fallback. The one-shot dispatch writes (`pre-plan`, `planning`) and implementation/review writes are follow-up — they touch different code paths and can be added incrementally.

### 3c. Preserve `is_draft` and `pr_state` in Plan metadata

In `packages/erk-shared/src/erk_shared/plan_store/conversion.py`, update `pr_details_to_plan()`:

- Add `"is_draft": pr.is_draft` and `"pr_state": pr.state` to the metadata dict

### 3d. Add `lifecycle_display` field to `PlanRowData`

In `src/erk/tui/data/types.py`, add:

- `lifecycle_display: str` — display value for the stage column

### 3e. Compute lifecycle state in `_build_row_data()`

In `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`:

Add `_compute_lifecycle_display(plan: Plan) -> str`:

1. If `is_draft` not in metadata → `"-"` (issue-based plan)
2. If `pr_state == "MERGED"` → `"merged"`
3. If `pr_state == "CLOSED"` → `"closed"`
4. If not `is_draft` → `"review"` (open, non-draft)
5. Read `LIFECYCLE_STAGE` from `header_fields` — if present, use it directly
6. **Fallback inference** (for PRs without `lifecycle_stage` yet):
   - If `header_fields` empty → `"pre-plan"`
   - If `CREATED_FROM_WORKFLOW_RUN_URL` present but no `LAST_DISPATCHED_RUN_ID` → `"planning"`
   - If `LAST_LOCAL_IMPL_AT` or `LAST_REMOTE_IMPL_AT` → `"implementing"`
   - Otherwise → `"planned"`

Import `LIFECYCLE_STAGE`, `CREATED_FROM_WORKFLOW_RUN_URL`, `LAST_DISPATCHED_RUN_ID` from `schemas.py`.

### 3f. Add "stage" column to plan table

In `src/erk/tui/widgets/plan_table.py`, `_setup_columns()`:

- Only in draft_pr mode: add `self.add_column("stage", key="stage")` after the "pr" column

In `_row_to_values()`:

- Only in draft_pr mode: include styled `row.lifecycle_display` in the values tuple
- Colors: `pre-plan` magenta, `planning` magenta, `planned` dim, `implementing` yellow, `review` cyan, `merged` green, `closed` dim red

## Part 4: Update fake provider for tests

In `tests/fakes/plan_data_provider.py`:

- Add `lifecycle_display: str = "-"` to `make_plan_row()` helper

## Files modified

- `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` — add LIFECYCLE_STAGE
- `packages/erk-shared/src/erk_shared/plan_store/conversion.py` — preserve is_draft/pr_state in metadata
- `packages/erk-shared/src/erk_shared/gateway/github/real.py` — remove draft filter, use actual isDraft
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — lifecycle computation
- `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py` — write lifecycle_stage="planned" on create
- `src/erk/cli/commands/plan/list_cmd.py` — pass plan_backend
- `src/erk/tui/app.py` — plan_backend param, display name helper
- `src/erk/tui/widgets/view_bar.py` — plans_display_name override
- `src/erk/tui/widgets/plan_table.py` — column header + stage column
- `src/erk/tui/data/types.py` — lifecycle_display field
- `tests/fakes/plan_data_provider.py` — update fake

## Verification

- `erk dash -i` (no ERK_PLAN_BACKEND) — shows "Plans", no stage column, no regression
- `ERK_PLAN_BACKEND=draft_pr erk dash -i` — shows:
  - Tab bar: `1:Planned PRs  2:Learn  3:Objectives`
  - Loading message: `Loading planned PRs...`
  - Status bar: `N planned prs`
  - Column header: `pr` (not `plan`)
  - New `stage` column with lifecycle states
  - Both draft and non-draft PRs visible
- `pytest tests/tui/`

## Follow-up (not in this PR)

- One-shot dispatch writes `lifecycle_stage: "pre-plan"` to PR body plan-header
- Planning job writes `lifecycle_stage: "planning"` when starting
- `register-one-shot-plan` writes `lifecycle_stage: "planned"` when done
- Implementation start writes `lifecycle_stage: "implementing"`
- `mark_pr_ready` writes `lifecycle_stage: "review"`
