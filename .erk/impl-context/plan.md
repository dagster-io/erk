# Plan: Rename "plan" terminology to "pr" — Phase 1 (Core Types & Gateway)

**Objective:** #9109 — Rename "plan" terminology to "pr" across all APIs
**Nodes:** 1.1 through 1.8

## Context

Erk's internal APIs use "plan" terminology (PlanService, plan_number, plan_id, etc.) but these entities are actually GitHub draft PRs. This rename aligns internal naming with reality. Phase 1 covers the core type definitions, gateway ABC, and all their direct consumers — the foundational layer that everything else builds on.

This is a massive mechanical rename touching 80+ files across `packages/erk-shared/` and `src/erk/`. All nodes must ship together since changing types without updating consumers would break compilation.

## Implementation Strategy

Use `libcst-refactor` agent for batch renames across many files, supplemented by manual edits for directory renames and complex cases.

## Steps

### Step 1: Rename gateway directory and ABC (Node 1.1)

**Directory rename:** `packages/erk-shared/src/erk_shared/gateway/plan_service/` → `pr_service/`

**Files:** All 4 files in the directory
- `abc.py`: `PlanService` → `PrService`, rename methods and params:
  - `close_plan(plan_id, plan_url)` → `close_pr(pr_number, pr_url)`
  - `dispatch_to_queue(plan_id, plan_url)` → `dispatch_to_queue(pr_number, pr_url)`
  - `fetch_plan_content(plan_id, plan_body)` → `fetch_pr_content(pr_number, pr_body)`
  - `fetch_objective_content(plan_id, plan_body)` → `fetch_objective_content(pr_number, pr_body)`
- `real.py`: `RealPlanService` → `RealPrService`, match new signatures
  - Internal helper `_close_linked_prs_http(plan_id, ...)` → `_close_linked_prs_http(pr_number, ...)`
- `fake.py`: `FakePlanService` → `FakePrService`, match new signatures
  - `_plan_content_by_plan_id` → `_pr_content_by_pr_number`
  - `_objective_content_by_plan_id` → `_objective_content_by_pr_number`
  - `set_plan_content(plan_id, ...)` → `set_pr_content(pr_number, ...)`
  - `set_objective_content(plan_id, ...)` → `set_objective_content(pr_number, ...)`
- `__init__.py`: Update docstring references

### Step 2: Rename plan_store types (Node 1.2)

**File:** `packages/erk-shared/src/erk_shared/plan_store/types.py`
- `Plan.plan_identifier` → `Plan.pr_identifier`
- `CreatePlanResult.plan_id` → `CreatePlanResult.pr_id`
- `PlanNotFound.plan_id` → `PlanNotFound.pr_id`

**File:** `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py`
- `CreatePlanDraftPRResult.plan_number` → `CreatePlanDraftPRResult.pr_number`
- `CreatePlanDraftPRResult.plan_url` → `CreatePlanDraftPRResult.pr_url`

### Step 3: Merge prompt executor types (Node 1.3)

Plans are PRs, so `PlanNumberEvent` and `PrNumberEvent` are the same concept. Similarly, `CommandResult.plan_number` is redundant with `CommandResult.pr_number`.

**File:** `packages/erk-shared/src/erk_shared/core/prompt_executor.py`
- **Delete `PlanNumberEvent`** class entirely
- Remove `PlanNumberEvent` from the `ExecutorEvent` union type
- **Remove `plan_number`** field from `CommandResult`

**File:** `src/erk/core/prompt_executor.py` (real implementation)
- Where `PlanNumberEvent` is yielded (lines 244-245, 273-275), yield `PrNumberEvent` instead
- Remove import of `PlanNumberEvent`

**File:** `src/erk/core/codex_output_parser.py`
- Replace `PlanNumberEvent` usage with `PrNumberEvent`

**File:** `src/erk/cli/output.py`
- Remove `PlanNumberEvent` import and match case
- Remove `plan_number` variable tracking
- Remove `plan_number` from `CommandResult` construction
- Update `format_implement_summary()` to remove "Linked Plan" display (or show it from `pr_number`)

**File:** `src/erk/core/output_filter.py`
- Remove `plan_number` key from `extract_pr_metadata_from_text()` return dict
- Remove `plan_number` from `parse_stream_json_line()` return dict

**File:** `tests/fakes/prompt_executor.py`
- Remove `_simulated_plan_number` and `PlanNumberEvent` usage

### Step 4: Rename output types (Node 1.4)

**File:** `packages/erk-shared/src/erk_shared/output/next_steps.py`
- `PlanNextSteps.plan_number` → `PlanNextSteps.pr_number`
- `format_plan_next_steps_plain(plan_number, ...)` → `format_plan_next_steps_plain(pr_number, ...)`
- `format_next_steps_markdown(plan_number, ...)` → `format_next_steps_markdown(pr_number, ...)`
- Update internal string references: `self.plan_number` → `self.pr_number`

### Step 5: Rename metadata schema fields (Node 1.5)

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

