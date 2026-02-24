# Plan: Set lifecycle_stage to "impl" in PR submit and rewrite pipelines

> **Replans:** #8005

## Context

When a plan-linked PR is submitted via `erk pr submit` or rewritten via `erk pr rewrite`, the plan's `lifecycle_stage` metadata is not updated. The `/erk:plan-implement` pipeline calls `erk exec impl-signal submitted` to handle this, but direct CLI usage of `erk pr submit` and `erk pr rewrite` leaves plans stuck at earlier stages (e.g., `planned` or `null`).

This plan adds lifecycle_stage updates to both pipelines so that submitting or rewriting a plan-linked PR correctly transitions the plan to `"impl"` stage.

## What Changed Since Original Plan

- **PR #7999** collapsed `"implementing"`/`"implemented"` into a single `"impl"` stage. The canonical value is `"impl"`, NOT `"implementing"`.
- **PR #7992** added `impl_signal.py` with `_signal_submitted()` that sets `lifecycle_stage: "impl"`. This is called from `/erk:plan-implement` and `plan-implement.yml`, but NOT from `erk pr submit` or `erk pr rewrite`.
- The `LifecycleStageValue` type is `Literal["prompted", "planning", "planned", "impl"]` (`schemas.py:404-409`).

## Investigation Findings

### Corrections to Original Plan
- Original plan used `"implementing"` — correct value is `"impl"` per the stage consolidation in PR #7999.
- Draft-PR backend self-reference concern: already handled in `finalize_pr()` lines 700-706. The lifecycle update needs no special handling for draft-PR backend because `update_metadata()` on draft-PR plans is safe (updates metadata within the same PR body).

### Key Architecture Details
- `PlanContext` has `plan_id: str` field — this is the plan identifier needed for `update_metadata()`.
- `ctx.plan_backend` property provides `PlanBackend` (with `get_plan()`, `update_metadata()` methods).
- `header_str(plan.header_fields, LIFECYCLE_STAGE)` reads the current stage.
- `PlanNotFound` type for LBYL check on plan existence.
- Stages earlier than `"impl"`: `{None, "prompted", "planning", "planned"}`.
- Tests use `context_for_test()` with `GitHubPlanStore(issues)` as default plan_store.
- `FakeGitHubIssues` tracks metadata updates via the plan store.

## Implementation Steps

### 1. Add shared helper in `src/erk/cli/commands/pr/shared.py`

Add `maybe_advance_lifecycle_to_impl()` function after the existing helpers (~line 131):

```python
def maybe_advance_lifecycle_to_impl(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_id: str,
    quiet: bool,
) -> None:
```

Logic:
- LBYL: `ctx.plan_backend.get_plan(repo_root, plan_id)` — return early if `PlanNotFound`
- Read current stage: `header_str(plan.header_fields, LIFECYCLE_STAGE)`
- Only update if stage is in `{None, "prompted", "planning", "planned"}`
- Call `ctx.plan_backend.update_metadata(repo_root, plan_id, {"lifecycle_stage": "impl"})`
- Wrap in try/except RuntimeError — log warning via `click.echo` (unless `quiet`), never block submission
- Echo success message unless `quiet`

Imports needed:
- `from erk_shared.gateway.github.metadata.schemas import LIFECYCLE_STAGE`
- `from erk_shared.plan_store.conversion import header_str`
- `from erk_shared.plan_store.types import PlanNotFound`

### 2. Call helper from `finalize_pr()` in `submit_pipeline.py`

In `finalize_pr()` (~line 770, after "PR metadata updated" echo), add:

```python
# Update lifecycle stage for linked plan
if state.plan_context is not None:
    maybe_advance_lifecycle_to_impl(
        ctx,
        repo_root=state.repo_root,
        plan_id=state.plan_context.plan_id,
        quiet=state.quiet,
    )
```

Import `maybe_advance_lifecycle_to_impl` from `erk.cli.commands.pr.shared`.

### 3. Call helper from `_execute_pr_rewrite()` in `rewrite_cmd.py`

In `_execute_pr_rewrite()` (~line 203, after "PR updated" echo), add:

```python
# Update lifecycle stage for linked plan
if plan_context is not None:
    maybe_advance_lifecycle_to_impl(
        ctx,
        repo_root=discovery.repo_root,
        plan_id=plan_context.plan_id,
        quiet=False,
    )
```

Import `maybe_advance_lifecycle_to_impl` from `erk.cli.commands.pr.shared`.

### 4. Add tests for the shared helper

File: `tests/unit/cli/commands/pr/test_lifecycle_update.py`

Tests:
- `test_advances_planned_to_impl` — plan at `"planned"` stage gets updated to `"impl"`
- `test_skips_when_already_impl` — plan already at `"impl"` is not updated (idempotent)
- `test_skips_when_plan_not_found` — `PlanNotFound` result causes graceful return
- `test_skips_when_no_stage` — plan with `None` stage gets updated to `"impl"`
- `test_graceful_on_runtime_error` — `RuntimeError` from `update_metadata` is caught, no crash

### 5. Add test for `finalize_pr` lifecycle update

File: `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`

Add one test:
- `test_updates_lifecycle_stage_for_linked_plan` — finalize_pr with a `PlanContext` triggers lifecycle update. Create plan issue in `FakeGitHubIssues` with `lifecycle_stage: "planned"`, verify it becomes `"impl"`.

### 6. Add test for `_execute_pr_rewrite` lifecycle update

File: `tests/commands/pr/test_rewrite.py`

Add one test:
- `test_updates_lifecycle_stage_for_linked_plan` — rewrite with a plan-linked branch triggers lifecycle update.

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/pr/shared.py` | Add `maybe_advance_lifecycle_to_impl()` helper |
| `src/erk/cli/commands/pr/submit_pipeline.py` | Import + call helper in `finalize_pr()` |
| `src/erk/cli/commands/pr/rewrite_cmd.py` | Import + call helper in `_execute_pr_rewrite()` |
| `tests/unit/cli/commands/pr/test_lifecycle_update.py` | New: unit tests for shared helper |
| `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` | Add lifecycle update test |
| `tests/commands/pr/test_rewrite.py` | Add lifecycle update test |

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/pr/test_lifecycle_update.py`
2. Run finalize_pr tests: `pytest tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`
3. Run rewrite tests: `pytest tests/commands/pr/test_rewrite.py`
4. Run type checker: `ty check src/erk/cli/commands/pr/shared.py src/erk/cli/commands/pr/submit_pipeline.py src/erk/cli/commands/pr/rewrite_cmd.py`
5. Run linter: `ruff check src/erk/cli/commands/pr/`
