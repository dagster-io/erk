# Plan: Collapse "implementing"/"implemented" into single "impl" lifecycle stage

**Part of Objective #7978, Node 0.1** (new node to add)

## Context

The lifecycle stage metadata stores `"implementing"` and `"implemented"` as distinct values, but the TUI already displays both as `"impl"` (differentiated only by color). The user wants the underlying metadata to match the display: a single `"impl"` stage with a single color. The draft/published/ready distinction is already conveyed by status indicator emojis (🚧/👀/🚀), so the two-stage split is unnecessary complexity.

## Changes

### 1. Schema: Replace "implementing"/"implemented" with "impl"

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

- Line 404-410: Update `LifecycleStageValue` Literal to replace `"implementing"`, `"implemented"` with `"impl"`
- Line 777: Update `valid_stages` set — replace `"implementing"`, `"implemented"` with `"impl"`

### 2. Display: Single color for "impl", backwards-compat for old values

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`

- Lines 49-51: Change upgrade target from `"implementing"` to `"impl"` (planned + workflow run → impl)
- Lines 38-44: Change inferred stage from `"implemented"` to `"impl"` (non-draft + OPEN PR → impl)
- Lines 54-61: Collapse the two stage branches into one:
  ```python
  if stage in ("impl", "implementing", "implemented"):
      return f"[yellow]{stage}[/yellow]"
  ```
  This handles both the new `"impl"` value and old `"implementing"`/`"implemented"` values on existing PRs. All render as yellow.
- Lines 205-206 in `_build_indicators()`: Replace `is_implementing`/`is_implemented` with single `is_impl`:
  ```python
  is_impl = "impl" in lifecycle_display  # matches "impl", "implementing", "implemented"
  ```
  Then update all references from `is_implementing or is_implemented` to `is_impl`. The rocket emoji logic (line 236) changes from `is_implemented` to `is_impl`.

### 3. Write-sites: Change all metadata writes to "impl"

**File:** `src/erk/cli/commands/exec/scripts/mark_impl_started.py`
- Line 142: `"lifecycle_stage": "implementing"` → `"lifecycle_stage": "impl"`
- Line 154: `"lifecycle_stage": "implementing"` → `"lifecycle_stage": "impl"`

**File:** `src/erk/cli/commands/exec/scripts/impl_signal.py`
- Line 399: `"lifecycle_stage": "implemented"` → `"lifecycle_stage": "impl"`
- Lines 6, 362, 439: Update docstrings/comments

**File:** `src/erk/cli/commands/exec/scripts/handle_no_changes.py`
- Line 248: `"lifecycle_stage": "implemented"` → `"lifecycle_stage": "impl"`
- Line 243: Update comment

### 4. Docstring/comment update

**File:** `src/erk/tui/data/types.py`
- Line 85: Update docstring example from `"implementing"` to `"impl"`

### 5. Tests

**File:** `tests/unit/plan_store/test_lifecycle_display.py`
- All assertions with `"[yellow]impl[/yellow]"` stay as-is (already correct!)
- All assertions with `"[cyan]impl[/cyan]"` change to `"[yellow]impl[/yellow]"` (single color)
- Update `_build_indicators` tests: merge `is_implementing`/`is_implemented` test cases

**File:** `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`
- Line 374: `"implemented"` → `"impl"`

**File:** `tests/unit/cli/commands/exec/scripts/test_mark_impl_started_ended.py`
- Lines 135, 197: `"implementing"` → `"impl"`

**File:** `tests/unit/cli/commands/exec/scripts/test_update_plan_header.py`
- Line 95: `"implementing"` → `"impl"`

## Verification

1. Run lifecycle tests: `pytest tests/unit/plan_store/test_lifecycle_display.py`
2. Run exec script tests: `pytest tests/unit/cli/commands/exec/scripts/`
3. Run TUI tests: `pytest tests/tui/`
4. Visually confirm with `erk dash` — all "impl" PRs should be yellow