Replace existing `_migrate_issue_number_to_plan_number()` with a unified migration:
```python
def _migrate_to_pr_number(data: dict[str, Any]) -> None:
    """Migrate legacy issue_number or plan_number to pr_number."""
    if "issue_number" in data and "pr_number" not in data:
        data["pr_number"] = data.pop("issue_number")
    if "plan_number" in data and "pr_number" not in data:
        data["pr_number"] = data.pop("plan_number")
```

Update schemas:
- `PlanSchema`: required field `"plan_number"` → `"pr_number"`, call `_migrate_to_pr_number`
- `WorktreeCreationSchema`: optional field `"plan_number"` → `"pr_number"`, call `_migrate_to_pr_number`
- `SubmissionQueuedSchema`: required field `"plan_number"` → `"pr_number"`, call `_migrate_to_pr_number`
- `WorkflowStartedSchema`: required field `"plan_number"` → `"pr_number"`, call `_migrate_to_pr_number`

**Keep as-is:** `PLAN_COMMENT_ID` and `plan_comment_id` in PlanHeaderSchema — these are persisted YAML keys in GitHub issue bodies. Renaming requires a separate data migration.

### Step 6: Rename config field (Node 1.6)

**File:** `packages/erk-shared/src/erk_shared/context/types.py`
- `LoadedConfig.plans_repo` → `LoadedConfig.github_repo`

**File:** `packages/erk-shared/src/erk_shared/config/schema.py`
- Update schema field and CLI key

**File:** `packages/erk-shared/src/erk_shared/context/helpers.py`
- Update references to `plans_repo`

### Step 7: Update gateway implementations (Node 1.7)

Gateway impl files already handled in Step 1. Additionally:
- `packages/erk-shared/src/erk_shared/gateway/gt/types.py`: `PreAnalysisResult.plan_number` → `PreAnalysisResult.pr_number`

### Step 8: Update all importers/consumers (Node 1.8)

Use `libcst-refactor` or `rename-swarm` for mechanical import updates across ~80 files.

**Import path changes:**
- `erk_shared.gateway.plan_service.abc.PlanService` → `erk_shared.gateway.pr_service.abc.PrService`
- `erk_shared.gateway.plan_service.real.RealPlanService` → `erk_shared.gateway.pr_service.real.RealPrService`
- `erk_shared.gateway.plan_service.fake.FakePlanService` → `erk_shared.gateway.pr_service.fake.FakePrService`

**Field access changes** (grep and fix):
- `.plan_identifier` → `.pr_identifier`
- `.plan_id` → `.pr_id` (on CreatePlanResult, PlanNotFound)
- `.plan_number` → `.pr_number` (on CreatePlanDraftPRResult, PlanNextSteps, PreAnalysisResult)
- `.plan_url` → `.pr_url` (on CreatePlanDraftPRResult)
- `.plans_repo` → `.github_repo`

**Key consumer files** (non-exhaustive):
- `src/erk/tui/app.py` — PlanService → PrService
- `src/erk/tui/screens/plan_body_screen.py` — plan_id params → pr_number
- `src/erk/tui/screens/plan_detail_screen.py` — close_plan → close_pr
- `src/erk/tui/operations/workers.py` — _close_plan_async → _close_pr_async
- `src/erk/tui/actions/navigation.py` — action_close_plan → action_close_pr
- `src/erk/tui/data/real_provider.py` — plan_id variables, plan_identifier access
- `src/erk/cli/commands/pr/list_cmd.py` — RealPlanService instantiation
- `src/erk/cli/commands/pr/create_cmd.py` — result.plan_number → result.pr_number
- All ~30 exec scripts that reference plan_number on CreatePlanDraftPRResult
- `src/erk/status/models/status_data.py` — PlanStatus.plan_number → pr_number
- Tests: ~20 test files importing FakePlanService

**Delete imports of removed types:**
- Remove all `PlanNumberEvent` imports (replaced by `PrNumberEvent`)
- Remove `CommandResult.plan_number` accesses

## Execution Approach

1. **Directory rename first** (`git mv plan_service pr_service`)
2. **Delete `PlanNumberEvent`** and remove `plan_number` from `CommandResult`
3. **Batch rename classes** via libcst-refactor: PlanService→PrService, RealPlanService→RealPrService, FakePlanService→FakePrService
4. **Batch rename fields** via libcst-refactor: plan_identifier→pr_identifier, plan_id→pr_id
5. **Batch rename method names**: close_plan→close_pr, fetch_plan_content→fetch_pr_content
6. **Batch rename parameters**: plan_id→pr_number, plan_url→pr_url, plan_body→pr_body
7. **Manual edits** for metadata schema migration function, config changes, and output_filter cleanup
8. **Fix all remaining compilation errors** via ty + grep sweeps

## Verification

1. `make fast-ci` — unit tests pass
2. `ty` — type checker passes (catches missed renames)
3. `ruff check` — no lint errors
4. Grep sweeps for completeness:
   - `grep -r "plan_service" packages/erk-shared/src/` — zero hits
   - `grep -r "PlanService" packages/erk-shared/src/ src/erk/` — zero hits
   - `grep -r "PlanNumberEvent" src/ packages/ tests/` — zero hits
   - `grep -r "\.plan_id\b" packages/erk-shared/src/erk_shared/plan_store/` — zero hits
