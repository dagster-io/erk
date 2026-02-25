# Remove "active" special case in head-state column

## Context

The head-state column in the objectives TUI maps `in_progress` → `"active"` via a special-case dict lookup. All other statuses pass through with underscores replaced by spaces. This inconsistency is unnecessary — just let `in_progress` display as `"in progress"` like everything else.

## Changes

1. **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py:685-687`** — Replace the dict-based mapping with the simple `.replace("_", " ")` fallback:
   ```python
   # Before
   objective_head_state = {"in_progress": "active"}.get(
       min_status, min_status.replace("_", " ")
   )
   # After
   objective_head_state = min_status.replace("_", " ")
   ```

2. **`src/erk/tui/data/types.py:77`** — Update docstring from `"active"` to `"in progress"`

3. **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py:286`** — Update docstring from `"active"` to `"in progress"`

## Verification

- `ruff check` and `ty check` pass
- Search for any remaining references to `"active"` in head-state context
