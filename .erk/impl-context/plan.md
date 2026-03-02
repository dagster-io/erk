# Plan: Ensure plan-header exists before writing dispatch metadata

## Context

PR #8623 was created through a non-standard path (`/local:replan-learn-plans`) that doesn't go through the standard `PlannedPRBackend.create_plan()` pipeline. As a result, the PR body had no plan-header metadata block. When `erk pr dispatch` ran, `write_dispatch_metadata()` tried to update the plan-header but `update_metadata()` raised `PlanHeaderNotFoundError`. The exception was caught silently by a broad `except Exception` handler, so dispatch appeared to succeed but the metadata was never written. Consequently, `erk dash` couldn't find the run-id association and showed `–`.

**Goal:** When dispatching a plan that lacks a plan-header, automatically create a minimal plan-header block before writing dispatch metadata. This ensures all dispatch paths produce working metadata regardless of how the PR was created.

## Implementation

### 1. Add `ensure_plan_header()` to PlanBackend ABC

**File:** `packages/erk-shared/src/erk_shared/plan_store/backend.py`

Add abstract method:

```python
@abstractmethod
def ensure_plan_header(self, repo_root: Path, plan_id: str) -> None:
    """Ensure plan has a plan-header metadata block.

    If the plan already has a plan-header, this is a no-op.
    If missing, creates a minimal plan-header with required fields
    (schema_version, created_at, created_by) and injects it.

    Args:
        repo_root: Repository root directory
        plan_id: Provider-specific identifier

    Raises:
        RuntimeError: If plan not found
    """
    ...
```

### 2. Implement in PlannedPRBackend

**File:** `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`

Add implementation that:
1. Fetches PR details via `self._github.get_pr()`
2. Checks if plan-header block exists via `find_metadata_block(result.body, "plan-header")`
3. If exists → return (no-op)
4. If missing → create minimal plan-header using `format_plan_header_body()` with:
   - `created_at` from `pr_details.created_at` (use PR creation time, not current time)
   - `created_by` from `pr_details.author` (PR author, not current user)
   - All optional fields as None
5. Inject the metadata block into the PR body before the footer separator (`\n---\n`). If no footer, append to end.
6. Update PR body via `self._github.update_pr_body()`

Key functions to reuse:
- `format_plan_header_body()` from `erk_shared/gateway/github/metadata/plan_header.py:205`
- `find_metadata_block()` from `erk_shared/gateway/github/metadata/core.py:607`
- PR footer splitting: `body.rsplit("\n---\n", 1)`

### 3. Update `write_dispatch_metadata()` to call ensure first

**File:** `src/erk/cli/commands/pr/metadata_helpers.py`

In `write_dispatch_metadata()`, add `plan_backend.ensure_plan_header(repo_root, str(plan_number))` before the `plan_backend.update_metadata()` call. This way the header is guaranteed to exist before the update.

### 4. Simplify `maybe_update_plan_dispatch_metadata()` guards

**File:** `src/erk/cli/commands/pr/metadata_helpers.py`

Replace the manual incomplete-header guards (lines 89-104) with a call to `ensure_plan_header()`. The flow becomes:
1. Resolve plan ID for branch → return if None
2. Get node_id → return if None
3. `ctx.plan_backend.ensure_plan_header(repo.root, plan_id)` → creates if missing
4. `ctx.plan_backend.update_metadata(...)` → now safe

### 5. Tests

**File:** `tests/unit/cli/commands/pr/test_metadata_helpers.py` (extend existing)

Add tests:
- `test_ensure_plan_header_creates_when_missing` — PR with no plan-header gets one created
- `test_ensure_plan_header_noop_when_exists` — PR with existing plan-header is unchanged
- `test_write_dispatch_metadata_succeeds_without_plan_header` — new test verifying the full dispatch path works when plan-header is initially missing
- `test_maybe_update_creates_header_when_missing` — `maybe_update_plan_dispatch_metadata` now succeeds when plan-header missing (instead of skipping)

**File:** Add `ensure_plan_header` tests to an appropriate location (could be in `tests/unit/plan_store/` if that exists, or in the metadata_helpers test file).

Test patterns from existing tests:
- Use `create_plan()` and `create_plan_store_with_plans()` from conftest
- Create plans with `body=` that has no plan-header metadata block (just plain content)
- Verify `fake_github.updated_pr_bodies` was called with body containing plan-header block

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/backend.py` | Add `ensure_plan_header()` abstract method |
| `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` | Implement `ensure_plan_header()` |
| `src/erk/cli/commands/pr/metadata_helpers.py` | Call ensure before update in both functions |
| `tests/unit/cli/commands/pr/test_metadata_helpers.py` | Add tests for new behavior |

## Verification

1. Run existing metadata_helpers tests: `uv run pytest tests/unit/cli/commands/pr/test_metadata_helpers.py`
2. Run dispatch tests: `uv run pytest tests/commands/dispatch/`
3. Run plan store tests: `uv run pytest tests/unit/` (scoped to plan store if exists)
4. Run `make fast-ci` for full validation
