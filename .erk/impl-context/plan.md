# Plan: Update tests for renamed pr/* files (Objective #7724, Node 6.2)

Part of Objective #7724, Node 6.2

## Context

Objective #7724 renames `issue_number` → `plan_number` across the codebase. Node 6.1 (PR #8266) renamed source files in `src/erk/cli/commands/pr/` (dispatch_cmd.py, create_cmd.py, metadata_helpers.py). Node 6.2 completes the phase by updating corresponding tests.

**Key finding:** PR #8266 already updated `tests/commands/pr/test_dispatch.py`, and the other directly corresponding test files (`test_create.py`, `test_rewrite.py`, `test_metadata_helpers.py`, `test_submit*.py`) have no remaining `issue_number` references. They're already clean.

The remaining `issue_number` occurrences in pr-related test files are **all erk_shared dependencies** that cannot be renamed until Phase 9:

| File | Occurrences | Reason cannot rename |
|------|------------|---------------------|
| `tests/commands/pr/test_log.py` | 8 | Keyword args to `erk_shared.gateway.github.metadata.core` functions that still use `issue_number` parameter |
| `tests/commands/pr/test_list.py` | 3 | `.impl/issue.json` JSON keys read by `erk_shared.impl_folder.py` which still expects `"issue_number"` |
| `tests/unit/cli/commands/pr/submit_pipeline/test_prepare_state.py` | 4 | Same `.impl/issue.json` format |
| `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` | 2 | Same `.impl/issue.json` format |

Additionally, `submit_pipeline.py:165` has a local variable `issue_url` that should be renamed to `plan_url` (a node 6.1 leftover).

## Changes

### 1. Rename local variable in submit_pipeline.py
- **File:** `src/erk/cli/commands/pr/submit_pipeline.py`
- **Line 165:** `issue_url` → `plan_url` (and line 170 reference)
- This is a purely internal local variable rename with no test impact

### 2. Verify all pr/ tests pass
- Run tests scoped to pr/ test directories to confirm nothing is broken:
  - `tests/commands/pr/`
  - `tests/unit/cli/commands/pr/`

### 3. Update objective roadmap
- Mark node 6.2 as done since all erk-local test renames are complete
- Note in the action comment that remaining `issue_number` in pr/ test files are erk_shared dependencies deferred to Phase 9

## Verification

```bash
uv run pytest tests/commands/pr/ tests/unit/cli/commands/pr/ -x
```

All tests should pass without changes to test files (since the remaining `issue_number` references correctly match erk_shared's current API).
