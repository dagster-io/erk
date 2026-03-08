# Plan: Structured Per-PR Reconcile Report (Objective #8950, Node 3.1)

## Context

The `erk reconcile` command currently reports per-PR results with simple boolean flags (`learn_created`, `objective_updated`, `cleaned_up`) and a single error string. This loses important information: *why* a step was skipped (no plan linked, learn plan already exists, no objective, no erk-pr label) and per-step failure details. Node 3.1 replaces this with structured per-step results showing done/skipped/failed status with reasons.

**Dependency:** This builds on Phase 2 (PR #8957) which adds idempotency guards and label stamping. Must be stacked on or merged after #8957.

## Changes

### 1. Define `StepResult` type in `reconcile_pipeline.py`

Add `StepStatus` literal and `StepResult` frozen dataclass alongside existing types:

```python
StepStatus = Literal["done", "skipped", "failed"]

@dataclass(frozen=True)
class StepResult:
    status: StepStatus
    reason: str | None  # Required for skipped/failed, None for done

def step_done() -> StepResult:
    return StepResult(status="done", reason=None)

def step_skipped(*, reason: str) -> StepResult:
    return StepResult(status="skipped", reason=reason)

def step_failed(*, reason: str) -> StepResult:
    return StepResult(status="failed", reason=reason)
```

### 2. Replace `ReconcileResult` fields

```python
@dataclass(frozen=True)
class ReconcileResult:
    branch: str
    pr_number: int
    learn: StepResult
    objective: StepResult
    label: StepResult
    cleanup: StepResult

    @property
    def has_failure(self) -> bool:
        return any(s.status == "failed" for s in (self.learn, self.objective, self.label, self.cleanup))
```

### 3. Add `LearnOutcome` return type in `land_learn.py`

```python
LearnOutcome = Literal["created", "skipped_no_material", "skipped_erk_learn", "skipped_already_exists", "skipped_config_disabled"]
```

Change `_create_learn_pr_for_merged_branch` to return `LearnOutcome` instead of `None`. Map each early-return path to the appropriate outcome string. Also update `_create_learn_pr_core` to return `LearnOutcome`.

Only `reconcile_pipeline.py` calls `_create_learn_pr_for_merged_branch`, so this is safe.

### 4. Refactor `process_merged_branch()` in `reconcile_pipeline.py`

Replace boolean tracking with `StepResult` construction per step:

- **Learn**: LBYL for `skip_learn` flag and `plan_id is None` → `step_skipped`. Otherwise call function and map `LearnOutcome` to `StepResult`. Catch exceptions → `step_failed`.
- **Objective**: LBYL for `objective_number is None` → `step_skipped`. Otherwise try → `step_done` / catch → `step_failed`.
- **Label**: LBYL for `has_pr_label` check (Phase 2 code) → `step_skipped` if no `erk-pr` label. Otherwise try add label → `step_done` / catch → `step_failed`.
- **Cleanup**: try → `step_done` / catch → `step_failed`.
- **Dry run**: All steps `step_skipped(reason="dry run")`.

Add a helper to map `LearnOutcome` to skip reason strings:
```python
_LEARN_SKIP_REASONS: dict[str, str] = {
    "skipped_no_material": "no session material found",
    "skipped_erk_learn": "plan is an erk-learn (cycle prevention)",
    "skipped_already_exists": "learn plan already exists",
    "skipped_config_disabled": "learn plans disabled in config",
}
```

### 5. Update `_display_results()` in `reconcile_cmd.py`

Per-step detail under each branch:

```
Reconciliation complete:

  feature-1  #100
    learn      done
    objective  skipped  (no linked objective)
    label      done
    cleanup    done

2 branch(es) reconciled. 0 failed.
```

Color: green for done, yellow for skipped, red for FAILED. Reason in parentheses.

### 6. Update existing tests in `tests/commands/test_reconcile.py`

Migrate all `ReconcileResult` assertions:
- `result.learn_created is False` → `result.learn.status == "skipped"`
- `result.cleaned_up is True` → `result.cleanup.status == "done"`
- `result.error is None` → `not result.has_failure`

### 7. Add new tests

- `test_step_result_skip_reasons_no_plan_no_objective`: Branch with no plan_id, no objective. Assert learn/objective skipped with correct reasons, cleanup done.
- `test_step_result_learn_failure`: Learn raises → `learn.status == "failed"`, objective/cleanup still proceed.
- `test_step_result_label_skip_no_erk_pr`: PR lacks erk-pr label → `label.status == "skipped"` with reason.
- `test_pr_number_in_result`: Assert `result.pr_number` matches `info.pr_number`.
- `test_display_results_shows_per_step_detail`: CLI integration test with `--force`, assert output contains step status words.

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/reconcile_pipeline.py` | Add `StepStatus`, `StepResult`, helpers. Replace `ReconcileResult`. Refactor `process_merged_branch()`. |
| `src/erk/cli/commands/land_learn.py` | Add `LearnOutcome` type. Change `_create_learn_pr_for_merged_branch` and `_create_learn_pr_core` return types. |
| `src/erk/cli/commands/reconcile_cmd.py` | Rewrite `_display_results()` for per-step output. |
| `tests/commands/test_reconcile.py` | Update existing assertions, add new tests. |
| `tests/unit/cli/commands/test_reconcile_pipeline.py` | Update Phase 2 label tests for new result structure (if exists after #8957 merge). |

## Implementation Order

1. `StepResult` types and helpers in `reconcile_pipeline.py`
2. `ReconcileResult` dataclass replacement
3. `LearnOutcome` return type in `land_learn.py`
4. `process_merged_branch()` refactor
5. `_display_results()` rewrite in `reconcile_cmd.py`
6. Update existing tests
7. Add new tests
8. Run tests via devrun

## Verification

1. Run `devrun` with `uv run pytest tests/commands/test_reconcile.py -v`
2. Run `devrun` with `uv run pytest tests/unit/cli/commands/test_reconcile_pipeline.py -v` (if exists)
3. Run `devrun` with `uv run ty check src/erk/cli/commands/reconcile_pipeline.py src/erk/cli/commands/reconcile_cmd.py src/erk/cli/commands/land_learn.py`
4. Run `devrun` with `uv run ruff check src/erk/cli/commands/reconcile_pipeline.py src/erk/cli/commands/reconcile_cmd.py src/erk/cli/commands/land_learn.py`
