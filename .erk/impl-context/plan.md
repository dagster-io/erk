# Extract generic `inject_metadata_block_before_footer` utility

## Context

`ensure_plan_header()` in `planned_pr.py` contains inline footer-separator injection logic that is plan-specific but mechanically generic. The same "inject a metadata block before the `\n---\n` footer" pattern will be needed for objectives and future entity types. This extracts the injection logic into a reusable pure function, then refactors `ensure_plan_header()` to use it.

## Changes

### 1. Add `inject_metadata_block_before_footer()` to `core.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`
**Location:** After `replace_metadata_block_in_body()` (~line 689), before `create_objective_header_block()` (~line 692)

Pure string function — takes `(body: str, rendered_block: str) -> str`. Injects the rendered block before the last `\n---\n` footer separator, or appends if none found. No new imports needed.

### 2. Refactor `ensure_plan_header()` to use it

**File:** `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`

- Add `inject_metadata_block_before_footer` to imports from `erk_shared.gateway.github.metadata.core`
- Replace lines 657-665 (inline footer injection) with:
  ```python
  updated_body = inject_metadata_block_before_footer(result.body, metadata_body)
  ```

### 3. Add unit tests for the new function

**File:** `tests/unit/gateways/github/metadata_blocks/test_block_injection.py` (new)

Test cases:
- Block injected before footer separator
- Block appended when no footer separator
- Uses last separator when multiple exist
- Handles empty body

## Verification

1. Run `pytest tests/unit/gateways/github/metadata_blocks/test_block_injection.py` — new tests pass
2. Run `pytest tests/unit/gateways/github/metadata_blocks/` — all existing metadata tests pass
3. Run `pytest tests/unit/cli/commands/pr/test_metadata_helpers.py` — ensure_plan_header callers still pass
4. Run `make fast-ci` — full fast CI green
